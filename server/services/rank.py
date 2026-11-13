"""岗位匹配评估（参考 ResumeAgent 的多维评估思路）：
1. 确定性否决先行（外包/加班/档案底线，代码判断不经过 LLM）
2. LLM 四维评估（技能40/经历35/学历15/发展10），每维 score+证据+评价；
   **总分由代码按权重计算，不信任 LLM 算术**；结论（推荐/谨慎/不建议）由总分阈值判定
3. AI 不可用时退到关键词启发式，结果标记 estimated，前端如实提示
"""
from __future__ import annotations

from concurrent.futures import CancelledError
from copy import deepcopy
import json
import re

import threading
import uuid

from server.services import ai, prompts
from server.services.parse import VETO_KEYWORDS
from server.storage.profile import load_candidate

WEIGHTS = {"技能匹配": 0.40, "经历匹配": 0.35, "学历资质": 0.15, "发展匹配": 0.10}
DIM_NAMES = list(WEIGHTS)

EMPLOYMENT_VETO = "外包/劳务派遣 一票否决"
OVERTIME_BANNED = {
    "不接受大小周和996": ("大小周", "996"),
    "可接受大小周，不接受996": ("996",),
}
_SPLIT = re.compile(r"[、，,/;；\s]+")
_VERDICTS = [(75, "推荐投递"), (55, "谨慎投递"), (0, "不建议投递")]

# 批量评估后台任务（进程内）
_BATCH: dict = {}
_BATCH_LOCK = threading.RLock()
_BATCH_CANCEL = {}


def _norm_points(items, limit: int) -> list[str]:
    """规整 AI 返回的亮点/差距：兼容 dict（取 content/text）与 str，剥离首尾空白。"""
    out = []
    for x in (items or [])[:limit]:
        if isinstance(x, dict):
            v = x.get("content") or x.get("text") or " ".join(str(v_) for v_ in x.values())
        else:
            v = str(x)
        v = v.strip()
        if v:
            out.append(v[:400])
    return out


def _keywords(text: str) -> list[str]:
    return [k for k in _SPLIT.split(text.strip()) if 2 <= len(k) <= 12]


def _profile_text(cand: dict) -> str:
    """档案摘要：技能与经历前置（研究方向判断的主要依据），教育/论文/奖项作资历佐证。"""
    lines = [f"技能：" + cand.get("skills", ""),
             f"姓名：{cand.get('name', '')}（{cand.get('identity', '')}）· 城市：{cand.get('city', '')}"
             f" · 期望：{cand.get('target_cities', '')} · 目标类型：{'、'.join(cand.get('target_type', []) or [])}"
             f" · 薪资期望：{cand.get('salary_expect', '')}"]
    for label, key in (("实习", "internship"), ("工作", "work"), ("项目", "project")):
        for e in cand.get(key) or []:
            lines.append(f"- {label}：{e.get('company') or e.get('name', '')} · {e.get('title', '')}{e.get('role', '')}"
                         f"（{e.get('start', '')}~{e.get('end', '') or '至今'}）{e.get('description', '')[:200]}")
    for e in cand.get("education") or []:
        lines.append(f"- 教育：{e.get('school', '')} {e.get('degree', '')} {e.get('major', '')}"
                     f" 排名{e.get('rank_', '') or '未填'}")
    for p in cand.get("publications") or []:
        lines.append(f"- 论文：{p.get('title', '')}（{p.get('level', '')}·{p.get('venue', '')}·{p.get('authors', '')}）")
    for a in cand.get("awards") or []:
        lines.append(f"- 奖项：{a.get('name', '')}（{a.get('level', '')}）")
    return "\n".join(lines)


def _verdict(score: int) -> str:
    for low, v in _VERDICTS:
        if score >= low:
            return v
    return _VERDICTS[-1][1]


def evaluate(entry_text: str, parsed: dict | None = None, cancel_event=None) -> dict:
    """评估一个岗位。返回统一结构：veto / score / verdict / dimensions / strengths / gaps / suggestion / reasons / ai_used / estimated"""
    ai.check_cancelled(cancel_event)
    cand = load_candidate()
    text = entry_text

    # —— 确定性否决（不经过 LLM）——
    veto_hits = [k for k in VETO_KEYWORDS if k in text]
    if veto_hits and cand.get("employment_bottom_line") == EMPLOYMENT_VETO:
        return {"veto": True, "score": 0, "ai_used": False, "estimated": False,
                "reasons": [f"疑似外包/劳务派遣（{'、'.join(veto_hits)}），档案底线为一票否决"]}
    banned = OVERTIME_BANNED.get(cand.get("overtime_tolerance", ""), ())
    ot_hits = [k for k in banned if k in text]
    if ot_hits:
        return {"veto": True, "score": 0, "ai_used": False, "estimated": False,
                "reasons": [f"JD 出现 {'、'.join(ot_hits)}，档案加班容忍度为「{cand['overtime_tolerance']}」"]}
    for kw in _keywords(cand.get("other_vetoes", "")):
        if kw in text:
            return {"veto": True, "score": 0, "ai_used": False, "estimated": False,
                    "reasons": [f"触碰底线：{kw}（档案 · 其他否决项）"]}

    # —— LLM 多维评估 ——
    try:
        result = _ai_evaluate(text, cand, cancel_event=cancel_event)
        result.update({"veto": False, "ai_used": True, "estimated": False})
        return result
    except CancelledError:
        raise
    except Exception:
        ai.check_cancelled(cancel_event)
        result = _heuristic(text, parsed, cand)
        result.update({"veto": False, "ai_used": False, "estimated": True})
        return result


def _ai_evaluate(text: str, cand: dict, cancel_event=None) -> dict:
    prompt = prompts.render("rank-job", profile=_profile_text(cand)[:4000], jd=text[:8000])
    raw = ai.chat([{"role": "user", "content": prompt}], timeout=120, cancel_event=cancel_event)
    start, end = raw.find("{"), raw.rfind("}")
    data = json.loads(raw[start:end + 1])
    dims_in = data.get("dimensions")
    if not isinstance(dims_in, list):
        raise RuntimeError("评估结果缺少 dimensions")
    by_name = {d.get("name"): d for d in dims_in if isinstance(d, dict)}
    dimensions, overall = [], 0.0
    for name in DIM_NAMES:
        d = by_name.get(name) or {}
        score = int(max(0, min(100, round(float(d.get("score", 50))))))
        overall += score * WEIGHTS[name]
        dimensions.append({"name": name, "weight": WEIGHTS[name], "score": score,
                           "evidence": str(d.get("evidence", ""))[:160],
                           "comment": str(d.get("comment", ""))[:160]})
    score = int(round(overall))
    return {
        "score": score,
        "verdict": _verdict(score),
        "dimensions": dimensions,
        "strengths": _norm_points(data.get("strengths"), 5),
        "gaps": _norm_points(data.get("gaps"), 5),
        "suggestion": str(data.get("suggestion", ""))[:200],
        "reasons": [f"四维加权 {score} 分（技能/经历/学历/发展）"],
    }


def _heuristic(text: str, parsed: dict | None, cand: dict) -> dict:
    """无 AI 时的关键词启发式（保留原有逻辑），结果标记 estimated。"""
    reqs = (parsed or {}).get("requirements") or [
        ln for ln in text.splitlines() if re.search(r"(要求|熟悉|精通|掌握|经验)", ln)][:6]
    keywords: list[str] = []
    for ln in reqs:
        keywords += [k for k in _SPLIT.split(re.sub(r"^\d+[.、]\s*", "", ln.strip())) if 2 <= len(k) <= 12]
    keywords = list(dict.fromkeys(keywords))[:20]
    skills = _keywords(cand.get("skills", ""))
    if not skills or not keywords:
        return {"score": 50, "verdict": "谨慎投递", "dimensions": [], "strengths": [], "gaps": [],
                "suggestion": "完善档案技能或重新粘贴 JD 后可用 AI 评估",
                "reasons": ["信息不足，中性分 50（规则估算）"]}
    hit = [k for k in keywords if any(s in k or k in s for s in skills)]
    sc = int(min(40 + 60 * len(hit) / len(keywords), 99))
    return {"score": sc, "verdict": _verdict(sc), "dimensions": [],
            "strengths": [], "gaps": [], "suggestion": "",
            "reasons": [f"关键词命中 {len(hit)}/{len(keywords)}：{'、'.join(hit[:6]) or '无'}（规则估算，建议重试 AI 评估）"]}


def start_batch(ids: list[str]) -> str:
    ids = list(dict.fromkeys(ids))
    task_id = uuid.uuid4().hex[:10]
    event = threading.Event()
    with _BATCH_LOCK:
        _BATCH_CANCEL[task_id] = event
        _BATCH[task_id] = dict(status='running', done=0, total=len(ids), current='', ok=0, failed=0, error=None)

    def run():
        from server.storage import inbox as inbox_store
        try:
            for eid in ids:
                ai.check_cancelled(event)
                try:
                    entry = inbox_store.get_entry(eid)
                    if entry is None:
                        raise ValueError('岗位不存在')
                    with _BATCH_LOCK:
                        ai.check_cancelled(event)
                        _BATCH[task_id]['current'] = f"{entry['company']} · {entry['role']}"
                    result = evaluate(inbox_store.entry_text(eid), entry.get('parsed'), cancel_event=event)
                    details = {k: result.get(k) for k in ('verdict', 'dimensions', 'strengths', 'gaps', 'suggestion', 'estimated')}
                    # Stop and persistence share a lock: late responses cannot write after cancellation.
                    with _BATCH_LOCK:
                        ai.check_cancelled(event)
                        inbox_store.update_entry(eid, score=result['score'], veto=result['veto'], reasons=result['reasons'],
                            status='已否决' if result['veto'] else '已评估', rank=details)
                        _BATCH[task_id]['ok'] += 1
                        _BATCH[task_id]['done'] += 1
                except CancelledError:
                    raise
                except Exception:
                    with _BATCH_LOCK:
                        ai.check_cancelled(event)
                        _BATCH[task_id]['failed'] += 1
                        _BATCH[task_id]['done'] += 1
            with _BATCH_LOCK:
                ai.check_cancelled(event)
                _BATCH[task_id].update(status='done', current='')
        except CancelledError:
            pass
        finally:
            with _BATCH_LOCK:
                _BATCH_CANCEL.pop(task_id, None)

    threading.Thread(target=run, daemon=True).start()
    return task_id


def get_batch_task(task_id: str) -> dict | None:
    with _BATCH_LOCK:
        return deepcopy(_BATCH.get(task_id))


def stop_batch(task_id: str) -> dict | None:
    with _BATCH_LOCK:
        task = _BATCH.get(task_id)
        if task and task['status'] == 'running':
            _BATCH_CANCEL[task_id].set()
            task.update(status='cancelled', current='', error=None)
        return deepcopy(task)
