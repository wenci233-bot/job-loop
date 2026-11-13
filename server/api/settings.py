from __future__ import annotations

import json
import urllib.error
import urllib.request

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.config import AI_KEYS, read_env, write_env
from server.services import ai as ai_svc

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_settings():
    cfg = read_env()
    masked = dict(cfg)
    if masked["AI_API_KEY"]:
        masked["AI_API_KEY_MASKED"] = masked["AI_API_KEY"][:6] + "…" + masked["AI_API_KEY"][-4:]
    else:
        masked["AI_API_KEY_MASKED"] = ""
    masked.pop("AI_API_KEY")
    return masked


class SettingsBody(BaseModel):
    AI_BASE_URL: str = ""
    AI_API_KEY: str = ""
    AI_MODEL: str = ""


@router.put("")
def save_settings(body: SettingsBody):
    vals = {k: v for k, v in body.model_dump().items() if k in AI_KEYS}
    # Key 留空 = 保留原值（前端不回显完整 Key）
    if not vals["AI_API_KEY"]:
        vals["AI_API_KEY"] = read_env()["AI_API_KEY"]
    write_env(vals)
    return {"ok": True}


@router.post("/test")
def test_connection():
    return ai_svc.test_connection()


@router.get("/models")
def list_models():
    """从 AI 网关拉取可用模型列表（模型广场数据源）。"""
    cfg = read_env()
    if not cfg["AI_API_KEY"]:
        raise HTTPException(status_code=400, detail="未配置 AI_API_KEY")
    url = cfg["AI_BASE_URL"].rstrip("/") + "/models"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {cfg['AI_API_KEY']}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"网关返回 HTTP {e.code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"拉取模型列表失败：{e}")
    ids = sorted({str(m.get("id")) for m in data.get("data", []) if m.get("id")})
    return {"models": ids}
