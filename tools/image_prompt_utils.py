"""Resolve a human image subject from workflow task fields and agent prompts."""
from __future__ import annotations

import re

_IMAGE_INSTR_BOILERPLATE = (
    "submit the prompt",
    "image generation plugin",
    "return the result url",
    "return the result url.",
)

_PREPARE_TITLE_MARKERS = ("prepare image", "prepare prompt", "formulate prompt", "formulate image")
_PREPARE_INSTR_MARKERS = (
    "formulate a detailed",
    "formulate a descriptive",
    "formulate prompt",
    "write a detailed prompt",
    "craft a detailed prompt",
    "descriptive prompt for image",
)


def is_prepare_image_prompt_task(title: str, instructions: str) -> bool:
    """True when the step should author an image prompt (no plugin call)."""
    t = (title or "").lower()
    i = (instructions or "").lower()
    if any(k in t for k in _PREPARE_TITLE_MARKERS):
        return True
    if any(k in i for k in _PREPARE_INSTR_MARKERS):
        return True
    if "formulate" in i and "prompt" in i and "image" in i:
        return True
    return False


def is_image_generation_task(title: str, instructions: str) -> bool:
    """True when the step should call the image plugin (not prepare-only steps)."""
    if is_prepare_image_prompt_task(title, instructions):
        return False
    t = (title or "").lower()
    i = (instructions or "").lower()
    if any(k in t for k in ("generate image", "generate logo", "render image", "create logo")):
        return True
    if any(k in i for k in _IMAGE_INSTR_BOILERPLATE):
        return True
    return False


def _is_boilerplate(text: str) -> bool:
    low = (text or "").lower()
    return any(b in low for b in _IMAGE_INSTR_BOILERPLATE)


def _is_coding_meta_prompt(text: str) -> bool:
    low = (text or "").lower()
    return any(
        k in low
        for k in (
            "write concise, working code",
            "return only the code",
            "no markdown fences",
            "accomplish the following task",
        )
    )


def extract_goal_from_instructions(instructions: str) -> str:
    """Pull the user subject from 'Formulate ... prompt ...: {goal}' instructions."""
    instr = (instructions or "").strip()
    if not instr:
        return ""
    m = re.search(
        r"(?:prompt\s+for\s+image\s+generation|image\s+generation\s+prompt|logo\s+for|logo\s+of)\s*:\s*(.+)$",
        instr,
        re.I,
    )
    if m:
        return m.group(1).strip()
    if ":" in instr:
        tail = instr.rsplit(":", 1)[-1].strip()
        if tail and not _is_boilerplate(tail) and len(tail) > 3:
            return tail
    return instr


def build_prepare_image_prompt_request(*, goal: str, instructions: str = "") -> str:
    """LLM prompt that returns a single image-generation prompt string."""
    subject = (goal or "").strip() or extract_goal_from_instructions(instructions)
    if not subject:
        subject = instructions.strip() or "professional logo for Concierge"
    return (
        "You are an expert at writing prompts for text-to-image models.\n"
        f"Create one detailed, descriptive image-generation prompt for: {subject}\n"
        "Return ONLY the prompt text — no code, markdown fences, labels, or explanation."
    )


def extract_prepared_image_prompt(text: str) -> str | None:
    """Parse a stored prepare-step summary into the image prompt string."""
    if not text or not isinstance(text, str):
        return None
    if _is_coding_meta_prompt(text):
        return None
    for pat in (
        r"(?im)^(?:image\s+prompt|prompt)\s*:\s*(.+)$",
        r"(?im)^(?:prepared\s+prompt|formulated\s+prompt)\s*:\s*(.+)$",
    ):
        m = re.search(pat, text)
        if m:
            candidate = m.group(1).strip()
            if candidate and not _is_boilerplate(candidate):
                return candidate[:240]
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines:
        low = line.lower()
        if low.startswith(("image generated", "saved path", "image saved", "http", "/media/")):
            continue
        if _is_boilerplate(line) or _is_coding_meta_prompt(line):
            continue
        if len(line) > 24 and any(k in low for k in ("logo", "icon", "design", "minimal", "vector", "brand")):
            return line[:240]
    body = text.strip()
    if body and len(body) > 24 and not _is_coding_meta_prompt(body):
        first = body.splitlines()[0].strip()
        if first and not _is_boilerplate(first):
            return first[:240]
    return None


def resolve_image_prompt(
    *,
    title: str = "",
    instructions: str = "",
    goal: str | None = None,
    rag_context: str | None = None,
    agent_prompt: str | None = None,
) -> str:
    """Best-effort subject string for LM image generation."""
    if rag_context and rag_context.strip():
        prepared = extract_prepared_image_prompt(rag_context)
        if prepared:
            return prepared

    if goal and goal.strip() and not _is_boilerplate(goal):
        return goal.strip()[:240]

    if agent_prompt:
        prepared = extract_prepared_image_prompt(agent_prompt)
        if prepared:
            return prepared
        for pat in (
            r"(?:image of\s+|picture of\s+|logo for\s+|logo of\s+)(.+?)(?:\n|Provide|$)",
            r"generate(?:\s+an?)?\s+(?:image|logo)\s+(?:of|for)\s+(.+?)(?:\n|Provide|$)",
        ):
            m = re.search(pat, agent_prompt, re.I)
            if m:
                sub = m.group(1).strip()
                if sub and not _is_boilerplate(sub):
                    return sub[:240]

        goal_m = re.search(r"\bGoal:\s*(.+?)(?:\n|$)", agent_prompt, re.I)
        if goal_m:
            g = goal_m.group(1).strip()
            if g and not _is_boilerplate(g):
                return g[:240]

    instr = (instructions or "").strip()
    if instr and not _is_boilerplate(instr):
        return instr[:240]

    title_clean = (title or "").strip()
    generic_titles = ("generate image", "prepare image", "generate logo", "create logo", "render image")
    if title_clean and not any(x in title_clean.lower() for x in generic_titles):
        return title_clean[:240]

    if rag_context and rag_context.strip():
        chunks = [c.strip() for c in re.split(r"[|.\n]+", rag_context) if len(c.strip()) > 12]
        for chunk in chunks:
            if not _is_boilerplate(chunk) and any(
                k in chunk.lower() for k in ("logo", "image", "design", "concierge", "generate")
            ):
                return chunk[:240]

    return "professional logo design for Concierge"