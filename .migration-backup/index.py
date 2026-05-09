"""Lightweight FastAPI entry wrapper for Vercel.

Avoid importing the project's heavy `app` module at import-time so the
builder can detect a top-level `app` symbol without executing expensive
initialization. The real application is mounted at startup.
"""
from fastapi import FastAPI

app = FastAPI()


@app.on_event("startup")
async def _mount_real_app():
	try:
		import importlib
		real = importlib.import_module('app')
		real_app = getattr(real, 'app', None)
		if real_app is not None:
			app.mount('/', real_app)
	except Exception:
		# swallow; runtime logs will reveal details if mounting fails
		return
