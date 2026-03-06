"""Unit tests for Phase 16 file agents and task queue.

Run with: python tests/test_file_agents.py
No external services required — all tests run offline.
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import uuid

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
# _sandbox path-safety tests
# ---------------------------------------------------------------------------

def _setup_upload(content: str = "hello\nworld\n") -> tuple[str, str]:
    """Write a temp file in the upload sandbox, return (upload_id, filename)."""
    from workstation.storage_service import allocation_dir

    uid = str(uuid.uuid4())
    d = allocation_dir(uid)
    fname = "sample.txt"
    with open(os.path.join(d, fname), "w", encoding="utf-8") as f:
        f.write(content)
    return uid, fname


def _teardown_upload(uid: str) -> None:
    from workstation.storage_service import delete_upload

    delete_upload(uid)


def test_sandbox_read_file():
    uid, fname = _setup_upload("foo bar baz\n")
    try:
        from agents.file_agents._sandbox import read_file_safe

        text = read_file_safe(uid, fname)
        assert "foo bar baz" in text, f"expected content in '{text}'"
        ok("sandbox_read_file")
    finally:
        _teardown_upload(uid)


def test_sandbox_write_file():
    uid, fname = _setup_upload("initial\n")
    try:
        from agents.file_agents._sandbox import write_file_safe, read_file_safe

        write_file_safe(uid, fname, "replaced\n")
        text = read_file_safe(uid, fname)
        assert "replaced" in text
        assert "initial" not in text
        ok("sandbox_write_file")
    finally:
        _teardown_upload(uid)


def test_sandbox_append_file():
    uid, fname = _setup_upload("line1\n")
    try:
        from agents.file_agents._sandbox import append_file_safe, read_file_safe

        append_file_safe(uid, fname, "line2\n")
        text = read_file_safe(uid, fname)
        assert "line1" in text
        assert "line2" in text
        ok("sandbox_append_file")
    finally:
        _teardown_upload(uid)


def test_sandbox_path_traversal_blocked():
    uid, _ = _setup_upload()
    try:
        from agents.file_agents._sandbox import resolve_safe_path

        try:
            resolve_safe_path(uid, "../../etc/passwd")
            fail("sandbox_path_traversal_blocked", "should have raised ValueError")
        except ValueError:
            ok("sandbox_path_traversal_blocked")
    finally:
        _teardown_upload(uid)


def test_sandbox_missing_file_raises():
    uid = str(uuid.uuid4())
    from workstation.storage_service import allocation_dir

    allocation_dir(uid)
    try:
        from agents.file_agents._sandbox import read_file_safe

        try:
            read_file_safe(uid, "does_not_exist.txt")
            fail("sandbox_missing_file_raises", "should have raised FileNotFoundError")
        except FileNotFoundError:
            ok("sandbox_missing_file_raises")
    finally:
        _teardown_upload(uid)


# ---------------------------------------------------------------------------
# FileReaderAgent tests
# ---------------------------------------------------------------------------

async def _test_file_reader_agent():
    from agents.file_agents.file_reader_agent import FileReaderAgent
    from tasks.task_model import Task, TaskStatus

    uid, fname = _setup_upload("read me please\n")
    try:
        agent = FileReaderAgent()
        task = Task(
            id="t-read-001",
            type="read_file",
            payload={"upload_id": uid, "filename": fname},
            status=TaskStatus.RUNNING,
        )
        result = await agent.handle_task(task)
        assert "read me please" in result["content"]
        assert result["chars"] > 0
        ok("file_reader_agent_handle_task")
    finally:
        _teardown_upload(uid)


def test_file_reader_agent():
    asyncio.run(_test_file_reader_agent())


# ---------------------------------------------------------------------------
# FileEditorAgent tests
# ---------------------------------------------------------------------------

async def _test_file_editor_write():
    from agents.file_agents.file_editor_agent import FileEditorAgent
    from agents.file_agents._sandbox import read_file_safe
    from tasks.task_model import Task, TaskStatus

    uid, fname = _setup_upload("old content\n")
    try:
        agent = FileEditorAgent()
        task = Task(
            id="t-write-001",
            type="write_file",
            payload={"upload_id": uid, "filename": fname, "content": "new content\n"},
            status=TaskStatus.RUNNING,
        )
        result = await agent.handle_task(task)
        assert result["bytes_written"] > 0
        assert "new content" in read_file_safe(uid, fname)
        ok("file_editor_agent_write")
    finally:
        _teardown_upload(uid)


async def _test_file_editor_append():
    from agents.file_agents.file_editor_agent import FileEditorAgent
    from agents.file_agents._sandbox import read_file_safe
    from tasks.task_model import Task, TaskStatus

    uid, fname = _setup_upload("first\n")
    try:
        agent = FileEditorAgent()
        task = Task(
            id="t-append-001",
            type="append_file",
            payload={"upload_id": uid, "filename": fname, "content": "second\n"},
            status=TaskStatus.RUNNING,
        )
        result = await agent.handle_append_task(task)
        assert result["bytes_appended"] > 0
        text = read_file_safe(uid, fname)
        assert "first" in text and "second" in text
        ok("file_editor_agent_append")
    finally:
        _teardown_upload(uid)


def test_file_editor_agent():
    asyncio.run(_test_file_editor_write())
    asyncio.run(_test_file_editor_append())


# ---------------------------------------------------------------------------
# CodeExecutionAgent tests
# ---------------------------------------------------------------------------

async def _test_code_exec_agent():
    from agents.file_agents.code_execution_agent import CodeExecutionAgent
    from tasks.task_model import Task, TaskStatus

    agent = CodeExecutionAgent()
    task = Task(
        id="t-code-001",
        type="generate_code",
        payload={"context": "print all numbers from 1 to 10", "language": "python"},
        status=TaskStatus.RUNNING,
    )
    result = await agent.handle_task(task)
    assert result["language"] == "python"
    assert result["chars"] > 0
    assert isinstance(result["code"], str) and len(result["code"]) > 5
    ok("code_execution_agent")


def test_code_execution_agent():
    asyncio.run(_test_code_exec_agent())


# ---------------------------------------------------------------------------
# DatasetAnalysisAgent tests
# ---------------------------------------------------------------------------

async def _test_dataset_agent():
    from agents.file_agents.dataset_analysis_agent import DatasetAnalysisAgent
    from tasks.task_model import Task, TaskStatus

    csv_content = "name,score,grade\nAlice,95,A\nBob,80,B\nCarol,72,B\nDan,60,D\n"
    uid, fname = _setup_upload(csv_content)
    # rename to .csv
    from workstation.storage_service import upload_root

    csv_path = os.path.join(upload_root(), uid, "stats.csv")
    txt_path = os.path.join(upload_root(), uid, fname)
    os.rename(txt_path, csv_path)

    try:
        agent = DatasetAnalysisAgent()
        task = Task(
            id="t-ds-001",
            type="dataset_analysis",
            payload={"upload_id": uid, "filename": "stats.csv"},
            status=TaskStatus.RUNNING,
        )
        result = await agent.handle_task(task)
        assert result["row_count"] == 4, f"expected 4 rows, got {result['row_count']}"
        assert "name" in result["columns"]
        assert "score" in result["columns"]
        stats = result["column_stats"]
        assert stats["score"]["numeric"] is True
        assert stats["score"]["max"] == 95.0
        assert stats["name"]["numeric"] is False
        ok("dataset_analysis_agent")
    finally:
        _teardown_upload(uid)


def test_dataset_analysis_agent():
    asyncio.run(_test_dataset_agent())


# ---------------------------------------------------------------------------
# TaskQueue tests
# ---------------------------------------------------------------------------

async def _test_task_queue_enqueue_and_process():
    from tasks.task_queue import TaskQueue
    from tasks.task_model import Task, TaskStatus

    q = TaskQueue()

    async def echo_handler(task):
        return {"echo": task.payload.get("msg")}

    q.register_handler("echo", echo_handler)
    await q.start_worker()

    try:
        task = Task(type="echo", payload={"msg": "hello-queue"})
        queued = q.enqueue(task)
        assert queued.status == TaskStatus.QUEUED

        # Wait for the worker to process it.
        for _ in range(20):
            await asyncio.sleep(0.1)
            t = q.get(queued.id)
            if t and t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                break

        final = q.get(queued.id)
        assert final is not None
        assert final.status == TaskStatus.COMPLETED, f"status: {final.status}, error: {final.error}"
        assert final.result == {"echo": "hello-queue"}
        ok("task_queue_enqueue_and_process")
    finally:
        # stop the internal worker task
        if q._worker_task:
            q._worker_task.cancel()


async def _test_task_queue_failed_handler():
    from tasks.task_queue import TaskQueue
    from tasks.task_model import TaskStatus, Task

    q = TaskQueue()

    async def boom_handler(task):
        raise RuntimeError("intentional failure")

    q.register_handler("boom", boom_handler)
    await q.start_worker()

    try:
        task = Task(type="boom", payload={})
        queued = q.enqueue(task)

        for _ in range(20):
            await asyncio.sleep(0.1)
            t = q.get(queued.id)
            if t and t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                break

        final = q.get(queued.id)
        assert final.status == TaskStatus.FAILED, f"expected FAILED, got {final.status}"
        assert "intentional failure" in (final.error or "")
        ok("task_queue_failed_handler")
    finally:
        if q._worker_task:
            q._worker_task.cancel()


def test_task_queue():
    asyncio.run(_test_task_queue_enqueue_and_process())
    asyncio.run(_test_task_queue_failed_handler())


# ---------------------------------------------------------------------------
# Task router endpoint tests
# ---------------------------------------------------------------------------

def test_task_endpoints():
    try:
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app, raise_server_exceptions=True)

        # Submit a task
        resp = client.post(
            "/api/v1/tasks",
            json={"type": "read_file", "payload": {"upload_id": "x", "filename": "y.txt"}},
        )
        assert resp.status_code == 200, f"POST /api/v1/tasks: {resp.status_code} {resp.text}"
        body = resp.json()
        assert body.get("status") == "success"
        task_id = body["data"]["id"]

        # Poll task
        resp2 = client.get(f"/api/v1/tasks/{task_id}")
        assert resp2.status_code == 200
        assert resp2.json()["data"]["id"] == task_id

        # List tasks
        resp3 = client.get("/api/v1/tasks")
        assert resp3.status_code == 200
        tasks = resp3.json()["data"]
        assert any(t["id"] == task_id for t in tasks)

        ok("task_endpoints")
    except ImportError:
        print("  [SKIP] task_endpoints — TestClient not available")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all():
    print("\n=== test_file_agents ===\n")

    test_sandbox_read_file()
    test_sandbox_write_file()
    test_sandbox_append_file()
    test_sandbox_path_traversal_blocked()
    test_sandbox_missing_file_raises()
    test_file_reader_agent()
    test_file_editor_agent()
    test_code_execution_agent()
    test_dataset_analysis_agent()
    test_task_queue()
    test_task_endpoints()

    print(f"\nResults: {len(_PASS)} passed, {len(_FAIL)} failed")
    if _FAIL:
        print("FAILED:", _FAIL)
        sys.exit(1)
    else:
        print("All tests passed ✓")


if __name__ == "__main__":
    run_all()
