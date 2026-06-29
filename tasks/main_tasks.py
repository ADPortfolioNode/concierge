"""Main Celery tasks — compatibility shim.

This module re-exports tasks from the existing agent_tasks and plugin_tasks
modules so that legacy import paths work without modification.
"""
from __future__ import annotations

from tasks.agent_tasks import *  # noqa: F401, F403
from tasks.plugin_tasks import *  # noqa: F401, F403
from tasks.step_assistant_tasks import *  # noqa: F401, F403
