"""投递流水账：稳定编号、状态与备注更新，以及按用户选择精确删除。"""
from __future__ import annotations

import csv
import uuid
from io import StringIO
from server.storage.files import write_text
from server.storage.locking import locked
from datetime import date, datetime
from pathlib import Path

from server.config import ALL_STATUS, TRACKER_CSV, ensure_dirs

COLUMNS = [
    "id",
    "date", "company", "sector", "role", "role_type", "channel", "status",
    "contact_person", "fit_rating", "notes", "cv_file", "message_file",
    "source_url", "deadline",
]


def _load() -> list[dict]:
    ensure_dirs()
    if not TRACKER_CSV.exists():
        TRACKER_CSV.write_text(",".join(COLUMNS) + "\n", encoding="utf-8-sig")
        return []
    with open(TRACKER_CSV, "r", encoding="utf-8-sig", newline="") as f:
        result = [dict(row) for row in csv.DictReader(f)]
    changed = False
    seen = set()
    for row in result:
        if not row.get("id") or row["id"] in seen:
            row["id"] = uuid.uuid4().hex
            changed = True
        seen.add(row["id"])
    if changed:
        _save(result)
    return result


def _save(rows: list[dict]) -> None:
    ensure_dirs()
    buffer = StringIO(newline='')
    columns = list(dict.fromkeys(COLUMNS + [key for row in rows for key in row]))
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader(); writer.writerows(rows)
    write_text(TRACKER_CSV, '\ufeff' + buffer.getvalue())


@locked
def rows() -> list[dict]:
    return _load()


@locked
def append_row(entry: dict) -> dict:
    row = {c: str(entry.get(c, "")) for c in COLUMNS}
    row["id"] = uuid.uuid4().hex
    if not row["date"]:
        row["date"] = date.today().isoformat()
    if not row.get("status"):
        row["status"] = "drafted"
    rows_ = _load()
    rows_.append(row)
    _save(rows_)
    return row


def _match(rows_: list[dict], company: str, role: str = "") -> int | None:
    for i, r in enumerate(rows_):
        if r["company"] == company and (not role or r["role"] == role):
            return i
    return None


@locked
def set_status(company: str, role: str, status: str, note: str = "") -> dict | None:
    if status not in ALL_STATUS:
        raise ValueError(f"非法状态：{status}（允许：{', '.join(ALL_STATUS)}）")
    rows_ = _load()
    i = _match(rows_, company, role)
    if i is None:
        return None
    rows_[i]["status"] = status
    if note:
        _append_note_cell(rows_[i], note)
    _save(rows_)
    return rows_[i]


@locked
def append_note(company: str, role: str, note: str) -> dict | None:
    rows_ = _load()
    i = _match(rows_, company, role)
    if i is None:
        return None
    _append_note_cell(rows_[i], note)
    _save(rows_)
    return rows_[i]


def _append_note_cell(row: dict, note: str) -> None:
    stamp = date.today().isoformat()
    cell = row.get("notes", "")
    row["notes"] = f"{cell} | {stamp} {note}".strip(" |") if cell else f"{stamp} {note}"


@locked
def delete_rows(ids: list[str]) -> list[dict]:
    selected = set(ids)
    current = _load()
    removed = [row for row in current if row['id'] in selected]
    if removed:
        _save([row for row in current if row['id'] not in selected])
    return removed
