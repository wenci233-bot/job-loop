from __future__ import annotations

from fastapi import APIRouter

from server.services import dashboard as dashboard_svc

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary():
    return dashboard_svc.summary()
