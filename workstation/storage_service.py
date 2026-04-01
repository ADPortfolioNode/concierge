"""Safe temporary-file storage service.

All uploads land in a single root directory that is created on first use.
Every upload gets its own UUID sub-directory to prevent collisions and
directory-traversal attacks.
"""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

# Root for all uploaded files. Override via `UPLOAD_ROOT` env var.
# Behavior (best-effort, zero-regression):
# - If `UPLOAD_ROOT` is set, use it.
# - Otherwise prefer a writable `/tmp/concierge_uploads` (serverless-friendly).
# - If `/tmp` is not writable (e.g., some constrained build environments),
#   fall back to a repo-local `media/uploads` directory for local development.
def _default_upload_root() -> Path:
    env_val = os.getenv("UPLOAD_ROOT")
    if env_val:
        return Path(env_val)

    candidates = [Path("/tmp/concierge_uploads"), Path(__file__).resolve().parent.parent / "media" / "uploads"]
    for cand in candidates:
        try:
            cand.mkdir(parents=True, exist_ok=True)
            # quick writable check: try creating and removing a small file
            test_file = cand / ".write_test"
            with test_file.open("w", encoding="utf-8") as f:
                f.write("ok")
            test_file.unlink()
            return cand
        except Exception:
            # not writable or other error, try next candidate
            continue

    # Last-resort: use a relative uploads directory in the current working dir.
    fallback = Path.cwd() / "uploads"
    try:
        fallback.mkdir(parents=True, exist_ok=True)
    except Exception:
        # If even this fails, raise an explicit error so callers can handle it.
        raise RuntimeError("No writable upload root available; set UPLOAD_ROOT environment variable.")
    return fallback


_UPLOAD_ROOT = _default_upload_root()


def _uploads_root() -> Path:
    _UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    return _UPLOAD_ROOT


def allocation_dir(upload_id: Optional[str] = None) -> Path:
    """Return (and create) a per-upload directory.

    Parameters
    ----------
    upload_id:
        Caller-supplied ID. If ``None`` a new UUID4 is generated.
    """
    uid = upload_id or str(uuid.uuid4())
    target = _uploads_root() / uid
    target.mkdir(parents=True, exist_ok=True)
    return target


def safe_path(upload_id: str, filename: str) -> Path:
    """Return the absolute path for *filename* within *upload_id*.

    Raises ``ValueError`` if the resolved path would escape the upload
    directory (path-traversal guard).
    """
    root = _uploads_root() / upload_id
    # Resolve without following symlinks first to detect traversal attempts.
    candidate = (root / Path(filename).name).resolve()
    root_resolved = root.resolve()
    if not str(candidate).startswith(str(root_resolved)):
        raise ValueError(f"Path traversal detected for filename {filename!r}")
    return candidate


def delete_upload(upload_id: str) -> None:
    """Remove a whole upload directory (idempotent)."""
    target = _uploads_root() / upload_id
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)


def upload_root() -> Path:
    """Public accessor for the uploads root path."""
    return _uploads_root()
