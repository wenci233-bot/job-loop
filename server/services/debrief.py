"""面试复盘：用户记录「面试问题 + 我的回答」→ AI 逐题评价与改进意见 → 落盘 debrief.json（追加式）。"""
from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import datetime
from server.storage.locking import locked
from server.storage.files import write_json
from datetime import date
from pathlib import Path

from server.config import APPLICATIONS_DIR, ensure_dirs
from server.services import ai, prompts
from server.services.interview import _parse_json, _profile_text
from server.storage.profile import load_candidate


def _archive(company: str, role: str) -> Path:
    ensure_dirs()
    return APPLICATIONS_DIR / f"{company}_{role}"


def _rounds_path(company: str, role: str) -> Path:
    return _archive(company, role) / "debrief.json"


def load_rounds(company: str, role: str) -> list[dict]:
    p = _rounds_path(company, role)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("rounds", [])
    except (json.JSONDecodeError, OSError):
        return []


def organize(raw: str) -> dict:
    prompt = prompts.render("debrief-organize", raw=raw[:4000])
    return _parse_json(ai.chat([{"role": "user", "content": prompt}], timeout=120))


def _past_text(exclude_company: str = "", exclude_role: str = "") -> str:
    lines = []
    for archive in APPLICATIONS_DIR.rglob("debrief.json"):
        if archive.parent.relative_to(APPLICATIONS_DIR).as_posix().startswith(f"{exclude_company}_"):
            continue
        try:
            data = json.loads(archive.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for r in data.get("rounds", []):
            for item in r.get("qa", []):
                lines.append(f"- 被问：{str(item.get('question', ''))[:80]}（{archive.parent.relative_to(APPLICATIONS_DIR).as_posix()}）")
    return "\n".join(lines)[:3000] or "（暂无历史复盘）"


def review(company: str, role: str, qa: list[dict], focus: list[str]) -> dict:
    cand = load_candidate()
    qa_text = "\n".join(
        f"{i}、问题：{item.get('question', '')}\n   我的回答：{item.get('answer', '') or '（未记录）'}"
        for i, item in enumerate(qa, 1))
    prompt = prompts.render("debrief-review", company=company, role=role,
                            profile=_profile_text(cand)[:3000],
                            qa=qa_text[:4000], focus="、".join(focus) or "（未记录）",
                            past=_past_text(company, role))
    data = _parse_json(ai.chat([{"role": "user", "content": prompt}], timeout=180))
    per_question = [q for q in (data.get("per_question") or []) if isinstance(q, dict) and q.get("question")]
    for q in per_question:
        q["verdict"] = q.get("verdict") if q.get("verdict") in ("出色", "达标", "需改进") else "达标"
        q["evaluation"] = ai.plain_math(q.get("evaluation", ""))[:400]
        q["improved_points"] = [ai.plain_math(x)[:200] for x in (q.get("improved_points") or [])][:4]
    return {
        "overall": int(max(0, min(100, float(data.get("overall", 60))))),
        "per_question": per_question,
        "strengths": [ai.plain_math(x) for x in (data.get("strengths") or [])][:3],
        "weaknesses": [ai.plain_math(x) for x in (data.get("weaknesses") or [])][:3],
        "star_proposals": [{"title": ai.plain_math(s.get("title", "")),
                            "content": ai.plain_math(s.get("content", ""))}
                           for s in (data.get("star_proposals") or [])[:2] if isinstance(s, dict)],
        "repeated": data.get("repeated", [])[:4],
        "advice": ai.plain_math(data.get("advice", ""))[:300],
    }


@locked
def save_round(company: str, role: str, qa: list[dict], focus: list[str],
               rating: int, note: str, review: dict | None) -> dict:
    dest = _rounds_path(company, role)
    document = _read_rounds_document(dest)
    rounds = document["rounds"]
    entry = {
        "id": uuid.uuid4().hex,
        "round": max((int(r.get("round", 0)) for r in rounds), default=0) + 1,
        "date": date.today().isoformat(),
        "qa": [{"question": str(i.get("question", ""))[:300],
                "answer": str(i.get("answer", ""))[:1000]} for i in qa if i.get("question")],
        "focus": [str(x) for x in focus][:8],
        "rating": int(rating),
        "note": str(note)[:300],
        "review": review,
    }
    rounds.append(entry)
    dest = _rounds_path(company, role)
    dest.parent.mkdir(parents=True, exist_ok=True)
    write_json(dest, document)
    return entry


def all_stuck_points() -> list[dict]:
    """全部历史卡壳/需改进考点（供校准与技能提升使用）。"""
    out = []
    for archive in sorted(APPLICATIONS_DIR.rglob("debrief.json")):
        try:
            data = json.loads(archive.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for r in data.get("rounds", []):
            # 新结构：从 review 的需改进题取；兼容旧结构 stuck
            for q in (r.get("review") or {}).get("per_question", []):
                if q.get("verdict") == "需改进":
                    out.append({"question": str(q.get("question", "")), "gap": "需改进",
                                "source": archive.parent.relative_to(APPLICATIONS_DIR).as_posix(), "date": r.get("date", "")})
            for s in r.get("stuck", []):
                out.append({"question": str(s.get("question", "")), "gap": str(s.get("gap", "")),
                            "source": archive.parent.relative_to(APPLICATIONS_DIR).as_posix(), "date": r.get("date", "")})
    return out


def _read_rounds_document(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'rounds': []}
    if not isinstance(data, dict) or not isinstance(data.get('rounds'), list) or not all(isinstance(r, dict) for r in data['rounds']):
        raise ValueError('历史复盘格式异常，未修改原文件')
    return data


@locked
def import_mock(company: str, role: str, session_id: str) -> dict:
    from server.services import interview
    return _import_mock_at_paths(_rounds_path(company, role), interview._mock_path(company, role), company, role, session_id)


@locked
def _import_mock_at_paths(dest: Path, source_path: Path, company: str, role: str, session_id: str) -> dict:
    from server.services import interview
    for path, root in ((dest, APPLICATIONS_DIR), (source_path, interview.APPLICATIONS_DIR)):
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            raise ValueError('申请路径无效')
    document = _read_rounds_document(dest)
    if session_id in document.get('suppressed_mock_sessions', []):
        raise ValueError('该模拟场次的复盘已删除，不会自动重新导入')
    for entry in document['rounds']:
        if entry.get('source_type') == 'mock_interview' and entry.get('source_session_id') == session_id:
            return {'round': entry, 'duplicate': True}
    if not source_path.exists():
        raise LookupError('模拟面试记录不存在，请刷新列表')
    source = json.loads(source_path.read_text(encoding='utf-8'))
    if not isinstance(source, dict) or not isinstance(source.get('sessions'), list) or not all(isinstance(r, dict) for r in source['sessions']):
        raise ValueError('模拟面试记录格式异常，未执行导入')
    session = next((r for r in source['sessions'] if r.get('id') == session_id), None)
    if session is None:
        raise LookupError('模拟面试记录不存在，请刷新列表')
    report = session.get('report')
    history = session.get('history')
    if not isinstance(report, dict) or not report or not isinstance(history, list):
        raise ValueError('该场记录缺少对话或分析报告，无法导入')
    qa, questions, answers = [], [], []
    def flush():
        if questions and answers:
            qa.append({'question': '\n'.join(questions), 'answer': '\n'.join(answers)})
    for turn in history:
        if not isinstance(turn, dict):
            continue
        text = str(turn.get('text') or '').strip()
        if not text:
            continue
        if turn.get('role') == 'interviewer':
            if answers:
                flush(); questions, answers = [], []
            questions.append(text)
        elif turn.get('role') == 'candidate' and questions:
            answers.append(text)
    flush()
    if not qa:
        raise ValueError('该场记录没有已回答的问答，无法导入')
    review = deepcopy(report)
    per_question = []
    for question in report.get('per_question') or []:
        if not isinstance(question, dict):
            continue
        item = deepcopy(question)
        item['evaluation'] = '\n'.join(
            [str(item.get('evaluation') or '')]
            + ['亮点：' + str(x) for x in item.get('highlights') or []]
            + ['问题：' + str(x) for x in item.get('problems') or []]).strip()
        item['improved_points'] = deepcopy(item.get('better_answer') or item.get('improved_points') or [])
        per_question.append(item)
    review['per_question'] = per_question
    entry = {
        'id': uuid.uuid4().hex,
        'round': max((int(r.get('round', 0)) for r in document['rounds']), default=0) + 1,
        'date': str(session.get('date') or datetime.now().isoformat())[:10],
        'company': company, 'role': role,
        'qa': qa, 'focus': [], 'rating': None,
        'note': '从模拟面试导入，非正式面试记录。',
        'review': review,
        'source_type': 'mock_interview', 'source_session_id': session_id,
        'source_date': session.get('date'), 'imported_at': datetime.now().isoformat(timespec='seconds'),
        'mock_history': deepcopy(history), 'mock_report': deepcopy(report),
    }
    document['rounds'].append(entry)
    write_json(dest, document)
    return {'round': entry, 'duplicate': False}


@locked
def sync_mock_history() -> list[str]:
    """补齐已有模拟面试到复盘存档；重复访问不会产生重复记录。"""
    from server.services import interview
    warnings = []
    for source in sorted(interview.APPLICATIONS_DIR.rglob('mock_interview.json')):
        relative_archive = source.parent.relative_to(interview.APPLICATIONS_DIR)
        dest = APPLICATIONS_DIR / relative_archive / 'debrief.json'
        try:
            document = _read_rounds_document(dest)
            imported = {r.get('source_session_id') for r in document['rounds'] if r.get('source_type') == 'mock_interview'}
            imported.update(document.get('suppressed_mock_sessions', []))
            data = json.loads(source.read_text(encoding='utf-8'))
            if not isinstance(data, dict) or not isinstance(data.get('sessions'), list):
                raise ValueError('模拟记录格式异常')
            sessions = data['sessions']
        except (OSError, ValueError) as exc:
            warnings.append(f'{source.parent.name}：{exc}')
            continue
        for session in sessions:
            if not isinstance(session, dict) or not session.get('id'):
                warnings.append(f'{source.parent.name}：存在缺少编号的模拟记录，未自动导入')
                continue
            if session['id'] in imported:
                continue
            company, _, role = relative_archive.as_posix().partition('_')
            try:
                _import_mock_at_paths(dest, source, session.get('company') or company,
                                      session.get('role') or role, session['id'])
                imported.add(session['id'])
            except (OSError, ValueError, LookupError) as exc:
                warnings.append(f"{source.parent.name} · {session['id']}：{exc}")
    return warnings


@locked
def list_history() -> dict:
    warnings = sync_mock_history()
    out = []
    for path in sorted(APPLICATIONS_DIR.rglob('debrief.json')):
        try:
            document = _read_rounds_document(path)
            changed, seen = False, set()
            for entry in document['rounds']:
                if not entry.get('id') or entry['id'] in seen:
                    entry['id'] = uuid.uuid4().hex
                    changed = True
                seen.add(entry['id'])
            if changed:
                write_json(path, document)
            out.extend({**r, 'company_role': path.parent.relative_to(APPLICATIONS_DIR).as_posix()} for r in document['rounds'])
        except (OSError, ValueError) as exc:
            warnings.append(f'{path.parent.name}：{exc}')
    return {'rounds': sorted(out, key=lambda r: r.get('date', ''), reverse=True), 'sync_warnings': warnings}


@locked
def delete_round(archive: str, entry_id: str) -> bool:
    root = APPLICATIONS_DIR.resolve()
    folder = (root / archive).resolve()
    if Path(archive).is_absolute() or '..' in Path(archive).parts or folder == root or not folder.is_relative_to(root):
        raise ValueError('复盘路径无效')
    path = folder / 'debrief.json'
    if not path.exists():
        return False
    document = _read_rounds_document(path)
    target = next((r for r in document['rounds'] if r.get('id') == entry_id), None)
    if target is None:
        return False
    if target.get('source_type') == 'mock_interview' and target.get('source_session_id'):
        suppressed = set(document.get('suppressed_mock_sessions', []))
        suppressed.add(target['source_session_id'])
        document['suppressed_mock_sessions'] = sorted(suppressed)
    document['rounds'] = [r for r in document['rounds'] if r.get('id') != entry_id]
    write_json(path, document)
    return True
