"""数据重置：按模块清点与批量清空。红线：documents/backup/（真实档案备份）与 .env 永不触碰。"""
from __future__ import annotations

import shutil

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.config import (APPLICATIONS_DIR, DATA_DIR, DOCUMENTS_DIR, INBOX_DIR,
                           INBOX_INDEX_JSON, RANK_MANUAL, SEEN_JOBS_JSON,
                           TRACKER_CSV, UPSKILL_DIR, ensure_dirs)
from server.storage import inbox as inbox_store
from server.storage import tracker as tracker_store

router = APIRouter(prefix="/reset", tags=["reset"])

PROFILE_CANDIDATE = DOCUMENTS_DIR.parent / "profile" / "candidate.json"
PROFILE_STARS = DOCUMENTS_DIR.parent / "profile" / "stars.json"
CALIBRATION_DIR = DOCUMENTS_DIR / "calibration"
UPLOADS_DIR = DOCUMENTS_DIR / "uploads"
CV_DIR = DOCUMENTS_DIR / "cv"
LOGOS_DIR = DATA_DIR / "logos"


def _dir_files(d) -> int:
    return sum(1 for p in d.iterdir() if p.is_file()) if d.is_dir() else 0


def _subdirs(d) -> int:
    return sum(1 for p in d.iterdir() if p.is_dir()) if d.is_dir() else 0


def inventory() -> list[dict]:
    """按模块清点可重置数据（供前端勾选展示）。"""
    ensure_dirs()
    try:
        inbox_count = len(inbox_store.list_entries())
    except Exception:
        inbox_count = 0
    try:
        tracker_count = len(tracker_store.rows())
    except Exception:
        tracker_count = 0
    cand_name = ""
    try:
        import json
        if PROFILE_CANDIDATE.exists():
            cand_name = json.loads(PROFILE_CANDIDATE.read_text(encoding="utf-8")).get("name", "")
    except Exception:
        pass
    try:
        stars_count = len([s for s in __import__("json").loads(
            PROFILE_STARS.read_text(encoding="utf-8"))]) if PROFILE_STARS.exists() else 0
    except Exception:
        stars_count = 0
    return [
        {"key": "profile", "label": "个人档案", "desc": "候选人档案与面试素材库（星空 STAR）",
         "detail": f"候选人：{cand_name or '空'} · 素材 {stars_count} 条",
         "count": (1 if PROFILE_CANDIDATE.exists() else 0) + (1 if PROFILE_STARS.exists() else 0) + stars_count},
        {"key": "inbox", "label": "岗位收集", "desc": "贴入的 JD 记录与候选池标记（含收藏/评估结果）",
         "detail": f"{inbox_count} 条收集记录",
         "count": inbox_count},
        {"key": "tracker", "label": "投递跟踪", "desc": "投递流水账（申请记录与状态流转）",
         "detail": f"{tracker_count} 条投递记录",
         "count": tracker_count},
        {"key": "applications", "label": "面试存档", "desc": "每个申请的准备包题库、模拟面试记录、复盘记录",
         "detail": f"{_subdirs(APPLICATIONS_DIR)} 个申请存档",
         "count": _subdirs(APPLICATIONS_DIR)},
        {"key": "upskill", "label": "技能提升", "desc": "学习路线图与打卡进度",
         "detail": f"{_dir_files(UPSKILL_DIR)} 个文件",
         "count": _dir_files(UPSKILL_DIR)},
        {"key": "calibration", "label": "复盘校准", "desc": "评分手册校准区与复盘简报",
         "detail": f"手册校准区{'有' if RANK_MANUAL.exists() else '无'} · 简报 {_dir_files(CALIBRATION_DIR)} 份",
         "count": (1 if RANK_MANUAL.exists() else 0) + _dir_files(CALIBRATION_DIR)},
        {"key": "uploads", "label": "简历与生成稿", "desc": "上传的简历原件与 documents/cv 下的底稿",
         "detail": f"上传 {_dir_files(UPLOADS_DIR)} 个 · 底稿 {_dir_files(CV_DIR)} 个",
         "count": _dir_files(UPLOADS_DIR) + _dir_files(CV_DIR)},
        {"key": "cache", "label": "缓存", "desc": "公司 logo 缓存与已见岗位去重标记（可安全删除，自动重建）",
         "detail": f"logo {_dir_files(LOGOS_DIR)} 个",
         "count": _dir_files(LOGOS_DIR) + (1 if SEEN_JOBS_JSON.exists() else 0)},
    ]


def _clear_dir_files(d) -> int:
    n = 0
    if d.is_dir():
        for p in d.iterdir():
            if p.is_file():
                p.unlink()
                n += 1
            elif p.is_dir():
                shutil.rmtree(p)
                n += 1
    return n


_VALID_KEYS = ("profile", "inbox", "tracker", "applications",
               "upskill", "calibration", "uploads", "cache")


def _clear_subdirs(d) -> int:
    n = 0
    if d.is_dir():
        for p in d.iterdir():
            if p.is_dir():
                shutil.rmtree(p)
                n += 1
            elif p.is_file():
                p.unlink()
                n += 1
    return n


def run_reset(keys: list[str]) -> dict:
    unknown = [k for k in keys if k not in _VALID_KEYS]
    if unknown:
        raise HTTPException(status_code=400, detail=f"未知重置项：{', '.join(unknown)}")
    ensure_dirs()
    removed = {}

    if "profile" in keys:
        PROFILE_CANDIDATE.unlink(missing_ok=True)
        PROFILE_STARS.unlink(missing_ok=True)
        removed["profile"] = "候选人档案与面试素材库已清空"

    if "inbox" in keys:
        n = _clear_dir_files(INBOX_DIR)
        INBOX_INDEX_JSON.unlink(missing_ok=True)
        removed["inbox"] = f"已清空 {n} 条 JD 收集记录与候选池标记"

    if "tracker" in keys:
        TRACKER_CSV.unlink(missing_ok=True)
        tracker_store.rows()  # 重建带表头的空流水账
        removed["tracker"] = "投递记录已清空（空表已重建）"

    if "applications" in keys:
        n = _clear_subdirs(APPLICATIONS_DIR)
        removed["applications"] = f"已清空 {n} 个申请存档（题库/模拟面试/复盘）"

    if "upskill" in keys:
        n = _clear_dir_files(UPSKILL_DIR)
        removed["upskill"] = f"已清空 {n} 个学习计划文件"

    if "calibration" in keys:
        RANK_MANUAL.unlink(missing_ok=True)
        n = _clear_dir_files(CALIBRATION_DIR)
        removed["calibration"] = f"已清空评分手册校准区与 {n} 份复盘简报"

    if "uploads" in keys:
        n1 = _clear_dir_files(UPLOADS_DIR)
        n2 = _clear_dir_files(CV_DIR)
        removed["uploads"] = f"已清空 {n1} 个上传简历、{n2} 个底稿"

    if "cache" in keys:
        n = _clear_dir_files(LOGOS_DIR)
        SEEN_JOBS_JSON.unlink(missing_ok=True)
        removed["cache"] = f"已清空 {n} 个 logo 缓存与已见岗位标记"

    return {"removed": removed}


class ResetBody(BaseModel):
    keys: list[str] = []
    confirm: str = ""


@router.get("/inventory")
def reset_inventory():
    return {"groups": inventory()}


@router.post("/run")
def reset_run(body: ResetBody):
    if body.confirm.strip() != "重置":
        raise HTTPException(status_code=400, detail='请输入「重置」二字确认（不可撤销）')
    if not body.keys:
        raise HTTPException(status_code=400, detail="请至少勾选一项要重置的数据")
    return run_reset(body.keys)
