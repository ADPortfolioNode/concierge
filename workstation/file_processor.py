"""File type detection and text extraction.

Supports: txt, pdf, docx, csv, json.
Falls back to raw bytes when a dependency is unavailable.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)

# Optional heavy deps — imported lazily and guarded.
try:
    import pypdf  # type: ignore
    _PYPDF = True
except ImportError:
    _PYPDF = False

try:
    import docx  # python-docx  # type: ignore
    _DOCX = True
except ImportError:
    _DOCX = False

# --------------------------------------------------------------------------- #
# MIME / extension detection                                                    #
# --------------------------------------------------------------------------- #

_EXTENSION_MAP: Dict[str, str] = {
    ".txt":  "text/plain",
    ".pdf":  "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".csv":  "text/csv",
    ".json": "application/json",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".mp3":  "audio/mpeg",
    ".wav":  "audio/wav",
    ".mp4":  "video/mp4",
}

_ALLOWED_EXTENSIONS = set(_EXTENSION_MAP.keys())

# Magic-byte signatures for common types (offset, signature)
_MAGIC: list[Tuple[int, bytes, str]] = [
    (0, b"%PDF",          "application/pdf"),
    (0, b"\x50\x4b\x03\x04", "application/zip"),   # docx is a zip
    (0, b"\x89PNG\r\n",   "image/png"),
    (0, b"\xff\xd8\xff",  "image/jpeg"),
    (0, b"ID3",           "audio/mpeg"),
    (0, b"\xff\xfb",      "audio/mpeg"),
    (4, b"ftyp",          "video/mp4"),
]


def detect_mime(filename: str, header: bytes) -> str:
    """Return MIME type, preferring magic-byte detection over extension."""
    # 1. magic bytes
    for offset, sig, mime in _MAGIC:
        excerpt = header[offset: offset + len(sig)]
        if excerpt == sig:
            return mime
    # 2. extension
    ext = Path(filename).suffix.lower()
    if ext in _EXTENSION_MAP:
        return _EXTENSION_MAP[ext]
    # 3. stdlib fallback
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def is_allowed(filename: str) -> bool:
    """Return True if the file extension is in the allowed list."""
    return Path(filename).suffix.lower() in _ALLOWED_EXTENSIONS


# --------------------------------------------------------------------------- #
# Text extraction                                                               #
# --------------------------------------------------------------------------- #

def extract_text(path: Path | str, mime: str) -> Tuple[str, Dict[str, Any]]:
    """Extract text and metadata from *path*.

    Returns ``(extracted_text, metadata_dict)``.
    """
    path = Path(path)
    size = path.stat().st_size
    meta: Dict[str, Any] = {"size": size, "mime": mime}

    try:
        if mime == "text/plain":
            text = path.read_text(encoding="utf-8", errors="replace")
            meta["chars"] = len(text)
            return text, meta

        if mime == "application/json":
            raw = path.read_text(encoding="utf-8", errors="replace")
            try:
                obj = json.loads(raw)
                text = json.dumps(obj, indent=2)
            except json.JSONDecodeError:
                text = raw
            meta["chars"] = len(text)
            return text, meta

        if mime == "text/csv":
            return _extract_csv(path, meta)

        if mime == "application/pdf":
            return _extract_pdf(path, meta)

        if mime in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/zip",  # treat unrecognised zips as potential docx
        ):
            return _extract_docx(path, meta)

    except Exception:
        logger.exception("Text extraction failed for %s", path)

    # Non-extractable (images, audio, video)
    meta["note"] = "Binary file — no text extracted."
    return "", meta


# --------------------------------------------------------------------------- #
# Format-specific helpers                                                       #
# --------------------------------------------------------------------------- #

def _extract_csv(path: Path, meta: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    lines: list[list[str]] = []
    with path.open(newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.reader(fh)
        for row in reader:
            lines.append(row)
    meta["rows"] = len(lines)
    meta["columns"] = len(lines[0]) if lines else 0
    # Convert first 100 rows to readable text to keep context manageable
    preview = lines[:100]
    text = "\n".join(",".join(r) for r in preview)
    if len(lines) > 100:
        text += f"\n... ({len(lines) - 100} more rows)"
    return text, meta


def _extract_pdf(path: Path, meta: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    if not _PYPDF:
        meta["note"] = "pypdf not installed — PDF text extraction unavailable."
        return "", meta
    import pypdf as _pypdf  # type: ignore
    reader = _pypdf.PdfReader(str(path))
    pages = len(reader.pages)
    meta["pages"] = pages
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")
    text = "\n".join(parts)
    meta["chars"] = len(text)
    return text, meta


def _extract_docx(path: Path, meta: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    if not _DOCX:
        meta["note"] = "python-docx not installed — DOCX text extraction unavailable."
        return "", meta
    import docx as _docx  # type: ignore
    doc = _docx.Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs]
    meta["paragraphs"] = len(paragraphs)
    text = "\n".join(paragraphs)
    meta["chars"] = len(text)
    return text, meta
