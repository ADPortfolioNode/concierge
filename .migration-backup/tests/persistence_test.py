"""Persistence test for MemoryStore with Chroma/Qdrant.

Run after bringing up the chosen DB service. The script will:
- set VECTOR_DB=chroma
- store a reflection entry
- query for reflections

Usage:
    .venv\Scripts\python tests\persistence_test.py
"""
from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime

import sys
from pathlib import Path

# ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from memory.memory_store import MemoryStore


async def main():
    os.environ.setdefault("VECTOR_DB", "chroma")
    # ensure MemoryStore tries to use the chosen DB
    ms = MemoryStore(collection_name="persistence_test_collection")

    # give some time if client initialization is async-ish
    await asyncio.sleep(0.5)

    if ms._client is None:
        print("MemoryStore did not initialize a vector DB client; aborting persistence test.")
        return

    key = f"reflection_test_{int(time.time())}"
    summary = f"reflection for persistence test at {datetime.utcnow().isoformat()}"
    meta = {"agent_type": "test_agent", "reflection": True}

    print("Storing summary...", key)
    rid = await ms.store_summary(task_name=key, summary=summary, metadata=meta)
    print("Stored id:", rid)

    await asyncio.sleep(1)

    print("Querying for 'reflection'... (top_k=10)")
    res = await ms.query("reflection", top_k=10)
    print("Query result count:", len(res))
    for r in res:
        print(r.get("id"), r.get("metadata"))


if __name__ == "__main__":
    asyncio.run(main())
