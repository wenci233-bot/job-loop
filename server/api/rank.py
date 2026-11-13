from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.services import careers as careers_svc
from server.services import rank as rank_svc
from server.storage import inbox as inbox_store
from server.storage import tracker as tracker_store

router = APIRouter(prefix="/rank", tags=["rank"])


class BatchBody(BaseModel):
    ids: list[str] = []


@router.post("/score/batch/start")
def score_batch_start(body: BatchBody):
    ids = [i for i in body.ids if str(i).strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="未选择要评估的岗位")
    return {"task_id": rank_svc.start_batch(ids)}


@router.get("/score/batch/{task_id}")
def score_batch_task(task_id: str):
    task = rank_svc.get_batch_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在（服务可能已重启）")
    return task


@router.get("/candidates")
def candidates():
    entries = inbox_store.list_entries()
    applied = {(row['company'], row['role']) for row in tracker_store.rows()}
    for e in entries:
        if (e['company'], e['role']) in applied:
            e['status'] = '已申请'
        e["text"] = inbox_store.entry_text(e["id"])
        e["apply_url"] = careers_svc.careers_url(e["company"])
    return {"entries": entries}


@router.post("/score/{entry_id}")
def score(entry_id: str):
    e = inbox_store.get_entry(entry_id)
    if not e:
        raise HTTPException(status_code=404, detail=f"岗位 #{entry_id} 不存在")
    text = inbox_store.entry_text(entry_id)
    result = rank_svc.evaluate(text, e.get("parsed"))
    status = "已否决" if result["veto"] else "已评估"
    rank = {k: result.get(k) for k in ("verdict", "dimensions", "strengths", "gaps", "suggestion", "estimated")}
    updated = inbox_store.update_entry(
        entry_id, score=result["score"], veto=result["veto"],
        reasons=result["reasons"], status=status, rank=rank)
    return {"entry": updated, "result": result}


@router.post("/score/batch/{task_id}/stop")
def stop_task(task_id: str):
    task = rank_svc.stop_batch(task_id)
    if task is None:
        raise HTTPException(404, '任务不存在（服务可能已重启）')
    return task
