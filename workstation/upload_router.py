"""FastAPI router for the workstation upload endpoint.

POST /api/v1/workstation/upload
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .file_processor import detect_mime, extract_text, is_allowed
from .media_processor import extract_image_metadata, extract_video_metadata
from .storage_service import allocation_dir, safe_path
from .transcription_service import transcribe

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workstation", tags=["workstation"])

# 50 MB hard limit
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

# Inlined to avoid circular imports; mirrors app._api_response
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


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
):
    """Accept a multipart file upload, extract text/metadata, and return
    a structured file-context payload.

    Optionally pass ``project_id`` to associate the upload with a project.
    """
    filename = file.filename or "upload"

    # Extension allow-list
    if not is_allowed(filename):
        raise HTTPException(
            status_code=415,
            detail="File type not supported. Allowed: txt,pdf,docx,csv,json,png,jpg,jpeg,mp3,wav,mp4",
        )

    # Read with size limit  
    header = await file.read(512)
    rest = await file.read(MAX_UPLOAD_BYTES - len(header) + 1)
    total = len(header) + len(rest)

    if total > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File exceeds maximum allowed size of 50 MB.",
        )

    content = header + rest

    # Detect MIME from magic bytes + extension
    mime = detect_mime(filename, header)

    # Allocate a safe upload directory
    upload_id = str(uuid.uuid4())
    upload_dir = allocation_dir(upload_id)
    dest = safe_path(upload_id, filename)

    # Write to disk in a threadpool to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, dest.write_bytes, content)

    # Extract text / metadata based on type
    extracted_text = ""
    metadata: dict = {"size": total, "mime": mime}

    if mime.startswith("image/"):
        metadata.update(extract_image_metadata(dest))

    elif mime.startswith("video/"):
        metadata.update(extract_video_metadata(dest))

    elif mime.startswith("audio/"):
        extracted_text = await transcribe(dest)
        metadata["transcribed"] = bool(extracted_text)

    else:
        extracted_text, extra_meta = await loop.run_in_executor(
            None, extract_text, dest, mime
        )
        metadata.update(extra_meta)

    # Attach to project if requested
    if project_id:
        try:
            from projects.project_service import attach_file_to_project
            await loop.run_in_executor(
                None,
                attach_file_to_project,
                project_id,
                {
                    "upload_id": upload_id,
                    "filename": filename,
                    "mime": mime,
                    "size": total,
                },
            )
        except Exception:
            logger.exception("Failed to attach upload to project %s", project_id)

    payload = {
        "type": "file_context",
        "upload_id": upload_id,
        "filename": filename,
        "extracted_text": extracted_text,
        "metadata": metadata,
    }

    return JSONResponse(content=_resp(payload))
