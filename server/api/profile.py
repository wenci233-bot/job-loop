from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from server.config import DOCUMENTS_DIR
from server.services import resume_import
from server.storage import profile as profile_store

router = APIRouter(prefix="/profile", tags=["profile"])


class StarItem(BaseModel):
    title: str = ""
    content: str = ""
    source: str = "手填"


class ProfileBody(BaseModel):
    candidate: dict = {}
    stars: list[StarItem] = []


@router.get("")
def get_profile():
    return {"candidate": profile_store.load_candidate(), "stars": profile_store.load_stars()}


@router.put("")
def save_profile(body: ProfileBody):
    profile_store.save(body.candidate, [s.model_dump() for s in body.stars])
    return {"ok": True}


@router.post("/import")
async def import_resume(file: UploadFile):
    """上传 PDF/Word 简历 → 提取文本 → AI 解析为档案字段（返回给前端预填，不直接落盘）。"""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in resume_import.SUPPORTED:
        raise HTTPException(status_code=400, detail="仅支持 .pdf / .docx")
    uploads = DOCUMENTS_DIR / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    dest = uploads / f"resume_{datetime.now():%Y%m%d%H%M%S}{suffix}"
    dest.write_bytes(await file.read())
    try:
        text = resume_import.extract_text(dest)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="文件解析失败，请确认不是加密或扫描件")
    text = text.strip()
    if len(text) < 50:
        raise HTTPException(status_code=400, detail="提取到的文本太少（可能是扫描件/图片型 PDF），请换文本版简历")
    try:
        partial = resume_import.parse_to_candidate(text)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 调用失败：{e}")
    return {"candidate": partial, "text_len": len(text)}
