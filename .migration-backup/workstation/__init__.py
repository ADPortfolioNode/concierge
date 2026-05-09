"""Workstation — file upload, extraction, and media processing layer."""

from .upload_router import router as upload_router

__all__ = ["upload_router"]
