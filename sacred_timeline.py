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

        # task map holds task state
        task_map = {t["task_id"]: {**t, "status": "pending", "output": None} for t in tasks}
        completed = set()
        total_spawned = len(tasks)
        depth = 0
        refine_count = 0
        max_refine = 2

        while depth < max_depth and total_spawned <= max_tasks:
            depth += 1
            # find ready tasks
            ready = [t for tid, t in task_map.items() if t["status"] == "pending" and all(d in completed for d in t.get("depends_on", []))]
            if not ready:
                logger.info("No ready tasks at depth %s", depth)
                break

            # spawn specialized agents
            trackers = []
            for t in ready:
                tid = t["task_id"]
                t["status"] = "running"
                instr = t.get("instructions", "")
                title = t.get("title", tid)

                # select an agent using the ToolRouter (LLM-assisted) with heuristics fallback
                router = ToolRouter(llm=self._llm)
                try:
                    selected_tool = await router.select_tool(instr, available_tools=registry().list_tools())
                except Exception:
                    selected_tool = None

                if selected_tool == "web_search":
                    agent = ResearchAgent(self._memory, llm=self._llm)
                    coro = agent.execute(t)
                elif selected_tool == "code_exec":
                    agent = CodingAgent(self._memory, llm=self._llm)
                    coro = agent.execute(t)
                else:
                    # fallback heuristics (keyword-based)
                    lower = instr.lower()
                    if "search" in lower or "survey" in lower or "summar" in lower:
                        agent = ResearchAgent(self._memory, llm=self._llm)
                        coro = agent.execute(t)
                    elif "code" in lower or "implement" in lower or "execute" in lower or "python" in lower:
                        agent = CodingAgent(self._memory, llm=self._llm)
                        coro = agent.execute(t)
                    else:
                        agent = TaskAgent(task_name=title, task_input=t, memory=self._memory, vector_tool=self._vector_tool, llm_tool=self._llm)
                        coro = agent.run()

                # register and track
                manager_agent_id, result_future = await self._concurrency.register(coro)
                trackers.append((tid, agent, manager_agent_id, asyncio.create_task(self._track_agent(agent, manager_agent_id, result_future, t))))

            results = await asyncio.gather(*(tr[3] for tr in trackers), return_exceptions=True)

            # collect outputs
            combined_outputs = []
            for (tid, agent, manager_agent_id, _), res in zip(trackers, results):
                if isinstance(res, Exception):
                    logger.exception("Tracker for %s failed", tid)
                    task_map[tid]["status"] = "failed"
                    task_map[tid]["output"] = str(res)
                else:
                    task_map[tid]["status"] = "done"
                    # result may be nested differently depending on agent
                    out = None
                    if isinstance(res, dict):
                        out = res.get("result", {}).get("output") if res.get("result") else res.get("output")
                    elif isinstance(res, str):
                        out = res
                    task_map[tid]["output"] = out
                    if out:
                        combined_outputs.append(str(out))
                    completed.add(tid)

            combined_text = "\n".join(combined_outputs)

            # Critic reviews combined outputs (run as an agent)
            critic_task = {"outputs": combined_text, "goal": goal}
            crit_manager_id, crit_future = await self._concurrency.register(critic_agent.execute(critic_task))
            try:
                evaluation = await crit_future
            except Exception:
                logger.exception("Critic failed; defaulting to refine")
                evaluation = {"decision": "refine", "comments": "critic error"}
            logger.info("Critic decision: %s", evaluation)

            if evaluation.get("decision") == "approve":
                reflection = {"goal": goal, "depth": depth, "evaluation": evaluation}
                await self._memory.store_summary(task_name="reflection", summary=str(reflection), metadata={"goal": goal})
                return {"status": "approved", "evaluation": evaluation, "task_map": task_map}

            # refine requested
            if evaluation.get("decision") == "refine":
                refine_count += 1
                if refine_count > max_refine:
                    reflection = {"goal": goal, "depth": depth, "status": "max_refine_exceeded", "evaluation": evaluation}
                    await self._memory.store_summary(task_name="reflection", summary=str(reflection), metadata={"goal": goal})
                    return {"status": "failed", "reason": "max_refine_exceeded", "evaluation": evaluation, "task_map": task_map}

                # ask planner for suggested subtasks from critic feedback
                feedback = evaluation.get("feedback", "") or evaluation.get("comments", "")
                refine_prompt = goal + "\nCritic feedback:\n" + feedback
                new_plan = await planner.plan(refine_prompt)
                new_tasks = new_plan.get("tasks", [])
                for nt in new_tasks:
                    nid = nt.get("task_id")
                    if nid in task_map:
                        idx = 1
                        new_id = f"{nid}_{idx}"
                        while new_id in task_map:
                            idx += 1
                            new_id = f"{nid}_{idx}"
                        nt["task_id"] = new_id
                        nid = new_id
                    task_map[nid] = {**nt, "status": "pending", "output": None}
                    total_spawned += 1

                # continue loop to execute refined tasks
                continue

        # ended without approval
        reflection = {"goal": goal, "depth": depth, "status": "incomplete"}
        await self._memory.store_summary(task_name="reflection", summary=str(reflection), metadata={"goal": goal})
        return {"status": "incomplete", "task_map": task_map}

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
