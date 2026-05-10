"""Task model for the background task queue."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def _new_task_id() -> str:
    return "task_" + str(uuid.uuid4()).replace("-", "")[:12]


class Task(BaseModel):
    id: str = Field(default_factory=_new_task_id)
    type: str                    # e.g. "dataset_analysis", "read_file", "generate_code"
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.QUEUED
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    project_id: Optional[str] = None


class CreateTaskRequest(BaseModel):
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    project_id: Optional[str] = None
