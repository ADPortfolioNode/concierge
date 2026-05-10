"""Base class for all Concierge plugins.

Mirrors the BaseTool contract so plugins can be treated uniformly by the
orchestration layer. Concrete plugins subclass BasePlugin, set ``name``,
``description``, and ``version``, and implement :meth:`run`.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BasePlugin(ABC):
    """Abstract base class for platform plugins.

    Attributes
    ----------
    name:
        Unique machine-readable identifier (snake_case).
    description:
        One-line human-readable summary shown in the UI.
    version:
        Semver string. Defaults to ``"0.1.0"``.
    enabled:
        Whether the plugin is active. Disabled plugins are registered but
        not invoked by the orchestration layer.
    """

    name: str = ""
    description: str = ""
    version: str = "0.1.0"
    enabled: bool = True

    @abstractmethod
    async def run(self, input_data: Any) -> Any:
        """Execute plugin logic.

        Parameters
        ----------
        input_data:
            Arbitrary input — string prompt, dict of params, etc.

        Returns
        -------
        Any:
            Plugin output. Must be JSON-serialisable.
        """

    # ------------------------------------------------------------------
    # Convenience wrappers (mirrors BaseTool interface)
    # ------------------------------------------------------------------

    async def arun(self, input_data: Any) -> Any:
        """Async alias kept for API symmetry with BaseTool."""
        return await self.run(input_data)

    def run_sync(self, input_data: Any) -> Any:
        """Blocking wrapper for callers that cannot be async."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.run(input_data))
        finally:
            loop.close()

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable summary (used by the capabilities API)."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "type": "plugin",
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Plugin name={self.name!r} version={self.version!r} enabled={self.enabled}>"
