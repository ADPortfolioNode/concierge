"""ImageGenerationTool — wraps ImageGenerationPlugin as a tool_registry tool.

Callable by ToolRouter and TaskAgent for image-generation tasks.
Returns a plain URL string so the frontend can render it inline.
"""

from __future__ import annotations

import asyncio
from .base_tool import BaseTool


class ImageGenerationTool(BaseTool):
    name = "image_gen"
    description = "Generate an image from a text prompt using the OpenAI image API (or a picsum placeholder)."

    async def run(self, input_data: str) -> str:
        """Run image generation and return the image URL."""
        try:
            # Import lazily to avoid circular imports at module load time
            from plugins.image_generation_plugin import ImageGenerationPlugin
            plugin = ImageGenerationPlugin()
            result = await plugin.run(input_data)
            return result.get("url", "")
        except Exception as exc:
            import logging
            logging.getLogger(__name__).exception("ImageGenerationTool failed: %s", exc)
            return ""

    async def arun(self, input_data: str) -> str:
        return await self.run(input_data)
