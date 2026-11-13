from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal
from server.config import ALL_STATUS
from server.storage.locking import locked

from server.config import APPLICATIONS_DIR
from server.storage import inbox as inbox_store
from server.storage import tracker as tracker_store
from server.storage.files import write_text

router = APIRouter(prefix="/apply", tags=["apply"])


class CreateBody(BaseModel):
    inbox_id: str


@router.get("/list")
def list_applications():
    return {"rows": tracker_store.rows()}


@router.post("/create")
@locked
def create(body: CreateBody):
    """从候选池创建申请：登记 tracker（drafted）+ 建申请存档目录。材料生成是 P4。"""
    e = inbox_store.get_entry(body.inbox_id)
    if not e:
        raise HTTPException(status_code=404, detail=f"岗位 #{body.inbox_id} 不存在")
    existing = next((row for row in tracker_store.rows() if row['company'] == e['company'] and row['role'] == e['role']), None)
    if existing:
        inbox_store.update_entry(e['id'], status='已申请')
        return {'tracker_row': existing, 'duplicate': True}
    folder = APPLICATIONS_DIR / f"{e['company']}_{e['role']}"
    try:
        folder.resolve().relative_to(APPLICATIONS_DIR.resolve())
    except ValueError:
        raise HTTPException(400, '公司或岗位名称不能包含越界路径')
    write_text(folder / 'job_posting.md', inbox_store.entry_text(e['id']))
    row = tracker_store.append_row({
        "date": date.today().isoformat(),
        "company": e["company"], "role": e["role"],
        "channel": e.get("channel", ""), "status": "drafted",
        "fit_rating": str(e.get("score") or ""),
        "source_url": f"inbox#{e['id']}",
    })
    inbox_store.update_entry(e["id"], status="已申请")
    return {"tracker_row": row, "archive": str(folder.relative_to(APPLICATIONS_DIR.parents[2]))}


class ManualBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    company: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=200)
    status: str = 'applied'
    channel: str = Field(default='手动登记', max_length=120)
    notes: str = Field(default='', max_length=5000)


@router.post('/manual')
@locked
def add_manual(body: ManualBody):
    if body.status not in ALL_STATUS:
        raise HTTPException(400, '投递状态无效')
    existing = next((row for row in tracker_store.rows() if row['company'] == body.company and row['role'] == body.role), None)
    if existing:
        return {'tracker_row': existing, 'duplicate': True}
    row = tracker_store.append_row(body.model_dump())
    for entry in inbox_store.list_entries():
        if entry['company'] == body.company and entry['role'] == body.role:
            inbox_store.update_entry(entry['id'], status='已申请')
    return {'tracker_row': row, 'duplicate': False}


class DeleteApplicationsBody(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=500)
    confirmed: Literal[True]


@router.post('/delete')
@locked
def delete_applications(body: DeleteApplicationsBody):
    removed = tracker_store.delete_rows(body.ids)
    remaining = {(r['company'], r['role']) for r in tracker_store.rows()}
    identities = {(r['company'], r['role']) for r in removed} - remaining
    for entry in inbox_store.list_entries():
        if (entry['company'], entry['role']) in identities:
            status = '已否决' if entry.get('veto') else '已评估' if entry.get('score') is not None else '待评估'
            # Explicitly reset only the workflow status; keep all evaluation data.
            inbox_store.update_entry(entry['id'], status=status, preserve_application=False)
    return {'deleted': len(removed)}
