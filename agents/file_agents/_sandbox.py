"""Shared sandbox utilities for all file agents.

All file operations MUST go through these helpers to ensure:
  - Paths stay within the uploads root
  - No shell commands are executed
  - File sizes are bounded
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from workstation.storage_service import upload_root

logger = logging.getLogger(__name__)

MAX_READ_BYTES = 10 * 1024 * 1024  # 10 MB read cap per operation


def resolve_safe_path(upload_id: str, filename: Optional[str] = None) -> Path:
    """Return a sandboxed absolute path.

    Parameters
    ----------
    upload_id:
        The upload directory UUID.
    filename:
        Optional filename within the upload dir. If ``None`` the directory
        itself is returned.

    Raises
    ------
    ValueError
        If the resolved path would escape the uploads root.
    """
    root = upload_root()
    if filename:
        candidate = (root / upload_id / Path(filename).name).resolve()
    else:
        candidate = (root / upload_id).resolve()

    root_resolved = root.resolve()
    if not str(candidate).startswith(str(root_resolved)):
        raise ValueError(
            f"Path traversal attempt: upload_id={upload_id!r} filename={filename!r}"
        )
    return candidate


def read_file_safe(upload_id: str, filename: str) -> str:
    """Read a file from the sandbox, returning text content."""
    path = resolve_safe_path(upload_id, filename)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path.name}")
    size = path.stat().st_size
    if size > MAX_READ_BYTES:
        raise ValueError(
            f"File {path.name!r} is {size} bytes — exceeds {MAX_READ_BYTES} read cap."
        )
    return path.read_text(encoding="utf-8", errors="replace")


def write_file_safe(upload_id: str, filename: str, content: str) -> int:
    """Write *content* to a sandboxed file.  Returns bytes written."""
    path = resolve_safe_path(upload_id, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return len(content.encode("utf-8"))


def append_file_safe(upload_id: str, filename: str, content: str) -> int:
    """Append *content* to a sandboxed file. Returns new total bytes."""
    path = resolve_safe_path(upload_id, filename)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(content)
    return path.stat().st_size
