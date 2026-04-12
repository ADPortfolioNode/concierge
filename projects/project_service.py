"""In-memory + JSONL-backed project service.

Projects are kept in an in-memory dict for fast access and persisted to
``data/projects.jsonl`` on every mutation so they survive restarts.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .project_model import CreateProjectRequest, Project, ProjectFile

logger = logging.getLogger(__name__)


def _resolve_store_path() -> Path:
    raw_path = os.getenv("PROJECTS_FILE", "data/projects.jsonl")
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / path
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        test_file = path.parent / ".write_test"
        with test_file.open("w", encoding="utf-8") as fh:
            fh.write("x")
        test_file.unlink(missing_ok=True)
        return path
    except Exception:
        fallback = Path(tempfile.gettempdir()) / path.name
        try:
            fallback.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        logger.warning("Could not use project storage path %s; falling back to %s", path, fallback)
        return fallback


_STORE_PATH = _resolve_store_path()
_projects: Dict[str, Project] = {}
_lock = threading.RLock()


# --------------------------------------------------------------------------- #
# Persistence helpers                                                           #
# --------------------------------------------------------------------------- #

def _load_from_disk() -> None:
    """Load projects from the JSONL backing file into memory."""
    if not _STORE_PATH.exists():
        return
    with _lock:
        with _STORE_PATH.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    p = Project(**obj)
                    _projects[p.id] = p
                except Exception:
                    logger.exception("Failed to parse project from disk: %s", line[:80])


def _flush_to_disk() -> None:
    """Overwrite the JSONL file with current in-memory state."""
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _STORE_PATH.open("w", encoding="utf-8") as fh:
        for project in _projects.values():
            fh.write(project.json() + "\n")


# Load persisted projects at import time.
try:
    _load_from_disk()
except Exception:
    logger.exception("Failed to load projects from disk on startup")


# --------------------------------------------------------------------------- #
# CRUD                                                                          #
# --------------------------------------------------------------------------- #

def create_project(req: CreateProjectRequest) -> Project:
    project = Project(name=req.name, description=req.description, meta=req.meta)
    with _lock:
        _projects[project.id] = project
        _flush_to_disk()
    logger.info("Project created: %s (%s)", project.name, project.id)
    return project


def list_projects() -> List[Project]:
    with _lock:
        return list(_projects.values())


def get_project(project_id: str) -> Optional[Project]:
    with _lock:
        return _projects.get(project_id)


def delete_project(project_id: str) -> bool:
    with _lock:
        if project_id not in _projects:
            return False
        del _projects[project_id]
        _flush_to_disk()
    return True


# --------------------------------------------------------------------------- #
# File attachment                                                               #
# --------------------------------------------------------------------------- #

def attach_file_to_project(project_id: str, file_info: dict) -> None:
    """Attach an uploaded file reference to an existing project."""
    with _lock:
        project = _projects.get(project_id)
        if project is None:
            raise KeyError(f"Project {project_id!r} not found")
        pf = ProjectFile(
            upload_id=file_info["upload_id"],
            filename=file_info["filename"],
            mime=file_info["mime"],
            size=file_info["size"],
        )
        project.files.append(pf)
        project.updated_at = datetime.utcnow().isoformat() + "Z"
        _flush_to_disk()


# --------------------------------------------------------------------------- #
# Task reference attachment                                                     #
# --------------------------------------------------------------------------- #

def attach_task_to_project(project_id: str, task_id: str) -> None:
    with _lock:
        project = _projects.get(project_id)
        if project is None:
            raise KeyError(f"Project {project_id!r} not found")
        if task_id not in project.agent_tasks:
            project.agent_tasks.append(task_id)
        project.updated_at = datetime.utcnow().isoformat() + "Z"
        _flush_to_disk()
