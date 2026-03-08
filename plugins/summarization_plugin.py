"""Text summarisation plugin.

Uses an LLM when ``OPENAI_API_KEY`` is configured; otherwise applies an
extraction-based algorithm that ranks sentences by term frequency and
returns the top 3 most representative sentences.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import List

from plugins.base_plugin import BasePlugin


class SummarizationPlugin(BasePlugin):
    name = "summarization"
    description = "Condenses long text into a concise summary using extractive NLP."
    version = "0.2.0"

    async def run(self, input_data: str) -> str:
        text = str(input_data).strip()
        if not text:
            return ""

        # Try LLM-based summarization first
        try:
            import os
            if os.getenv("OPENAI_API_KEY"):
                from tools.llm_tool import LLMTool
                llm = LLMTool()
                prompt = (
                    "Summarize the following text concisely in 2-4 sentences, "
                    "preserving the key points:\n\n" + text[:4000]
                )
                result = await llm.generate(prompt)
                if result and not result.startswith("["):
                    return result.strip()
        except Exception:
            pass

        # Extractive fallback — sentence ranking via TF-IDF-like scoring
        return _extractive_summary(text, max_sentences=3)


# ---------------------------------------------------------------------------
# Extractive summarisation helpers
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "that", "this", "it", "its",
    "from", "as", "not", "no", "so", "if", "then", "than", "more", "also",
}


def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r"[a-zA-Z]+", text) if w.lower() not in _STOPWORDS and len(w) > 2]


def _extractive_summary(text: str, max_sentences: int = 3) -> str:
    # Split into sentences
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 20]
    if not sentences:
        return text[:300]
    if len(sentences) <= max_sentences:
        summary = " ".join(sentences)
        # if our extractive result is still very long (e.g. a single 300‑char
        # blob without punctuation), truncate to a sensible length with ellipsis
        if len(summary) > 200:
            return summary[:197] + "…"
        return summary

    # Term frequency across entire document
    all_words = _tokenize(text)
    tf = Counter(all_words)
    total = max(len(all_words), 1)

    # Score each sentence
    scores: List[float] = []
    for sent in sentences:
        words = _tokenize(sent)
        if not words:
            scores.append(0.0)
            continue
        score = sum(tf[w] / total for w in words) / math.sqrt(len(words))
        scores.append(score)

    # Pick top-N by score, preserve original order
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    selected = sorted(ranked[:max_sentences])
    return " ".join(sentences[i] for i in selected)
