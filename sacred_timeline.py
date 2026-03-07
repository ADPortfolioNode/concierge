"""Compatibility shim.

The real implementation now lives under :mod:`orchestration.sacred_timeline`.
This module exists so that imports from the project root continue to work
without modification.
"""

from orchestration.sacred_timeline import *

from agents.base_agent import BaseAgent
from core.concurrency import AsyncConcurrencyManager
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
        # agent registry for specialized terminal agents (not used in routing)
        self._agents: Dict[str, Any] = {}
        try:
            self._agents["synthesizer"] = SynthesizerAgent(self._llm)
        except Exception:
            logger.exception("Failed to initialize SynthesizerAgent")
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
            "task_id": task_info.get("task_id"),
            "task_name": task_info.get("title") or task_info.get("task_id"),
            "status": result.get("status") if isinstance(result, dict) else "complete",
            "agent_id": getattr(agent_obj, 'id', None),
            "manager_agent_id": manager_agent_id,
            "agent_type": getattr(agent_obj, 'name', getattr(agent_obj, '__class__', {}).__name__),
        }
        # if context contains prior_ids, treat them as parent relationships
        ctx = task_info.get("context") if isinstance(task_info.get("context"), dict) else None
        if ctx:
            pids = ctx.get("prior_ids")
            if pids:
                metadata["parent_ids"] = pids
        summary_id = await self._memory.store_summary(task_name=metadata.get("task_name", "task"), summary=summary, metadata=metadata)

        return {"status": "spawned", "manager_agent_id": manager_agent_id, "agent_id": metadata.get("agent_id"), "result": result, "summary_id": summary_id}

    def _compute_priority(self, task: Dict[str, Any], ctx: Any = None) -> float:
        """Score a task deterministically using settings and context.

        This method is exposed for testing and reuse. Parameters mirror the
        logic previously embedded in :meth:`run_autonomous`.
        """
        settings = get_settings()
        score = 0.0
        goal_text = task.get("title", "") + " " + task.get("instructions", "")
        # relevance: count tokens
        tokens = [w for w in goal_text.split() if len(w) > 3]
        score += settings.relevance_weight * len(tokens)
        # confidence: check any prior_ids in context if exists
        if isinstance(ctx, dict) and ctx.get("prior_ids"):
            vals = []
            for pid in ctx.get("prior_ids"):
                n = self._memory._graph.get(pid)
                if n:
                    vals.append(n.confidence)
            if vals:
                score += settings.confidence_weight * (sum(vals) / len(vals))
        # recency: none for task-level, skip
        # impact: number of dependents? approximate by len(depends_on)
        deps = task.get("depends_on") or []
        score += settings.impact_weight * len(deps)
        # contradiction: use context flag
        if isinstance(ctx, dict) and ctx.get("contradiction_risk"):
            score -= settings.contradiction_weight * ctx.get("contradiction_risk")
        # explicit task priority override (external config/historical hint)
        try:
            prio = float(task.get("priority", 1.0))
        except Exception:
            prio = 1.0
        score *= (settings.priority_weight * prio)
        return score

    async def run_autonomous(self, goal: str, max_depth: int = 3, max_tasks: int = 20, per_task_timeout: int = 60) -> Dict[str, Any]:
        """Coordinator: plan -> assign to specialized agents -> critic loop.

        Assigns tasks to ResearchAgent or CodingAgent where applicable, runs
        them under the concurrency manager, collects outputs, and asks the
        CriticAgent to approve or request refinements. Prevents infinite
        critique loops via `max_refine`.

        Memory recall support is added before planning.  Any prior structured
        intelligence relevant to the goal is fetched deterministically and
        injected into the context object that accompanies every task.  The
        context may be mutated by agents (e.g. reflection_reused flag) and is
        returned to the caller as part of the final result.
        """
        logger.info("Coordinator starting for goal: %s", goal)
        planner = self._planner
        critic_agent = CriticAgent(self._memory, llm=self._llm)
        settings = get_settings()

        # --- deterministic memory retrieval ---
        prior_entries = []
        try:
            prior_entries = await self._memory.retrieve_relevant_intelligence(goal)
        except Exception:
            logger.exception("Memory retrieval failed during run_autonomous")
            prior_entries = []
        print(f"[MEMORY] retrieval_count={len(prior_entries)}")
        print(f"[MEMORY] artifacts_used={[p.get('id') for p in prior_entries]}")

        # build task context that will be passed into every dispatched task
        context: Dict[str, Any] = {
            "goal": goal,
            "prior_summaries": [p.get("summary") for p in prior_entries],
            "prior_ids": [p.get("id") for p in prior_entries],
            "prior_key_points": [],
            "prior_recommendations": [],
            "memory_hit": bool(prior_entries),
            "reflection_reused": False,
            "recall_run": getattr(self, '_recall_run', False),
        }
        # autonomous refinement limits
        MAX_AUTONOMOUS_TASKS = getattr(self, '_max_auton_tasks', 2)
        autonomous_count = 0
        for p in prior_entries:
            struct = p.get("metadata", {}).get("structured") or {}
            if struct:
                kps = struct.get("key_points") or []
                if kps:
                    context["prior_key_points"].append(kps)
                recs = struct.get("recommendations")
                if recs:
                    context["prior_recommendations"].append(recs)

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

        # helper for priority calculation delegates to class method
        def compute_priority(task: Dict[str, Any]) -> float:
            ctx = task.get("context")
            return self._compute_priority(task, ctx)

        # Main control loop
        while True:
            # find pending tasks whose dependencies are done
            pending = [t for t in task_map.values() if t["status"] == "pending" and all(task_map.get(d, {}).get("status") == "done" for d in t.get("depends_on", []))]
            # sort pending by priority descending
            pending.sort(key=lambda t: compute_priority(t), reverse=True)

            # self-initiated refinement before dispatch (handles case of zero initial tasks)
            if autonomous_count < MAX_AUTONOMOUS_TASKS:
                # contradictions
                for node in self._memory.get_contradiction_nodes():
                    tid_new = f"auto_reconcile_{node.id}"
                    if tid_new not in task_map:
                        task_map[tid_new] = {
                            "task_id": tid_new,
                            "title": "Auto Reconcile",
                            "instructions": f"Reconcile contradictions related to node {node.id}",
                            "depends_on": [],
                            "depth": 0,
                            "refine_count": 0,
                            "status": "pending",
                            "output": None,
                            "seen_hashes": set(),
                            "last_evaluated_hash": None,
                            "needs_review": True,
                            "priority": settings.autonomous_task_priority,
                        }
                        autonomous_count += 1
                        if autonomous_count >= MAX_AUTONOMOUS_TASKS:
                            break
                # low confidence
                if autonomous_count < MAX_AUTONOMOUS_TASKS:
                    for node in self._memory.get_low_confidence_nodes():
                        tid_new = f"auto_refine_{node.id}"
                        if tid_new not in task_map:
                            task_map[tid_new] = {
                                "task_id": tid_new,
                                "title": "Auto Refine",
                                "instructions": f"Refine low-confidence node {node.id}",
                                "depends_on": [],
                                "depth": 0,
                                "refine_count": 0,
                                "status": "pending",
                                "output": None,
                                "seen_hashes": set(),
                                "last_evaluated_hash": None,
                                "needs_review": True,
                                "priority": settings.autonomous_task_priority,
                            }
                            autonomous_count += 1
                            if autonomous_count >= MAX_AUTONOMOUS_TASKS:
                                break

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
                # attach shared context object so agents can reason over prior memory
                t["context"] = context
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

                pr = compute_priority(t)
                logger.debug(f"[PRIORITY] task={t.get('task_id')} priority={pr}")
                manager_agent_id, result_future = await self._concurrency.register(coro, priority=pr)
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
                        # detect if agent result indicated reflection reuse
                        if isinstance(res, dict):
                            r = res.get("result")
                            if isinstance(r, dict) and r.get("reflection_reused"):
                                context["reflection_reused"] = True
                                logger.info("[MEMORY] reflection_reused=True")
                        t["status"] = "done"
                        out = None
                        if isinstance(res, dict):
                            # attempt to coerce meaningful output for harness
                            r = res.get("result")
                            if isinstance(r, dict):
                                # prefer summary or output fields
                                out = r.get("summary") or r.get("output") or str(r)
                            else:
                                out = str(r)
                        elif isinstance(res, str):
                            out = res
                        t["output"] = out
                        t["needs_review"] = True
                # self-initiated refinement: check graph for contradictions or low confidence
                if autonomous_count < MAX_AUTONOMOUS_TASKS:
                    # contradictions
                    for node in self._memory.get_contradiction_nodes():
                        tid_new = f"auto_reconcile_{node.id}"
                        if tid_new not in task_map:
                            task_map[tid_new] = {
                                "task_id": tid_new,
                                "title": "Auto Reconcile",
                                "instructions": f"Reconcile contradictions related to node {node.id}",
                                "depends_on": [],
                                "depth": 0,
                                "refine_count": 0,
                                "status": "pending",
                                "output": None,
                                "seen_hashes": set(),
                                "last_evaluated_hash": None,
                                "needs_review": True,
                                "priority": settings.autonomous_task_priority,
                            }
                            autonomous_count += 1
                            if autonomous_count >= MAX_AUTONOMOUS_TASKS:
                                break
                    # low confidence
                    if autonomous_count < MAX_AUTONOMOUS_TASKS:
                        for node in self._memory.get_low_confidence_nodes():
                            tid_new = f"auto_refine_{node.id}"
                            if tid_new not in task_map:
                                task_map[tid_new] = {
                                    "task_id": tid_new,
                                    "title": "Auto Refine",
                                    "instructions": f"Refine low-confidence node {node.id}",
                                    "depends_on": [],
                                    "depth": 0,
                                    "refine_count": 0,
                                    "status": "pending",
                                    "output": None,
                                    "seen_hashes": set(),
                                    "last_evaluated_hash": None,
                                    "needs_review": True,
                                    "priority": settings.autonomous_task_priority,
                                }
                                autonomous_count += 1
                                if autonomous_count >= MAX_AUTONOMOUS_TASKS:
                                    break

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
                # propagate original task context so critic can detect recall
                crit_context: Dict[str, Any] = {"last_suggestion": None}
                if t.get("context") and isinstance(t.get("context"), dict):
                    # merge without overwriting last_suggestion
                    crit_context.update({k: v for k, v in t.get("context", {}).items() if k != "last_suggestion"})
                crit_task = {"outputs": str(out_text), "goal": goal, "context": crit_context}
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

        # After main loop: assemble final synthesis from approved tasks
        approved = {tid: t["output"] for tid, t in task_map.items() if t.get("status") == "done" and t.get("output")}

        # persist a lightweight reflection entry regardless
        reflection = {"goal": goal, "status": "complete"}
        await self._memory.store_summary(task_name="reflection", summary=str(reflection), metadata={"goal": goal})

        final_result = None
        if not approved:
            # No approved tasks — return failure-like summary
            final_result = {"summary": "No approved task outputs available for synthesis", "structured": {"key_points": [], "risks": [], "recommendations": []}, "confidence": 0.0}
            status_out = "failure"
        else:
            synth = self._agents.get("synthesizer")
            if synth is not None:
                try:
                    final_result = await synth.run(goal, approved)
                except Exception:
                    logger.exception("Synthesizer failed; falling back to deterministic aggregation")
                    # deterministic fallback — preserve URLs, skip noise
                    parts = []
                    for k, v in approved.items():
                        s = str(v).strip()
                        if not s or s.startswith("[LLM-Error]") or str(k).startswith("auto_refine"):
                            continue
                        parts.append(s if s.startswith("http") else f"{k}: {s}")
                    concat = "\n".join(parts)
                    final_result = {"summary": concat[:2000], "structured": {"key_points": [], "risks": [], "recommendations": []}, "confidence": 0.0}
            else:
                parts = []
                for k, v in approved.items():
                    s = str(v).strip()
                    if not s or s.startswith("[LLM-Error]") or str(k).startswith("auto_refine"):
                        continue
                    parts.append(s if s.startswith("http") else f"{k}: {s}")
                concat = "\n".join(parts)
                final_result = {"summary": concat[:2000], "structured": {"key_points": [], "risks": [], "recommendations": []}, "confidence": 0.0}

        # Persist final synthesis into memory with structured payload for restart-safety
        try:
            await self._memory.store_summary(task_name="final_synthesis", summary=final_result.get("summary", ""), metadata={"type": "final_summary", "structured": final_result.get("structured", {}), "agent_type": "SynthesizerAgent"})
        except Exception:
            logger.exception("Failed to persist final synthesis into memory")

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

        # make sure evaluation field is always a dict for downstream consumers
        eval_out = {}
        if 'last_evaluation' in locals() and last_evaluation is not None:
            if isinstance(last_evaluation, dict):
                eval_out = last_evaluation
            else:
                eval_out = {"decision": last_evaluation}
        result_out: Dict[str, Any] = {"status": status_out if 'status_out' in locals() else "success", "goal": goal, "task_map": serializable_map, "final": final_result, "evaluation": eval_out}
        # attach reflection flag if available
        if 'context' in locals():
            result_out["reflection_reused"] = context.get("reflection_reused", False)
        # housekeeping: prune low-confidence graph entries after run
        try:
            self._memory.prune_graph()
        except Exception:
            logger.exception("Pruning graph failed")
        return result_out

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
