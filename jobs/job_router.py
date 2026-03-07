"""Job submission and result-polling router.

Endpoints
---------
POST /api/v1/jobs/run_agent      — enqueue an agent orchestration job
POST /api/v1/jobs/run_plugin     — enqueue a plugin execution job
POST /api/v1/jobs/process_file   — enqueue a workstation file-processing job
GET  /api/v1/jobs/{job_id}       — poll job status / result

All responses wrap data in the standard ApiResponse envelope:
    { status, timestamp, request_id, data, meta, errors }
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _envelope(data: Any, status: str = "success") -> Dict[str, Any]:
    now = datetime.utcnow()
    return {
        "status": status,
        "timestamp": now.isoformat() + "Z",
        "request_id": str(int(now.timestamp() * 1000)),
        "data": data,
        "meta": {"confidence": None, "priority": None, "media": None},
        "errors": None,
    }


def _job_status(result: AsyncResult) -> Dict[str, Any]:
    """Convert a Celery AsyncResult to a JSON-safe status dict."""
    state = result.state  # PENDING | STARTED | SUCCESS | FAILURE | REVOKED

    payload: Dict[str, Any] = {
        "job_id": result.id,
        "state": state,
    }

    if state == "SUCCESS":
        payload["status"] = "completed"
        payload["result"] = result.result
    elif state == "FAILURE":
        payload["status"] = "failed"
        payload["error"] = str(result.result)
    elif state == "STARTED":
        payload["status"] = "running"
    else:
        payload["status"] = "queued"

    return payload


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class RunAgentRequest(BaseModel):
    goal: str = Field(..., description="The goal / prompt to pass to the agent.")
    context: str = Field("", description="Optional background context.")


class RunPluginRequest(BaseModel):
    plugin_name: str = Field(..., description="Registered plugin key.")
    input_data: Dict[str, Any] = Field(
        default_factory=dict, description="Plugin input payload."
    )


class ProcessFileRequest(BaseModel):
    upload_id: str = Field(..., description="UUID from the workstation upload.")
    filename: str = Field(..., description="Original filename.")
    task_type: str = Field(
        "read_file",
        description="Agent action: read_file | dataset_analysis | generate_code",
    )
    extra: Optional[Dict[str, Any]] = Field(
        None, description="Additional payload forwarded to the agent."
    )


# ---------------------------------------------------------------------------
# Submission endpoints
# ---------------------------------------------------------------------------

@router.post("/run_agent", summary="Enqueue an agent orchestration job")
async def submit_run_agent(body: RunAgentRequest):
    from tasks.agent_tasks import run_agent_task

    async_result = run_agent_task.delay(context=body.context, goal=body.goal)
    logger.info("Enqueued run_agent job %s  goal=%r", async_result.id, body.goal[:60])
    return _envelope(
        {"status": "accepted", "job_id": async_result.id, "type": "run_agent"}
    )


@router.post("/run_plugin", summary="Enqueue a plugin execution job")
async def submit_run_plugin(body: RunPluginRequest):
    from tasks.plugin_tasks import run_plugin

    async_result = run_plugin.delay(
        plugin_name=body.plugin_name, input_data=body.input_data
    )
    logger.info(
        "Enqueued run_plugin job %s  plugin=%r", async_result.id, body.plugin_name
    )
    return _envelope(
        {
            "status": "accepted",
            "job_id": async_result.id,
            "type": "run_plugin",
            "plugin_name": body.plugin_name,
        }
    )


@router.post("/process_file", summary="Enqueue a workstation file-processing job")
async def submit_process_file(body: ProcessFileRequest):
    from tasks.workspace_tasks import process_uploaded_file

    async_result = process_uploaded_file.delay(
        upload_id=body.upload_id,
        filename=body.filename,
        task_type=body.task_type,
        extra=body.extra,
    )
    logger.info(
        "Enqueued process_file job %s  upload_id=%r task_type=%r",
        async_result.id,
        body.upload_id,
        body.task_type,
    )
    return _envelope(
        {
            "status": "accepted",
            "job_id": async_result.id,
            "type": "process_file",
            "upload_id": body.upload_id,
            "filename": body.filename,
        }
    )


# ---------------------------------------------------------------------------
# Polling endpoint
# ---------------------------------------------------------------------------

@router.get("/{job_id}", summary="Poll job status and result")
async def get_job_status(job_id: str):
    # Basic validation — Celery UUIDs are 36 chars (with dashes)
    if len(job_id) > 64:
        raise HTTPException(status_code=400, detail="Invalid job_id")

    result = AsyncResult(job_id, app=celery_app)
    try:
        status = _job_status(result)
    except Exception as exc:
        logger.exception("Error fetching job %s", job_id)
        raise HTTPException(status_code=500, detail=str(exc))

    return _envelope(status)
