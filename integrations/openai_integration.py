"""OpenAI integration stub.

Replace the ``call`` body with real ``openai`` SDK calls once the
``OPENAI_API_KEY`` environment variable is available.
"""

from __future__ import annotations

import os
from typing import Any

from integrations.base_integration import BaseIntegration


class OpenAIIntegration(BaseIntegration):
    name = "openai"
    description = "Language model completions and embeddings via the OpenAI API."
    service = "OpenAI"
    version = "0.1.0"
    # Disable by default until a real API key is present
    enabled = bool(os.getenv("OPENAI_API_KEY"))

    async def call(self, action: str, payload: Any = None) -> Any:
        """Stub — returns a mock response for every action."""
        return {
            "integration": self.name,
            "action": action,
            "status": "stub",
            "message": (
                "OpenAI integration is not yet configured. "
                "Set OPENAI_API_KEY and implement the real call."
            ),
        }

    async def health_check(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))
