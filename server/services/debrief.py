"""面试复盘：用户记录「面试问题 + 我的回答」→ AI 逐题评价与改进意见 → 落盘 debrief.json（追加式）。"""
from __future__ import annotations

import json
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
    for archive in APPLICATIONS_DIR.glob("*/debrief.json"):
        if archive.parent.name.startswith(f"{exclude_company}_"):
            continue
        try:
            data = json.loads(archive.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for r in data.get("rounds", []):
            for item in r.get("qa", []):
                lines.append(f"- 被问：{str(item.get('question', ''))[:80]}（{archive.parent.name}）")
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


def save_round(company: str, role: str, qa: list[dict], focus: list[str],
               rating: int, note: str, review: dict | None) -> dict:
    rounds = load_rounds(company, role)
    entry = {
        "round": len(rounds) + 1,
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
    dest.write_text(json.dumps({"rounds": rounds}, ensure_ascii=False, indent=2), encoding="utf-8")
    return entry


def all_stuck_points() -> list[dict]:
    """全部历史卡壳/需改进考点（供校准与技能提升使用）。"""
    out = []
    for archive in sorted(APPLICATIONS_DIR.glob("*/debrief.json")):
        try:
            data = json.loads(archive.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for r in data.get("rounds", []):
            # 新结构：从 review 的需改进题取；兼容旧结构 stuck
            for q in (r.get("review") or {}).get("per_question", []):
                if q.get("verdict") == "需改进":
                    out.append({"question": str(q.get("question", "")), "gap": "需改进",
                                "source": archive.parent.name, "date": r.get("date", "")})
            for s in r.get("stuck", []):
                out.append({"question": str(s.get("question", "")), "gap": str(s.get("gap", "")),
                            "source": archive.parent.name, "date": r.get("date", "")})
    return out
