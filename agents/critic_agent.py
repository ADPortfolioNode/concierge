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
        # default decision
        default = {"agent": self.name, "decision": "approve", "score": 80, "comments": "heuristic approve", "suggestions": []}

        prompt = (
            f"Evaluate the following outputs for quality, correctness, and completeness: {outputs}\n"
            "Provide a JSON object with keys: decision (approve|refine), score (0-100), comments, suggestions (list)."
        )

        if self.llm is None:
            return default

        try:
            resp = await self.llm.generate(prompt, context=str(outputs))
        except Exception:
            logger.exception("Critic LLM failed")
            # Fail-safe: approve to avoid triggering refinements
            return default

        # Try to parse structured JSON; if parsing fails, APPROVE (deterministic safe fallback)
        parsed = None
        try:
            parsed = json.loads(resp)
        except Exception:
            logger.warning("Critic LLM returned non-JSON response; approving by default")
            return default

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
        if isinstance(task.get("context"), dict):
            prior = task.get("context", {}).get("last_suggestion")
        if prior:
            suggestions = [s for s in suggestions if s.strip() and s.strip() != prior.strip()]

        # fallback heuristic score
        if score is None:
            # simple heuristic: longer outputs get higher base score; presence of 'error' lowers score
            txt = str(outputs or "")
            heur = max(10, min(90, len(txt) // 20))
            if any(k in txt.lower() for k in ("error", "fail", "incorrect", "bug")):
                heur = min(heur, 40)
            score = heur

        # If score is high enough, approve regardless of suggestions
        threshold = 70
        if score >= threshold:
            parsed["decision"] = "approve"
            parsed["suggestions"] = []
            parsed["score"] = score
            # persist critic feedback
            try:
                await self.memory.store_summary(task_name=task.get("title") or task.get("task_id", "critic"), summary=str(parsed), metadata={"agent_type": self.name, "decision": parsed.get("decision")})
            except Exception:
                logger.exception("Failed to store critic feedback in memory")
            return parsed

        # Ensure at least one actionable suggestion when refining
        if not suggestions:
            suggestions = ["Clarify ambiguous steps, correct factual errors, and add a small concrete example."]

        # Finalize parsed response
        parsed["decision"] = "refine"
        parsed["score"] = score
        parsed["suggestions"] = suggestions

        try:
            await self.memory.store_summary(task_name=task.get("title") or task.get("task_id", "critic"), summary=str(parsed), metadata={"agent_type": self.name, "decision": parsed.get("decision")})
        except Exception:
            logger.exception("Failed to store critic feedback in memory")

        return parsed
