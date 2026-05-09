"""FastAPI router for the projects/workspaces system."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from .project_model import CreateProjectRequest
from .project_service import (
    create_project,
    delete_project,
    get_project,
    list_projects,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


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


@router.post("")
async def create_project_endpoint(req: CreateProjectRequest):
    """Create a new project/workspace."""
    project = create_project(req)
    return JSONResponse(content=_resp(project.dict()))


@router.get("")
async def list_projects_endpoint():
    """List all projects."""
    projects = list_projects()
    return JSONResponse(content=_resp([p.dict() for p in projects]))


@router.get("/{project_id}")
async def get_project_endpoint(project_id: str):
    """Get a single project by ID."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id!r} not found")
    return JSONResponse(content=_resp(project.dict()))


@router.delete("/{project_id}")
async def delete_project_endpoint(project_id: str):
    """Delete a project by ID."""
    deleted = delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Project {project_id!r} not found")
    return JSONResponse(content=_resp({"deleted": project_id}))
