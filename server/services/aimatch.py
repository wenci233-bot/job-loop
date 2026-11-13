"""AI 智能匹配 v2：三梯度（冲刺/匹配/稳妥）并行生成，支持进度回调与后台任务。
总耗时 ≈ 最慢一路（约 40-70s），而不是三路串行相加。"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from server.services import ai, prompts
from server.services.careers import careers_url
from server.services.rank import _profile_text
from server.storage.profile import load_candidate

JOB_TYPES = ("暑期实习", "日常实习", "校招", "社招")
TIERS = ("冲刺", "匹配", "稳妥")
_TIER_ORDER = {t: i for i, t in enumerate(TIERS)}
_TIER_GUIDE = {
    "冲刺": ("3-4", "业内顶级团队/核心研究院级别的岗位（各厂 AI Lab、核心大模型团队、业内公认高门槛岗位），竞争激烈但值得冲"),
    "匹配": ("5-6", "与候选人当前水平匹配的大厂正式岗位，是主投方向"),
    "稳妥": ("3-4", "把握较大的岗位——中厂、国企/央企研究院、独角兽、研究所等"),
}


def _profile_summary() -> str:
    return _profile_text(load_candidate())[:1500]


def _clean_item(it: dict, tier: str) -> dict | None:
    if not isinstance(it, dict) or not it.get("company"):
        return None
    try:
        stars = max(1, min(5, int(it.get("stars", 3))))
    except (TypeError, ValueError):
        stars = 3
    reqs = it.get("requirements")
    if not isinstance(reqs, list):
        reqs = []
    return {"tier": tier,
            "company": str(it.get("company", "")), "role": str(it.get("role", "")),
            "why": str(it.get("why", "")), "channel_hint": str(it.get("channel_hint", "")),
            "stars": stars, "salary": str(it.get("salary", "")),
            "careers_url": careers_url(str(it.get("company", ""))) or "",
            "description": str(it.get("description") or it.get("detail", "")),
            "requirements": [str(r) for r in reqs][:8],
            "bonus": [str(b) for b in (it.get("bonus") or []) if str(b).strip()][:4]}


def _match_tier(tier: str, directions: list[str], cities: list[str],
                job_type: str, categories: list[str], profile: str) -> list[dict]:
    count, guide = _TIER_GUIDE[tier]
    prompt = prompts.render("ai-match-tier", profile=profile, job_type=job_type,
                            directions="、".join(directions) or "不限",
                            cities="、".join(cities) or "不限",
                            categories="、".join(categories) or "不限",
                            tier=tier, count=count, guide=guide)
    raw = ai.chat([{"role": "user", "content": prompt}], timeout=180)
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end <= start:
        raise RuntimeError("返回内容无法解析")
    items = json.loads(raw[start:end + 1])
    out = []
    for it in items[:8]:
        cleaned = _clean_item(it, tier)
        if cleaned:
            out.append(cleaned)
    return out


def match(directions: list[str], cities: list[str], job_type: str,
          categories: list[str], progress_cb=None) -> list[dict]:
    profile = _profile_summary() or "（档案未填写，按应届生一般水平推荐）"
    results: list[dict] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(_match_tier, t, directions, cities, job_type, categories, profile): t
                for t in TIERS}
        done_n = 0
        for fut in as_completed(futs):
            tier = futs[fut]
            try:
                items = fut.result()
                results.extend(items)
            except Exception as e:
                errors.append(f"{tier}档：{e}")
            done_n += 1
            if progress_cb:
                progress_cb(f"{tier}档完成 {done_n}/3")
    # 同公司同岗位去重 + 梯度排序
    seen, unique = set(), []
    for r in results:
        key = r["company"] + "|" + r["role"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    unique.sort(key=lambda r: (_TIER_ORDER[r["tier"]], -r["stars"]))
    if not unique:
        raise RuntimeError("AI 未返回有效推荐" + ("；".join(errors) or "") + "，请重试")
    return unique
