"""面试准备：分层题库生成（后台任务+进度）、模拟面试对话、复盘报告。产物存申请存档目录。"""
from __future__ import annotations

from concurrent.futures import CancelledError
from copy import deepcopy
from server.storage.files import write_json
from server.storage.locking import locked
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path

from server.config import APPLICATIONS_DIR, ensure_dirs
from server.services import ai, prompts
from server.services.rank import _profile_text
from server.storage import inbox as inbox_store
from server.storage import tracker as tracker_store
from server.storage.profile import load_candidate, load_stars

LAYER_NAMES = {"L1": "表述层", "L2": "深挖层", "L3": "压力层", "L4": "映射层"}

# 后台生成任务（进程内）
_GEN_TASKS: dict[str, dict] = {}
_GEN_LOCK = threading.RLock()
_GEN_CANCEL = {}


def _parse_json(raw: str) -> dict:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise RuntimeError("AI 返回内容无法解析，请重试")
    return json.loads(raw[start:end + 1])


def _past_stuck() -> str:
    from server.services import debrief as debrief_svc
    stuck = debrief_svc.all_stuck_points()
    if not stuck:
        return "（暂无历史复盘数据）"
    return "\n".join(f"- {s['question'][:80]}（{s['date']}）" for s in stuck[:8])


def _archive(company: str, role: str) -> Path:
    ensure_dirs()
    return APPLICATIONS_DIR / f"{company}_{role}"


def _find_jd(company: str, role: str) -> str:
    for e in inbox_store.list_entries():
        if e["company"] == company and (not role or e["role"] == role):
            return inbox_store.entry_text(e["id"])
    return "（未找到原始 JD，按岗位名与公司常识出题）"


def _stars_text() -> str:
    stars = load_stars()
    if not stars:
        return "（暂无，答题要点直接依据档案生成）"
    return "\n".join(f"- {s['title']}：{s['content'][:150]}（来源：{s['source']}）" for s in stars)


def generate_prep(company: str, role: str, cancel_event=None, persist=True) -> dict:
    ai.check_cancelled(cancel_event)
    cand = load_candidate()
    prompt = prompts.render("interview-prep", profile=_profile_text(cand)[:4000],
                            company=company, role=role,
                            jd=_find_jd(company, role)[:6000], stars=_stars_text(),
                            past_stuck=_past_stuck())
    data = _parse_json(ai.chat([{"role": "user", "content": prompt}], timeout=180, cancel_event=cancel_event))
    questions = [q for q in data.get("questions", []) if isinstance(q, dict) and q.get("question")]
    for q in questions:
        q["layer"] = q.get("layer") if q.get("layer") in LAYER_NAMES else "L2"
        q["question"] = ai.plain_math(str(q.get("question", "")))
        q["intent"] = ai.plain_math(str(q.get("intent", "")))
        q["answer_points"] = [ai.plain_math(str(x)) for x in (q.get("answer_points") or [])][:6]
        q["insight_points"] = [ai.plain_math(str(x)) for x in (q.get("insight_points") or [])][:2]
        q["followups"] = [ai.plain_math(str(x)) for x in (q.get("followups") or [])][:3]
    if len(questions) < 6:
        raise RuntimeError("AI 生成的题目过少，请重试")
    prep = {"company": company, "role": role,
            "checklist": [str(x) for x in (data.get("checklist") or [])][:5],
            "questions": questions}
    ai.check_cancelled(cancel_event)
    if persist:
        write_json(_archive(company, role) / "prep.json", prep)
    return prep


def _mock_path(company: str, role: str) -> Path:
    return _archive(company, role) / "mock_interview.json"


@locked
def save_mock(company: str, role: str, history: list[dict], report: dict) -> dict:
    """持久化模拟面试会话（追加式 sessions 数组）。"""
    p = _mock_path(company, role)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"sessions": []}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {"sessions": []}
    session = {
        "id": uuid.uuid4().hex[:10],
        "date": datetime.now().isoformat(timespec="seconds"),
        "rounds": sum(1 for h in history if h["role"] == "candidate"),
        "history": history,
        "report": report,
    }
    data.setdefault("sessions", []).append(session)
    write_json(p, data)
    return session


@locked
def list_mocks(company: str, role: str) -> list[dict]:
    p = _mock_path(company, role)
    if not p.exists():
        return []
    try:
        return [{"id": s_["id"], "date": s_["date"], "rounds": s_["rounds"],
                 "overall": (s_.get("report") or {}).get("overall"),
                 "history": s_.get("history", []), "report": s_.get("report")}
                for s_ in json.loads(p.read_text(encoding="utf-8")).get("sessions", [])]
    except (json.JSONDecodeError, OSError):
        return []


@locked
def delete_mock(company: str, role: str, session_id: str) -> bool:
    """仅删除指定申请下的一场模拟记录，不修改准备包或其他场次。"""
    path = _mock_path(company, role)
    try:
        path.resolve().relative_to(APPLICATIONS_DIR.resolve())
    except ValueError:
        raise ValueError('申请路径无效')
    if not path.exists():
        return False
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or not isinstance(data.get('sessions'), list):
        raise ValueError('历史记录格式异常，未执行删除')
    sessions = data['sessions']
    if not all(isinstance(item, dict) for item in sessions):
        raise ValueError('历史记录格式异常，未执行删除')
    kept = [item for item in sessions if item.get('id') != session_id]
    if len(kept) == len(sessions):
        return False
    data['sessions'] = kept
    write_json(path, data)
    return True


def start_generation(company: str, role: str) -> str:
    task_id = uuid.uuid4().hex[:10]
    event = threading.Event()
    with _GEN_LOCK:
        _GEN_CANCEL[task_id] = event
        _GEN_TASKS[task_id] = dict(status='running', progress='生成题库中…', company=company, role=role, prep=None, error=None)

    def run():
        try:
            prep = generate_prep(company, role, cancel_event=event, persist=False)
            with _GEN_LOCK:
                ai.check_cancelled(event)
                write_json(_archive(company, role) / 'prep.json', prep)
                _GEN_TASKS[task_id].update(status='done', prep=prep, progress=f"完成，{len(prep['questions'])} 题")
        except CancelledError:
            pass
        except Exception as exc:
            with _GEN_LOCK:
                if not event.is_set():
                    _GEN_TASKS[task_id].update(status='error', error=str(exc)[:200])
        finally:
            with _GEN_LOCK:
                _GEN_CANCEL.pop(task_id, None)

    threading.Thread(target=run, daemon=True).start()
    return task_id


def get_generation_task(task_id: str) -> dict | None:
    with _GEN_LOCK:
        return deepcopy(_GEN_TASKS.get(task_id))


def stop_generation(task_id: str) -> dict | None:
    with _GEN_LOCK:
        task = _GEN_TASKS.get(task_id)
        if task and task['status'] == 'running':
            _GEN_CANCEL[task_id].set()
            task.update(status='cancelled', progress='已停止生成，已有准备包已保留', error=None)
        return deepcopy(task)


def get_prep(company: str, role: str) -> dict | None:
    path = _archive(company, role) / "prep.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_applications() -> list[dict]:
    rows = tracker_store.rows()
    for r in rows:
        r["has_prep"] = (_archive(r["company"], r["role"]) / "prep.json").exists()
    return rows


def _brief_jd(company: str, role: str) -> str:
    return _find_jd(company, role)[:1500]


def mock_turn(company: str, role: str, job_type: str, round_hint: str,
              history: list[dict]) -> dict:
    turns = "\n".join(f"{'面试官' if h['role'] == 'interviewer' else '候选人'}：{h['text']}"
                      for h in history[-14:])
    prompt = prompts.render("mock-interview", company=company, role=role, job_type=job_type,
                            round_hint=round_hint,
                            profile=_profile_text(load_candidate())[:2500],
                            jd=_brief_jd(company, role), history=turns or "（面试刚开始）")
    data = _parse_json(ai.chat([{"role": "user", "content": prompt}], timeout=120))
    return {"question": ai.plain_math(str(data.get("question", ""))), "end": bool(data.get("end"))}


def mock_report(company: str, role: str, history: list[dict]) -> dict:
    """逐题深度分析：每道回答过的问题独立打分（分数由代码判定档位，不信任 LLM 算术）。"""
    turns = "\n".join(f"{'面试官' if h['role'] == 'interviewer' else '候选人'}：{h['text']}"
                      for h in history)
    prompt = prompts.render("mock-report", company=company, role=role, history=turns[:8000])
    data = _parse_json(ai.chat([{"role": "user", "content": prompt}], timeout=180))

    def _flag(v) -> bool:
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("true", "yes", "是")

    per_question = []
    for q in (data.get("per_question") or [])[:12]:
        if not isinstance(q, dict) or not q.get("question"):
            continue
        score = int(max(0, min(100, float(q.get("score", 0) or 0))))
        per_question.append({
            "question": ai.plain_math(q.get("question", ""))[:160],
            "answer_summary": ai.plain_math(q.get("answer_summary", ""))[:300],
            "score": score,
            "verdict": "出色" if score >= 80 else ("达标" if score >= 60 else "需改进"),
            "highlights": [ai.plain_math(x)[:200] for x in (q.get("highlights") or []) if str(x).strip()][:3],
            "problems": [ai.plain_math(x)[:200] for x in (q.get("problems") or []) if str(x).strip()][:3],
            "off_topic": _flag(q.get("off_topic")),
            "missed_key_points": _flag(q.get("missed_key_points")),
            "wrong_facts": _flag(q.get("wrong_facts")),
            "better_answer": [ai.plain_math(x)[:300] for x in (q.get("better_answer") or []) if str(x).strip()][:4],
        })
    # 整体分 = AI 整体印象 40% + 逐题均分 60%（逐题分数是用户最关心的信号）
    ai_overall = int(max(0, min(100, float(data.get("overall", 60) or 60))))
    overall = ai_overall
    if per_question:
        avg = sum(q["score"] for q in per_question) / len(per_question)
        overall = int(round(ai_overall * 0.4 + avg * 0.6))
    return {
        "overall": overall,
        "per_question": per_question,
        "strengths": [ai.plain_math(x) for x in (data.get("strengths") or [])][:3],
        "weaknesses": [ai.plain_math(x) for x in (data.get("weaknesses") or [])][:3],
        "off_topic": _flag(data.get("off_topic")),
        "missed_key_points": _flag(data.get("missed_key_points")),
        "wrong_facts": _flag(data.get("wrong_facts")),
        "stuck_points": [ai.plain_math(x) for x in (data.get("stuck_points") or [])][:5],
        "advice": ai.plain_math(data.get("advice", ""))[:300],
    }
