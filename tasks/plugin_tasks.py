"""Celery tasks that invoke plugins from the plugin registry.

Usage (from the jobs router):
    from tasks.plugin_tasks import run_plugin
    result = run_plugin.delay(plugin_name="web_search", input_data={"query": "…"})
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.plugin_tasks.run_plugin")
def run_plugin(self, plugin_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a registered plugin synchronously inside a Celery worker.

    Args:
        plugin_name: Key used when the plugin was registered
                     (e.g. ``"web_search"``, ``"code_exec"``).
        input_data: Arbitrary JSON-safe payload forwarded to the plugin.

    Returns:
        Dict with ``status``, ``result`` / ``error``, and ``task_id``.
    """
    task_id = self.request.id
    logger.info("run_plugin[%s] plugin=%r", task_id, plugin_name)

    try:
        from plugins.plugin_loader import load_default_plugins
        import plugins.plugin_registry as _plugin_reg

        load_default_plugins()

        plugin = _plugin_reg.get_plugin(plugin_name)
        if plugin is None:
            return {
                "status": "failed",
                "error": f"Plugin {plugin_name!r} not found",
                "task_id": task_id,
            }

        # Plugins expose a synchronous `run` or `execute` method.
        runner = getattr(plugin, "run", None) or getattr(plugin, "execute", None)
        if runner is None:
            return {
                "status": "failed",
                "error": f"Plugin {plugin_name!r} has no run/execute method",
                "task_id": task_id,
            }

        result = runner(input_data)
        return {"status": "completed", "result": result, "task_id": task_id}

    except Exception as exc:
        logger.exception("run_plugin[%s] failed", task_id)
        return {"status": "failed", "error": str(exc), "task_id": task_id}
