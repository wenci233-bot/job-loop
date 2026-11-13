"""技能提升：差距热图（确定性统计）+ AI 学习路线图（能力画像 × 投递/收藏岗位 JD）。"""
from __future__ import annotations

import json
import re
from datetime import date
from collections import Counter

from server.config import DATA_DIR, INBOX_DIR, UPSKILL_DIR, ensure_dirs
from server.services import ai, debrief, prompts
from server.services.rank import _profile_text
from server.storage import inbox as inbox_store
from server.storage.profile import load_candidate

_SPLIT = re.compile(r"[/、，,;；\s，。;：:（）()\-—]+")
_STOP = {"熟悉", "精通", "掌握", "了解", "具备", "优先", "熟练", "相关", "经验", "能力", "以上", "学历",
         "本科", "硕士", "博士", "熟练掌握", "能力要求", "深入理解", "扎实", "任职要求", "岗位职责", "加分项",
         "计算机", "人工智能", "数学", "软件工程", "专业", "基础", "描述", "包括", "不限于", "岗位",
         "实践", "领域", "技术", "框架", "系统", "设计", "开发", "具有", "良好", "较强", "以及", "等",
         "实战", "工程", "及以上", "主流", "硕士及以上", "者优先", "跟进", "深入"}
_NOISE_HINTS = ("要求", "专业", "描述", "介绍", "负责", "熟悉", "掌握", "优先", "加分", "基础", "相关",
                "学历", "良好", "及以上", "相关方向", "主流", "出众", "优异", "及以下")
_LEAD_VERBS = ("熟练掌握", "深入理解", "熟练运用", "精通", "熟悉", "掌握", "了解", "具备", "深入")
_GLUE_SUFFIX = ("原理", "框架", "机制", "经验", "能力", "架构", "技术", "学历", "背景")


def _clean_kw(raw: str) -> str | None:
    """洗出一个技术关键词：去动词前缀、拆『等』粘连、去名词后缀；洗完仍像套话则丢弃。"""
    kw = raw.strip()
    changed = True
    while changed:
        changed = False
        for v in _LEAD_VERBS:
            if kw.startswith(v) and len(kw) > len(v):
                kw = kw[len(v):]
                changed = True
        if kw.startswith("与") and len(kw) > 2:
            kw = kw[1:]
            changed = True
        if kw.startswith("有") and len(kw) > 3:
            kw = kw[1:]
            changed = True
    if "等" in kw:
        kw = kw.split("等")[0]
    for suf in _GLUE_SUFFIX:
        if kw.endswith(suf) and len(kw) > len(suf) + 1:
            kw = kw[: -len(suf)]
    if not (2 <= len(kw) <= 14) or kw in _STOP:
        return None
    if re.fullmatch(r"[\d\w]{1,3}", kw):
        return None
    if re.match(r"^[a-z]+[\u4e00-\u9fff]", kw):  # 英文小写粘连中文（如 based生成），拆坏了
        return None
    if any(h in kw for h in _NOISE_HINTS):
        return None
    return kw


def _extract_jd_keywords() -> Counter:
    counter: Counter = Counter()
    for e in inbox_store.list_entries():
        text = inbox_store.entry_text(e["id"])
        reqs = (e.get("parsed") or {}).get("requirements") or [
            ln for ln in text.splitlines() if re.search(r"(要求|熟悉|精通|掌握)", ln)][:6]
        for ln in reqs:
            for token in _SPLIT.split(re.sub(r"^\d+[.、]\s*", "", ln.strip())):
                kw = _clean_kw(token)
                if kw:
                    counter[kw] += 1
    return counter


def gaps() -> dict:
    cand = load_candidate()
    skills = cand.get("skills", "")
    freq = _extract_jd_keywords()
    stuck = debrief.all_stuck_points()
    stuck_counter: Counter = Counter()
    for s in stuck:
        for token in _SPLIT.split(s["question"]):
            kw = _clean_kw(token)
            if kw:
                stuck_counter[kw] += 1

    items = []
    for kw, n in freq.most_common(24):
        in_profile = kw in skills
        stuck_n = sum(c for k, c in stuck_counter.items() if kw in k or k in kw)
        if in_profile and stuck_n == 0:
            continue  # 已掌握且没卡过壳的不算差距
        items.append({"keyword": kw, "jd_count": n, "stuck_count": stuck_n,
                      "in_profile": in_profile})
    stuck_only = [{"keyword": k, "jd_count": 0, "stuck_count": c, "in_profile": False}
                  for k, c in stuck_counter.most_common(6)
                  if not any(i["keyword"] in k or k in i["keyword"] for i in items)]
    items = sorted(items + stuck_only, key=lambda x: (-x["stuck_count"], -x["jd_count"]))[:15]
    return {"gaps": items, "stuck_sources": stuck[:5], "total_jd": len(inbox_store.list_entries())}


def _target_jds_text() -> tuple[str, int]:
    """全部候选岗位（投递+收藏+待评估）的 JD 全文；返回 (文本, 数量)。"""
    lines, n = [], 0
    for e in inbox_store.list_entries():
        n += 1
        lines.append(f"【{e['company']} · {e['role']}（{e['status']}）】\n{inbox_store.entry_text(e['id'])[:900]}")
    return "\n\n".join(lines)[:9000], n


def roadmap() -> dict:
    cand = load_candidate()
    stuck = debrief.all_stuck_points()
    stuck_text = "\n".join(f"- {s['question'][:80]}（{s['date']}）" for s in stuck) or "（暂无）"
    jds_text, jd_n = _target_jds_text()
    if jd_n == 0:
        raise RuntimeError("暂无目标岗位（先在岗位收集里添加岗位）")
    prompt = prompts.render("upskill-roadmap",
                            profile=_profile_text(cand)[:3500],
                            jds=jds_text, stuck=stuck_text[:1500])
    raw = ai.chat([{"role": "user", "content": prompt}], timeout=240)
    start, end = raw.find("{"), raw.rfind("}")
    data = json.loads(raw[start:end + 1])
    clusters = [c for c in (data.get("clusters") or []) if isinstance(c, dict) and c.get("theme")]
    for c in clusters:
        c["coverage"] = c.get("coverage") if c.get("coverage") in ("已覆盖", "部分覆盖", "缺口") else "部分覆盖"
    roadmap = []
    for item in (data.get("roadmap") or [])[:5]:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        roadmap.append({
            "phase": len(roadmap) + 1,
            "title": str(item.get("title", ""))[:80],
            "why": str(item.get("why", ""))[:200],
            "weeks": int(item.get("weeks", 3)),
            "goal": str(item.get("goal", ""))[:200],
            "milestone": str(item.get("milestone", ""))[:200],
            "topics": [str(t) for t in (item.get("topics") or [])][:4],
            "closes": [str(c) for c in (item.get("closes") or [])][:4],
            "resources": [{"title": str(r.get("title", ""))[:80], "url": str(r.get("url", ""))}
                          for r in (item.get("resources") or [])[:3] if isinstance(r, dict)],
            "done": False,
        })
    if not roadmap:
        raise RuntimeError("AI 未生成有效路线图，请重试")
    tags = [str(t)[:12] for t in (data.get("portrait_tags") or []) if str(t).strip()][:9]
    out = {"date": date.today().isoformat(), "direction": str(data.get("direction", ""))[:200],
           "portrait_tags": tags,
           "clusters": clusters[:5], "roadmap": roadmap,
           "advice": str(data.get("advice", ""))[:300]}
    ensure_dirs()
    (UPSKILL_DIR / f"roadmap_{date.today():%Y%m%d}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def latest_roadmap() -> dict | None:
    ensure_dirs()
    files = sorted(UPSKILL_DIR.glob("roadmap_*.json"))
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def toggle_phase_done(phase: int, done: bool) -> dict | None:
    rm = latest_roadmap()
    if not rm:
        return None
    for item in rm["roadmap"]:
        if item["phase"] == phase:
            item["done"] = bool(done)
    files = sorted(UPSKILL_DIR.glob("roadmap_*.json"))
    files[-1].write_text(json.dumps(rm, ensure_ascii=False, indent=2), encoding="utf-8")
    return rm


def make_plan() -> dict:
    g = gaps()
    if not g["gaps"]:
        raise RuntimeError("暂无技能差异数据（先收集岗位或填写面试复盘）")
    cand = load_candidate()
    gaps_text = "\n".join(
        f"- {i['keyword']}（JD 出现 {i['jd_count']} 次{'；★面试卡壳 ' + str(i['stuck_count']) + ' 次' if i['stuck_count'] else ''}）"
        for i in g["gaps"][:12])
    prompt = prompts.render("upskill-plan", skills=cand.get("skills", "")[:600] or "（未填写）", gaps=gaps_text)
    raw = ai.chat([{"role": "user", "content": prompt}], timeout=180)
    start, end = raw.find("{"), raw.rfind("}")
    data = json.loads(raw[start:end + 1])
    plan = []
    for item in (data.get("plan") or [])[:6]:
        if not isinstance(item, dict) or not item.get("topic"):
            continue
        plan.append({
            "topic": str(item["topic"])[:80],
            "priority": item.get("priority") if item.get("priority") in ("P0", "P1", "P2") else "P1",
            "why": str(item.get("why", ""))[:200],
            "weeks": int(item.get("weeks", 2)),
            "resources": [{"title": str(r.get("title", ""))[:80], "url": str(r.get("url", ""))}
                          for r in (item.get("resources") or [])[:3] if isinstance(r, dict)],
        })
    if not plan:
        raise RuntimeError("AI 未生成有效计划，请重试")
    ensure_dirs()
    out = {"date": date.today().isoformat(), "gaps": g["gaps"], "plan": plan}
    (UPSKILL_DIR / f"plan_{date.today():%Y%m%d}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def latest_plan() -> dict | None:
    ensure_dirs()
    files = sorted(DATA_DIR.parent.glob("upskill/plan_*.json"))
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
