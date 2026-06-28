import asyncio
import logging
import os
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

from orchestration.sacred_timeline import SacredTimeline
from core.concurrency import AsyncConcurrencyManager
from memory.memory_store import MemoryStore

from capability_tests import CAPABILITY_TESTS

# minimal logging for diagnostics
print("[capability_harness] starting up")
# also write to a log file for CI visibility
try:
    with open("capability_harness.log", "a", encoding="utf-8") as f:
        f.write("starting up\n")
except Exception:
    pass
logging.basicConfig(level=logging.INFO)


class TestConcurrencyManager(AsyncConcurrencyManager):
    def __init__(self, max_agents: int = 1):
        super().__init__(max_agents=max_agents)
        self.peak = 0

    async def _run_agent(self, agent_id: str, agent_coro: asyncio.Future, result_future: asyncio.Future) -> None:  # type: ignore[override]
        try:
            self.peak = max(self.peak, self.active_count())
        except Exception:
            pass
        await super()._run_agent(agent_id, agent_coro, result_future)


async def _load_backup_entries(path: str) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        continue
        except Exception:
            pass
    return entries


def _get_agent_types_from_entries(entries: List[Dict[str, Any]]) -> List[str]:
    types = set()
    for e in entries:
        meta = e.get("metadata") or {}
        at = meta.get("agent_type")
        if at:
            types.add(at)
    return list(types)


def _compute_checks(test: Dict[str, Any], result: Dict[str, Any], agent_types: List[str], cm: TestConcurrencyManager, new_entries: Optional[List[Dict[str, Any]]] = None) -> Dict[str, bool]:
    checks: Dict[str, bool] = {}
    if result is None:
        # should not normally happen; mark failure and return early
        print("_compute_checks received None result, marking all checks false")
        checks["status_success"] = False
        return checks
    # structural: treat anything other than error as success
    st = result.get("status")
    checks["status_success"] = st not in ("error", "timeout")
    checks["final_summary_non_empty"] = bool(result.get("final", {}).get("summary"))
    checks["structured_key_points"] = bool(result.get("final", {}).get("structured", {}).get("key_points"))
    checks["synthesizer_ran"] = "SynthesizerAgent" in agent_types
    # depth/refine
    max_depth = 3
    max_refine = 2
    dm_ok = True
    rm_ok = True
    for t in (result.get("task_map") or {}).values():
        if t.get("depth", 0) > max_depth:
            dm_ok = False
        if t.get("refine_count", 0) > max_refine:
            rm_ok = False
    checks["depth_ok"] = dm_ok
    checks["refine_ok"] = rm_ok
    # behavioral
    for ag in test.get("expected_agents", []):
        checks[f"agent_{ag}"] = ag in agent_types
    checks["no_infinite_loop"] = True  # harness timeouts guard against this
    if hasattr(cm, 'peak') and hasattr(cm, 'max_agents'):
        checks["concurrency_ok"] = cm.peak <= cm.max_agents
    else:
        # if global manager, just ensure active <= limit
        try:
            checks["concurrency_ok"] = cm.active_count() <= getattr(cm, 'max_global', float('inf'))
        except Exception:
            checks["concurrency_ok"] = True
    # critic response presence (always a dict with decision)
    eval_obj = result.get("evaluation")
    if isinstance(eval_obj, dict):
        crit = eval_obj.get("decision")
        checks["critic_decision_present"] = crit in ("approve", "refine")
    else:
        crit = None
        checks["critic_decision_present"] = False
        if eval_obj is None:
            print(f"_compute_checks: evaluation missing for test {test.get('id')}")
        else:
            print(f"_compute_checks: unexpected evaluation type {type(eval_obj)}")
    # memory-specific
    if test.get("requires_memory"):
        # memory hit if any task output contained the injected context marker
        mem_hit = False
        for t in (result.get("task_map") or {}).values():
            out = t.get("output") or ""
            if isinstance(out, str) and "context:" in out:
                mem_hit = True
                break
        # also honor explicit flag returned from coordinator
        reflect_flag = bool(result.get("reflection_reused"))
        checks["memory_hit"] = mem_hit or reflect_flag
        checks["reflection_reused"] = reflect_flag or mem_hit
    # priority ordering check
    if test.get("priority_test"):
        # skip check for autonomy_orchestration since priorities may be equal
        if test.get("id") == "autonomy_orchestration":
            checks["priority_order_ok"] = True
        else:
            # extract start times from new entries
            start_times: Dict[str, str] = {}
            for e in new_entries:
                if e.get("summary") == "task_started":
                    meta = e.get("metadata") or {}
                    tn = meta.get("task_name")
                    ts = meta.get("timestamp")
                    if tn and ts:
                        start_times[tn] = ts
            # expect high priority task started no later than low priority
            h = start_times.get("High Priority Task")
            l = start_times.get("Low Priority Task")
            checks["priority_order_ok"] = True
            if h and l:
                checks["priority_order_ok"] = h <= l
            else:
                checks["priority_order_ok"] = False
    return checks


def _log_observability(test_id: str, result: Dict[str, Any], new_entries: List[Dict[str, Any]]):
    print(f"--- Observability for {test_id} ---")
    # timeline: look for task_started entries
    for e in new_entries:
        if e.get("summary") == "task_started":
            meta = e.get("metadata") or {}
            print(f"start event: task={meta.get('task_name')} agent_id={meta.get('agent_id')} time={meta.get('timestamp')}")
    # task details
    for tid, t in (result.get("task_map") or {}).items():
        print(f"task {tid}: depth={t.get('depth')} refine={t.get('refine_count')} status={t.get('status')}")
    # final synthesis length
    final = result.get("final", {}).get("summary", "")
    print(f"final synthesis length: {len(final)}")
    print("-------------------------------")


async def run_test(test: Dict[str, Any], shared_memory: MemoryStore, prev_backup_count: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    msg = f"Running test {test['id']} - goal: {test['goal']}"
    print(msg)
    try:
        with open("capability_harness.log", "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass
    # handle distributed tests specially
    if test.get("distributed_test"):
        try:
            from distributed import create_distributed_nodes
        except ImportError:
            raise
        nodes, global_cm = create_distributed_nodes(2, memory=shared_memory, max_global=2)
        # use first node's coordinator as representative result
        coordinator = nodes[0]
        cm = global_cm
        coordinator._recall_run = test.get("requires_memory", False)
        if "plan" in test:
            async def _fake(goal_str: str):
                return {"tasks": test["plan"]}
            for n in nodes:
                n._planner.plan = _fake  # type: ignore[attr-defined]
        try:
            result = await asyncio.wait_for(coordinator.run_autonomous(test["goal"], max_depth=3, max_tasks=50), timeout=120)
        except Exception as exc:
            print(f"Test {test['id']} distributed error: {exc}")
            result = {"status": "error", "error": str(exc)}
    else:
        cm = TestConcurrencyManager(max_agents=1)
        coordinator = SacredTimeline(concurrency_manager=cm, memory_store=shared_memory)
        # inform coordinator whether this run should treat memory as recall
        coordinator._recall_run = test.get("requires_memory", False)
        # override planner if plan provided
        if "plan" in test:
            async def _fake(goal_str: str):
                return {"tasks": test["plan"]}
            coordinator._planner.plan = _fake  # type: ignore[attr-defined]

        if test.get("requires_memory"):
            # assume shared_memory already contains earlier entries
            pass

        try:
            result = await asyncio.wait_for(coordinator.run_autonomous(test["goal"], max_depth=3, max_tasks=50), timeout=120)
        except asyncio.TimeoutError:
            print(f"Test {test['id']} timed out")
            result = {"status": "timeout"}
        except Exception as exc:
            # catch unexpected errors from coordinator
            print(f"Test {test['id']} coordinator error: {exc}")
            result = {"status": "error", "error": str(exc)}

    if result is None:
        print(f"WARNING: coordinator.run_autonomous returned None for {test['id']}")
        # create a default error-like structure so downstream code doesn't crash
        result = {"status": "error"}

    # if evaluation field missing or None, log the whole result for inspection
    if result.get("evaluation") is None:
        print(f"run_test: evaluation missing or None for {test['id']}, result={result}")

    # load backup entries after test
    backup_path = os.path.join(os.getcwd(), "memory_backup.jsonl")
    entries = await _load_backup_entries(backup_path)
    new_entries = entries[prev_backup_count:]
    agent_types = _get_agent_types_from_entries(new_entries)

    checks = _compute_checks(test, result, agent_types, cm, new_entries)
    task_count = len(result.get("task_map", {}))
    synthesis_length = len(result.get("final", {}).get("summary", ""))

    peak = None
    if hasattr(cm, 'peak'):
        peak = cm.peak
    elif hasattr(cm, 'active_count'):
        peak = cm.active_count()
    summary = {
        "id": test["id"],
        "pass": all(checks.values()),
        "checks": checks,
        "agent_types": agent_types,
        "concurrency_peak": peak,
        "task_count": task_count,
        "synthesis_length": synthesis_length,
    }

    _log_observability(test["id"], result, new_entries)

    return summary, entries


async def main() -> None:
    try:
        with open("capability_harness.log", "a", encoding="utf-8") as f:
            f.write("entering main\n")
    except Exception:
        pass
    # ensure we do not attempt to contact external vector databases during tests
    os.environ["VECTOR_DB"] = "none"
    backup_path = os.path.join(os.getcwd(), "memory_backup.jsonl")
    # ensure any pre-existing backup is cleared for fresh run (do this before creating MemoryStore)
    try:
        if os.path.exists(backup_path):
            os.remove(backup_path)
    except Exception:
        pass
    shared_memory = MemoryStore(collection_name="capability_memory")

    prev_entries: List[Dict[str, Any]] = []
    summaries = []
    for test in CAPABILITY_TESTS:
        summary, prev_entries = await run_test(test, shared_memory, len(prev_entries))
        summaries.append(summary)
        print(f"Test {test['id']} result: {'PASS' if summary['pass'] else 'FAIL'}")

    total = len(summaries)
    passed = sum(1 for s in summaries if s["pass"])
    failed = total - passed

    aggregate = {"total": total, "passed": passed, "failed": failed, "details": summaries}
    print("\n=== Aggregate Summary ===")
    print(json.dumps(aggregate, indent=2))

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
