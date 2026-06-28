"""Summarizer agent: create brief summaries of task outputs.

This is a small utility agent; in production it could wrap an LLM summarizer.
"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Summarizer:
    """Minimal async-friendly summarizer.

    Production implementations would call a model; here we keep it simple
    and non-blocking.
    """

    async def summarize(self, text: str, max_length: int = 200) -> str:
        if not text:
            return ""
        text = text.strip()
        if len(text) <= max_length:
            logger.debug("Summarizer returning full text")
            return text
        logger.debug("Summarizer truncating text to %d chars", max_length)
        return text[:max_length] + "..."


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    s = Summarizer()
    print(asyncio.run(s.summarize("a" * 300)))
