"""Audio transcription service (stub).

In production, replace the stub body with a call to OpenAI Whisper,
AssemblyAI, or a local whisper model. The interface is intentionally
minimal so the backing service can be swapped without changing callers.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


async def transcribe(path: Path, language: Optional[str] = None) -> str:
    """Return a transcription string for the audio/video file at *path*.

    Currently a deterministic stub. Set ``WHISPER_ENABLED=1`` to enable
    real Whisper transcription when the ``openai`` package is available and
    ``OPENAI_API_KEY`` is set.
    """
    if os.getenv("WHISPER_ENABLED", "0") == "1":
        return await _transcribe_openai_whisper(path, language)

    # Stub response so the rest of the pipeline works end-to-end.
    return (
        f"[Transcription stub] File: {path.name}. "
        "Set WHISPER_ENABLED=1 and OPENAI_API_KEY to enable real transcription."
    )


async def _transcribe_openai_whisper(path: Path, language: Optional[str]) -> str:
    """Real Whisper transcription via the OpenAI API."""
    try:
        import openai  # type: ignore
        client = openai.AsyncOpenAI()
        with path.open("rb") as fh:
            kwargs: dict = {"model": "whisper-1", "file": fh}
            if language:
                kwargs["language"] = language
            result = await client.audio.transcriptions.create(**kwargs)
        return result.text
    except Exception:
        logger.exception("Whisper transcription failed for %s", path)
        return f"[Transcription error] Could not transcribe {path.name}."
