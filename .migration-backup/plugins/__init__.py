"""Plugin system for Concierge/Quesarc.

Plugins extend the platform's capabilities beyond built-in tools.
Each plugin is a self-contained unit with metadata, configuration, and
an async ``run`` entry-point that the orchestration layer can invoke.
"""

from .base_plugin import BasePlugin
from .plugin_registry import PluginRegistry, register_plugin, get_plugin, list_plugins, registry

__all__ = [
    "BasePlugin",
    "PluginRegistry",
    "register_plugin",
    "get_plugin",
    "list_plugins",
    "registry",
]
