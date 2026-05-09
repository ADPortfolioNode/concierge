"""FastAPI router for the background task queue."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from .task_model import CreateTaskRequest, Task
from .task_queue import get_queue

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _resp(data, status: str = "success") -> dict:
    from datetime import datetime
    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": str(int(datetime.utcnow().timestamp() * 1000)),
        "data": data,
        "meta": {"confidence": None, "priority": None, "media": None},
        "errors": None,
    }


def _task_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "type": task.type,
        "status": task.status.value,
        "payload": task.payload,
        "result": task.result,
        "error": task.error,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "project_id": task.project_id,
    }


@router.post("")
@router.post("/")
async def create_task(req: CreateTaskRequest):
    """Enqueue a new background task. Returns the task ID for polling."""
    task = Task(type=req.type, payload=req.payload, project_id=req.project_id)
    queued = get_queue().enqueue(task)

    # Optionally attach to project
    if req.project_id:
        try:
            from projects.project_service import attach_task_to_project
            attach_task_to_project(req.project_id, queued.id)
        except Exception:
            pass  # non-fatal

    return JSONResponse(content=_resp(_task_dict(queued)))


@router.get("/{task_id}")
async def get_task(task_id: str):
    """Poll task status and retrieve result when completed."""
    task = get_queue().get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found")
    return JSONResponse(content=_resp(_task_dict(task)))


@router.get("")
@router.get("/")
async def list_tasks():
    """List all tasks (for debugging/admin)."""
    tasks = get_queue().list_tasks()
    return JSONResponse(content=_resp([_task_dict(t) for t in tasks]))
