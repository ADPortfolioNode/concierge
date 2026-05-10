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

# Root for all uploaded files.  Override via UPLOAD_ROOT env var.
_UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", "/tmp/concierge_uploads"))


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
