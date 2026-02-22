import asyncio
import logging
import os
import json
from typing import Any, Dict

# Minimal logging
logging.basicConfig(level=logging.WARNING)

from sacred_timeline import SacredTimeline
from concurrency import AsyncConcurrencyManager
from memory.memory_store import MemoryStore

GOAL = "Research async orchestration, implement demo, evaluate quality, and store persistent reflection."


class TestConcurrencyManager(AsyncConcurrencyManager):
    def __init__(self, max_agents: int = 1):
        super().__init__(max_agents=max_agents)
        self.peak = 0

    async def _run_agent(self, agent_id: str, agent_coro: asyncio.Future, result_future: asyncio.Future) -> None:  # type: ignore[override]
        try:
            # active_count already includes this task when _run_agent is scheduled by register()
            self.peak = max(self.peak, self.active_count())
        except Exception:
            pass
        await super()._run_agent(agent_id, agent_coro, result_future)


async def main() -> None:
    # Create test concurrency manager and memory store
    cm = TestConcurrencyManager(max_agents=1)
    ms = MemoryStore(collection_name="sacred_memory_test")

    # Preload local backup into MemoryStore to guarantee restart-safe tests
    try:
        loop = asyncio.get_running_loop()
        # run the synchronous loader in an executor to avoid blocking
        if hasattr(ms, "load_local_backup"):
            await loop.run_in_executor(None, ms.load_local_backup)
            print("Local memory backup preloaded into MemoryStore")
    except Exception:
        print("Warning: failed to preload local memory backup; continuing")

    # Check vector DB health (Qdrant/Chroma) before running coordinator
    try:
        healthy = await ms.health_check()
    except Exception:
        healthy = False
    print(f"Vector DB health: {healthy}")
    if not healthy:
        print("Warning: Vector DB health check failed; falling back to local backup/in-memory")

    # Create the coordinator with injected manager and memory
    coordinator = SacredTimeline(concurrency_manager=cm, memory_store=ms)

    # Run coordinator with timeout to avoid infinite loops
    try:
        result = await asyncio.wait_for(coordinator.run_autonomous(GOAL, max_depth=3, max_tasks=12), timeout=120)
    except asyncio.TimeoutError:
        print("Coordinator timed out - possible infinite loop")
        return

    print("Coordinator result:", json.dumps(result, indent=2))

    # Query memory for reflection entries
    try:
        reflections = await ms.query("reflection", top_k=50)
    except Exception:
        reflections = []

    print(f"Found {len(reflections)} reflection-like entries via MemoryStore.query()")
    for r in reflections:
        print("-", r.get("id"), r.get("metadata", {}).get("agent_type"), (r.get("summary") or "")[:120])

    # Check local backup file (restart-safe)
    backup_path = os.path.join(os.getcwd(), "memory_backup.jsonl")
    backup_entries = []
    if os.path.exists(backup_path):
        try:
            with open(backup_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        obj = json.loads(line)
                        backup_entries.append(obj)
                    except Exception:
                        continue
        except Exception:
            pass

    print(f"Found {len(backup_entries)} entries in local memory backup ({backup_path})")

    # Simulate restart by creating a fresh MemoryStore and querying
    ms2 = MemoryStore(collection_name="sacred_memory_test")
    # Ensure ms2 loads the local backup (async-safe via executor)
    try:
        loop = asyncio.get_running_loop()
        if hasattr(ms2, "load_local_backup"):
            await loop.run_in_executor(None, ms2.load_local_backup)
            print("Local memory backup reloaded into restarted MemoryStore (ms2)")
    except Exception:
        print("Warning: failed to reload local memory backup into ms2; continuing")
    try:
        reflections2 = await ms2.query("reflection", top_k=50)
    except Exception:
        reflections2 = []

    print(f"After restart, MemoryStore.query found {len(reflections2)} reflection-like entries")

    # Validate agent types observed in backup (ResearchAgent + CodingAgent)
    agent_types = set()
    for e in backup_entries:
        meta = e.get("metadata") or {}
        at = meta.get("agent_type")
        if at:
            agent_types.add(at)

    checks: Dict[str, Any] = {
        "no_infinite_loop": True,
        "concurrency_respected": cm.peak <= cm.max_agents,
        # consider critic ran if coordinator returned evaluation or any task has last_evaluated_hash
        "critic_ran": bool(result.get("evaluation")) or any((t.get("last_evaluated_hash") for t in (result.get("task_map") or {}).values())),
        "research_and_coding_assigned": ("ResearchAgent" in agent_types) and ("CodingAgent" in agent_types),
        "reflection_stored": len(reflections) > 0 or any((m.get("task_name") == "reflection") for m in backup_entries),
        "persistence_available": os.path.exists(backup_path) and len(backup_entries) > 0,
        "restart_safe_validation": len(reflections2) > 0 or len(backup_entries) > 0,
        "concurrency_peak": cm.peak,
        "agent_types_observed": list(agent_types),
    }

    print("\nChecks summary:")
    for k, v in checks.items():
        print(f"- {k}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
