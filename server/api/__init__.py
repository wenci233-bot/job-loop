"""API 路由聚合：每个 WebUI 模块一组薄路由（参数校验在这里，业务在 services，落盘在 storage）。"""
from __future__ import annotations

from fastapi import APIRouter

from server.api import (apply, dashboard, debrief, inbox, interview, logo, profile,
                        rank, reset, settings, tracker, upskill)

api_router = APIRouter(prefix="/api")
for r in (dashboard.router, profile.router, inbox.router, rank.router,
          apply.router, tracker.router, interview.router, debrief.router,
          upskill.router, settings.router, logo.router, reset.router):
    api_router.include_router(r)


@api_router.get("/health")
def health():
    return {"ok": True, "service": "job-loop", "version": "0.1.0"}
