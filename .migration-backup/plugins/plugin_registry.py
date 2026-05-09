"""Thread-safe plugin registry singleton.

Usage
-----
    from plugins import register_plugin, get_plugin, list_plugins

    register_plugin(MyPlugin())
    info = list_plugins()          # [ {"name": ..., "description": ...}, ... ]
    plugin = get_plugin("my_plugin")
    result = await plugin.run("hello")
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional

from .base_plugin import BasePlugin

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Thread-safe registry for :class:`BasePlugin` instances.

    Mirrors the design of ``tools.ToolRegistry`` for consistency.
    """

    def __init__(self) -> None:
        self._plugins: Dict[str, BasePlugin] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, plugin: BasePlugin) -> None:
        """Register *plugin*, replacing any previous entry with the same name."""
        if not plugin.name:
            raise ValueError("Plugin must have a non-empty 'name' attribute")
        with self._lock:
            if plugin.name in self._plugins:
                logger.debug("PluginRegistry: replacing existing plugin %r", plugin.name)
            self._plugins[plugin.name] = plugin
            logger.info("PluginRegistry: registered plugin %r (v%s)", plugin.name, plugin.version)

    def unregister(self, name: str) -> None:
        """Remove plugin *name* from the registry (idempotent)."""
        with self._lock:
            self._plugins.pop(name, None)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[BasePlugin]:
        """Return the plugin registered as *name*, or ``None``."""
        with self._lock:
            return self._plugins.get(name)

    def list_plugins(self, enabled_only: bool = False) -> List[dict]:
        """Return a list of plugin summary dicts. API endpoint uses this."""
        with self._lock:
            plugins = list(self._plugins.values())
        if enabled_only:
            plugins = [p for p in plugins if p.enabled]
        return [p.to_dict() for p in plugins]

    def __len__(self) -> int:
        with self._lock:
            return len(self._plugins)


# ---------------------------------------------------------------------------
# Module-level singleton and convenience functions
# ---------------------------------------------------------------------------

_REG = PluginRegistry()


def register_plugin(plugin: BasePlugin) -> None:
    """Register *plugin* in the module-level singleton registry."""
    _REG.register(plugin)


def get_plugin(name: str) -> Optional[BasePlugin]:
    """Return plugin *name* from the singleton registry, or ``None``."""
    return _REG.get(name)


def list_plugins(enabled_only: bool = False) -> List[dict]:
    """Return all plugin summaries from the singleton registry."""
    return _REG.list_plugins(enabled_only=enabled_only)


def registry() -> PluginRegistry:
    """Return the module-level singleton registry instance."""
    return _REG
