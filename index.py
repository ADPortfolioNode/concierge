"""Vercel FastAPI entry wrapper.

Some Vercel deployments fail to detect the FastAPI `app` symbol inside
complex modules. Export a simple top-level symbol that points at the
real application instance so the Python builder reliably finds it.
"""
from app import app as app
