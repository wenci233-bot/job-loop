from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from server.services import interview as interview_svc

router = APIRouter(prefix="/interview", tags=["interview"])


@router.get("/applications")
def applications():
    return {"rows": interview_svc.list_applications()}


@router.get("/prep")
def get_prep(company: str, role: str):
    return {"prep": interview_svc.get_prep(company, role)}


class GenerateBody(BaseModel):
    company: str
    role: str


@router.post("/generate/start")
def generate_start(body: GenerateBody):
    """后台生成准备包：立即返回 task_id，前端轮询进度；切页不中断。"""
    return {"task_id": interview_svc.start_generation(body.company, body.role)}


@router.get("/generate/task/{task_id}")
def generate_task(task_id: str):
    task = interview_svc.get_generation_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在（服务可能已重启），请重新生成")
    return task


class MockTurnBody(BaseModel):
    company: str
    role: str
    job_type: str = "校招"
    round_hint: str = "一面技术主管"
    history: list[dict] = []


@router.post("/mock")
def mock_turn(body: MockTurnBody):
    try:
        return interview_svc.mock_turn(body.company, body.role, body.job_type,
                                       body.round_hint, body.history)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 调用失败：{e}")


class MockReportBody(BaseModel):
    company: str
    role: str
    history: list[dict] = []


@router.post("/report")
def mock_report(body: MockReportBody):
    if len(body.history) < 2:
        raise HTTPException(status_code=400, detail="对话太短，至少完成一轮问答")
    try:
        return interview_svc.mock_report(body.company, body.role, body.history)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 调用失败：{e}")


class MockSaveBody(BaseModel):
    company: str
    role: str
    history: list[dict] = []
    report: dict = {}


@router.post("/mock/save")
def save_mock(body: MockSaveBody):
    """保存本场模拟面试（完整对话 + 逐题报告），供历史回看。"""
    if len(body.history) < 2:
        raise HTTPException(status_code=400, detail="对话太短，至少完成一轮问答")
    if not body.report:
        raise HTTPException(status_code=400, detail="缺少评估报告")
    session = interview_svc.save_mock(body.company, body.role, body.history, body.report)
    return {"session": session}


@router.get("/mock/list")
def list_mocks(company: str, role: str):
    return {"sessions": interview_svc.list_mocks(company, role)}


@router.post("/generate/task/{task_id}/stop")
def stop_task(task_id: str):
    task = interview_svc.stop_generation(task_id)
    if task is None:
        raise HTTPException(404, '任务不存在（服务可能已重启）')
    return task


class DeleteMockBody(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=300)
    session_id: str = Field(min_length=1, max_length=100)
    confirmed: Literal[True]


@router.post('/mock/delete')
def delete_mock(body: DeleteMockBody):
    try:
        deleted = interview_svc.delete_mock(body.company, body.role, body.session_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {'deleted': deleted, 'session_id': body.session_id}
