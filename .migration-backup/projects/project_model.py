"""Pydantic models for the project/workspace system."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
import uuid


def _new_id() -> str:
    return "proj_" + str(uuid.uuid4()).replace("-", "")[:12]


class ProjectFile(BaseModel):
    upload_id: str
    filename: str
    mime: str
    size: int
    attached_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ChatRef(BaseModel):
    """Lightweight reference to a chat message stored elsewhere."""
    message_id: str
    role: str
    content_preview: str
    timestamp: str


class Project(BaseModel):
    id: str = Field(default_factory=_new_id)
    name: str
    description: Optional[str] = None
    files: List[ProjectFile] = Field(default_factory=list)
    chats: List[ChatRef] = Field(default_factory=list)
    memory_refs: List[str] = Field(default_factory=list)
    agent_tasks: List[str] = Field(default_factory=list)  # task IDs
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    meta: Dict[str, Any] = Field(default_factory=dict)


class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
