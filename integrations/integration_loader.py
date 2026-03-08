"""Integration loader — auto-discovers and registers built-in integrations.

Call :func:`load_default_integrations` once during application startup to
populate the singleton registry with all built-in integrations.
"""

from __future__ import annotations

import logging
from typing import List

from .base_integration import BaseIntegration
from .integration_registry import register_integration
from .openai_integration import OpenAIIntegration
from .gemini_integration import GeminiIntegration
from .stripe_integration import StripeIntegration
from .slack_integration import SlackIntegration

logger = logging.getLogger(__name__)

_BUILTIN_INTEGRATIONS: List[BaseIntegration] = [
    OpenAIIntegration(),
    GeminiIntegration(),
    StripeIntegration(),
    SlackIntegration(),
]


def load_default_integrations() -> None:
    """Register all built-in integrations in the global registry."""
    for intg in _BUILTIN_INTEGRATIONS:
        try:
            register_integration(intg)
        except Exception:
            logger.exception(
                "Failed to register integration %r — skipping", intg.name
            )
    logger.info(
        "Integration loader: registered %d built-in integration(s)",
        len(_BUILTIN_INTEGRATIONS),
    )
