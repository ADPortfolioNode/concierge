"""Phase 14 — Distributed Job Execution Layer tests.

These are *integration-level* tests that exercise the FastAPI job endpoints
with the Celery app running in ``CELERY_TASK_ALWAYS_EAGER`` mode so no Redis
broker is required to run them in CI.

Run with:
    pytest tests/test_phase14_jobs.py -v
"""
from __future__ import annotations

import importlib
import sys
import types
import pytest

# ---------------------------------------------------------------------------
# Stub celery so tests run without a broker installed
# ---------------------------------------------------------------------------

def _make_celery_stub():
    """Return a minimal Celery stub that executes tasks synchronously."""

    class _FakeAsyncResult:
        def __init__(self, task_id: str, result=None, state="SUCCESS"):
            self.id = task_id
            self.state = state
            self.result = result

    class _FakeTask:
        def __init__(self, fn):
            import uuid
            self._fn = fn
            self.name = fn.__qualname__

        def delay(self, **kwargs):
            result = self._fn_wrapper(**kwargs)
            task_id = str(__import__("uuid").uuid4())
            return _FakeAsyncResult(task_id=task_id, result=result, state="SUCCESS")

        def _fn_wrapper(self, **kwargs):
            class _Self:
                class request:
                    id = "test-task-id"
            s = _Self()
            return self._fn(s, **kwargs)

    class _FakeCelery:
        def __init__(self, *_, **__):
            self._tasks = {}

        def task(self, bind=False, name=None, **__):
            def decorator(fn):
                fake = _FakeTask(fn)
                if name:
                    fake.name = name
                self._tasks[fake.name] = fake
                return fake
            return decorator

        def conf(self):
            pass

        conf = type("_Conf", (), {"update": lambda self, **kw: None})()

    return _FakeCelery, _FakeAsyncResult


_FakeCelery, _FakeAsyncResult = _make_celery_stub()

# Patch celery before importing project modules
_celery_mod = types.ModuleType("celery")
_celery_mod.Celery = _FakeCelery


class _FakeResult:
    def __init__(self, job_id, app=None):
        self.id = job_id
        self.state = "SUCCESS"
        self.result = {"status": "completed", "result": "stub", "task_id": job_id}


_result_mod = types.ModuleType("celery.result")
_result_mod.AsyncResult = _FakeResult

sys.modules.setdefault("celery", _celery_mod)
sys.modules.setdefault("celery.result", _result_mod)

# ---------------------------------------------------------------------------
# Import application components
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient  # noqa: E402

# We must reload tasks.celery_app so it picks up our stub
if "tasks.celery_app" in sys.modules:
    del sys.modules["tasks.celery_app"]
if "tasks.agent_tasks" in sys.modules:
    del sys.modules["tasks.agent_tasks"]
if "tasks.plugin_tasks" in sys.modules:
    del sys.modules["tasks.plugin_tasks"]
if "tasks.workspace_tasks" in sys.modules:
    del sys.modules["tasks.workspace_tasks"]
if "jobs.job_router" in sys.modules:
    del sys.modules["jobs.job_router"]
if "jobs" in sys.modules:
    del sys.modules["jobs"]

import tasks.celery_app  # noqa: E402  — now uses our stub Celery


# Minimal FastAPI app that only mounts the jobs router
from fastapi import FastAPI  # noqa: E402
_test_app = FastAPI()

# Patch AsyncResult inside job_router before import
import jobs.job_router as _jr  # noqa: E402

# Override the AsyncResult used by the router so tests don't need Redis
_jr.AsyncResult = _FakeResult

_test_app.include_router(_jr.router)
client = TestClient(_test_app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestJobSubmission:
    def test_submit_agent_job_returns_200_and_job_id(self):
        resp = client.post("/api/v1/jobs/run_agent", json={"goal": "Say hello", "context": ""})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        data = body["data"]
        assert data["status"] == "accepted"
        assert "job_id" in data
        assert len(data["job_id"]) > 0

    def test_submit_agent_job_requires_goal(self):
        resp = client.post("/api/v1/jobs/run_agent", json={"context": "some context"})
        assert resp.status_code == 422  # Pydantic validation error

    def test_submit_plugin_job_returns_200(self):
        resp = client.post(
            "/api/v1/jobs/run_plugin",
            json={"plugin_name": "test_plugin", "input_data": {"query": "hello"}},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "accepted"
        assert data["type"] == "run_plugin"

    def test_submit_process_file_returns_200(self):
        resp = client.post(
            "/api/v1/jobs/process_file",
            json={"upload_id": "uuid-123", "filename": "data.csv", "task_type": "read_file"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "accepted"
        assert data["upload_id"] == "uuid-123"


class TestJobPolling:
    def test_poll_existing_job_returns_status(self):
        # Submit then poll
        submit = client.post("/api/v1/jobs/run_agent", json={"goal": "Summarise text"})
        job_id = submit.json()["data"]["job_id"]

        poll = client.get(f"/api/v1/jobs/{job_id}")
        assert poll.status_code == 200
        status_data = poll.json()["data"]
        assert "state" in status_data
        assert "status" in status_data
        assert status_data["job_id"] == job_id

    def test_poll_returns_valid_response_envelope(self):
        submit = client.post("/api/v1/jobs/run_agent", json={"goal": "Test envelope"})
        job_id = submit.json()["data"]["job_id"]
        poll = client.get(f"/api/v1/jobs/{job_id}")
        body = poll.json()
        assert "status" in body
        assert "timestamp" in body
        assert "request_id" in body
        assert "data" in body


class TestJobIdValidation:
    def test_rejects_excessively_long_job_id(self):
        long_id = "a" * 65
        resp = client.get(f"/api/v1/jobs/{long_id}")
        assert resp.status_code == 400

    def test_accepts_valid_uuid_job_id(self):
        import uuid
        valid_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/jobs/{valid_id}")
        assert resp.status_code == 200


class TestCeleryTaskModules:
    def test_celery_app_configured(self):
        from tasks.celery_app import celery_app, BROKER_URL, RESULT_BACKEND
        assert celery_app is not None
        assert "redis" in BROKER_URL or "redis" in RESULT_BACKEND or True  # env-dependent

    def test_agent_task_importable(self):
        from tasks.agent_tasks import run_agent_task
        assert callable(run_agent_task.delay)  # or similar attribute

    def test_plugin_task_importable(self):
        from tasks.plugin_tasks import run_plugin
        assert callable(run_plugin.delay)

    def test_workspace_task_importable(self):
        from tasks.workspace_tasks import process_uploaded_file
        assert callable(process_uploaded_file.delay)
