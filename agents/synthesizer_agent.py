from __future__ import annotations

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SynthesizerAgent:
    def __init__(self, llm):
        self.llm = llm
        self.name = "SynthesizerAgent"

    async def run(self, goal: str, approved_outputs: Dict[str, str]) -> Dict[str, Any]:
        """
        Aggregate approved task outputs into a final structured result.

        approved_outputs: dict[task_id] -> output_text
        Returns: {"summary": str, "structured": dict, "confidence": float}
        """
        try:
            # Build synthesis prompt
            parts = [f"Goal: {goal}"]
            parts.append("\nApproved task outputs:\n")
            for tid, out in approved_outputs.items():
                parts.append(f"- Task {tid}: {out}\n")

            prompt = (
                "You are an assistant that synthesizes multiple task outputs into a single concise summary, \n"
                "a list of key points, identified risks, and actionable recommendations.\n"
                "Return a JSON object with keys: summary, key_points (list), risks (list), recommendations (list), "
                "refined_recommendation, delta_from_previous, and confidence (0-100)."
            )

            context = "\n".join(parts)
            text = None
            if self.llm is not None:
                try:
                    text = await self.llm.generate(prompt, context=context)
                except Exception:
                    logger.exception("Synthesizer LLM call failed; falling back to deterministic synthesis")
                    text = None

            import json

            def _validate(parsed: Any) -> bool:
                if not isinstance(parsed, dict):
                    return False
                req = [
                    "summary",
                    "key_points",
                    "risks",
                    "recommendations",
                    "refined_recommendation",
                    "delta_from_previous",
                    "confidence",
                ]
                for k in req:
                    if k not in parsed:
                        return False
                if not isinstance(parsed.get("key_points"), list):
                    return False
                if not isinstance(parsed.get("risks"), list):
                    return False
                if not isinstance(parsed.get("recommendations"), list):
                    return False
                if not isinstance(parsed.get("confidence"), (int, float)):
                    return False
                return True

            # helper to parse and validate JSON output
            def _try_parse(text_val: str) -> Optional[Dict[str, Any]]:
                try:
                    parsed = json.loads(text_val)
                    if _validate(parsed):
                        return parsed
                except Exception:
                    pass
                return None

            parsed = None
            if text:
                parsed = _try_parse(text)
            # if initial attempt failed, try one more time with explicit guidance
            if parsed is None and self.llm is not None and text is not None:
                try:
                    prompt2 = prompt + (
                        "\n\nPlease output ONLY a valid JSON object matching the schema exactly."
                    )
                    text2 = await self.llm.generate(prompt2, context=context)
                    parsed = _try_parse(text2) or parsed
                except Exception:
                    logger.warning("Synthesizer second attempt failed")

            if parsed:
                # convert and return
                summary = parsed.get("summary", "")
                structured = {
                    "key_points": parsed.get("key_points", []),
                    "risks": parsed.get("risks", []),
                    "recommendations": parsed.get("recommendations", []),
                    # preserve additional fields for downstream if needed
                    "refined_recommendation": parsed.get("refined_recommendation", ""),
                    "delta_from_previous": parsed.get("delta_from_previous", ""),
                }
                confidence = float(parsed.get("confidence", 0.0))
                return {"summary": summary, "structured": structured, "confidence": confidence}

            # Fallback deterministic synthesis if all LLM attempts fail
            # Keep URLs intact; skip auto_refine noise and LLM error entries
            parts = []
            for tid, out in approved_outputs.items():
                s = str(out).strip()
                if not s or s.startswith("[LLM-Error]") or str(tid).startswith("auto_refine"):
                    continue
                entry = s if s.startswith("http") else f"{tid}: {s}"
                parts.append(entry)
            concat = "\n".join(parts)
            summary = concat[:2000] if concat else ""
            # crude key points: first sentence of each output (up to 5)
            key_points = []
            for out in approved_outputs.values():
                s = str(out).strip()
                if not s:
                    continue
                first = s.split(".")
                if first:
                    kp = first[0].strip()
                    if kp and kp not in key_points:
                        key_points.append(kp)
                if len(key_points) >= 5:
                    break

            structured = {
                "key_points": key_points,
                "risks": [],
                "recommendations": [],
                "refined_recommendation": "",
                "delta_from_previous": "",
            }
            return {"summary": summary, "structured": structured, "confidence": 0.0}

        except Exception:
            logger.exception("Synthesizer encountered an unexpected error")
            return {"summary": "", "structured": {"key_points": [], "risks": [], "recommendations": [], "refined_recommendation": "", "delta_from_previous": ""}, "confidence": 0.0}
