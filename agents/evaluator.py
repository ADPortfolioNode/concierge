"""Evaluator: reviews task outputs and returns a decision.

The evaluator uses an LLM to judge whether the overall goal is satisfied
or whether further tasks/refinements are required. It returns a dict:

    {"result": "complete"|"continue"|"refine", "feedback": "..."}

If the LLM is unavailable, a lightweight heuristic is used.
"""

from __future__ import annotations

from typing import Optional, Dict
import logging

from tools.llm_tool import LLMTool

logger = logging.getLogger(__name__)


class Evaluator:
    def __init__(self, llm: Optional[LLMTool] = None) -> None:
        self.llm = llm or LLMTool()

    async def evaluate(self, goal: str, task_outputs: str, context: Optional[str] = None) -> Dict[str, str]:
        """Evaluate combined task outputs against the goal.

        Returns a dict with keys: `result` and `feedback`.
        """
        prompt = (
            "You are an evaluator. Given the user goal and the following combined "
            "task outputs, decide whether the goal is satisfied. Respond with one "
            "of: 'complete', 'continue', or 'refine'. Provide a brief justification.\n\n"
            f"Goal:\n{goal}\n\nTask outputs:\n{task_outputs}\n\nDecision:" 
        )

        try:
            raw = await self.llm.generate(prompt, context=goal)
        except Exception:
            logger.exception("Evaluator LLM failed; falling back to heuristic")
            raw = ""

        # Simple parsing heuristics
        text = (raw or "").lower()
        if "complete" in text:
            return {"result": "complete", "feedback": raw}
        if "refine" in text or "rework" in text or "incorrect" in text:
            return {"result": "refine", "feedback": raw}

        # Fallback heuristic: if outputs are reasonably long, treat as complete
        if len(task_outputs or "") > 200:
            return {"result": "complete", "feedback": "Outputs appear comprehensive."}

        return {"result": "continue", "feedback": raw or "More work needed."}


if __name__ == "__main__":
    import asyncio

    async def _demo():
        e = Evaluator()
        r = await e.evaluate("Summarize dataset", "Here is a short summary...")
        print(r)

    asyncio.run(_demo())
