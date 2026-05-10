"""Plugin loader — auto-discovers and registers built-in plugins.

Call :func:`load_default_plugins` once during application startup (e.g.
inside the FastAPI ``@app.on_event("startup")`` handler) to populate the
singleton :data:`plugins.plugin_registry._REG` with all built-in plugins.

Adding a new built-in plugin
----------------------------
1.  Create a file in ``plugins/`` (e.g. ``my_plugin.py``) with a class that
    subclasses :class:`~plugins.base_plugin.BasePlugin`.
2.  The plugin will be auto-discovered and loaded at startup.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path

from .base_plugin import BasePlugin
from .plugin_registry import register_plugin

logger = logging.getLogger(__name__)


def load_default_plugins() -> None:
    """Dynamically discover and register all plugins in the 'plugins' directory."""
    plugins_dir = Path(__file__).parent
    registered_count = 0
    
    module_infos = list(pkgutil.iter_modules([str(plugins_dir)]))

    for module_info in module_infos:
        # Skip special modules, e.g. `_` prefixed, base, registry, and the loader itself
        if module_info.name.startswith('_') or module_info.name in ("base_plugin", "plugin_registry", "plugin_loader"):
            continue

        try:
            module = importlib.import_module(f"{__package__}.{module_info.name}")

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BasePlugin) and obj is not BasePlugin and obj.__module__ == module.__name__:
                    logger.info("Found plugin class: %s in module %s", obj.__name__, module_info.name)
                    plugin_instance = obj()
                    register_plugin(plugin_instance)
                    registered_count += 1
        except Exception:
            logger.exception("Failed to load or register plugin from module %s — skipping", module_info.name)

    logger.info("Plugin loader: registered %d plugin(s)", registered_count)
