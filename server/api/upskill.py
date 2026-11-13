from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.services import upskill as upskill_svc

router = APIRouter(prefix="/upskill", tags=["upskill"])


@router.get("/gaps")
def get_gaps():
    return upskill_svc.gaps()


@router.get("/plan")
def get_plan():
    return {"plan": upskill_svc.latest_plan()}


@router.post("/plan")
def make_plan():
    try:
        return {"plan": upskill_svc.make_plan()}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 调用失败：{e}")


@router.get("/roadmap")
def get_roadmap():
    return {"roadmap": upskill_svc.latest_roadmap()}


@router.post("/roadmap")
def make_roadmap():
    try:
        return {"roadmap": upskill_svc.roadmap()}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 调用失败：{e}")


class PhaseDoneBody(BaseModel):
    phase: int
    done: bool


@router.post("/roadmap/progress")
def phase_done(body: PhaseDoneBody):
    rm = upskill_svc.toggle_phase_done(body.phase, body.done)
    if not rm:
        raise HTTPException(status_code=404, detail="暂无路线图")
    return rm
