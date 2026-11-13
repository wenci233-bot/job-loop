"""岗位收集：贴入的 JD 明文存 inbox/，索引与状态在 state/inbox_index.json。

state 丢了可由 inbox/ 文件重建；反之索引是唯一记录状态的地方，
所以状态只存索引（state 不进 git 属可接受损失，job 文本是事实来源）。"""
from __future__ import annotations

from datetime import datetime
from copy import deepcopy
from server.storage.locking import locked
from pathlib import Path

from server.config import INBOX_DIR, INBOX_INDEX_JSON, ensure_dirs
from server.storage.files import read_json, read_text, write_json, write_text

DEFAULT_INDEX: dict = {"next_id": 1, "entries": {}}


def _index() -> dict:
    ensure_dirs()
    return read_json(INBOX_INDEX_JSON, deepcopy(DEFAULT_INDEX))


def _save_index(idx: dict) -> None:
    write_json(INBOX_INDEX_JSON, idx)


@locked
def save_entry(company: str, role: str, text: str, parsed: dict | None = None,
               channel: str = "手动贴入", status: str = "待评估") -> dict:
    idx = _index()
    # 去重：同公司同岗位（忽略括号标注）已存在则返回原条目并标记 duplicate
    def _norm(s: str) -> str:
        import re as _re
        return _re.sub(r"[（(].*?[)）]|[\s·]", "", s or "")
    for e in idx["entries"].values():
        if _norm(e["company"]) == _norm(company) and _norm(e["role"]) == _norm(role):
            return {**e, "duplicate": True}
    entry_id = str(idx["next_id"])
    while (INBOX_DIR / f"{int(entry_id):03d}.md").exists():
        entry_id = str(int(entry_id) + 1)
    idx["next_id"] = int(entry_id) + 1
    created = datetime.now().isoformat(timespec="seconds")
    header = [
        f"# 岗位 #{entry_id}",
        f"- 公司：{company}",
        f"- 岗位：{role}",
        f"- 渠道：{channel}",
        f"- 收集时间：{created}",
        f"- 状态：{status}",
        "",
    ]
    write_text(INBOX_DIR / f"{int(entry_id):03d}.md", "\n".join(header) + text.strip() + "\n")
    entry = {
        "id": entry_id, "company": company, "role": role, "channel": channel,
        "status": status, "created": created, "file": f"{int(entry_id):03d}.md",
        "parsed": parsed or {},
        "score": None, "veto": False, "reasons": [],
    }
    idx["entries"][entry_id] = entry
    _save_index(idx)
    return entry


@locked
def list_entries() -> list[dict]:
    entries = list(_index()["entries"].values())
    return sorted(entries, key=lambda e: int(e["id"]))


@locked
def get_entry(entry_id: str) -> dict | None:
    return _index()["entries"].get(str(entry_id))


@locked
def entry_text(entry_id: str) -> str:
    e = get_entry(entry_id)
    if not e:
        return ""
    body = read_text(INBOX_DIR / e["file"])
    # 去掉头部元信息，只留正文
    parts = body.split("\n\n", 1)
    return parts[1] if len(parts) > 1 else body


@locked
def update_entry(entry_id: str, *, preserve_application: bool = True, **fields) -> dict | None:
    idx = _index()
    e = idx["entries"].get(str(entry_id))
    if not e:
        return None
    if preserve_application and e.get("status") == "已申请" and fields.get("status") in ("已评估", "已否决"):
        fields["status"] = "已申请"
    e.update(fields)
    _save_index(idx)
    return e


@locked
def delete_entries(ids: list[str]) -> int:
    """批量删除收集条目（含对应 md 文件）。"""
    idx = _index()
    n = 0
    for i in ids:
        e = idx["entries"].get(str(i))
        if not e:
            continue
        p = INBOX_DIR / e["file"]
        if p.exists():
            p.unlink()
        del idx["entries"][str(i)]
        n += 1
    _save_index(idx)
    return n
