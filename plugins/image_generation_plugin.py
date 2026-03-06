"""Image-generation plugin (stub).

Returns a deterministic mock image URL to simulate an image-generation
service. In production, replace the ``run`` body with an API call to
DALL-E, Stable Diffusion, etc.
"""

from __future__ import annotations

from plugins.base_plugin import BasePlugin


class ImageGenerationPlugin(BasePlugin):
    name = "image_generation"
    description = "Generates images from text prompts."
    version = "0.1.0"

    async def run(self, input_data: str) -> dict:
        prompt = str(input_data).strip()
        # Stub: return a placeholder image URL
        return {
            "prompt": prompt,
            "url": f"https://placeholder.example.com/image?prompt={prompt[:60]}",
            "mime_type": "image/png",
        }
