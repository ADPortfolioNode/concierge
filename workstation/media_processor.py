"""Image and video metadata extraction.

Uses Pillow for images when available; falls back to basic file stats.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

try:
    from PIL import Image  # type: ignore
    _PIL = True
except ImportError:
    _PIL = False


def extract_image_metadata(path: Path) -> Dict[str, Any]:
    """Return basic image metadata dict."""
    meta: Dict[str, Any] = {"size": path.stat().st_size}
    if not _PIL:
        meta["note"] = "Pillow not installed — image metadata unavailable."
        return meta
    try:
        with Image.open(path) as img:
            meta["width"] = img.width
            meta["height"] = img.height
            meta["mode"] = img.mode
            meta["format"] = img.format
    except Exception:
        logger.exception("Image metadata extraction failed for %s", path)
        meta["note"] = "Could not open image."
    return meta


def extract_video_metadata(path: Path) -> Dict[str, Any]:
    """Return basic video metadata (file size only for now)."""
    return {
        "size": path.stat().st_size,
        "note": "Video metadata extraction not yet implemented.",
    }
