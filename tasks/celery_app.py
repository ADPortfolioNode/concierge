"""Celery application instance for distributed task execution.

Broker  : Redis db 0  (CELERY_BROKER_URL env var, default redis://redis:6379/0)
Backend : Redis db 1  (CELERY_RESULT_BACKEND env var, default redis://redis:6379/1)

Import this module wherever a task or result is needed:
    from tasks.celery_app import celery_app
"""
from __future__ import annotations

import os
from celery import Celery

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery(
    "quesarc",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "tasks.agent_tasks",
        "tasks.plugin_tasks",
        "tasks.workspace_tasks",
    ],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,          # keep results for 1 hour
    worker_prefetch_multiplier=1,  # fair dispatch for long-running tasks
)
