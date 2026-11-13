from __future__ import annotations

from concurrent.futures import CancelledError
from copy import deepcopy
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
_MATCH_LOCK = threading.RLock()
_MATCH_CANCEL = {}


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
    exclude_companies: list[str] = Field(default_factory=list, max_length=5000)
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
    event = threading.Event()
    with _MATCH_LOCK:
        _MATCH_CANCEL[task_id] = event
        _MATCH_TASKS[task_id] = dict(status='running', progress='启动中…', results=None, error=None, warning='', done=0, total=3)

    def progress(message, done):
        with _MATCH_LOCK:
            if not event.is_set():
                _MATCH_TASKS[task_id].update(progress=message, done=done)

    def warning(message):
        with _MATCH_LOCK:
            if not event.is_set():
                _MATCH_TASKS[task_id]['warning'] = message

    def run():
        try:
            results = aimatch_svc.match(directions, cities, body.job_type, categories,
                progress_cb=progress, exclude_companies=body.exclude_companies,
                cancel_event=event, warning_cb=warning)
            with _MATCH_LOCK:
                if not event.is_set():
                    _MATCH_TASKS[task_id].update(status='done', results=results, done=3, progress=f'完成，共 {len(results)} 条')
        except CancelledError:
            pass
        except Exception as exc:
            with _MATCH_LOCK:
                if not event.is_set():
                    _MATCH_TASKS[task_id].update(status='error', error=str(exc)[:300])
        finally:
            with _MATCH_LOCK:
                _MATCH_CANCEL.pop(task_id, None)

    threading.Thread(target=run, daemon=True).start()
    return {'task_id': task_id}


@router.get('/ai-match/task/{task_id}')
def ai_match_task(task_id: str):
    with _MATCH_LOCK:
        task = _MATCH_TASKS.get(task_id)
        if task is None:
            raise HTTPException(404, '任务不存在（服务可能已重启），请重新匹配')
        return deepcopy(task)


@router.post('/ai-match/task/{task_id}/stop')
def stop_ai_match(task_id: str):
    with _MATCH_LOCK:
        task = _MATCH_TASKS.get(task_id)
        if task is None:
            raise HTTPException(404, '任务不存在（服务可能已重启）')
        if task['status'] == 'running':
            _MATCH_CANCEL[task_id].set()
            task.update(status='cancelled', progress='匹配已停止，上一批结果已保留', results=None, error=None)
        return deepcopy(task)
