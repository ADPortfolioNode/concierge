"""Async-friendly MemoryStore wrapper.

This file provides a small async wrapper around a (synchronous) ChromaDB
HTTP client. Since the upstream Chroma client may be synchronous, we run
blocking calls in an executor to keep the asyncio event loop responsive.

In production this can be replaced with a true async client.
"""
from __future__ import annotations

import os
import asyncio
import logging
from typing import Any, Dict, List, Optional

try:
    import chromadb
except Exception:  # pragma: no cover - optional dependency for local dev
    chromadb = None

logger = logging.getLogger(__name__)


class MemoryStore:
    def __init__(self, collection_name: str = "sacred_memory") -> None:
        chroma_host = os.getenv("CHROMA_HOST", "localhost")
        chroma_port = os.getenv("CHROMA_PORT", "8000")

        self._collection_name = collection_name
        self._client = None
        self._collection = None

        if chromadb is not None:
            try:
                # Use the HttpClient for remote Chroma server; keep sync client
                self._client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
                self._collection = self._client.get_or_create_collection(name=self._collection_name)
            except Exception:
                logger.exception("Failed to initialize chromadb client; continuing with in-memory stub")
                self._client = None

        # fallback in-memory store
        self._in_memory: List[Dict[str, Any]] = []

    async def store_summary(self, task_name: str, summary: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a summary asynchronously and return an id."""
        metadata = metadata or {}
        if self._collection is None:
            # fallback: store in-memory
            rec_id = f"{task_name}_{hash(summary)}"
            self._in_memory.append({"id": rec_id, "summary": summary, "metadata": metadata})
            logger.debug("MemoryStore (in-memory) stored %s", rec_id)
            await asyncio.sleep(0)  # yield to event loop
            return rec_id

        loop = asyncio.get_running_loop()
        rec_id = f"{task_name}_{hash(summary)}"

        def _add():
            self._collection.add(documents=[summary], metadatas=[metadata], ids=[rec_id])

        await loop.run_in_executor(None, _add)
        logger.debug("MemoryStore stored %s in chroma", rec_id)
        return rec_id

    async def query(self, context: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query memory for context. Returns a list of dicts with keys like `summary` and `metadata`."""
        if self._collection is None:
            # naive in-memory semantic by substring matching
            results = []
            for r in self._in_memory:
                if context.lower() in r.get("summary", "").lower():
                    results.append({"id": r["id"], "summary": r["summary"], "metadata": r.get("metadata", {})})
            await asyncio.sleep(0)
            return results[:top_k]

        loop = asyncio.get_running_loop()

        def _query():
            # This example uses a simple lookup; replace with chroma query API as needed
            try:
                hits = self._collection.query(query_texts=[context], n_results=top_k)
                # hits is client-specific; normalize to list of dicts
                out = []
                for docs, metas, ids in zip(hits.get("documents", []), hits.get("metadatas", []), hits.get("ids", [])):
                    for d, m, i in zip(docs, metas, ids):
                        out.append({"id": i, "summary": d, "metadata": m})
                return out
            except Exception:
                logger.exception("Chroma query failed")
                return []

        results = await loop.run_in_executor(None, _query)
        return results


__all__ = ["MemoryStore"]