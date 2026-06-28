"""Async web search tool.

Uses the DuckDuckGo Instant Answer API (no API key required) to return
real search summaries. Falls back to a descriptive message on network
failure so the pipeline continues gracefully.
"""

from __future__ import annotations

import asyncio
import logging
import os
import urllib.parse

import httpx

from .base_tool import BaseTool

logger = logging.getLogger(__name__)

_DDG_URL = "https://api.duckduckgo.com/"
_TIMEOUT = 8.0  # seconds


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Web search returning real results via DuckDuckGo Instant Answer API."

    async def arun(self, input_data: str) -> str:
        query = str(input_data).strip()
        if not query:
            return "No search query provided."

        # DuckDuckGo Instant Answer API — no key needed
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
            "no_redirect": "1",
        }
        url = _DDG_URL + "?" + urllib.parse.urlencode(params)

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("WebSearchTool request failed: %s", exc)
            return f"Search results for '{query}' are currently unavailable. Please try again later."

        parts: list[str] = []

        # Abstract (instant answer paragraph)
        abstract = (data.get("Abstract") or "").strip()
        if abstract:
            source = data.get("AbstractSource") or ""
            parts.append(f"{abstract} (Source: {source})" if source else abstract)

        # Answer (short factual answer, e.g. for calculations / definitions)
        answer = (data.get("Answer") or "").strip()
        if answer and answer not in parts:
            parts.append(answer)

        # Definition
        definition = (data.get("Definition") or "").strip()
        if definition and definition not in parts:
            src = data.get("DefinitionSource") or ""
            parts.append(f"{definition} (Source: {src})" if src else definition)

        # Related topics — up to 3 titles/snippets
        for topic in (data.get("RelatedTopics") or [])[:3]:
            if isinstance(topic, dict):
                text = (topic.get("Text") or "").strip()
                if text and text not in parts:
                    parts.append(text)

        if parts:
            return "\n".join(parts)

        # DuckDuckGo returned no instant-answer data for this query
        return f"No concise instant-answer found for '{query}'. Consider rephrasing or consulting a web browser for detailed results."
