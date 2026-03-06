"""Integration layer for Concierge/Quesarc.

Integrations connect the platform to external services (APIs, SaaS tools,
payment providers, etc.). Each integration exposes a uniform async interface
so the orchestration layer can call any service without knowing its details.
"""

from .base_integration import BaseIntegration
from .integration_registry import (
    IntegrationRegistry,
    register_integration,
    get_integration,
    list_integrations,
    registry,
)

__all__ = [
    "BaseIntegration",
    "IntegrationRegistry",
    "register_integration",
    "get_integration",
    "list_integrations",
    "registry",
]
