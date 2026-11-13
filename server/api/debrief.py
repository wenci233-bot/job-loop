from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.services import debrief as debrief_svc

router = APIRouter(prefix="/debrief", tags=["debrief"])


@router.get("/list")
def list_all():
    from server.config import APPLICATIONS_DIR
    out = []
    for archive in sorted(APPLICATIONS_DIR.glob("*/debrief.json")):
        try:
            data = json.loads(archive.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for r in data.get("rounds", []):
            out.append({"company_role": archive.parent.name, **r})
    return {"rounds": sorted(out, key=lambda x: x.get("date", ""), reverse=True)}


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
