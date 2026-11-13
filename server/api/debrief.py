from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from server.services import debrief as debrief_svc

router = APIRouter(prefix="/debrief", tags=["debrief"])


@router.get("/list")
def list_all():
    return debrief_svc.list_history()


class OrganizeBody(BaseModel):
    raw: str


@router.post("/organize")
def organize(body: OrganizeBody):
    if len(body.raw.strip()) < 20:
        raise HTTPException(status_code=400, detail="口述内容太短")
    try:
        return debrief_svc.organize(body.raw)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 调用失败：{e}")


class ReviewBody(BaseModel):
    company: str
    role: str
    qa: list[dict] = []
    focus: list[str] = []


@router.post("/review")
def review(body: ReviewBody):
    qa = [q for q in body.qa if isinstance(q, dict) and str(q.get("question", "")).strip()]
    if not qa:
        raise HTTPException(status_code=400, detail="请至少填写一道面试题")
    try:
        return debrief_svc.review(body.company, body.role, qa, body.focus)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 调用失败：{e}")


class SaveBody(BaseModel):
    company: str
    role: str
    qa: list[dict] = []
    focus: list[str] = []
    rating: int = 3
    note: str = ""
    review: dict | None = None


@router.post("/save")
def save_round(body: SaveBody):
    qa = [q for q in body.qa if isinstance(q, dict) and str(q.get("question", "")).strip()]
    if not qa:
        raise HTTPException(status_code=400, detail="至少要有一道面试题")
    entry = debrief_svc.save_round(body.company, body.role, qa, body.focus,
                                   body.rating, body.note, body.review)
    return {"round": entry}


class ImportMockBody(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=300)
    session_id: str = Field(min_length=1, max_length=100)


@router.post('/import-mock')
def import_mock(body: ImportMockBody):
    try:
        return debrief_svc.import_mock(body.company, body.role, body.session_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


class DeleteRoundBody(BaseModel):
    archive: str = Field(min_length=1, max_length=500)
    id: str = Field(min_length=1, max_length=100)
    confirmed: Literal[True]


@router.post('/delete')
def delete_round(body: DeleteRoundBody):
    try:
        return {'deleted': debrief_svc.delete_round(body.archive, body.id)}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
