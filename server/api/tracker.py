from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.config import ALL_STATUS
from server.storage import tracker as tracker_store

router = APIRouter(prefix="/tracker", tags=["tracker"])


@router.get("")
def all_rows():
    return {"rows": tracker_store.rows(), "status_vocab": ALL_STATUS}


class StatusBody(BaseModel):
    company: str
    role: str
    status: str
    note: str = ""


@router.post("/status")
def update_status(body: StatusBody):
    try:
        row = tracker_store.set_status(body.company, body.role, body.status, body.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not row:
        raise HTTPException(status_code=404, detail="tracker 中未找到该申请")
    return row


class NoteBody(BaseModel):
    company: str
    role: str
    note: str


@router.post("/note")
def append_note(body: NoteBody):
    row = tracker_store.append_note(body.company, body.role, body.note)
    if not row:
        raise HTTPException(status_code=404, detail="tracker 中未找到该申请")
    return row
