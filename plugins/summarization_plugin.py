"""Text summarisation plugin (stub).

Returns a trimmed excerpt of the input to simulate a summarisation service.
In production, replace the ``run`` body with a call to an LLM or dedicated
summarisation API.
"""

from __future__ import annotations

from plugins.base_plugin import BasePlugin


class SummarizationPlugin(BasePlugin):
    name = "summarization"
    description = "Condenses long text into a concise summary."
    version = "0.1.0"

    async def run(self, input_data: str) -> str:
        text = str(input_data).strip()
        if not text:
            return ""
        # Stub: return first 200 chars with an ellipsis
        if len(text) <= 200:
            return text
        return text[:197] + "…"
