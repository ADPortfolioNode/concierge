"""Unit tests for the Phase 14 workstation upload layer.

Run with: python tests/test_workstation_upload.py
No external services required — all tests are offline.
"""
from __future__ import annotations

import os
import sys
import tempfile
import asyncio
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PASS = []
_FAIL = []


def ok(name: str) -> None:
    _PASS.append(name)
    print(f"  [PASS] {name}")


def fail(name: str, reason: str) -> None:
    _FAIL.append(name)
    print(f"  [FAIL] {name}: {reason}")


# ---------------------------------------------------------------------------
# workstation.file_processor tests
# ---------------------------------------------------------------------------

def test_is_allowed():
    from workstation.file_processor import is_allowed

    assert is_allowed("report.pdf"), "pdf should be allowed"
    assert is_allowed("data.csv"), "csv should be allowed"
    assert not is_allowed("malware.exe"), "exe should be blocked"
    assert not is_allowed("script.sh"), "sh should be blocked"
    ok("is_allowed")


def test_detect_mime_by_extension():
    from workstation.file_processor import detect_mime

    mime = detect_mime("hello.txt", b"")
    assert "text" in mime, f"expected text mime, got {mime}"
    ok("detect_mime_by_extension")


def test_detect_mime_magic_bytes_png():
    from workstation.file_processor import detect_mime

    png_header = b"\x89PNG\r\n\x1a\n"
    mime = detect_mime("image.bin", png_header)
    assert "png" in mime or "image" in mime, f"expected png/image, got {mime}"
    ok("detect_mime_magic_bytes_png")


def test_detect_mime_magic_bytes_pdf():
    from workstation.file_processor import detect_mime

    pdf_header = b"%PDF-1.4"
    mime = detect_mime("doc.bin", pdf_header)
    assert "pdf" in mime, f"expected pdf, got {mime}"
    ok("detect_mime_magic_bytes_pdf")


def test_extract_text_plain():
    from workstation.file_processor import extract_text
    import tempfile, pathlib

    content = "Hello, world!\nSecond line."
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "sample.txt"
        p.write_text(content, encoding="utf-8")
        text, meta = extract_text(str(p), "text/plain")
        assert "Hello" in text, f"extracted text: {text!r}"
        ok("extract_text_plain")


def test_extract_text_csv():
    from workstation.file_processor import extract_text
    import tempfile, pathlib

    content = "name,age\nAlice,30\nBob,25"
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "data.csv"
        p.write_text(content, encoding="utf-8")
        text, meta = extract_text(str(p), "text/csv")
        assert "Alice" in text, f"csv extraction: {text!r}"
        ok("extract_text_csv")


def test_extract_text_json():
    from workstation.file_processor import extract_text
    import tempfile, pathlib

    content = '{"key": "value", "items": [1, 2, 3]}'
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "data.json"
        p.write_text(content, encoding="utf-8")
        text, meta = extract_text(str(p), "application/json")
        assert "value" in text, f"json extraction: {text!r}"
        ok("extract_text_json")


# ---------------------------------------------------------------------------
# workstation.storage_service tests
# ---------------------------------------------------------------------------

def test_storage_allocation():
    from workstation.storage_service import allocation_dir, delete_upload

    uid = "test-alloc-001"
    d = allocation_dir(uid)
    assert os.path.isdir(d), f"allocation_dir should have created {d}"
    delete_upload(uid)
    assert not os.path.exists(d), "delete_upload should remove the directory"
    ok("storage_allocation")


def test_safe_path_traversal_blocked():
    from workstation.storage_service import safe_path, allocation_dir, delete_upload
    uid = "test-trav-002"
    allocation_dir(uid)
    try:
        from workstation.storage_service import safe_path
        safe_path(uid, "../../etc/passwd")
        fail("safe_path_traversal_blocked", "should have raised ValueError")
    except ValueError:
        ok("safe_path_traversal_blocked")
    except Exception as exc:
        fail("safe_path_traversal_blocked", str(exc))
    finally:
        delete_upload(uid)


# ---------------------------------------------------------------------------
# workstation.upload_router integration (FastAPI TestClient)
# ---------------------------------------------------------------------------

def test_upload_endpoint_txt():
    try:
        from fastapi.testclient import TestClient
        from app import app

        with tempfile.TemporaryDirectory() as _:
            client = TestClient(app, raise_server_exceptions=True)
            content = b"Hello from test upload!"
            resp = client.post(
                "/api/v1/workstation/upload",
                files={"file": ("test.txt", content, "text/plain")},
            )
            assert resp.status_code == 200, f"status {resp.status_code}: {resp.text}"
            body = resp.json()
            assert body.get("status") == "success", f"envelope status: {body}"
            data = body.get("data", {})
            assert "upload_id" in data, f"missing upload_id: {data}"
            assert "filename" in data, f"missing filename: {data}"
            ok("upload_endpoint_txt")
    except ImportError:
        print("  [SKIP] upload_endpoint_txt — TestClient not available")


def test_upload_endpoint_csv():
    try:
        from fastapi.testclient import TestClient
        from app import app

        csv_data = b"col1,col2\nA,1\nB,2\n"
        client = TestClient(app, raise_server_exceptions=True)
        resp = client.post(
            "/api/v1/workstation/upload",
            files={"file": ("data.csv", csv_data, "text/csv")},
        )
        assert resp.status_code == 200, f"status {resp.status_code}"
        body = resp.json()
        data = body.get("data", {})
        assert data.get("mime") in ("text/csv", "text/plain", "application/octet-stream", "text/csv; charset=utf-8") or "csv" in (data.get("mime") or ""), f"mime: {data.get('mime')}"
        ok("upload_endpoint_csv")
    except ImportError:
        print("  [SKIP] upload_endpoint_csv — TestClient not available")


def test_upload_endpoint_blocked_extension():
    try:
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/v1/workstation/upload",
            files={"file": ("evil.exe", b"\x4d\x5a", "application/octet-stream")},
        )
        assert resp.status_code == 400, f"expected 400, got {resp.status_code}"
        ok("upload_endpoint_blocked_extension")
    except ImportError:
        print("  [SKIP] upload_endpoint_blocked_extension — TestClient not available")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all():
    print("\n=== test_workstation_upload ===\n")

    test_is_allowed()
    test_detect_mime_by_extension()
    test_detect_mime_magic_bytes_png()
    test_detect_mime_magic_bytes_pdf()
    test_extract_text_plain()
    test_extract_text_csv()
    test_extract_text_json()
    test_storage_allocation()
    test_safe_path_traversal_blocked()
    test_upload_endpoint_txt()
    test_upload_endpoint_csv()
    test_upload_endpoint_blocked_extension()

    print(f"\nResults: {len(_PASS)} passed, {len(_FAIL)} failed")
    if _FAIL:
        print("FAILED:", _FAIL)
        sys.exit(1)
    else:
        print("All tests passed ✓")


if __name__ == "__main__":
    run_all()
