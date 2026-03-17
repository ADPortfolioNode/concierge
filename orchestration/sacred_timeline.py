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
from agents.synthesizer_agent import SynthesizerAgent
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

# ---------------------------------------------------------------------------
# Conversational message detection
# ---------------------------------------------------------------------------

_CONVERSATIONAL_STARTS = (
    "what are", "what is", "what's", "what do you", "what can you",
    "how are", "how do you", "how does", "who are", "who is",
    "can you", "could you tell", "do you", "are you",
    "tell me about yourself", "tell me what", "describe yourself",
    "why do", "why are", "help me understand", "explain what",
    "i'm curious", "i am curious",
)
_CONVERSATIONAL_KEYWORDS = {
    "capabilities", "features", "capabilit", "able to", "able to do",
    "can do", "do you do", "are you able", "what you do", "functionality",
    "how are you", "how's it going", "how do you feel",
}


def _is_conversational(text: str) -> bool:
    """Return True if *text* is a conversational question vs. an actionable goal."""
    lowered = text.strip().lower()
    # Very short inputs are conversational
    if len(lowered.split()) <= 3:
        return True
    # Starts with a common conversational pattern
    if any(lowered.startswith(p) for p in _CONVERSATIONAL_STARTS):
        return True
    # Contains capability/status keywords
    if any(k in lowered for k in _CONVERSATIONAL_KEYWORDS):
        return True
    # Pure question without action words
    action_words = {"create", "build", "implement", "generate", "write", "make",
                    "design", "develop", "fix", "update", "add", "remove", "change",
                    "deploy", "run", "execute", "analyze", "process", "search",
                    "fetch", "upload", "download", "convert", "migrate", "refactor"}
    has_action = any(w in lowered.split() for w in action_words)
    is_question = lowered.endswith("?") or lowered.startswith(("what ", "how ", "why ", "who ", "when ", "where ", "is ", "are ", "can ", "do "))
    if is_question and not has_action:
        return True
    return False


class Metrics:
    """Very lightweight in-memory metrics for visibility."""
    def __init__(self) -> None:
        self.total_requests = 0
        self.requests_queued = 0
        self.failovers = 0


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
        self.metrics = Metrics()
        self._concurrency = concurrency_manager or AsyncConcurrencyManager(max_agents=settings.max_concurrent_agents)
        # limit the number of simultaneous handle_user_input calls to avoid
        # flooding the LLM/backend.  Additional requests queue until a slot
        # frees up, providing a simple back-pressure mechanism.
        self._request_sem = asyncio.Semaphore(settings.max_concurrent_requests)
        # create a shared LLM instance and pass it into components that can use it
        from tools.llm_tool import LLMTool

        self._llm = LLMTool()
        self._memory = memory_store or MemoryStore(collection_name=settings.memory_collection, llm_tool=self._llm)
        self._planner = planner or Planner(llm=self._llm)
        self._summarizer = summarizer or Summarizer()
        # compile the regex once for detecting explicit web-search commands
        import re
        self._SEARCH_PATTERN = re.compile(r"\b(?:search for|look up|web search for|find)\b\s+(.+)", re.I)
        # agent registry for specialized terminal agents (not used in routing)
        self._agents: Dict[str, Any] = {}
        try:
            self._agents["synthesizer"] = SynthesizerAgent(self._llm)
        except Exception:
            logger.exception("Failed to initialize SynthesizerAgent")
        try:
            from agents.research_agent import ResearchAgent
            self._agents["research"] = ResearchAgent(self._memory, llm=self._llm)
        except Exception:
            logger.exception("Failed to initialize ResearchAgent")
        self._vector_tool = vector_tool or VectorSearchTool(self._memory)
        # Register default tools so specialized agents can find them
        try:
            register_tool(WebSearchTool())
            register_tool(FileMemoryTool())
            register_tool(CodeExecutionTool())
        except Exception:
            logger.exception("Failed to register default tools")

    async def _generate_chat_reply(self, user_input: str) -> str:
        """Produce a friendly chat-style response for non-goal input.

        This helper uses the shared LLM instance (`self._llm`). Tests may
        override `self._chat_llm` if they need a dummy implementation.

        When the user directly asks what the system can do or about its
        capabilities we add an extra hint so the reply can point them at
        multimedia/image/audio/file features, helping to "sell" the app.
        """
        # prefer injected chat-specific LLM for tests or customization
        llm = getattr(self, "_chat_llm", None) or self._llm
        hint = ""
        lower = user_input.strip().lower()
        # generic capability prompt question
        if any(k in lower for k in ("what can you", "what do you", "capabilit", "features")):
            hint = (
                " You might mention that I can generate images, transcribe audio or "
                "video, analyse uploaded files, plan projects, and much more. "
                "Describe your goal and I’ll suggest a starting prompt."
            )
        # keywords signalling features we support
        cap_keywords = {
            "image": "You can generate or analyse images using the 📷 button.",
            "audio": "Try uploading an audio clip for transcription.",
            "video": "I can analyse videos and describe them.",
            "file": "Attach a file and ask me to read or summarise it.",
            "goal": "Describe a goal and I'll decompose it into tasks.",
        }
        for kw, tip in cap_keywords.items():
            if kw in lower and tip not in hint:
                hint += " " + tip
        prompt = (
            "You are a helpful, friendly assistant conversing with a user. "
            "The user said:\n" + user_input + "\n"
            "Respond naturally and encourage next steps, but do not attempt to "
            "break the input into tasks unless the user explicitly asks you to."
            + hint
        )
        try:
            return (await llm.generate(prompt, context=user_input)).strip()
        except Exception:
            logger.exception("Chat reply generation failed; echoing input")
            return user_input

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
        # placeholder for any queued-notice passed from caller (not used currently)
        queued_notice: str | None = None
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
        plan = plan or {}
        # normalize tasks from planner to avoid None entries
        tasks = [t for t in (plan.get("tasks") or []) if isinstance(t, dict)]

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
                "write code", "generate code", "code snippet", "write a function",
                "write a class", "write a script", "create a function",
                "python function", "javascript function", "typescript function",
                "implement the code", "write the code", "produce code",
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
                            # Handle multiple agent return shapes:
                            # BaseAgent subclasses: {"result": {...}, ...} or direct {"output": ..., "summary": ...}
                            # TaskAgent: {"output": str, "agent_id": ..., "status": ...}
                            # CodingAgent/ResearchAgent via BaseAgent.execute: wraps in outer {"result": inner}
                            r = res.get("result")
                            if isinstance(r, dict):
                                out = r.get("summary") or r.get("output") or str(r)
                            elif r is not None:
                                out = str(r)
                            else:
                                # Direct output fields (TaskAgent, CodingAgent when result is not nested)
                                out = res.get("output") or res.get("summary") or res.get("code")
                                if out is None:
                                    out = str(res)
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

        # Make task_map JSON-serializable (convert sets to lists) and return
        serializable_map = {}
        for tid, info in task_map.items():
            entry = dict(info)
            if isinstance(entry.get("seen_hashes"), set):
                entry["seen_hashes"] = list(entry["seen_hashes"])
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

        result_out = {
            "status": status_out if 'status_out' in locals() else "success",
            "goal": goal,
            "task_map": serializable_map,
            "final": final_result,
            "evaluation": eval_out,
        }
        llm_provider = getattr(self._llm, "last_provider", None)
        if llm_provider:
            result_out["llm_provider"] = llm_provider
        if getattr(self._llm, "last_fallback", None):
            result_out["llm_error"] = self._llm.last_fallback
        if 'context' in locals():
            result_out["reflection_reused"] = context.get("reflection_reused", False)
        if queued_notice:
            result_out.setdefault("notice", queued_notice)
        if getattr(self._llm, "last_fallback", None):
            notice = f"Note: {self._llm.last_fallback}."
            result_out.setdefault("notice", notice)
            self.metrics.failovers += 1

        _final_summary = ""
        if isinstance(final_result, dict):
            _final_summary = final_result.get("summary") or ""
        result_out["response"] = _final_summary or str(final_result)
        # housekeeping: prune low-confidence graph entries after run
        try:
            self._memory.prune_graph()
        except Exception:
            logger.exception("Pruning graph failed")

        return result_out

    async def _perform_web_search(self, query: str) -> str:
        """Fetch a simple search results page for *query* and return main text.

        We use DuckDuckGo's HTML interface to avoid JS.  This is a very
        lightweight helper intended to give users a rough answer rather than a
        comprehensive report.  Errors are surfaced as plain text.
        """
        import httpx
        import urllib.parse

        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url)
            r.raise_for_status()
            text = r.text
            # strip tags naively for brevity
            import re
            text = re.sub(r"<[^>]+>", "", text)
            # limit length so we don't flood the chat
            return text.strip()[:2000] or "(no text found)"
        except Exception as exc:
            return f"[web search failed: {exc}]"
        

    def get_last_plan(self) -> Optional[Dict[str, Any]]:
        """Return the most recent plan produced by the planner (or None)."""
        return getattr(self, '_last_plan', None)

    def get_plan_graph_png(self) -> bytes:
        """Generate a simple PNG rendering of the last plan using matplotlib.

        Returns raw PNG bytes; caller should set content-type accordingly.
        """
        import matplotlib.pyplot as plt
        import io
        plan = self.get_last_plan()
        if not plan or not plan.get('tasks'):
            # empty placeholder
            fig = plt.figure(figsize=(4, 1))
            fig.text(0.5, 0.5, 'no plan', ha='center', va='center')
        else:
            tasks = plan['tasks']
            fig, ax = plt.subplots(figsize=(max(4, len(tasks)*1.2), 2))
            ax.axis('off')
            for i, task in enumerate(tasks):
                rect = plt.Rectangle((i, 0.5), 0.9, 0.8, fill=True, color='#7c6af7', alpha=0.3)
                ax.add_patch(rect)
                ax.text(i+0.45, 0.9, task.get('title', '')[:20] or task.get('instructions','')[:20],
                        ha='center', va='center', fontsize=8, wrap=True)
            ax.set_xlim(0, len(tasks))
            ax.set_ylim(0, 2)
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        return buf.read()
        if 'last_evaluation' in locals() and last_evaluation is not None:
            if isinstance(last_evaluation, dict):
                eval_out = last_evaluation
            else:
                eval_out = {"decision": last_evaluation}
        result_out: Dict[str, Any] = {"status": status_out if 'status_out' in locals() else "success", "goal": goal, "task_map": serializable_map, "final": final_result, "evaluation": eval_out}
        # append any information about the LLM provider that was used, as well
        # as any fallback notice (error message).  This makes it easy for
        # callers (and the frontend) to display which service generated the
        # text and whether a failover occurred.
        llm_provider = getattr(self._llm, "last_provider", None)
        if llm_provider:
            result_out["llm_provider"] = llm_provider
        if getattr(self._llm, "last_fallback", None):
            result_out["llm_error"] = self._llm.last_fallback
        # attach reflection flag if available
        if 'context' in locals():
            result_out["reflection_reused"] = context.get("reflection_reused", False)
        # queued notice override if present (should generally be None)
        if queued_notice:
            result_out.setdefault("notice", queued_notice)
        # add any user notices collected by the LLM tool
        if getattr(self._llm, "last_fallback", None):
            notice = f"Note: {self._llm.last_fallback}."
            result_out.setdefault("notice", notice)
            # track that we had to fail over
            self.metrics.failovers += 1

        # surface the final summary as a top-level "response" field so app.py
        # and other callers don't need to dig into the nested "final" dict.
        _final_summary = ""
        if isinstance(final_result, dict):
            _final_summary = final_result.get("summary") or ""
        result_out["response"] = _final_summary or str(final_result)
        # housekeeping: prune low-confidence graph entries after run
        try:
            self._memory.prune_graph()
        except Exception:
            logger.exception("Pruning graph failed")
        return result_out

    async def stream_user_input(self, user_input: str):
        """Stream a response to *user_input* as an async generator of SSE-ready strings.

        For conversational input the LLM tokens are yielded one-by-one so the
        browser can render them in real-time.  For autonomous goal execution a
        series of progress events are emitted followed by the final summary tokens.

        Every yielded value is a JSON-encoded dict so the HTTP layer only needs to
        do ``f"data: {token}\\n\\n"``.

        Event shapes
        ------------
        ``{"type": "token",    "text": "<token>"}``          – LLM output fragment
        ``{"type": "progress", "text": "<status message>"}`` – orchestration step
        ``{"type": "done",     "result": {...}}``             – final structured result
        ``{"type": "error",    "text": "<message>"}``         – error (stream ends)
        """
        import json as _json

        def _evt(obj: dict) -> str:
            return _json.dumps(obj)

        greeting = user_input.strip().lower()
        if greeting in ("hi", "hello", "hey", "hey there", "good morning", "good afternoon", "good evening"):
            # include some handy starting suggestions so the user knows what’s possible
            hello_msg = (
                "Hello! I'm Concierge — how can I assist you today?\n\n"
                "You can ask for an image, upload a file for analysis, or set a goal. "
                "For example: 'Generate an image of a sunset.' or "
                "'Create a 4-week goal to improve test coverage.'"
            )
            yield _evt({"type": "token", "text": hello_msg})
            # if fallback occured, send a progress notice
            if getattr(self._llm, "last_fallback", None):
                yield _evt({"type": "progress", "text": f"Note: {self._llm.last_fallback}."})
                self.metrics.failovers += 1
            yield _evt({"type": "done", "result": {"response": hello_msg}})
            return

        # detect explicit web-search requests and satisfy them before any
        # usual planning or chat behaviour.  This keeps the assistant from
        # ignoring phrases such as "search for LLM benchmarks 2026".
        m = self._SEARCH_PATTERN.search(user_input)
        if m:
            query = m.group(1).strip()
            # spawn a ResearchAgent so the planner/agents machinery can run it
            agent = self._agents.get("research")
            if agent:
                yield _evt({"type": "progress", "text": f"Searching the web for '{query}'…"})
                manager_id, fut = await self._concurrency.register(agent.execute({"query": query}))
                try:
                    result = await fut
                    summary = result.get("summary") or ""
                except Exception as exc:
                    summary = f"[search failed: {exc}]"
                yield _evt({"type": "token", "text": summary})
                yield _evt({"type": "done", "result": {"response": summary}})
                return
            else:
                # fallback to simple helper if agent unavailable
                search_text = await self._perform_web_search(query)
                yield _evt({"type": "token", "text": search_text})
                yield _evt({"type": "done", "result": {"response": search_text}})
                return

        # Bypass planner for conversational questions
        if _is_conversational(user_input):
            llm = getattr(self, "_chat_llm", None) or self._llm
            # hint for promotional questions and capability keywords
            hint = ""
            lower = user_input.strip().lower()
            if any(k in lower for k in ("what can you", "what do you", "capabilit", "features")):
                hint = (
                    " You might mention that I can generate images, transcribe audio or "
                    "video, analyse uploaded files, plan projects, and much more. "
                    "Describe your goal and I’ll suggest a starting prompt."
                )
            cap_keywords = {
                "image": "You can generate or analyse images using the 📷 button.",
                "audio": "Try uploading an audio clip for transcription.",
                "video": "I can analyse videos and describe them.",
                "file": "Attach a file and ask me to read or summarise it.",
                "goal": "Describe a goal and I'll decompose it into tasks.",
            }
            for kw, tip in cap_keywords.items():
                if kw in lower and tip not in hint:
                    hint += " " + tip
            prompt = (
                "You are a helpful, friendly assistant conversing with a user. "
                "The user said:\n" + user_input + "\n"
                "Respond naturally and encourage next steps." + hint
            )
            full_response_conv: list[str] = []
            try:
                async for token in llm.astream(prompt, context=user_input):
                    full_response_conv.append(token)
                    yield _evt({"type": "token", "text": token})
            except Exception as exc:
                yield _evt({"type": "error", "text": str(exc)})
                return
            # if there was a fallback, notify user
            if getattr(llm, "last_fallback", None):
                yield _evt({"type": "progress", "text": f"Note: {llm.last_fallback}."})
                self.metrics.failovers += 1
            yield _evt({"type": "done", "result": {"response": "".join(full_response_conv)}})
            return

        # Ask planner: is this conversational or a real goal?
        try:
            plan = await self._planner.plan(user_input)
            plan = plan or {}
        except Exception as exc:
            yield _evt({"type": "error", "text": f"Planner error: {exc}"})
            return

        # normalize tasks: planner may return None entries, ensure list of dicts
        tasks = [t for t in (plan.get("tasks") or []) if isinstance(t, dict)]
        is_conversational = (
            not tasks
            or (
                len(tasks) == 1
                and isinstance(tasks[0], dict)
                and tasks[0].get("instructions", "").strip().lower() == user_input.strip().lower()
                and len(user_input.strip().split()) <= 5
            )
        )

        if is_conversational:
            # Stream LLM tokens directly
            llm = getattr(self, "_chat_llm", None) or self._llm
            prompt = (
                "You are a helpful, friendly assistant conversing with a user. "
                "The user said:\n" + user_input + "\n"
                "Respond naturally and encourage next steps."
            )
            full_response: list[str] = []
            try:
                async for token in llm.astream(prompt, context=user_input):
                    full_response.append(token)
                    yield _evt({"type": "token", "text": token})
            except Exception as exc:
                logger.exception("Streaming chat reply failed")
                yield _evt({"type": "error", "text": str(exc)})
                return
            if getattr(llm, "last_fallback", None):
                yield _evt({"type": "progress", "text": f"Note: {llm.last_fallback}."})
                self.metrics.failovers += 1
            yield _evt({"type": "done", "result": {"response": "".join(full_response)}})
            return

        # Autonomous goal — emit progress events, then stream the final synthesis
        yield _evt({"type": "progress", "text": "Planning tasks…"})
        try:
            # Run the autonomous coordinator in a background task and emit
            # periodic progress events so clients see liveness during long
            # running plans (prevents silent timeouts in the browser).
            try:
                run_task = asyncio.create_task(self.run_autonomous(user_input))
            except Exception as exc:
                logger.exception("Failed to start run_autonomous task")
                yield _evt({"type": "error", "text": str(exc)})
                return

            # initial small delay to let planner start
            await asyncio.sleep(0.1)
            progress_count = 0
            while True:
                if run_task.done():
                    break
                progress_count += 1
                # emit a lightweight progress heartbeat every 3 seconds
                yield _evt({"type": "progress", "text": f"Working on plan (step {progress_count})..."})
                await asyncio.sleep(3)
            try:
                result = await run_task
            except Exception as exc:
                logger.exception("run_autonomous raised during execution")
                result = {"final": {"summary": ""}, "response": "", "status": "error", "error": str(exc)}
            if result is None:
                logger.warning("run_autonomous returned None; substituting empty result")
                result = {"final": {"summary": ""}, "response": ""}
            # ensure result is a dict so downstream .get() calls are safe
            if not isinstance(result, dict):
                logger.warning("run_autonomous returned non-dict result; coercing to dict")
                result = {"final": {"summary": str(result)}, "response": str(result)}
        except Exception as exc:
            logger.exception("run_autonomous failed during streaming")
            yield _evt({"type": "error", "text": str(exc)})
            return

        # Stream the final summary text token-by-token from the result
        final = result.get("final") or {}
        summary: str = final.get("summary") or str(result)
        yield _evt({"type": "progress", "text": "Generating response…"})
        # chunk the summary so the frontend renders progressively
        chunk_size = 8
        for i in range(0, len(summary), chunk_size):
            yield _evt({"type": "token", "text": summary[i: i + chunk_size]})
            await asyncio.sleep(0)  # yield to event loop between chunks
        yield _evt({"type": "done", "result": result})

    async def handle_user_input(self, user_input: str) -> Dict[str, Any]:
        """Handle user input asynchronously.

        - Ask Planner for decision (awaitable)
        - For direct responses: return immediately
        - For spawned tasks: create TaskAgent, register with concurrency manager,
          await its completion, summarize and store results in memory, and
          return structured metadata to the caller.
        """
        # throttle incoming requests
        # if the semaphore is already exhausted we mark this request as queued
        # and remember the raw input so we can notify the user later.
        queued_notice: str | None = None
        if self._request_sem._value == 0:
            self.metrics.requests_queued += 1
            queued_notice = f"OK - still working on the previous request; yours (\"{user_input}\") is queued and will run shortly."
        async with self._request_sem:
            logger.info("SacredTimeline handling input")
            # metrics: count every incoming call
            self.metrics.total_requests += 1

        # quick replies for simple greetings to avoid unnecessary planning
        greeting = user_input.strip().lower()
        if greeting in ("hi", "hello", "hey", "hey there", "good morning", "good afternoon", "good evening"):
            # if fallback occurred, note it
            note = None
            if getattr(self._llm, "last_fallback", None):
                note = f"Note: {self._llm.last_fallback}."
                self.metrics.failovers += 1
            resp = {"status": "success", "response": "Hello! I'm Concierge — how can I assist you today?"}
            if queued_notice:
                resp["notice"] = queued_notice
            elif note:
                resp["notice"] = note
            return resp

        # bypass orchestration for conversational questions
        if _is_conversational(user_input):
            reply = await self._generate_chat_reply(user_input)
            return {"status": "success", "response": reply}

        # ask planner to decompose into tasks. planner may return a trivial "echo"
        plan = await self._planner.plan(user_input)
        # persist the last plan so UI can query thread state
        self._last_plan = plan
        tasks = plan.get("tasks") or []

        # if the planner produced a single task that simply repeats the user_input,
        # consider treating the exchange as casual conversation.  however, don't
        # do this for longer inputs – a real goal may look exactly like the
        # original sentence when the planner falls back, so we require the input
        # to be quite short (<=5 words) before abandoning the autonomous loop.
        if tasks:
            if (
                len(tasks) == 1
                and tasks[0].get("instructions", "").strip().lower() == user_input.strip().lower()
            ):
                word_count = len(user_input.strip().split())
                if word_count <= 5:
                    # small talk or unstructured input; hand off to chat reply
                    reply = await self._generate_chat_reply(user_input)
                    return {"status": "success", "response": reply}
                # otherwise the user likely has a genuine goal; fall through

            # proceed with autonomous execution for non-trivial plans
            return await self.run_autonomous(user_input)

        # no tasks at all: still conversational
        reply = await self._generate_chat_reply(user_input)
        return {"status": "success", "response": reply}


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
