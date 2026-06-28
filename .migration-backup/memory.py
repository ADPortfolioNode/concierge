"""Memory entrypoint for Concierge.

This module re-exports the production-ready `MemoryStore` implementation from
`memory.memory_store` so any import path that references the top-level
`memory` module uses the same Chroma/Qdrant backend.
"""

from __future__ import annotations

from memory.memory_store import MemoryStore

__all__ = ["MemoryStore"]
