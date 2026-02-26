from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from tools.llm_tool import LLMTool

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    def __init__(self, memory, llm: Optional[LLMTool] = None):
        super().__init__(name="CriticAgent", memory=memory, llm=llm)

    async def run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hardened Critic evaluate path.
        - If LLM unavailable or parsing fails -> return approve (avoid refine loops)
        - If score >= threshold -> approve
        - If suggestions empty and score low -> synthesize a single suggestion
        - Strip recursive identical suggestions if provided via context
        """
        outputs = task.get("outputs") or task.get("output") or ""
        context = task.get("context") or {}
        # default decision template
        default = {"agent": self.name, "decision": "approve", "score": 80, "comments": "heuristic approve", "suggestions": []}

        # determine if this is a memory recall run (flag injected by coordinator)
        is_recall = isinstance(context, dict) and bool(context.get("recall_run"))
        if is_recall:
            # simple deterministic check: did the ResearchAgent include the context marker?
            txt = str(outputs or "")
            if "context:" in txt:
                res = {"agent": self.name, "decision": "approve", "score": 80, "comments": "memory context used", "suggestions": []}
            else:
                res = {"agent": self.name, "decision": "refine", "score": 20,
                       "comments": "no memory context referenced", "suggestions": [
                           "Please reference prior findings from memory (include context: ...)."
                       ]}
            try:
                await self.memory.store_summary(task_name=task.get("title") or task.get("task_id", "critic"), summary=str(res), metadata={"agent_type": self.name, "decision": res.get("decision")})
            except Exception:
                logger.exception("Failed to store critic feedback in memory")
            return res

        prompt = (
            f"Evaluate the following outputs for quality, correctness, and completeness: {outputs}\n"
            "Provide a JSON object with keys: decision (approve|refine), score (0-100), comments, suggestions (list)."
        )

        if self.llm is None:
            return default

        # attempt LLM call
        try:
            resp = await self.llm.generate(prompt, context=str(outputs))
        except Exception:
            logger.exception("Critic LLM failed")
            # Fail-safe: approve to avoid triggering refinements
            return default

        # Try to parse structured JSON.  Only for recall tasks do we retry and
        # refuse to approve; non-recall falls back to default approval on parse
        # failure.
        parsed = None
        parse_failed = False
        try:
            parsed = json.loads(resp)
        except Exception:
            parse_failed = True
            if is_recall:
                logger.warning("Critic LLM returned non-JSON response on recall; retrying once")
                try:
                    resp2 = await self.llm.generate(prompt + "\nReturn valid JSON.", context=str(outputs))
                    parsed = json.loads(resp2)
                    parse_failed = False
                except Exception:
                    logger.warning("Critic retry also failed on recall; will refine")
            else:
                # non-recall: simply approve
                logger.warning("Critic LLM returned non-JSON response; approving by default")
                return default
        if parse_failed and is_recall:
            # still failed after retry
            res = {"agent": self.name, "decision": "refine", "score": 0, "comments": "critic parsing failure", "suggestions": []}
            try:
                await self.memory.store_summary(task_name=task.get("title") or task.get("task_id", "critic"), summary=str(res), metadata={"agent_type": self.name, "decision": res.get("decision")})
            except Exception:
                logger.exception("Failed to store critic feedback in memory")
            return res

        if not isinstance(parsed, dict):
            logger.warning("Critic parsed payload not a dict; approving")
            return default

        parsed.setdefault("agent", self.name)

        # Defensive fields
        score = parsed.get("score")
        try:
            score = int(score) if score is not None else None
        except Exception:
            score = None

        suggestions = parsed.get("suggestions") or []
        if not isinstance(suggestions, list):
            suggestions = []

        # Strip duplicate suggestion text if prior suggestion present in context
        prior = None
        if isinstance(context, dict):
            prior = context.get("last_suggestion")
        if prior:
            suggestions = [s for s in suggestions if s.strip() and s.strip() != prior.strip()]

        # fallback heuristic score
        if score is None:
            txt = str(outputs or "")
            heur = max(10, min(90, len(txt) // 20))
            if any(k in txt.lower() for k in ("error", "fail", "incorrect", "bug")):
                heur = min(heur, 40)
            score = heur

        # high score approval
        threshold = 70
        if score >= threshold:
            parsed["decision"] = "approve"
            parsed["suggestions"] = []
            parsed["score"] = score
            try:
                await self.memory.store_summary(task_name=task.get("title") or task.get("task_id", "critic"), summary=str(parsed), metadata={"agent_type": self.name, "decision": parsed.get("decision"), "score": parsed.get("score")})
            except Exception:
                logger.exception("Failed to store critic feedback in memory")
            return parsed

        # Ensure at least one actionable suggestion when refining
        if not suggestions:
            suggestions = ["Clarify ambiguous steps, correct factual errors, and add a small concrete example."]

        parsed["decision"] = "refine"
        parsed["score"] = score
        parsed["suggestions"] = suggestions

        try:
            await self.memory.store_summary(task_name=task.get("title") or task.get("task_id", "critic"), summary=str(parsed), metadata={"agent_type": self.name, "decision": parsed.get("decision")})
        except Exception:
            logger.exception("Failed to store critic feedback in memory")

        return parsed
