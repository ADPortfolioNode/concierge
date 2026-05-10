"""Thread-safe integration registry singleton.

Usage
-----
    from integrations import register_integration, get_integration, list_integrations

    register_integration(MyIntegration())
    info = list_integrations()          # [ {"name": ..., "service": ...}, ... ]
    intg = get_integration("openai")
    result = await intg.call("complete", {"prompt": "Hello"})
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional

from .base_integration import BaseIntegration

logger = logging.getLogger(__name__)


class IntegrationRegistry:
    """Thread-safe registry for :class:`BaseIntegration` instances.

    Mirrors the design of ``tools.ToolRegistry`` for consistency.
    """

    def __init__(self) -> None:
        self._integrations: Dict[str, BaseIntegration] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, integration: BaseIntegration) -> None:
        """Register *integration*, replacing any previous entry with the same name."""
        if not integration.name:
            raise ValueError("Integration must have a non-empty 'name' attribute")
        with self._lock:
            if integration.name in self._integrations:
                logger.debug(
                    "IntegrationRegistry: replacing existing integration %r",
                    integration.name,
                )
            self._integrations[integration.name] = integration
            logger.info(
                "IntegrationRegistry: registered integration %r (service=%r, v%s)",
                integration.name,
                integration.service,
                integration.version,
            )

    def unregister(self, name: str) -> None:
        """Remove integration *name* from the registry (idempotent)."""
        with self._lock:
            self._integrations.pop(name, None)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[BaseIntegration]:
        """Return the integration registered as *name*, or ``None``."""
        with self._lock:
            return self._integrations.get(name)

    def list_integrations(self, enabled_only: bool = False) -> List[dict]:
        """Return a list of integration summary dicts. API endpoint uses this."""
        with self._lock:
            integrations = list(self._integrations.values())
        if enabled_only:
            integrations = [i for i in integrations if i.enabled]
        return [i.to_dict() for i in integrations]

    def __len__(self) -> int:
        with self._lock:
            return len(self._integrations)


# ---------------------------------------------------------------------------
# Module-level singleton and convenience functions
# ---------------------------------------------------------------------------

_REG = IntegrationRegistry()


def register_integration(integration: BaseIntegration) -> None:
    """Register *integration* in the module-level singleton registry."""
    _REG.register(integration)


def get_integration(name: str) -> Optional[BaseIntegration]:
    """Return integration *name* from the singleton registry, or ``None``."""
    return _REG.get(name)


def list_integrations(enabled_only: bool = False) -> List[dict]:
    """Return all integration summaries from the singleton registry."""
    return _REG.list_integrations(enabled_only=enabled_only)


def registry() -> IntegrationRegistry:
    """Return the module-level singleton registry instance."""
    return _REG
