"""Async SacredTimeline orchestrator (root agent).

This orchestrator is responsible for receiving user input, asking the
Planner for a course of action, spawning `TaskAgent`s as async coroutines,
registering them with `AsyncConcurrencyManager`, awaiting their results,
and persisting summaries in `MemoryStore`.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import logging
import asyncio

from agents.planner import Planner
from agents.evaluator import Evaluator
from agents.summarizer import Summarizer
from agents.research_agent import ResearchAgent
from agents.coding_agent import CodingAgent
from agents.critic_agent import CriticAgent
from agents.base_agent import BaseAgent
from concurrency import AsyncConcurrencyManager
from memory.memory_store import MemoryStore
from task_agent import TaskAgent
from tools.vector_search_tool import VectorSearchTool
from config.settings import get_settings
from tools.tool_registry import register_tool
from tools.web_search_tool import WebSearchTool
from tools.file_memory_tool import FileMemoryTool
from tools.code_execution_tool import CodeExecutionTool
from tools.tool_router import ToolRouter

logger = logging.getLogger(__name__)


class SacredTimeline:
    def __init__(
        self,
        concurrency_manager: Optional[AsyncConcurrencyManager] = None,
        memory_store: Optional[MemoryStore] = None,
        planner: Optional[Planner] = None,
        summarizer: Optional[Summarizer] = None,
        vector_tool: Optional[VectorSearchTool] = None,
    ) -> None:
        settings = get_settings()
        self._concurrency = concurrency_manager or AsyncConcurrencyManager(max_agents=settings.max_concurrent_agents)
        # create a shared LLM instance and pass it into components that can use it
        from tools.llm_tool import LLMTool

        self._llm = LLMTool()
        self._memory = memory_store or MemoryStore(collection_name=settings.memory_collection, llm_tool=self._llm)
        self._planner = planner or Planner(llm=self._llm)
        self._summarizer = summarizer or Summarizer()
        self._vector_tool = vector_tool or VectorSearchTool(self._memory)
        # Register default tools so specialized agents can find them
        try:
            register_tool(WebSearchTool())
            register_tool(FileMemoryTool())
            register_tool(CodeExecutionTool())
        except Exception:
            logger.exception("Failed to register default tools")

    async def _track_agent(self, agent_obj: Any, manager_agent_id: str, result_future: asyncio.Future, task_info: Dict[str, Any]) -> Dict[str, Any]:
        """Await an agent coroutine result, summarize and store it in memory.

        `agent_obj` may be a BaseAgent or TaskAgent instance. `task_info` is
        the original task dict for metadata.
        """
        try:
            result = await result_future
        except asyncio.CancelledError:
            logger.warning("Agent %s was cancelled", manager_agent_id)
            return {"status": "cancelled", "manager_agent_id": manager_agent_id}
        except Exception as exc:
            logger.exception("Agent %s raised an error", manager_agent_id)
            result = {"agent_id": getattr(agent_obj, 'id', None), "status": "failed", "output": str(exc)}

        # Normalize result to a string for summarization
        output_text = ""
        if isinstance(result, dict):
            output_text = str(result.get("output") or result.get("summary") or result)
        else:
            output_text = str(result)

        # Summarize the output (best-effort)
        try:
            summary = await self._summarizer.summarize(output_text)
        except Exception:
            logger.exception("Summarizer failed")
            summary = output_text

        # Store in memory with metadata
        metadata = {
            "task_name": task_info.get("title") or task_info.get("task_id"),
            "status": result.get("status") if isinstance(result, dict) else "complete",
            "agent_id": getattr(agent_obj, 'id', None),
            "manager_agent_id": manager_agent_id,
            "agent_type": getattr(agent_obj, 'name', getattr(agent_obj, '__class__', {}).__name__),
        }
        summary_id = await self._memory.store_summary(task_name=metadata.get("task_name", "task"), summary=summary, metadata=metadata)

        return {"status": "spawned", "manager_agent_id": manager_agent_id, "agent_id": metadata.get("agent_id"), "result": result, "summary_id": summary_id}

    async def run_autonomous(self, goal: str, max_depth: int = 3, max_tasks: int = 20, per_task_timeout: int = 60) -> Dict[str, Any]:
        """Coordinator: plan -> assign to specialized agents -> critic loop.

        Assigns tasks to ResearchAgent or CodingAgent where applicable, runs
        them under the concurrency manager, collects outputs, and asks the
        CriticAgent to approve or request refinements. Prevents infinite
        critique loops via `max_refine`.
        """
        logger.info("Coordinator starting for goal: %s", goal)
        planner = self._planner
        critic_agent = CriticAgent(self._memory, llm=self._llm)

        plan = await planner.plan(goal)
        tasks = plan.get("tasks", [])

        # initialize task_map with dedup fields and deterministic state
        import hashlib

        task_map = {
            t["task_id"]: {
                **t,
                "depth": t.get("depth", 0),
                "refine_count": 0,
                "status": "pending",
                "output": None,
                "seen_hashes": set(),
                "last_evaluated_hash": None,
                "needs_review": True,
            }
            for t in tasks
        }

        total_spawned = len(tasks)
        max_refine = 2

        # routing helper (deterministic keyword matching, prefer explicit task_type)
        def route_task_to_agent(task: Dict[str, Any]):
            # prefer explicit metadata.task_type
            meta = task.get("metadata", {}) or {}
            ttype = meta.get("task_type")
            if ttype:
                if ttype.lower() == "coding":
                    return CodingAgent(self._memory, llm=self._llm)
                if ttype.lower() == "research":
                    return ResearchAgent(self._memory, llm=self._llm)

            title = (task.get("title", "") or "").lower()
            instr = (task.get("instructions", "") or "").lower()
            text = f"{title} {instr}"

            coding_keywords = [
                "code", "implement", "build", "create", "write",
                "function", "class", "api", "endpoint", "service",
                "library", "script", "module",
            ]
            research_keywords = [
                "research", "analyze", "investigate", "web", "search",
                "compare", "study",
            ]

            if any(k in text for k in coding_keywords):
                return CodingAgent(self._memory, llm=self._llm)
            if any(k in text for k in research_keywords):
                return ResearchAgent(self._memory, llm=self._llm)

            # default
            return TaskAgent(task_name=task.get("title") or task.get("task_id"), task_input=task, memory=self._memory, vector_tool=self._vector_tool, llm_tool=self._llm)

        # Main control loop
        while True:
            # find pending tasks whose dependencies are done
            pending = [t for t in task_map.values() if t["status"] == "pending" and all(task_map.get(d, {}).get("status") == "done" for d in t.get("depends_on", []))]

            # termination guard: no pending, no running, no needs_review
            if (
                not pending
                and not any(t["status"] == "running" for t in task_map.values())
                and not any(t.get("needs_review", False) for t in task_map.values())
            ):
                break

            # dispatch pending tasks
            trackers = []
            for t in pending:
                tid = t["task_id"]
                # depth cap enforcement before execution
                if t["depth"] > max_depth:
                    t["status"] = "failed"
                    t["needs_review"] = False
                    continue

                t["status"] = "running"
                agent_obj = route_task_to_agent(t)
                # use agent.execute for BaseAgent subclasses or TaskAgent.run for TaskAgent
                if hasattr(agent_obj, "execute"):
                    coro = agent_obj.execute(t)
                else:
                    coro = agent_obj.run()

                manager_agent_id, result_future = await self._concurrency.register(coro)
                trackers.append((tid, agent_obj, manager_agent_id, asyncio.create_task(self._track_agent(agent_obj, manager_agent_id, result_future, t))))

            # gather results for this dispatch round
            if trackers:
                results = await asyncio.gather(*(tr[3] for tr in trackers), return_exceptions=True)

                for (tid, agent, manager_agent_id, _), res in zip(trackers, results):
                    t = task_map.get(tid)
                    if t is None:
                        continue
                    if isinstance(res, Exception):
                        logger.exception("Tracker for %s failed", tid)
                        t["status"] = "failed"
                        t["output"] = str(res)
                        t["needs_review"] = False
                    else:
                        t["status"] = "done"
                        out = None
                        if isinstance(res, dict):
                            out = res.get("result", {}).get("output") if res.get("result") else res.get("output")
                        elif isinstance(res, str):
                            out = res
                        t["output"] = out
                        t["needs_review"] = True

            # Critic: evaluate tasks that are done and need review (per-task, in-place refinement)
            for tid, t in list(task_map.items()):
                if t["status"] != "done" or not t.get("needs_review", False):
                    continue

                out_text = t.get("output")
                if not out_text:
                    t["needs_review"] = False
                    continue

                output_hash = hashlib.sha256(str(out_text).encode()).hexdigest()

                # duplicate output -> fail-fast
                if output_hash in t.get("seen_hashes", set()):
                    t["status"] = "failed"
                    t["needs_review"] = False
                    continue

                # only evaluate if not evaluated already for same output
                if output_hash == t.get("last_evaluated_hash"):
                    continue

                # mark seen and evaluate
                t["seen_hashes"].add(output_hash)
                crit_task = {"outputs": str(out_text), "goal": goal, "context": {"last_suggestion": None}}
                crit_manager_id, crit_future = await self._concurrency.register(critic_agent.execute(crit_task))
                try:
                    evaluation = await crit_future
                except Exception:
                    logger.exception("Critic failed; defaulting to approve")
                    evaluation = {"decision": "approve", "comments": "critic error"}

                logger.info("Critic decision for %s: %s", tid, evaluation)

                # store last evaluated hash
                t["last_evaluated_hash"] = output_hash

                # persist last evaluation globally for return
                last_evaluation = evaluation

                if evaluation.get("decision") == "approve":
                    t["needs_review"] = False
                    continue

                # refine requested -> in-place refinement
                t["refine_count"] = t.get("refine_count", 0) + 1
                suggestions = evaluation.get("suggestions") or []
                if t["refine_count"] >= max_refine:
                    t["status"] = "failed"
                    t["needs_review"] = False
                    continue
                # in-place update of instructions, bump depth, reset status to pending
                t["instructions"] = suggestions[0] if suggestions else f"Refine and improve:\n\n{t.get('output')}"
                t["status"] = "pending"
                t["depth"] = t.get("depth", 0) + 1
                t["needs_review"] = False

            # small sleep to yield
            await asyncio.sleep(0.02)

        # assemble final reflection and return
        reflection = {"goal": goal, "status": "complete"}
        await self._memory.store_summary(task_name="reflection", summary=str(reflection), metadata={"goal": goal})

        # Make task_map JSON-serializable (convert sets to lists)
        serializable_map = {}
        for tid, info in task_map.items():
            entry = dict(info)
            # convert any set values to lists (seen_hashes)
            if isinstance(entry.get("seen_hashes"), set):
                entry["seen_hashes"] = list(entry["seen_hashes"])
            # ensure last_evaluated_hash is JSON-friendly
            if isinstance(entry.get("last_evaluated_hash"), set):
                entry["last_evaluated_hash"] = list(entry["last_evaluated_hash"])
            serializable_map[tid] = entry

        return {"status": "complete", "task_map": serializable_map, "evaluation": last_evaluation if 'last_evaluation' in locals() else None}

    async def handle_user_input(self, user_input: str) -> Dict[str, Any]:
        """Handle user input asynchronously.

        - Ask Planner for decision (awaitable)
        - For direct responses: return immediately
        - For spawned tasks: create TaskAgent, register with concurrency manager,
          await its completion, summarize and store results in memory, and
          return structured metadata to the caller.
        """
        logger.info("SacredTimeline handling input")
        # Use new planner.plan() API to get structured tasks
        plan = await self._planner.plan(user_input)
        tasks = plan.get("tasks")
        if tasks:
            # Launch autonomous loop
            return await self.run_autonomous(user_input)

        # Fallback: no tasks generated
        logger.error("Planner returned no tasks for input: %s", user_input)
        return {"status": "error", "reason": "no_tasks"}


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def _demo():
        settings = get_settings()
        cm = AsyncConcurrencyManager(max_agents=settings.max_concurrent_agents)
        ms = MemoryStore(collection_name=settings.memory_collection)
        planner = Planner()
        summarizer = Summarizer()
        root = SacredTimeline(cm, ms, planner, summarizer)
        out = await root.handle_user_input("Please process and summarize this dataset")
        print(out)

    asyncio.run(_demo())
