"""Unit tests for the Phase 15 projects / workspace system.

Run with: python tests/test_projects.py
No external services required.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_PASS = []
_FAIL = []


def ok(name: str) -> None:
    _PASS.append(name)
    print(f"  [PASS] {name}")


def fail(name: str, reason: str) -> None:
    _FAIL.append(name)
    print(f"  [FAIL] {name}: {reason}")


# ---------------------------------------------------------------------------
# Helpers — reset the module-level store between tests
# ---------------------------------------------------------------------------

def _reset_store() -> None:
    """Clear the in-memory project store without touching disk."""
    import projects.project_service as svc
    with svc._lock:
        svc._projects.clear()


# ---------------------------------------------------------------------------
# project_model tests
# ---------------------------------------------------------------------------

def test_project_model_creation():
    from projects.project_model import Project, CreateProjectRequest

    req = CreateProjectRequest(name="My Project", description="A test project")
    p = Project(name=req.name, description=req.description)
    assert p.id is not None
    assert p.name == "My Project"
    assert p.files == []
    ok("project_model_creation")


def test_project_file_model():
    from projects.project_model import ProjectFile

    pf = ProjectFile(upload_id="up-001", filename="data.csv", mime="text/csv", size=1024)
    assert pf.upload_id == "up-001"
    assert pf.filename == "data.csv"
    ok("project_file_model")


# ---------------------------------------------------------------------------
# project_service tests (module-level functions)
# ---------------------------------------------------------------------------

def test_create_project():
    _reset_store()
    from projects.project_model import CreateProjectRequest
    import projects.project_service as svc

    req = CreateProjectRequest(name="Alpha", description="First project")
    p = svc.create_project(req)
    assert p.name == "Alpha"
    assert p.id is not None
    ok("create_project")


def test_list_projects():
    _reset_store()
    from projects.project_model import CreateProjectRequest
    import projects.project_service as svc

    svc.create_project(CreateProjectRequest(name="A"))
    svc.create_project(CreateProjectRequest(name="B"))
    all_p = svc.list_projects()
    assert len(all_p) == 2, f"expected 2, got {len(all_p)}"
    ok("list_projects")


def test_get_project():
    _reset_store()
    from projects.project_model import CreateProjectRequest
    import projects.project_service as svc

    p = svc.create_project(CreateProjectRequest(name="GetMe"))
    fetched = svc.get_project(p.id)
    assert fetched is not None
    assert fetched.name == "GetMe"
    ok("get_project")


def test_get_project_missing():
    _reset_store()
    import projects.project_service as svc

    result = svc.get_project("does-not-exist")
    assert result is None
    ok("get_project_missing")


def test_delete_project():
    _reset_store()
    from projects.project_model import CreateProjectRequest
    import projects.project_service as svc

    p = svc.create_project(CreateProjectRequest(name="DelMe"))
    deleted = svc.delete_project(p.id)
    assert deleted is True
    assert svc.get_project(p.id) is None
    ok("delete_project")


def test_delete_project_missing():
    _reset_store()
    import projects.project_service as svc

    result = svc.delete_project("ghost-id")
    assert result is False
    ok("delete_project_missing")


def test_attach_file_to_project():
    _reset_store()
    from projects.project_model import CreateProjectRequest
    import projects.project_service as svc

    p = svc.create_project(CreateProjectRequest(name="Files"))
    svc.attach_file_to_project(
        p.id,
        {"upload_id": "up-abc", "filename": "report.pdf", "mime": "application/pdf", "size": 50000},
    )
    updated = svc.get_project(p.id)
    assert updated is not None
    assert len(updated.files) == 1
    assert updated.files[0].upload_id == "up-abc"
    ok("attach_file_to_project")


# ---------------------------------------------------------------------------
# project_router endpoint tests
# ---------------------------------------------------------------------------

def test_project_crud_endpoints():
    try:
        _reset_store()
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app, raise_server_exceptions=True)

        # Create
        resp = client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "description": "desc"},
        )
        assert resp.status_code == 200, f"create status {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body.get("status") == "success"
        project_id = body["data"]["id"]

        # Get
        resp2 = client.get(f"/api/v1/projects/{project_id}")
        assert resp2.status_code == 200
        assert resp2.json()["data"]["name"] == "Test Project"

        # List
        resp3 = client.get("/api/v1/projects")
        assert resp3.status_code == 200
        projects = resp3.json()["data"]
        assert any(p["id"] == project_id for p in projects)

        # Delete
        resp4 = client.delete(f"/api/v1/projects/{project_id}")
        assert resp4.status_code == 200

        ok("project_crud_endpoints")
    except ImportError:
        print("  [SKIP] project_crud_endpoints — TestClient not available")


def test_project_get_missing():
    try:
        _reset_store()
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/projects/does-not-exist-xyz")
        assert resp.status_code == 404, f"expected 404, got {resp.status_code}"
        ok("project_get_missing")
    except ImportError:
        print("  [SKIP] project_get_missing — TestClient not available")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all():
    print("\n=== test_projects ===\n")

    test_project_model_creation()
    test_project_file_model()
    test_create_project()
    test_list_projects()
    test_get_project()
    test_get_project_missing()
    test_delete_project()
    test_delete_project_missing()
    test_attach_file_to_project()
    test_project_crud_endpoints()
    test_project_get_missing()

    print(f"\nResults: {len(_PASS)} passed, {len(_FAIL)} failed")
    if _FAIL:
        print("FAILED:", _FAIL)
        sys.exit(1)
    else:
        print("All tests passed ✓")


if __name__ == "__main__":
    run_all()
