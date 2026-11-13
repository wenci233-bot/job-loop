"""FastAPI 应用入口：/api/* 为接口，其余路径服务前端构建产物 web/dist。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from server.api import api_router
from server.config import WEB_DIST, ensure_dirs

ensure_dirs()

app = FastAPI(title="求职闭环系统", version="0.1.0")
app.include_router(api_router)


@app.exception_handler(ValueError)
def value_error_handler(request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


if WEB_DIST.exists():
    # assets 带内容哈希，可长缓存；index.html 禁缓存（否则重构建后浏览器拿旧引用 → 白屏）
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        resp = FileResponse(WEB_DIST / "index.html", media_type="text/html")
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
else:
    @app.get("/")
    def no_frontend():
        return {"hint": "前端未构建：cd web && npm install && npm run build，然后重启本服务",
                "api_docs": "/docs"}
