"""Base class for all Concierge integrations.

An integration wraps a single external service or API. Subclasses set
``name``, ``description``, and ``service`` then implement :meth:`call`.

The interface intentionally mirrors :class:`~plugins.base_plugin.BasePlugin`
so the orchestration layer can treat plugins and integrations uniformly.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseIntegration(ABC):
    """Abstract base class for external-service integrations.

    Attributes
    ----------
    name:
        Unique machine-readable identifier for this integration (snake_case).
    description:
        One-line human-readable summary shown in the UI.
    service:
        Name of the third-party service (e.g. ``"OpenAI"``, ``"Stripe"``).
    version:
        Semver string. Defaults to ``"0.1.0"``.
    enabled:
        Whether the integration is active. Disabled integrations are
        registered but skipped by the orchestration layer.
    """

    name: str = ""
    description: str = ""
    service: str = ""
    version: str = "0.1.0"
    enabled: bool = True

    @abstractmethod
    async def call(self, action: str, payload: Any = None) -> Any:
        """Invoke the external service.

        Parameters
        ----------
        action:
            Service-specific action identifier (e.g. ``"complete"``,
            ``"charge"``, ``"send_message"``).
        payload:
            Arbitrary action parameters. Must be JSON-serialisable.

        Returns
        -------
        Any:
            Service response. Must be JSON-serialisable.
        """

    # ------------------------------------------------------------------
    # Health / connectivity
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Return ``True`` if the integration can reach its external service.

        The default implementation always returns ``True``; subclasses
        should override this to test live connectivity.
        """
        return True

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable summary (used by the capabilities API)."""
        return {
            "name": self.name,
            "description": self.description,
            "service": self.service,
            "version": self.version,
            "enabled": self.enabled,
            "type": "integration",
        }

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Integration name={self.name!r} service={self.service!r} "
            f"version={self.version!r} enabled={self.enabled}>"
        )
