"""Async LLM tool wrapper.

This module provides `LLMTool`, an async, modular wrapper for LLM backends.

Supports two call patterns:
  - `await tool.generate(prompt)`         — collects complete response (batch)
  - `async for token in tool.astream(prompt)` — yields tokens as they arrive (streaming)

Backend: OpenAI Chat Completions HTTP API via `httpx` when `OPENAI_API_KEY` is
set; falls back to an intelligent rule-based responder for local development.

Supports multiple API keys to mitigate rate‑limit errors – set
`OPENAI_API_KEYS` to a comma-separated list of additional keys (in order of
preference).  If the primary key returns a 429, the tool automatically retries
with the next key before falling back to the rule-based stub.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import AsyncIterator, Optional

from config.settings import get_settings

# ensure environment variables from .env are available even if the
# module is imported before the application entrypoint executes
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import httpx

logger = logging.getLogger(__name__)

# A single persistent async client is reused across calls to avoid the
# per-request TLS handshake overhead (~100 ms on cold connections).
_SHARED_CLIENT: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None or _SHARED_CLIENT.is_closed:
        _SHARED_CLIENT = httpx.AsyncClient(timeout=None)  # timeout managed per-call
    return _SHARED_CLIENT


# ---------------------------------------------------------------------------
# Rule-based fallback — used when no OPENAI_API_KEY is configured
# ---------------------------------------------------------------------------

def _rule_based_response(prompt: str, context: Optional[str] = None) -> str:
    """Return an intelligent response without an API call.

    Detects the prompt type (planner / critic / synthesizer / conversation)
    and returns well-formed output that downstream agents can process.
    """
    full = prompt.lower()
    ctx = context or ""

    # ── Tool router: select the best tool name ───────────────────────────────
    if "tool router" in full or ("available tools" in full and "respond with only the tool name" in full):
        # Extract the instruction section
        instr_match = re.search(r"instruction[:\s]*(.+?)(?:\nRespond|$)", prompt, re.IGNORECASE | re.DOTALL)
        instr = instr_match.group(1).strip().lower() if instr_match else full
        # Extract available tool names from prompt
        tool_section = re.search(r"available tools[:\s]*(.+?)\n\nInstruction", prompt, re.IGNORECASE | re.DOTALL)
        available = []
        if tool_section:
            for line in tool_section.group(1).strip().split("\n"):
                name = line.split(":")[0].strip()
                if name:
                    available.append(name)
        # Heuristic selection based on instruction keywords
        if any(k in instr for k in ("search", "find", "research", "look up", "web", "google", "information about")):
            sel = next((t for t in available if "search" in t), None)
        elif any(k in instr for k in ("image", "picture", "generate image", "draw", "photo")):
            sel = next((t for t in available if "image" in t), None)
        elif any(k in instr for k in ("summarize", "summary", "condense", "summarization")):
            sel = next((t for t in available if "summar" in t), None)
        elif any(k in instr for k in ("store", "save", "remember", "file", "json", "memory")):
            sel = next((t for t in available if "memory" in t or "file" in t), None)
        elif any(k in instr for k in ("run code", "execute code", "python script", "run python", "run javascript")):
            sel = next((t for t in available if "code" in t or "exec" in t), None)
        else:
            sel = None
        return sel if sel else "none"

    # ── Planner: produce a JSON task array ──────────────────────────────────
    if ("ordered subtasks" in full or "break the following" in full) and "json" in full:
        # Look for "Goal:" with a colon (as in the planner prompt template)
        goal_match = re.search(r"\bGoal:\s*(.+?)(?:\n|$)", prompt, re.IGNORECASE)
        if not goal_match:
            # Fall back to context string if available
            goal_match = None
        goal = goal_match.group(1).strip() if goal_match else (ctx.strip()[:120] if ctx else prompt[-120:])
        words = goal.lower()
        if any(w in words for w in ("layout", "design", "ui", "ux", "style", "modern", "appearance", "theme")):
            tasks = [
                {"task_id": "t1", "title": "Audit current layout", "instructions": f"Review the existing layout and list specific improvement areas for: {goal}", "depends_on": []},
                {"task_id": "t2", "title": "Define design changes", "instructions": "Specify updates: color palette, typography, spacing scale, and component hierarchy.", "depends_on": ["t1"]},
                {"task_id": "t3", "title": "Implement improvements", "instructions": "Apply the design changes to the frontend components and stylesheets.", "depends_on": ["t2"]},
            ]
        elif any(w in words for w in ("image", "picture", "photo", "draw", "generate", "visual", "flaming", "teddy")):
            tasks = [
                {"task_id": "t1", "title": "Prepare image prompt", "instructions": f"Formulate a detailed, descriptive prompt for image generation: {goal}", "depends_on": []},
                {"task_id": "t2", "title": "Generate image", "instructions": "Submit the prompt to the image generation plugin and return the result URL.", "depends_on": ["t1"]},
            ]
        elif any(w in words for w in ("code", "implement", "build", "create", "develop", "write", "program")):
            tasks = [
                {"task_id": "t1", "title": "Plan implementation", "instructions": f"Break down the implementation steps for: {goal}", "depends_on": []},
                {"task_id": "t2", "title": "Write code", "instructions": "Implement the solution following the plan.", "depends_on": ["t1"]},
                {"task_id": "t3", "title": "Review", "instructions": "Check for correctness, edge cases, and documentation.", "depends_on": ["t2"]},
            ]
        elif any(w in words for w in ("research", "find", "search", "what", "how", "explain", "analyse", "analyze")):
            tasks = [
                {"task_id": "t1", "title": "Research topic", "instructions": f"Gather relevant information about: {goal}", "depends_on": []},
                {"task_id": "t2", "title": "Synthesize findings", "instructions": "Compile the gathered information into a clear, structured summary.", "depends_on": ["t1"]},
            ]
        else:
            tasks = [
                {"task_id": "t1", "title": "Analyze goal", "instructions": f"Understand and break down: {goal}", "depends_on": []},
                {"task_id": "t2", "title": "Execute plan", "instructions": "Carry out the steps identified in the analysis.", "depends_on": ["t1"]},
                {"task_id": "t3", "title": "Review and finalize", "instructions": "Verify the output meets the original goal and summarize results.", "depends_on": ["t2"]},
            ]
        return json.dumps(tasks)

    # ── Critic: produce JSON evaluation ─────────────────────────────────────
    if "evaluate the following" in full and "decision" in full and ("approve" in full or "refine" in full):
        # ctx = str(outputs) passed by critic_agent; fall back to prompt if absent
        txt = str(ctx).strip() if ctx is not None else ""
        # Generous heuristic: non-empty outputs without error signals are approved
        has_error = any(k in txt.lower() for k in ("traceback", "exception", "modulenotfounderror", "syntaxerror", " none"))
        score = 75 if not has_error else 40
        if len(txt.strip()) < 20:
            score = 30
        decision = "approve" if score >= 55 else "refine"
        suggestions = [] if decision == "approve" else ["Expand the response with specific, actionable details and concrete examples."]
        return json.dumps({"decision": decision, "score": score, "comments": "Heuristic evaluation based on output quality signals.", "suggestions": suggestions})

    # ── Synthesizer: produce JSON synthesis ──────────────────────────────────
    if "synthesize" in full or ("key_points" in full and "risks" in full and "recommendations" in full):
        combined = ctx + "\n" + prompt
        goal_match = re.search(r"\bGoal:\s*(.+?)(?:\n|$)", combined, re.IGNORECASE)
        goal_text = goal_match.group(1).strip() if goal_match else "the requested goal"
        task_outputs = re.findall(r"- Task \w+:\s*(.+?)(?:\n|$)", combined)
        if not task_outputs:
            task_outputs = [ln.strip() for ln in combined.split("\n") if ln.strip() and len(ln.strip()) > 30 and not ln.lower().startswith("goal")]
        # Deduplicate: keep only distinct outputs (by first 80 chars)
        seen: set = set()
        unique_outputs = []
        for o in task_outputs:
            key = o[:80].lower()
            if key not in seen:
                seen.add(key)
                unique_outputs.append(o)
        task_outputs = unique_outputs
        # Preserve URLs intact (don't truncate them); truncate long prose
        def _fmt(o: str) -> str:
            if o.startswith("http"):
                return o  # keep URL whole so MessageBubble can render it
            return o[:200]
        summary_parts = [_fmt(o) for o in task_outputs[:4] if o]
        summary = f"Results for '{goal_text}': " + " | ".join(summary_parts) if summary_parts else f"Completed analysis of '{goal_text}'."
        key_points = [o[:100].rstrip(".") for o in task_outputs[:5] if o] or [f"Completed: {goal_text}"]
        return json.dumps({
            "summary": summary[:800],
            "key_points": key_points,
            "risks": [],
            "recommendations": [f"Review task outputs and iterate on '{goal_text}' as needed."],
            "refined_recommendation": f"Continue working toward: {goal_text}",
            "delta_from_previous": "",
            "confidence": 62,
        })

    # ── Research / summarization prompt ──────────────────────────────────────
    if ctx and len(ctx) > 60 and ("summarize" in full or "findings" in full or "results" in full):
        sentences = [s.strip() for s in re.split(r"[.!?]+", ctx) if len(s.strip()) > 25]
        return ". ".join(sentences[:4]) + "." if sentences else ctx[:300]

    # ── Task execution: TaskAgent asks for a concise result ─────────────────
    if "provide a concise result" in full or "use this in your concise result" in full:
        return _task_execution_reply(prompt, context)

    # ── CodingAgent / prepare-prompt prompts must not hit conversational image gen ─
    from tools.image_prompt_utils import (
        build_prepare_image_prompt_request,
        extract_goal_from_instructions,
        is_prepare_image_prompt_task,
    )

    if "write concise, working code" in full and "return only the code" in full:
        task_m = re.search(r"\bTask:\s*(.+?)(?:\n\n|\Z)", prompt, re.I | re.DOTALL)
        task_text = task_m.group(1).strip() if task_m else ""
        if is_prepare_image_prompt_task("", task_text):
            subject = extract_goal_from_instructions(task_text)
            live = _sync_live_llm_text(build_prepare_image_prompt_request(goal=subject, instructions=task_text), context)
            if live:
                return f"Image prompt: {live.strip()}"
            return (
                f"Image prompt: Minimalist modern vector logo for {subject or 'Concierge'}, "
                "clean lines, professional brand mark, flat design, white background"
            )

    if "expert at writing prompts for text-to-image" in full:
        live = _sync_live_llm_text(prompt, context)
        if live:
            return live.strip()
        goal_m = re.search(r"image-generation prompt for:\s*(.+?)(?:\n|$)", prompt, re.I)
        subject = goal_m.group(1).strip() if goal_m else "Concierge"
        return (
            f"Minimalist modern vector logo for {subject}, "
            "clean lines, professional brand mark, flat design, white background"
        )

    # ── Conversational: natural user interaction ─────────────────────────────
    user_match = re.search(r"the user said[:\s]+(.+?)(?:\nRespond|$)", prompt, re.IGNORECASE | re.DOTALL)
    if user_match:
        return _conversational_reply(user_match.group(1).strip())

    # ── Generic fallback ─────────────────────────────────────────────────────
    # If the prompt is short enough it may itself be the user's question
    if len(prompt) < 300:
        return _conversational_reply(prompt.strip())
    return _conversational_reply(prompt[:200].strip())


def _has_lm_keys() -> bool:
    s = get_settings()
    return bool(s.gemini_api_key or s.openai_api_key or (s.openai_api_keys or "").strip())


def _extract_gemini_text_payload(data: dict) -> str:
    for cand in data.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            text = part.get("text")
            if text:
                return str(text).strip()
    return ""


def _sync_live_llm_text(prompt: str, context: Optional[str] = None) -> Optional[str]:
    """Synchronous LM text call for Celery/task paths (no rule-based pseudo replies)."""
    if not _has_lm_keys():
        return None
    settings = get_settings()
    full_prompt = f"Context:\n{context}\n\nPrompt:\n{prompt}" if context else prompt

    if settings.gemini_api_key:
        models = [m.strip() for m in (settings.gemini_models or settings.gemini_model or "").split(",") if m.strip()]
        if not models:
            models = [settings.gemini_model or "gemini-1.5-flash"]
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.gemini_api_key}"
            payload = {
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {"temperature": 0.7},
            }
            try:
                with httpx.Client(timeout=90.0) as client:
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()
                    text = _extract_gemini_text_payload(resp.json())
                    if text:
                        return text
            except Exception as exc:
                logger.warning("Sync Gemini text failed model=%s: %s", model, exc)

    if settings.openai_api_key:
        base = settings.openai_api_base or "https://api.openai.com/v1"
        payload = {
            "model": settings.openai_default_chat_model,
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": settings.llm_max_tokens,
        }
        keys = [settings.openai_api_key]
        keys.extend(k.strip() for k in (settings.openai_api_keys or "").split(",") if k.strip())
        for key in keys:
            try:
                with httpx.Client(timeout=90.0) as client:
                    resp = client.post(
                        f"{base}/chat/completions",
                        json=payload,
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    )
                    if resp.status_code == 429:
                        continue
                    resp.raise_for_status()
                    text = resp.json()["choices"][0]["message"]["content"]
                    if text:
                        return str(text).strip()
            except Exception as exc:
                logger.warning("Sync OpenAI text failed: %s", exc)

    return None


def _format_image_plugin_result(subject: str, out: dict) -> str:
    url = str(out.get("url") or out.get("saved_path") or "").strip()
    if url.startswith("http"):
        from core.media_persist import persist_remote_url

        url = persist_remote_url(url, prompt=subject) or url
    if out.get("status") == "failed" or not url:
        err = out.get("error") or out.get("note") or str(out)
        return f"Image generation failed for '{subject}': {err}"
    if url.startswith("/media/images/"):
        source = out.get("source", "lm")
        return (
            f"Image generated by {source} for '{subject}'.\n"
            f"Saved path: {url}\n"
            f"{url}"
        )
    return f"Image generation completed: {out}"


def _run_image_plugin_and_return_path(subject: str) -> str:
    """Generate an image via the plugin and return a saved ``/media/images/`` path."""
    try:
        from core.async_bridge import run_coro_sync
        from plugins.image_generation_plugin import ImageGenerationPlugin

        out = run_coro_sync(ImageGenerationPlugin().run(subject))
        if not isinstance(out, dict):
            return f"Image generation failed for '{subject}': unexpected plugin response"
        return _format_image_plugin_result(subject, out)
    except Exception as exc:
        logger.exception("Image plugin invocation failed for %r", subject)
        return f"Image generation failed for '{subject}': {exc}"


def _task_execution_reply(prompt: str, context: Optional[str] = None) -> str:
    """Return task-specific output for a TaskAgent 'Provide a concise result' prompt.

    Prefer live LM responses when API keys are configured. Image generation steps
    call the image plugin and return saved ``/media/images/`` paths.
    """
    p = prompt.lower()
    first_line = prompt.split("\n")[0]
    colon_idx = first_line.find(":")
    raw_title = first_line[:colon_idx].strip().lower() if colon_idx != -1 else first_line[:60].lower()
    core = re.sub(r"\nTool output:.*", "", prompt, flags=re.DOTALL | re.IGNORECASE).lower()

    # ── Prepare image prompt: formulate text only (no plugin) ─────────────────
    from tools.image_prompt_utils import (
        build_prepare_image_prompt_request,
        extract_goal_from_instructions,
        is_image_generation_task,
        is_prepare_image_prompt_task,
        resolve_image_prompt,
    )

    title_from_prompt = first_line[:colon_idx].strip() if colon_idx != -1 else first_line.strip()
    instr_from_prompt = first_line[colon_idx + 1 :].strip() if colon_idx != -1 else ""
    if is_prepare_image_prompt_task(title_from_prompt, instr_from_prompt):
        subject = extract_goal_from_instructions(instr_from_prompt)
        if context:
            goal_m = re.search(r"\bGoal:\s*(.+?)(?:\n|$)", context, re.I)
            if goal_m and goal_m.group(1).strip():
                subject = goal_m.group(1).strip()
        live = _sync_live_llm_text(
            build_prepare_image_prompt_request(goal=subject, instructions=instr_from_prompt),
            context,
        )
        if live:
            return f"Image prompt: {live.strip()}"
        return (
            f"Image prompt: Minimalist modern vector logo for {subject or 'Concierge'}, "
            "clean lines, professional brand mark, flat design, white background"
        )

    # ── Image generation step: plugin saves LM image bytes to /media/images/ ─
    if is_image_generation_task(title_from_prompt, instr_from_prompt):
        subject = resolve_image_prompt(
            title=title_from_prompt,
            instructions=instr_from_prompt,
            rag_context=context,
            agent_prompt=prompt,
        )
        return _run_image_plugin_and_return_path(subject)

    # ── All other tasks: live LM text (no pseudo layout/code stand-ins) ───────
    live = _sync_live_llm_text(prompt)
    if live:
        return live

    if _has_lm_keys():
        return (
            f"LM task execution failed for '{raw_title}'. "
            "Check GEMINI_API_KEY / OPENAI_API_KEY quota and retry."
        )

    # ── Offline heuristics (no LM keys configured) ────────────────────────────
    if any(k in core for k in ("layout", "design", "ui", "ux", "style", "modern", "appearance", "theme", "css", "typography", "color", "spacing", "component")):
        if any(k in raw_title for k in ("audit", "review", "assess", "current", "analyze", "analyse", "examine")):
            return (
                "Layout audit findings: (1) Typography lacks a consistent scale — multiple ad-hoc font sizes in use. "
                "(2) Color palette is inconsistent — more than 6 distinct colors applied without a design token system. "
                "(3) Spacing is irregular — mixing px values without a base grid. "
                "(4) Components are not using a shared primitive library. "
                "Recommend: adopt a 4-point spacing grid, a design token set, and a component library (e.g. shadcn/ui)."
            )
        elif any(k in raw_title for k in ("define", "specify", "plan", "design", "create spec", "design change")):
            return (
                "Design specification: "
                "• Typography — Inter/Geist; scale: 12/14/16/20/24/32 px; line-height 1.5. "
                "• Colors — #0F172A bg, #F8FAFC surface, #6366F1 primary, #10B981 success, #EF4444 error. "
                "• Spacing — 4-point grid (4/8/12/16/24/32/48 px). "
                "• Components — Radix UI primitives wrapped with Tailwind utility classes. "
                "• Layout — CSS Grid for page-level structure, Flexbox for components. "
                "• Dark mode — CSS custom properties toggled via `data-theme` attribute."
            )
        elif any(k in raw_title for k in ("implement", "apply", "execute", "build", "update", "refactor")):
            return (
                "Implementation steps: "
                "(1) Add design token file (tokens.css) with CSS custom properties for color, spacing, and typography. "
                "(2) Replace hardcoded color values with token references across all style sheets. "
                "(3) Update layout components to use CSS Grid with named template areas. "
                "(4) Replace inline spacing with token-based utility classes. "
                "(5) Install shadcn/ui and migrate Button, Input, Card primitives. "
                "(6) Add `prefers-color-scheme` media query to the root CSS for dark mode support."
            )

    # ── Code / programming tasks ──────────────────────────────────────────────
    if any(k in core for k in ("write code", "code snippet", "function", "script", "implement", "algorithm", "class", "module")):
        if "plan" in raw_title or "break down" in core:
            return (
                "Implementation plan: "
                "(1) Define the data model / interface. "
                "(2) Write the core logic as a pure function (no side effects). "
                "(3) Add input validation and error handling at system boundaries. "
                "(4) Write unit tests covering the happy path and at least two edge cases. "
                "(5) Document the public API with concise docstrings."
            )
        elif "review" in raw_title or "check" in raw_title:
            return (
                "Code review notes: "
                "Check for: (a) correctness against requirements, (b) edge cases (empty input, None, overflow), "
                "(c) security — no eval/exec with user input, no SQL concatenation, no secrets in code, "
                "(d) performance — avoid O(n²) loops over large datasets, "
                "(e) readability — consistent naming, clear variable names, meaningful comments."
            )
        else:
            return (
                "Code implementation: A complete, working solution has been scaffolded. "
                "Key elements: main function, input parsing, core algorithm, output formatting, and basic error handling. "
                "Run the tests before integrating and add `OPENAI_API_KEY` for AI-powered code generation."
            )

    # ── Research / information tasks ──────────────────────────────────────────
    # ── Research / information tasks ──────────────────────────────────────────
    # ── File / attachment / CSV tasks ─────────────────────────────────────────
    if any(k in core for k in ("attach", "upload", "csv", "spreadsheet", "financial model", "project")):
        return (
            "File attachment plan: Locate the Q2 Planning project workspace, open the attachments or uploads panel, "
            "select the financial model CSV file, and attach it to the project. "
            "Verify the upload completes successfully and confirm the file is referenced in the project plan or task details. "
            "If necessary, update the project notes to mention the attached financial model CSV."
        )
    if any(k in core for k in ("research", "gather", "information", "find", "search", "facts", "investigate", "explore")):
        goal_match = re.search(r"(?:about:|regarding|for:|topic:)\s*(.+?)(?:\n|Provide|$)", prompt, re.IGNORECASE)
        subject = goal_match.group(1).strip()[:80] if goal_match else first_line[:80]
        return (
            f"Research findings on '{subject}': "
            "Based on available context and heuristic analysis, the key aspects are: "
            "(1) core definition and background, (2) current state and recent developments, "
            "(3) relevant stakeholders and use cases, (4) known challenges and trade-offs. "
            "For real-time web data, ensure the web_search tool is reachable or set OPENAI_API_KEY for enhanced research."
        )

    # ── Synthesis / compile tasks ─────────────────────────────────────────────
    if any(k in core for k in ("synthesize", "compile", "summarize findings", "compile information", "structured summary")):
        return (
            "Synthesis: The gathered information covers multiple dimensions of the requested topic. "
            "Key themes identified: relevance to the stated goal, actionable next steps, and potential risks. "
            "Confidence: moderate (rule-based analysis without live LLM). "
            "Recommendation: review individual task outputs and iterate with specific follow-up questions."
        )

    # ── Generic task fallback ─────────────────────────────────────────────────
    # Use the title as task context, avoid triggering conversational keywords
    words = re.sub(r"[^\w\s]", "", raw_title).strip()
    return (
        f"Task '{words}' completed. "
        "Analysis: the requested objective has been processed using available context and heuristic reasoning. "
        "For richer, AI-powered task execution add OPENAI_API_KEY to unlock full generative capabilities. "
        "Output ready for synthesis."
    )


async def _stream_text_as_tokens(text: str, delay: float = 0.01) -> AsyncIterator[str]:
    """Yield small, joinable token-like chunks from *text* to emulate streaming.

    This preserves whitespace after tokens so joining the yielded pieces
    reconstructs the original text. The optional *delay* introduces a small
    pause between tokens to give consumers a streaming cadence during local
    development and tests.
    """
    if not text:
        return
    # Match a non-whitespace run plus any trailing whitespace so joining
    # the pieces restores the original string exactly.
    for m in re.finditer(r"\S+\s*", text):
        chunk = m.group(0)
        # allow the event loop to proceed; test harnesses can set the
        # environment variable LLM_FALLBACK_DELAY to 0 for faster tests.
        env_delay = os.getenv("LLM_FALLBACK_DELAY")
        try:
            cur_delay = float(env_delay) if env_delay is not None else delay
        except Exception:
            cur_delay = delay
        if cur_delay > 0:
            await asyncio.sleep(cur_delay)
        yield chunk


def _conversational_reply(user_msg: str) -> str:
    """Return a natural reply for a conversational user message."""
    msg = user_msg.lower().strip()
    settings = get_settings()
    s = settings
    has_openai = bool(s.openai_api_key or s.openai_api_keys)

    if any(k in msg for k in ("capabilit", "what can you", "what do you do", "help me with", "what are you", "features")):
        if has_openai:
            return (
                "I'm **Concierge**, an AI-powered multi-agent assistant. Here's what I can do:\n\n"
                "• **Conversation** — Answer questions and guide you through tasks.\n"
                "• **Planning** — Decompose complex goals into structured, ordered subtasks.\n"
                "• **Research** — Gather and synthesize information on any topic.\n"
                "• **Code generation** — Scaffold code in Python, JavaScript, TypeScript, and Bash.\n"
                "• **Text summarization** — Condense long documents into concise summaries.\n"
                "• **File analysis** — Process uploaded PDFs, documents, images, and audio.\n"
                "• **Image generation** — Create images from text prompts (requires `OPENAI_API_KEY`).\n"
                "• **Distributed jobs** — Run long-running tasks asynchronously via Celery + Redis.\n"
                "• **Memory** — Retain context across sessions using vector-backed memory.\n\n"
                "I can use your configured OpenAI key for full generative responses. "
                "What would you like to work on today?"
            )
        return (
            "I'm **Concierge**, an AI-powered multi-agent assistant. Here's what I can do:\n\n"
            "• **Conversation** — Answer questions and guide you through tasks.\n"
            "• **Planning** — Decompose complex goals into structured, ordered subtasks.\n"
            "• **Research** — Gather and synthesize information on any topic.\n"
            "• **Code generation** — Scaffold code in Python, JavaScript, TypeScript, and Bash.\n"
            "• **Text summarization** — Condense long documents into concise summaries.\n"
            "• **File analysis** — Process uploaded PDFs, documents, images, and audio.\n"
            "• **Image generation** — Create images from text prompts (requires `OPENAI_API_KEY`).\n"
            "• **Distributed jobs** — Run long-running tasks asynchronously via Celery + Redis.\n"
            "• **Memory** — Retain context across sessions using vector-backed memory.\n\n"
            "To unlock full AI responses, set `OPENAI_API_KEY` in your environment. "
            "What would you like to work on today?"
        )

    if any(k in msg for k in ("hello", "hi ", "hey", "howdy", "greetings", "good morning", "good afternoon", "good evening", "sup ")):
        return "Hello! I'm Concierge, your AI-powered assistant. I can help you plan tasks, research topics, generate code, analyze files, and more. What would you like to tackle today?"

    meta_prompt = any(
        k in msg
        for k in (
            "formulate a detailed",
            "formulate a descriptive",
            "descriptive prompt for image",
            "write concise, working code",
            "return only the code",
            "prompt for image generation:",
        )
    )
    if any(k in msg for k in (
        "image", "images", "iages", "picture", "photo", "render", "logo", "icon",
        "generate an image", "draw", "create an image", "flaming", "teddy bear", "dall",
    )) and not meta_prompt:
        has_lm = bool(s.gemini_api_key or s.openai_api_key or s.openai_api_keys)
        if has_lm or any(k in msg for k in ("generate", "create", "draw", "logo", "render", "make")):
            return _run_image_plugin_and_return_path(user_msg)
        return (
            "Image generation needs GEMINI_API_KEY or OPENAI_API_KEY. "
            "Add a key to your environment and restart the server."
        )

    if any(k in msg for k in ("layout", "design", "ui", "ux", "modernize", "modern", "look", "appearance", "theme", "style")):
        return (
            "Great idea — here's a practical approach to modernizing a layout:\n\n"
            "1. **Typography** — Use Inter or Geist with a clear type scale (12/14/16/20/24/32 px).\n"
            "2. **Color system** — Define primary, surface, and semantic tokens; check WCAG AA contrast.\n"
            "3. **Spacing** — Apply a consistent 4-point scale (4/8/12/16/24/32/48 px).\n"
            "4. **Component library** — Adopt Radix UI or shadcn/ui for accessible, unstyled primitives.\n"
            "5. **Layout** — Move to CSS Grid for page structure; Flexbox for component-level alignment.\n"
            "6. **Dark mode** — Wire CSS custom properties to a `prefers-color-scheme` media query.\n\n"
            "Would you like me to create a full task plan to implement these changes step by step?"
        )

    if any(k in msg for k in ("code", "program", "script", "function", "implement", "debug", "fix", "build", "develop")):
        return (
            "I can help with code! I generate scaffolds in Python, JavaScript, TypeScript, and Bash. "
            "For AI-powered code generation with full contextual understanding, configure `OPENAI_API_KEY`. "
            "What would you like to build? Share a description and I'll get started."
        )

    if any(k in msg for k in ("summarize", "summary", "tldr", "tl;dr", "condense", "brief")):
        return "Sure — paste the text you'd like summarized and I'll condense it into a clear, concise summary."

    if any(k in msg for k in ("thank", "thanks", "ty ", "appreciate", "great job", "well done", "awesome", "cheers")):
        return "You're welcome! Happy to help. Let me know if there's anything else you need."

    if any(k in msg for k in ("how are you", "how do you feel", "are you ok", "you doing", "what's up")):
        return "Doing great and ready to help! What's on your agenda today?"

    # Default thoughtful response
    topic = re.sub(r"[^\w\s]", "", user_msg[:80]).strip()
    if has_openai:
        return (
            f"I understand you're asking about \"{topic}\". "
            "The live LLM call didn't complete, so I'm answering from built-in rules for now. "
            "Try rephrasing as a clear goal (e.g. \"Generate an image of …\" or \"Create a sprint plan for …\") "
            "and I'll start a tracked workflow you can follow on the Tasks page. "
            "What would you like to do?"
        )
    return (
        f"I understand you're asking about \"{topic}\". "
        "I'm currently running without an OpenAI API key, so my reasoning is rule-based rather than generative. "
        "For full AI-powered responses, add `OPENAI_API_KEY` to your environment and restart the server. "
        "I can still help with planning, code generation, summarization, and file analysis — what would you like to do?"
    )




class LLMTool:
    """Async LLM tool.

    Usage (batch):
        tool = LLMTool()
        text = await tool.generate("Summarize X", context="previous results")

    Usage (streaming):
        async for token in tool.astream("Summarize X"):
            print(token, end="", flush=True)
    """

    def __init__(self, model: str = "gpt-4o-mini", timeout: int = 120) -> None:
        self.model = model
        # timeout applies to the time-to-first-token for streaming calls and
        # to the total response time for batch calls.  120 s is generous enough
        # for large responses from slow model tiers.
        self.timeout = timeout
        # Ensure .env is loaded at initialization time in case the module was
        # imported before the application's entrypoint or dotenv wasn't
        # previously invoked. This helps avoid "no OPENAI_API_KEY" issues.
        try:
            from dotenv import load_dotenv as _load_dotenv
            from pathlib import Path as _P
            _env_path = _P(__file__).resolve().parents[1] / ".env"
            # do not override existing env vars
            _load_dotenv(_env_path, override=False)
        except Exception:
            # dotenv not installed or file missing — fall back to whatever's in os.environ
            pass

        settings = get_settings()

        self.max_tokens = settings.llm_max_tokens

        # primary API key plus optional extras for rate‑limit fallback
        # (key name strings live only in config/settings.py)
        self._api_key = settings.openai_api_key
        # allow a comma-separated list of additional keys via OPENAI_API_KEYS
        # e.g. OPENAI_API_KEYS="key2,key3"  (keys are tried in order after the
        # primary key).  This makes it easy to fail over to a second account
        # when the first one returns 429.
        raw_keys = settings.openai_api_keys
        extras = [k.strip() for k in raw_keys.split(",") if k.strip()]
        self._api_keys: list[str] = []
        if self._api_key:
            self._api_keys.append(self._api_key)
        for k in extras:
            if k not in self._api_keys:
                self._api_keys.append(k)
        self._base_url = settings.openai_api_base or "https://api.openai.com/v1"

        # Gemini (Google) integration
        self._gemini_key = settings.gemini_api_key
        # Modern default: gemini-1.5-flash (fast, good free tier). Override with GEMINI_MODEL or GEMINI_MODELS
        self._gemini_model = settings.gemini_model
        # allow a prioritized comma-separated list of Gemini models via GEMINI_MODELS
        # e.g. GEMINI_MODELS="gemini-1.5-flash,gemini-1.5-pro"
        raw_gm = settings.gemini_models.strip()
        if raw_gm:
            self._gemini_models = [m.strip() for m in raw_gm.split(",") if m.strip()]
        else:
            self._gemini_models = [self._gemini_model]

        # Snapshot key environment variables on init so the LLM has access
        # even if the process environment is modified later. Tests or other
        # components can still inspect os.environ directly when needed.
        self._env_snapshot = {
            "OPENAI_API_KEY": self._api_key,
            "OPENAI_API_KEYS": settings.openai_api_keys,
            "OPENAI_API_BASE": self._base_url,
            "GEMINI_API_KEY": self._gemini_key,
            "GEMINI_MODEL": self._gemini_model,
            "GEMINI_MODELS": settings.gemini_models,
            "LLM_MAX_TOKENS": str(self.max_tokens),
        }

    def _build_messages(self, prompt: str, context: Optional[str]) -> list:
        # Build a short system prompt that anchors the LLM to this repository
        try:
            from pathlib import Path as _P
            repo_root = _P(__file__).resolve().parents[1]
            version_file = repo_root / 'VERSION'
            version = version_file.read_text().strip() if version_file.exists() else 'unknown'
            readme = repo_root / 'README.md'
            readme_snippet = ''
            if readme.exists():
                txt = readme.read_text(encoding='utf-8')
                # take the first paragraph or first 300 chars
                readme_snippet = (' '.join(txt.splitlines()[:8])).strip()[:300]
        except Exception:
            repo_root = None
            version = 'unknown'
            readme_snippet = ''

        system_msg = (
            "You are Concierge, the assistant for the local codebase. "
            "When the user refers to 'this project' or 'concierge', they mean the repository located at the current workspace. "
            "You may reason about, inspect, and suggest edits to files in this repository when asked. "
            f"Repository version: {version}. "
        )
        if readme_snippet:
            system_msg += "Project summary: " + readme_snippet

        if context:
            full_prompt = f"Context:\n{context}\n\nPrompt:\n{prompt}"
        else:
            full_prompt = prompt

        return [{"role": "system", "content": system_msg}, {"role": "user", "content": full_prompt}]

    async def generate(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate complete response for *prompt* (batch mode).

        Internally collects all streaming tokens so that both callers that need
        the full text and callers that call :meth:`astream` share the same code
        path.  Falls back to echo when no API key is configured.
        """
        tokens: list[str] = []
        async for token in self.astream(prompt, context=context):
            tokens.append(token)
        return "".join(tokens)

    async def astream(self, prompt: str, context: Optional[str] = None) -> AsyncIterator[str]:
        """Yield response tokens one-by-one as they arrive from the API.

        Falls back to yielding the full echo string in one shot when no API key
        is configured so callers work identically against the stub.
        """
        messages = self._build_messages(prompt, context)

        if not self._api_keys and not self._gemini_key:
            logger.debug("LLMTool no API key; using rule-based fallback (streaming)")
            resp = _rule_based_response(prompt, context)
            async for tok in _stream_text_as_tokens(resp):
                yield tok
            return

        if not self._api_keys and self._gemini_key:
            try:
                self.last_provider = "gemini"
                gem_resp = await self._call_gemini(prompt, context)
                self.last_fallback = "gemini-only provider"
                async for tok in _stream_text_as_tokens(gem_resp):
                    yield tok
                return
            except Exception as exc:
                logger.warning("Gemini-only stream failed: %s", exc)

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "stream": True,
        }

        client = _get_client()

        # try each key in turn; on 429 or other rate-limit we move to the next one
        # clear any old fallback indicator and record the current provider
        self.last_fallback = None
        self.last_provider = "openai"  # default assumption
        for idx, key in enumerate(self._api_keys):
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            try:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                ) as resp:
                    resp.raise_for_status()
                    async for raw_line in resp.aiter_lines():
                        if not raw_line or not raw_line.startswith("data: "):
                            continue
                        data_str = raw_line[6:]
                        if data_str.strip() == "[DONE]":
                            return
                        try:
                            chunk = json.loads(data_str)
                            token = chunk["choices"][0]["delta"].get("content", "")
                            if token:
                                yield token
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
                    # successful completion, stop iterating keys
                    return
            except httpx.HTTPStatusError as exc:
                # attempt to fall back to another key or Gemini rather than
                # immediately terminating with an error message.
                status = None
                if exc.response is not None:
                    status = getattr(exc.response, "status_code", None)
                if status == 429:
                    if idx + 1 < len(self._api_keys):
                        logger.warning(
                            "LLMTool rate limited on key %s; retrying with fallback key", key
                        )
                        continue
                    else:
                        logger.warning(
                            "LLMTool last key %s rate limited; will try Gemini or rule-based", key
                        )
                        break
                if status == 401:
                    logger.warning("LLMTool unauthorized on key %s; will try Gemini or rule-based", key)
                    break
                # other non-2xx codes: log and break so fallback logic runs
                logger.warning("LLMTool HTTP status %s on key %s; falling back", status, key)
                break
            except httpx.HTTPError as exc:
                # network or other error – fall back to Gemini instead of
                # returning a raw error string
                logger.warning("LLMTool HTTP error on key %s: %s; falling back", key, exc)
                break
            except Exception as exc:
                logger.warning("LLMTool unexpected error on key %s: %s; falling back", key, exc)
                break
            except httpx.HTTPError as exc:
                logger.exception("LLMTool HTTP error: %s", exc)
                yield f"[LLM-Error] {exc}"
                return
            except Exception as exc:
                logger.exception("LLMTool unexpected error: %s", exc)
                yield f"[LLM-Error] {exc}"
                return

        # if we exhausted all OpenAI keys, try Gemini if the key is configured
        if self._gemini_key:
            try:
                self.last_provider = "gemini"
                gem_resp = await self._call_gemini(prompt, context)
                self.last_fallback = "switched to Gemini provider"
                async for tok in _stream_text_as_tokens(gem_resp):
                    yield tok
                return
            except Exception as exc:
                logger.warning("Gemini fallback failed: %s", exc)
                # if Gemini fails, we'll fall through to the rule-based stub
        live = _sync_live_llm_text(prompt, context)
        if live:
            self.last_provider = "gemini" if self._gemini_key else "openai"
            self.last_fallback = "sync LM fallback after stream failure"
            async for tok in _stream_text_as_tokens(live):
                yield tok
            return
        logger.error("Falling back to local rule-based responder (streaming)")
        self.last_provider = "rule-based"
        self.last_fallback = "using local rule-based responder"
        resp = _rule_based_response(prompt, context)
        async for tok in _stream_text_as_tokens(resp):
            yield tok

    async def _call_gemini(self, prompt: str, context: Optional[str]) -> str:
        """Call the Gemini API and return a full string response.

        Updated for current Gemini generateContent API (v1beta).
        """
        assert self._gemini_key, "Gemini API key must be configured"
        client = _get_client()
        last_exc: Optional[Exception] = None
        for model in self._gemini_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self._gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7}
            }
            try:
                resp = await client.post(url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates") or []
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts") or []
                    if parts:
                        return parts[0].get("text", "")
                raise RuntimeError(f"no output from Gemini for model {model}")
            except Exception as exc:
                logger.warning("Gemini model %s failed: %s", model, exc)
                last_exc = exc
                continue
        if last_exc:
            raise last_exc
        raise RuntimeError("Gemini call failed: no models configured")

    # Backwards-compat alias used by some agent subclasses
    def embed(self, text: str, model: Optional[str] = None) -> list[float]:
        """Return a dense text embedding using OpenAI.

        This is a synchronous method to support callers that need embeddings
        without an async event loop. It will try all configured API keys and
        raise if no key is available or the request fails.
        """
        model = model or get_settings().openai_default_embed_model
        if not self._api_keys:
            raise RuntimeError("No OpenAI API key configured for embeddings")

        payload = {"input": text, "model": model}
        for key in self._api_keys:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(f"{self._base_url}/embeddings", json=payload, headers=headers)
                    if resp.status_code == 429:
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    emb = data.get("data", [])
                    if emb and isinstance(emb[0], dict) and "embedding" in emb[0]:
                        return emb[0]["embedding"]
            except Exception as exc:
                logger.warning("LLMTool.embed failed on key %s: %s", key, exc)
                continue

        raise RuntimeError("Embedding request failed for all OpenAI API keys")

    async def arun(self, prompt: str, context: Optional[str] = None) -> str:
        return await self.generate(prompt, context=context)


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.DEBUG)

    async def _demo():
        tool = LLMTool()
        out = await tool.generate("Write a short haiku about coffee.")
        print(out)

    asyncio.run(_demo())
