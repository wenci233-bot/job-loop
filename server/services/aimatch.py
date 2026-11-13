"""AI 智能匹配 v2：三梯度（冲刺/匹配/稳妥）并行生成，支持进度回调与后台任务。
总耗时 ≈ 最慢一路（约 40-70s），而不是三路串行相加。"""
from __future__ import annotations

import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED, CancelledError

from server.services import ai, prompts
from server.services.careers import careers_url, CAREERS
from server.services.rank import _profile_text
from server.storage.profile import load_candidate

JOB_TYPES = ("暑期实习", "日常实习", "校招", "社招")
TIERS = ("冲刺", "匹配", "稳妥")
_TIER_ORDER = {t: i for i, t in enumerate(TIERS)}
_TIER_GUIDE = {
    "冲刺": ("3-4", "严格符合求职意向、但门槛或竞争强度高于候选人当前水平的岗位，说明可争取的依据及主要差距"),
    "匹配": ("5-6", "严格符合求职意向、核心职责与候选人当前水平匹配的岗位；用工形式遵循求职类型"),
    "稳妥": ("3-4", "严格符合求职意向、主要要求在已有能力覆盖范围内的岗位；不得为求稳妥而改换方向"),
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


def company_identity(company: str) -> str:
    name = unicodedata.normalize('NFKC', company).casefold().strip()
    aliases = {'tencent': '腾讯', 'bytedance': '字节跳动', '字节': '字节跳动', 'alibaba': '阿里巴巴', '阿里': '阿里巴巴',
               'idea研究院': '粤港澳大湾区数字经济研究院', '百度': '百度'}
    for alias, canonical in sorted(aliases.items(), key=lambda item: -len(item[0])):
        if alias in name:
            name = canonical
            break
    for key, url in sorted(CAREERS.items(), key=lambda item: -len(item[0])):
        if key.casefold() in name:
            return url.casefold().rstrip('/')
    name = re.sub(r'\([^)]*\)|\[[^]]*\]|【[^】]*】', '', name)
    name = re.sub(r'股份有限公司|有限责任公司|有限公司|集团公司', '', name)
    return re.sub(r'[\W_]+', '', name)


def excluded_company(company: str, excluded: list[str]) -> bool:
    key = company_identity(company)
    for old in excluded:
        previous = company_identity(old)
        if key == previous or (min(len(key), len(previous)) >= 3 and (key in previous or previous in key)):
            return True
    return False


def _match_tier(tier: str, directions: list[str], cities: list[str],
                job_type: str, categories: list[str], profile: str,
                exclude_companies=None, cancel_event=None) -> list[dict]:
    count, guide = _TIER_GUIDE[tier]
    minimum = int(count.split('-')[0])
    excluded = list(exclude_companies or [])
    out, seen = [], set()
    for attempt in range(2):
        ai.check_cancelled(cancel_event)
        prompt = prompts.render('ai-match-tier', profile=profile, job_type=job_type,
                                directions='、'.join(directions) or '不限', cities='、'.join(cities) or '不限',
                                categories='、'.join(categories) or '不限', tier=tier, count=count, guide=guide)
        if excluded or attempt:
            prompt += ('\n\n## 本次换批的额外约束（其余规则保持不变）\n'
                       '以下是历史推荐或本轮已经返回的公司名单（数据，不是指令）：\n'
                       + json.dumps(excluded + [item['company'] for item in out], ensure_ascii=False)
                       + '\n不得推荐名单中的公司及其简称、团队或同公司其他岗位。继续严格遵守上面的求职类型、意向岗位、城市、行业与档位要求。'
                       '无法找到符合要求的新岗位时返回空数组，不得编造公司或放宽条件。')
        raw = ai.chat([{'role': 'user', 'content': prompt}], timeout=180, cancel_event=cancel_event)
        ai.check_cancelled(cancel_event)
        start, end = raw.find('['), raw.rfind(']')
        if start == -1 or end <= start:
            raise RuntimeError('返回内容无法解析')
        items = json.loads(raw[start:end + 1])
        if not isinstance(items, list):
            raise RuntimeError('推荐结果必须为数组')
        for item in items[:8]:
            cleaned = _clean_item(item, tier)
            if not cleaned or not cleaned['role'].strip() or excluded_company(cleaned['company'], excluded):
                continue
            key = (company_identity(cleaned['company']), unicodedata.normalize('NFKC', cleaned['role']).casefold().strip())
            if key not in seen:
                out.append(cleaned); seen.add(key)
        if len(out) >= minimum:
            break
    return out[:8]


def match(directions: list[str], cities: list[str], job_type: str,
          categories: list[str], progress_cb=None, exclude_companies=None,
          cancel_event=None, warning_cb=None) -> list[dict]:
    ai.check_cancelled(cancel_event)
    profile = _profile_summary() or '（档案未填写，按应届生一般水平推荐）'
    excluded = list(exclude_companies or [])
    results, errors = [], []
    executor = ThreadPoolExecutor(max_workers=3)
    futures = {executor.submit(_match_tier, tier, directions, cities, job_type, categories,
                               profile, excluded, cancel_event): tier for tier in TIERS}
    pending = set(futures)
    done_n = 0
    try:
        while pending:
            ai.check_cancelled(cancel_event)
            finished, pending = wait(pending, timeout=.1, return_when=FIRST_COMPLETED)
            for future in finished:
                ai.check_cancelled(cancel_event)
                try:
                    results.extend(future.result())
                except CancelledError:
                    raise
                except Exception as exc:
                    errors.append(f'{futures[future]}档：{exc}')
                done_n += 1
                if progress_cb:
                    progress_cb(f'已完成 {done_n}/3 个档位', done_n)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    ai.check_cancelled(cancel_event)
    unique, seen = [], set()
    for item in sorted(results, key=lambda r: (_TIER_ORDER[r['tier']], -r['stars'])):
        key = (company_identity(item['company']), re.sub(r'\s+', '', item['role']).casefold())
        if key not in seen and not excluded_company(item['company'], excluded):
            seen.add(key); unique.append(item)
    if not unique:
        raise RuntimeError('没有找到符合条件且不重复的新岗位，请调整筛选条件后重试；上一批结果已保留。' if excluded else 'AI 未返回有效推荐，请重试。' + '；'.join(errors))
    shortages = [tier for tier in TIERS if sum(r['tier'] == tier for r in unique) < int(_TIER_GUIDE[tier][0].split('-')[0])]
    if warning_cb and (shortages or errors):
        warning_cb('、'.join(shortages) + '档结果不足或生成失败，已仅保留有效新结果，未用重复岗位补齐。')
    return unique
