from __future__ import annotations

"""Planner that produces structured multi-step plans using an LLM.

This module returns a structured plan: {"tasks": [...]}. It uses an
`LLMTool` (in tests this will be replaced with a DummyLLM).
"""

from typing import Any, Dict, List, Optional
import logging

from tools.llm_tool import LLMTool

logger = logging.getLogger(__name__)

_IMAGE_GOAL_MARKERS = ("logo", "image", "icon", "picture", "illustration", "render", "draw")


def _is_image_goal(goal: str) -> bool:
    g = (goal or "").lower()
    return any(m in g for m in _IMAGE_GOAL_MARKERS) or ("generate" in g and any(m in g for m in ("logo", "image", "icon")))


def normalize_image_workflow_plan(goal: str, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure image/logo goals always get prepare + generate steps."""
    if not _is_image_goal(goal):
        return tasks

    titles = [(t.get("title") or "").lower() for t in tasks]
    has_prepare = any("prepare" in t for t in titles)
    has_generate = any(
        any(k in t for k in ("generate image", "generate logo", "render image", "create logo"))
        for t in titles
    )
    if len(tasks) >= 2 and has_prepare and has_generate:
        return tasks

    return [
        {
            "task_id": "t1",
            "title": "Prepare image prompt",
            "instructions": f"Formulate a detailed, descriptive prompt for image generation: {goal}",
            "depends_on": [],
        },
        {
            "task_id": "t2",
            "title": "Generate image",
            "instructions": "Submit the prompt to the image generation plugin and return the result URL.",
            "depends_on": ["t1"],
        },
    ]


class Planner:
    """Async planner that uses an LLM to convert a goal into a structured plan.

    The planner returns a dict with a `tasks` list. Each task is a dict with
    fields: `task_id`, `title`, `instructions`, and optional `depends_on`.
    """

    def __init__(self, llm: Optional[LLMTool] = None) -> None:
        self.llm = llm or LLMTool()

    async def plan(self, goal: str, max_tasks: int = 5) -> Dict[str, Any]:
        """Return a plan for a high-level `goal`.

        The output is a dict: {"tasks": [...]}.
        """
        prompt = (
            "Break the following user goal into up to {max_tasks} ordered subtasks. "
            "Return a JSON array of tasks where each task has 'task_id', 'title', 'instructions', "
            "and optional 'depends_on' (a list of task_ids).\n"
            "For image or logo generation goals, ALWAYS return exactly two tasks: "
            "(1) Prepare image prompt, (2) Generate image (depends on step 1).\n"
            "Goal:\n{goal}".format(max_tasks=max_tasks, goal=goal)
        )

        try:
            raw = await self.llm.generate(prompt, context=goal)
        except Exception:
            logger.exception("Planner LLM failed; falling back to heuristic plan")
            raw = ""

        # Try to parse JSON from LLM; if it fails, fallback to simple heuristics
        import json

        tasks: List[Dict[str, Any]] = []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                if isinstance(parsed.get("tasks"), list):
                    parsed = parsed["tasks"]
                elif isinstance(parsed.get("plan"), list):
                    parsed = parsed["plan"]
                else:
                    parsed = [parsed]

            if isinstance(parsed, list):
                for i, t in enumerate(parsed[:max_tasks]):
                    # tolerate LLMs that return a list of strings instead of
                    # structured dicts. Coerce string items into a simple
                    # task dict so downstream code can safely call .get().
                    if isinstance(t, str):
                        tasks.append({
                            "task_id": f"t{i+1}",
                            "title": t,
                            "instructions": t,
                            "depends_on": [],
                        })
                        continue
                    # coerce unexpected types to dict with a string title
                    if not isinstance(t, dict):
                        t = {"title": str(t)}

                    # safe extraction using dict.get
                    task = {
                        "task_id": t.get("task_id") or f"t{i+1}",
                        "title": t.get("title") or t.get("task") or f"Step {i+1}",
                        "instructions": t.get("instructions") or t.get("details") or "",
                        "depends_on": t.get("depends_on", []),
                    }
                    tasks.append(task)
        except Exception:
            logger.debug("Planner fallback: simple split heuristic")
            if _is_image_goal(goal):
                tasks = normalize_image_workflow_plan(goal, [])
            else:
                parts = [p.strip() for p in goal.split(".") if p.strip()]
                for i, p in enumerate(parts[:max_tasks]):
                    tasks.append({"task_id": f"t{i+1}", "title": f"Step {i+1}", "instructions": p, "depends_on": []})

        if not tasks:
            tasks = [{"task_id": "t1", "title": "Perform goal", "instructions": goal, "depends_on": []}]

        tasks = normalize_image_workflow_plan(goal, tasks)
        return {"tasks": tasks}


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def _demo():
        p = Planner()
        plan = await p.plan("Collect data from source A and summarize key metrics.")
        print(json.dumps(plan, indent=2))

    asyncio.run(_demo())
