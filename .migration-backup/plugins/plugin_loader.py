"""Plugin loader — auto-discovers and registers built-in plugins.

Call :func:`load_default_plugins` once during application startup (e.g.
inside the FastAPI ``@app.on_event("startup")`` handler) to populate the
singleton :data:`plugins.plugin_registry._REG` with all built-in plugins.

Adding a new built-in plugin
----------------------------
1.  Create a file in ``plugins/`` (e.g. ``my_plugin.py``) with a class that
    subclasses :class:`~plugins.base_plugin.BasePlugin`.
2.  Import it here and add an instance to ``_BUILTIN_PLUGINS``.
"""

from __future__ import annotations

import logging
from typing import List

from .base_plugin import BasePlugin
from .plugin_registry import register_plugin
from .summarization_plugin import SummarizationPlugin
from .image_generation_plugin import ImageGenerationPlugin

logger = logging.getLogger(__name__)

# Ordered list of built-in plugin instances
_BUILTIN_PLUGINS: List[BasePlugin] = [
    SummarizationPlugin(),
    ImageGenerationPlugin(),
]


def load_default_plugins() -> None:
    """Register all built-in plugins in the global registry."""
    for plugin in _BUILTIN_PLUGINS:
        try:
            register_plugin(plugin)
        except Exception:
            logger.exception("Failed to register plugin %r — skipping", plugin.name)
    logger.info("Plugin loader: registered %d built-in plugin(s)", len(_BUILTIN_PLUGINS))
