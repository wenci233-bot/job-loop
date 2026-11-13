from __future__ import annotations

import threading
import time
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from server.services import aimatch as aimatch_svc
from server.services import parse as parse_svc
from server.storage import inbox as inbox_store

router = APIRouter(prefix="/inbox", tags=["inbox"])

# 后台匹配任务（进程内）：{task_id: {status, progress, results, error}}
_MATCH_TASKS: dict[str, dict] = {}


class ParseBody(BaseModel):
    text: str


class SaveBody(BaseModel):
    company: str
    role: str
    text: str
    parsed: dict = {}
    channel: str = "手动贴入"
    status: str = "待评估"


class StatusBody(BaseModel):
    status: str


@router.post("/parse")
def parse_jd(body: ParseBody):
    text = body.text.strip()
    if len(text) < 30:
        raise HTTPException(status_code=400, detail="JD 文本太短（至少 30 字），请完整粘贴岗位描述")
    return parse_svc.heuristic_parse(text)


@router.post("/save")
def save_jd(body: SaveBody):
    if not body.company.strip() or not body.role.strip() or not body.text.strip():
        raise HTTPException(status_code=400, detail="公司、岗位与 JD 文本不能为空")
    return inbox_store.save_entry(body.company.strip(), body.role.strip(),
                                  body.text, body.parsed, body.channel, body.status)


@router.get("/list")
def list_entries():
    return {"entries": inbox_store.list_entries()}


@router.post("/{entry_id}/status")
def set_status(entry_id: str, body: StatusBody):
    e = inbox_store.update_entry(entry_id, status=body.status)
    if not e:
        raise HTTPException(status_code=404, detail=f"岗位 #{entry_id} 不存在")
    return e


class DeleteBody(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=500)
    confirmed: Literal[True]


@router.post("/delete")
def delete_entries(body: DeleteBody):
    if not body.ids:
        raise HTTPException(status_code=400, detail="未选择要删除的条目")
    return {"deleted": inbox_store.delete_entries(body.ids)}


class AiMatchBody(BaseModel):
    directions: list[str] = []
    cities: list[str] = []
    job_type: str = "校招"
    categories: list[str] = []


@router.post("/ai-match/start")
def ai_match_start(body: AiMatchBody):
    """后台启动匹配：立即返回 task_id，前端轮询进度；切页不影响任务。"""
    directions = [d.strip() for d in body.directions if d.strip()]
    cities = [c.strip() for c in body.cities if c.strip()]
    categories = [c.strip() for c in body.categories if c.strip()]
    if not directions:
        raise HTTPException(status_code=400, detail="请选择或输入意向岗位")
    if body.job_type not in aimatch_svc.JOB_TYPES:
        raise HTTPException(status_code=400, detail=f"求职类型必须是 {'/'.join(aimatch_svc.JOB_TYPES)} 之一")
    task_id = uuid.uuid4().hex[:10]
    _MATCH_TASKS[task_id] = {"status": "running", "progress": "启动中…", "results": None, "error": None}

    def _run():
        t0 = time.time()
        try:
            results = aimatch_svc.match(
                directions, cities, body.job_type, categories,
                progress_cb=lambda msg: _MATCH_TASKS[task_id].update(progress=msg))
            _MATCH_TASKS[task_id].update(status="done", results=results,
                                         progress=f"完成，共 {len(results)} 条（{time.time() - t0:.0f} 秒）")
        except Exception as e:
            _MATCH_TASKS[task_id].update(status="error", error=str(e)[:200])

    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id}


@router.get("/ai-match/task/{task_id}")
def ai_match_task(task_id: str):
    task = _MATCH_TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在（服务可能已重启），请重新匹配")
    return {k: v for k, v in task.items()}
