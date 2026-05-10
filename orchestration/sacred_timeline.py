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
import time
import uuid
from collections import deque

from agents.planner import Planner
from agents.evaluator import Evaluator
from agents.summarizer import Summarizer
from agents.research_agent import ResearchAgent
from agents.coding_agent import CodingAgent
from agents.critic_agent import CriticAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.base_agent import BaseAgent
from memory.memory_store import MemoryStore
from tools.vector_search_tool import VectorSearchTool
from config.settings import get_settings 
from tools.tool_registry import register_tool
from tools.web_search_tool import WebSearchTool
from tools.file_memory_tool import FileMemoryTool
from tools.code_execution_tool import CodeExecutionTool
from tools.tool_router import ToolRouter
from jobs.task_tree_store import append_task_logs, get_task_tree, initialize_thread, upsert_task_node
from celery import chain
from tasks.step_assistant_tasks import execute_step_task

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


def _normalize_result(result: Any) -> Dict[str, Any]:
    """Normalize a result object into a safe dictionary for downstream consumers."""
    if isinstance(result, dict):
        return result
    if result is None:
        return {}
    return {"response": str(result)}


def _extract_result_text(result: Any) -> str:
    """Get the most useful text from a result dict or fallback to a string."""
    if isinstance(result, dict):
        for key in ("output", "summary", "response"):
            value = result.get(key)
            if value is not None and str(value).strip():
                return str(value)
        return str(result)
    return str(result)


def _result_status(result: Any) -> str:
    return result.get("status") if isinstance(result, dict) else "complete"


def _find_task_node(tree: Optional[Dict[str, Any]], task_id: str) -> Optional[Dict[str, Any]]:
    if tree is None:
        return None
    if tree.get("task_id") == task_id:
        return tree
    for child in tree.get("children", []):
        found = _find_task_node(child, task_id)
        if found is not None:
            return found
    return None


def _derive_visual_node_type(task_id: str, thread_id: Optional[str], metadata: Optional[Dict[str, Any]]) -> str:
    label = ""
    if isinstance(metadata, dict):
        label = str(metadata.get("task_name") or "")
        if metadata.get("agent_type") or metadata.get("tool_name"):
            return "tool_call"
    if task_id == thread_id:
        return "thread_root"
    normalized = label.lower()
    if "rag" in normalized or "retrieve" in normalized or "search" in normalized:
        return "rag_retrieval"
    if "observe" in normalized or "scan" in normalized or "read" in normalized:
        return "observation"
    return "reasoning"


def _result_final(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        final = result.get("final")
        if isinstance(final, dict):
            return final
        if isinstance(final, str):
            return {"summary": final}
    return {}


class Metrics:
    """Very lightweight in-memory metrics for visibility."""
    def __init__(self) -> None:
        self.total_requests = 0
        self.requests_queued = 0
        self.failovers = 0


class SacredTimeline:
    def __init__(
        self,
        memory_store: Optional[MemoryStore] = None,
        planner: Optional[Planner] = None,
        summarizer: Optional[Summarizer] = None,
        vector_tool: Optional[VectorSearchTool] = None,
    ) -> None:
        settings = get_settings()
        self.metrics = Metrics()
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
        # timeline subscription queues for SSE/live updates
        self._timeline_subscribers: set[asyncio.Queue] = set()
        self._timeline_graph_nodes: set[str] = set()
        self._timeline_graph_edges: set[str] = set()
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
                " You might mention that I can generate images, analyse uploaded files, "
                "plan projects, write code, and much more. Describe your goal and I’ll suggest a starting prompt."
            )
        # keywords signalling features we support
        cap_keywords = {
            "image": "You can generate or analyse images using the 📷 button.",
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

    def _publish_timeline_event(self, event: Dict[str, Any]) -> None:
        for q in list(self._timeline_subscribers):
            try:
                q.put_nowait(event)
            except Exception:
                continue

    def _timeline_node_key(self, thread_id: str, task_id: str) -> str:
        return f"{thread_id}:{task_id}"

    def _timeline_edge_key(self, thread_id: str, from_id: str, to_id: str) -> str:
        return f"{thread_id}:{from_id}:{to_id}"

    def _task_tree_update(self, thread_id: Optional[str], task_id: str, status: str, progress: int, color: str, metadata: Optional[Dict[str, Any]] = None, parent_id: Optional[str] = None) -> None:
        if not thread_id:
            return
        tree = get_task_tree(thread_id)
        existing_node = _find_task_node(tree, task_id)
        is_new_node = existing_node is None
        try:
            upsert_task_node(
                thread_id=thread_id,
                task_id=task_id,
                parent_id=parent_id,
                status=status,
                progress=progress,
                color=color,
                metadata=metadata,
            )
            try:
                task_update = {
                    "type": "task_update",
                    "thread_id": thread_id,
                    "task_id": task_id,
                    "task_name": metadata.get("task_name") if isinstance(metadata, dict) else None,
                    "status": status,
                    "progress": progress,
                    "summary": metadata.get("result_summary") if isinstance(metadata, dict) else None,
                }
                self._publish_timeline_event(task_update)

                visual_payload = {
                    "id": task_id,
                    "thread_id": thread_id,
                    "type": _derive_visual_node_type(task_id, thread_id, metadata),
                    "label": (metadata.get("task_name") if isinstance(metadata, dict) else task_id) or task_id,
                    "status": status,
                    "x": 180 + (len(self._timeline_graph_nodes) % 6) * 320,
                    "y": 120 + (len(self._timeline_graph_nodes) // 6) * 120,
                    "metadata": {
                        "progress": progress,
                        **({} if metadata is None else metadata),
                    },
                }

                if is_new_node:
                    node_key = self._timeline_node_key(thread_id, task_id)
                    if node_key not in self._timeline_graph_nodes:
                        self._timeline_graph_nodes.add(node_key)
                        self._publish_timeline_event({
                            "type": "node_add",
                            "payload": visual_payload,
                            "thread_id": thread_id,
                        })
                    if parent_id:
                        edge_key = self._timeline_edge_key(thread_id, parent_id, task_id)
                        if edge_key not in self._timeline_graph_edges:
                            self._timeline_graph_edges.add(edge_key)
                            self._publish_timeline_event({
                                "type": "edge_add",
                                "payload": {
                                    "fromId": parent_id,
                                    "toId": task_id,
                                    "type": "dependency",
                                },
                                "thread_id": thread_id,
                            })
                else:
                    self._publish_timeline_event({
                        "type": "node_update",
                        "payload": {
                            "id": task_id,
                            "status": status,
                            "label": visual_payload["label"],
                            "metadata": visual_payload["metadata"],
                        },
                        "thread_id": thread_id,
                    })
            except Exception:
                logger.exception('Failed to publish timeline progress update for %s/%s', thread_id, task_id)
        except Exception:
            logger.exception('Failed to update task tree for %s/%s', thread_id, task_id)

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

    def _topological_sort(self, tasks: list[dict]) -> list[dict]:
        """
        Performs a topological sort on a list of tasks with dependencies.
        Raises ValueError if a cycle is detected.
        """
        task_map = {t["task_id"]: t for t in tasks}
        in_degree = {tid: 0 for tid in task_map}
        adj = {tid: [] for tid in task_map}

        for tid, task in task_map.items():
            for dep in task.get("depends_on", []):
                if dep in task_map:
                    adj[dep].append(tid)
                    in_degree[tid] += 1

        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        sorted_order = []

        while queue:
            u = queue.popleft()
            sorted_order.append(task_map[u])

            for v in adj.get(u, []):
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        if len(sorted_order) == len(tasks):
            return sorted_order
        else:
            # Identify nodes in cycle for better error message
            cycle_nodes = {tid for tid, deg in in_degree.items() if deg > 0}
            raise ValueError(f"A cycle was detected in the task graph involving tasks: {cycle_nodes}")

    async def run_autonomous(self, goal: str, max_depth: int = 3, max_tasks: int = 20, per_task_timeout: int = 60, thread_id: Optional[str] = None) -> Dict[str, Any]:
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
        plan = await self._planner.plan(goal)
        tasks = plan.get("tasks", [])

        if not tasks:
            logger.warning("Planner returned no tasks for goal: %s", goal)
            return {"status": "success", "response": "I analyzed the goal but found no specific tasks to execute."}

        try:
            sorted_tasks = self._topological_sort(tasks)
        except ValueError as e:
            logger.error("Failed to sort tasks for goal '%s': %s", goal, e)
            return {"status": "error", "response": f"Failed to create a plan: {e}"}

        # Shared context for all tasks in the chain
        context = {"goal": goal}

        # Create a chain of Celery tasks for sequential execution.
        # We use `.si()` (immutable signature) instead of `.s()` to prevent Celery 
        # from implicitly passing the return value of one task as the first argument 
        # to the next task. This ensures the tasks run sequentially and hand off 
        # cleanly without throwing a TypeError that leaves tasks stuck in "pending".
        logger.info("Creating sequential task chain for %d tasks...", len(sorted_tasks))
        task_chain = chain(
            execute_step_task.si(task=task, thread_id=thread_id, context=context)
            for task in sorted_tasks
        )

        # Execute the chain asynchronously
        result = task_chain.apply_async()

        logger.info("Dispatched task chain for thread_id: %s (Celery Chain ID: %s)", thread_id, result.id)

        # This Celery task now only sets up the chain. The return value is
        # less critical as the client will monitor the task tree via WebSocket.
        return {
            "status": "processing",
            "response": "I have created a plan and started executing the tasks sequentially. You can monitor the progress.",
            "thread_id": thread_id,
            "task_map": {t["task_id"]: t for t in tasks},
        }

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

    def subscribe_timeline(self) -> "asyncio.Queue":
        """Create and return a subscriber queue which will receive timeline update dicts.

        Caller is responsible for removing the queue when done; prefer using
        it with an async-iterator pattern and cancelling the task on disconnect.
        """
        q: asyncio.Queue = asyncio.Queue()
        self._timeline_subscribers.add(q)
        # immediately send a snapshot of the current plan
        try:
            plan = self.get_last_plan()
            if plan:
                q.put_nowait({"type": "plan", "plan": plan})
        except Exception:
            pass
        return q

    def unsubscribe_timeline(self, q: "asyncio.Queue") -> None:
        try:
            self._timeline_subscribers.discard(q)
        except Exception:
            pass

    def get_plan_graph_png(self) -> bytes:
        """Generate a PNG rendering of the last plan.

        Prefer matplotlib for rich diagrams. If matplotlib is not
        available (e.g. slim serverless builds) fall back to a simple
        Pillow-rendered text image so the endpoint never returns 500.

        Returns raw PNG bytes; caller should set content-type accordingly.
        """
        import io
        import textwrap

        plan = self.get_last_plan()
        tasks = (plan.get('tasks') if plan and plan.get('tasks') else []) or []

        # Try to use matplotlib if available (full visual graph)
        try:
            import matplotlib.pyplot as plt  # type: ignore
            import matplotlib.patches as mpatches  # type: ignore
            use_matplotlib = True
        except Exception:
            use_matplotlib = False

        if use_matplotlib:
            # --- existing matplotlib implementation ---
            import math

            if not tasks:
                fig = plt.figure(figsize=(4, 1))
                fig.text(0.5, 0.5, 'no plan', ha='center', va='center')
                buf = io.BytesIO()
                fig.tight_layout()
                fig.savefig(buf, format='png')
                plt.close(fig)
                buf.seek(0)
                return buf.read()

            # Index tasks by id for easy lookup
            tasks_by_id = {t.get('task_id') or f"t{i}": t for i, t in enumerate(tasks)}
            # Ensure each task has an id and normalized depends_on
            for i, t in enumerate(tasks):
                if not t.get('task_id'):
                    t['task_id'] = f"t{i}"
                deps = t.get('depends_on') or []
                t['depends_on'] = deps

            # Compute depth (level) for each task: 0 for roots
            depths: dict = {}

            def compute_depth(tid, seen=None):
                if seen is None:
                    seen = set()
                if tid in depths:
                    return depths[tid]
                if tid in seen:
                    return 0
                seen.add(tid)
                t = tasks_by_id.get(tid)
                if not t:
                    depths[tid] = 0
                    return 0
                parents = t.get('depends_on') or []
                if not parents:
                    depths[tid] = 0
                    return 0
                d = max((compute_depth(p, seen) for p in parents), default=0) + 1
                depths[tid] = d
                return d

            for tid in list(tasks_by_id.keys()):
                compute_depth(tid)

            # Group tasks by depth
            levels: dict = {}
            for tid, d in depths.items():
                levels.setdefault(d, []).append(tasks_by_id.get(tid))

            max_level = max(levels.keys()) if levels else 0
            max_width = max(len(v) for v in levels.values())

            # Layout parameters
            node_w = 2.2
            node_h = 0.9
            x_gap = 0.8
            y_gap = 1.2

            fig_w = max(4, max_width * (node_w + x_gap) / 1.8)
            fig_h = max(2, (max_level + 1) * (node_h + y_gap) / 1.6)
            fig, ax = plt.subplots(figsize=(fig_w, fig_h))
            ax.set_xlim(0, max_width * (node_w + x_gap))
            ax.set_ylim(-0.5, (max_level + 1) * (node_h + y_gap))
            ax.axis('off')

            # Compute node positions: centered within their level
            positions: dict = {}
            for d in range(0, max_level + 1):
                row = levels.get(d, [])
                n = len(row)
                if n == 0:
                    continue
                total_w = n * node_w + (n - 1) * x_gap
                start_x = 0.5 * (max_width * (node_w + x_gap) - total_w)
                y = (max_level - d) * (node_h + y_gap) + 0.5
                for i, t in enumerate(row):
                    x = start_x + i * (node_w + x_gap)
                    positions[t['task_id']] = (x, y)

            # Color palette
            colors = ["#7c6af7", "#4fb0c6", "#f7a35c", "#90ed7d", "#f15c80"]

            # Draw nodes
            for idx, t in enumerate(tasks):
                tid = t['task_id']
                x, y = positions.get(tid, (0, 0.5))
                rect = mpatches.FancyBboxPatch((x, y), node_w, node_h,
                                               boxstyle="round,pad=0.1",
                                               linewidth=1, edgecolor="#333333",
                                               facecolor=colors[idx % len(colors)], alpha=0.25)
                ax.add_patch(rect)
                # Title + instructions (wrapped)
                title = t.get('title') or ''
                instr = t.get('instructions') or ''
                label = title if title.strip() else instr
                wrapped = textwrap.fill(label, width=24)
                ax.text(x + node_w / 2, y + node_h / 2, wrapped, ha='center', va='center', fontsize=8)

            # Draw arrows for dependencies (from parent -> child)
            for t in tasks:
                tid = t['task_id']
                child_pos = positions.get(tid)
                if not child_pos:
                    continue
                cx, cy = child_pos
                for parent_id in (t.get('depends_on') or []):
                    ppos = positions.get(parent_id)
                    if not ppos:
                        continue
                    px, py = ppos
                    # start at parent's center right, end at child's center left
                    start = (px + node_w, py + node_h / 2)
                    end = (cx, cy + node_h / 2)
                    ax.annotate('', xy=end, xytext=start,
                                arrowprops=dict(arrowstyle='->', color='#444444', lw=1.0,
                                                shrinkA=2, shrinkB=2))

            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=150)
            plt.close(fig)
            buf.seek(0)
            return buf.read()

        # --- Pillow fallback: return a simple textual PNG so callers still get an image ---
        try:
            from PIL import Image, ImageDraw, ImageFont  # type: ignore

            # Render a simple text-based image listing task titles (minimizes regression)
            if not tasks:
                lines = ["no plan"]
            else:
                lines = []
                for t in tasks:
                    title = (t.get('title') or '').strip()
                    instr = (t.get('instructions') or '').strip()
                    label = title if title else instr
                    lines.append((label or "(untitled task)")[:120])

            # Basic layout
            width = 800
            line_h = 20
            padding = 12
            height = max(60, padding * 2 + line_h * len(lines))

            img = Image.new('RGBA', (width, height), (6, 6, 12, 255))
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None

            y = padding
            for line in lines:
                draw.text((padding, y), line, fill=(230, 230, 230), font=font)
                y += line_h

            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return buf.read()
        except Exception:
            # As a last resort, return a 1x1 transparent PNG (avoid 500)
            return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDATx\x9cc``\x00\x00\x00\x04\x00\x01\x0e\x11\x02\xb5\x00\x00\x00\x00IEND\xaeB`\x82'

    async def stream_user_input(self, user_input: str, thread_id: Optional[str] = None):
        """
        This method is now deprecated for goal execution, which is handled by
        Celery tasks and WebSocket/SSE updates. It can still be used for
        streaming simple chat replies.
        """
        # For goals, we now dispatch a Celery task and the client listens on a WebSocket.
        # This method will now only handle the conversational/streaming part.
        # The main handle_user_input will decide whether to call this or dispatch the task.
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
                yield {"type": "token", "text": token}
        except Exception as exc:
            logger.exception("Streaming chat reply failed")
            yield {"type": "error", "text": str(exc)}
            return
        if getattr(llm, "last_fallback", None):
            yield {"type": "progress", "text": f"Note: {llm.last_fallback}."}
            self.metrics.failovers += 1
        yield {"type": "done", "result": {"response": "".join(full_response)}}

    async def handle_user_input(self, user_input: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
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

        if thread_id is not None:
            try:
                initialize_thread(thread_id, {
                    'task_name': 'assistant_thread',
                    'start_time': time.time(),
                    'color': '#7c6af7',
                })
            except Exception:
                logger.exception('Failed to initialize root task tree %s', thread_id)

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
        if not isinstance(plan, dict):
            logger.warning("Planner returned non-dict plan object in handle_user_input; coercing to empty plan: %r", plan)
            plan = {}
        # persist the last plan so UI can query thread state
        self._last_plan = plan
        # publish plan to timeline subscribers
        try:
            update = {"type": "plan", "plan": plan}
            for q in list(self._timeline_subscribers):
                try:
                    q.put_nowait(update)
                except Exception:
                    continue
        except Exception:
            logger.exception("Failed to publish timeline plan update")
        raw_tasks = plan.get("tasks")
        if not isinstance(raw_tasks, list):
            raw_tasks = []
        tasks = []
        for i, t in enumerate(raw_tasks):
            if isinstance(t, dict):
                tasks.append(t)
                continue
            tasks.append({
                "task_id": f"t{i+1}",
                "title": str(t),
                "instructions": str(t),
                "depends_on": [],
            })

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

            # This is a real goal. Dispatch it to Celery and return immediately.
            from tasks.main_tasks import run_autonomous_task

            thread_id = thread_id or str(uuid.uuid4())
            initialize_thread(thread_id, {
                'task_name': f'Goal: {user_input[:80]}',
                'start_time': time.time(),
                'metadata': {'goal': user_input},
            })
            run_autonomous_task.delay(goal=user_input, thread_id=thread_id)
            return {"status": "processing", "thread_id": thread_id}

        # no tasks at all: still conversational
        reply = await self._generate_chat_reply(user_input)
        return {"status": "success", "response": reply}


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def _demo():
        settings = get_settings()
        ms = MemoryStore(collection_name=settings.memory_collection)
        planner = Planner()
        summarizer = Summarizer()
        root = SacredTimeline(memory_store=ms, planner=planner, summarizer=summarizer)
        out = await root.handle_user_input("Please process and summarize this dataset")
        print(out)

    asyncio.run(_demo())
