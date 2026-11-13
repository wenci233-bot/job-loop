"""首页仪表盘统计：一切从 tracker 与 inbox 现算，不缓存（个人规模足够快）。"""
from __future__ import annotations

from datetime import date, datetime

from server.storage import inbox as inbox_store
from server.storage import tracker as tracker_store


def summary() -> dict:
    rows = tracker_store.rows()
    interview_stages = ("interviewing", "interview_1", "interview_2", "interview_3", "interview_4", "interview_hr")
    final_states = ("offer", "offer_declined", "rejected", "no_response", "withdrawn")
    counts = {
        "applying": sum(1 for r in rows if r["status"] in ("drafted", "applied")),
        "interviewing": sum(1 for r in rows if r["status"] in interview_stages),
        "offer": sum(1 for r in rows if r["status"] == "offer"),
        "finished": sum(1 for r in rows if r["status"] in final_states),
    }
    entries = inbox_store.list_entries()
    funnel = {
        "collected": len(entries),
        "evaluated": sum(1 for e in entries if e["status"] in ("已评估", "已申请", "已忽略")),
        "applied": sum(1 for r in rows if r["status"] != "drafted"),
        "interviewing": counts["interviewing"],
        "offer": counts["offer"],
    }
    todos = []
    today = date.today()
    for r in rows:
        if r["status"] != "applied":
            continue
        try:
            d = datetime.strptime(r["date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        quiet = (today - d).days
        follows = r.get("notes", "").count("跟进")
        if quiet >= 10 and follows < 2:
            todos.append({"company": r["company"], "role": r["role"], "days": quiet,
                          "action": "跟进", "detail": f"投递 {quiet} 天无回音，已跟进 {follows} 次"})
    todos.sort(key=lambda t: -t["days"])
    return {"stats": counts, "funnel": funnel, "todos": todos[:6],
            "tracker_rows": len(rows)}
