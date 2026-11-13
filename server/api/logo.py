from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from server.services import logos as logos_svc

router = APIRouter(prefix="/logo", tags=["logo"])


@router.get("")
def get_logo(company: str):
    path = logos_svc.get_logo(company)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="no logo")
    return FileResponse(path)


@router.get("/vendor")
def get_vendor_logo(v: str):
    path = logos_svc.get_vendor_logo(v)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="no logo")
    return FileResponse(path)
