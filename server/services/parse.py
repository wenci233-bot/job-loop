"""JD 启发式解析（P1 骨架版：纯正则，不调 AI；AI 解析在 P3 接入 prompts/parse-jd.md）。

解析结果始终带 ai_used 标记，前端如实呈现「规则解析 / AI 解析」。"""
from __future__ import annotations

import re

VETO_KEYWORDS = ["外包", "劳务派遣", "驻场"]

_SALARY_RE = re.compile(r"(\d{1,3}\s*[-–~]\s*\d{1,3}\s*[kK千])")
_REQ_HINT = re.compile(r"(要求|熟悉|精通|掌握|经验|优先|本科|硕士|学历)")


def heuristic_parse(text: str) -> dict:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    company = role = ""
    if lines:
        first = re.split(r"[·\-–—|,，(（:：]", lines[0])[0].strip()
        company = first or "（未识别，请手动补填）"
        role_part = lines[0][len(first):].strip(" ·-–—|,，(（:：") if len(lines[0]) > len(first) else ""
        role = role_part or "（未识别，请手动补填）"
    m = _SALARY_RE.search(text)
    requirements = [ln for ln in lines if _REQ_HINT.search(ln)][:6]
    veto_hits = [k for k in VETO_KEYWORDS if k in text]
    return {
        "ai_used": False,
        "company": company,
        "role": role,
        "salary": m.group(1).replace(" ", "") if m else "",
        "requirements": requirements,
        "role_type_warning": "疑似外包/劳务派遣" if veto_hits else "",
        "veto_keywords": veto_hits,
        "raw_len": len(text),
    }
