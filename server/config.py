"""路径与 AI 接入配置。所有明文数据的落盘位置集中在这里定义。

两种运行形态：
- 源码运行：BASE_DIR = 项目根，资产（prompts/、web/dist）和数据都在项目根下。
- PyInstaller 打包：程序资产随包放在 _internal/（只读），用户数据写在 exe 旁边（可写）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)

if FROZEN:
    # exe 所在目录：用户数据的家（profile/ inbox/ data/ documents/ upskill/ .env）
    BASE_DIR = Path(sys.executable).resolve().parent
    # 打包资产的目录：PyInstaller onedir 模式下是 exe 旁的 _internal/
    ASSET_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent / "_internal"))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    ASSET_DIR = BASE_DIR

PROFILE_DIR = BASE_DIR / "profile"
DATA_DIR = BASE_DIR / "data"
DOCUMENTS_DIR = BASE_DIR / "documents"
APPLICATIONS_DIR = DOCUMENTS_DIR / "applications"
INBOX_DIR = BASE_DIR / "inbox"
STATE_DIR = BASE_DIR / "state"
UPSKILL_DIR = BASE_DIR / "upskill"
ENV_FILE = BASE_DIR / ".env"

# 只读资产随包分发，从 ASSET_DIR 取
PROMPT_DIR = ASSET_DIR / "prompts"
WEB_DIST = ASSET_DIR / "web" / "dist"

TRACKER_CSV = DATA_DIR / "tracker.csv"
SEEN_JOBS_JSON = STATE_DIR / "seen_jobs.json"
INBOX_INDEX_JSON = STATE_DIR / "inbox_index.json"
RANK_MANUAL = DATA_DIR / "rank_manual.md"

AI_KEYS = ("AI_BASE_URL", "AI_API_KEY", "AI_MODEL")
DEFAULT_AI = {
    "AI_BASE_URL": "https://open.bigmodel.cn/api/paas/v4",
    "AI_API_KEY": "",
    "AI_MODEL": "glm-4.7",
}

STATUS_VOCAB = {
    "open": ["drafted", "applied", "interview_1", "interview_2", "interview_3",
             "interview_4", "interview_hr"],
    "final": ["offer", "offer_declined", "rejected", "withdrawn"],
}
ALL_STATUS = STATUS_VOCAB["open"] + STATUS_VOCAB["final"]
# 旧数据兼容（只读展示，不再可选）
LEGACY_STATUS = {"interviewing", "no_response"}


def ensure_dirs() -> None:
    for d in (PROFILE_DIR, DATA_DIR, DOCUMENTS_DIR, APPLICATIONS_DIR, INBOX_DIR, STATE_DIR, UPSKILL_DIR):
        d.mkdir(parents=True, exist_ok=True)


def read_env() -> dict:
    """读取 AI 接入配置：默认值 <- .env <- 环境变量。"""
    vals = dict(DEFAULT_AI)
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() in AI_KEYS:
                    vals[k.strip()] = v.strip()
    for k in AI_KEYS:
        env = os.environ.get(k)
        if env:
            vals[k] = env
    return vals


def write_env(vals: dict) -> None:
    cur = read_env()
    cur.update({k: str(v).strip() for k, v in vals.items() if k in AI_KEYS})
    lines = [f"# AI 接入配置（不进 git）", * [f"{k}={cur[k]}" for k in AI_KEYS]]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
