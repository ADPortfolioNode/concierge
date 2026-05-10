"""CodeExecutionAgent — generates code snippets from a context description.

Note: This agent does NOT execute code.  It synthesises code text using a
simple template engine (or an LLM tool if configured).  Shell execution is
intentionally absent to keep the sandbox safe.
"""

from __future__ import annotations

import logging
import textwrap
from typing import Any

from tasks.task_model import Task

logger = logging.getLogger(__name__)

# Attempt to use the LLM tool if available; fall back to template otherwise.
try:
    from tools.llm_tool import LLMTool as _LLMTool  # type: ignore

    _llm_tool: _LLMTool | None = _LLMTool()
except Exception:  # noqa: BLE001
    _llm_tool = None


# ---------------------------------------------------------------------------
# Simple built-in templates used when no LLM is available
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, str] = {
    "python": textwrap.dedent(
        """\
        # Generated Python scaffold
        def main():
            print("Hello from generated Python code")

        if __name__ == "__main__":
            main()
        """
    ),
    "javascript": textwrap.dedent(
        """\
        // Generated JavaScript scaffold
        function main() {
            console.log("Hello from generated JavaScript code");
        }

        main();
        """
    ),
    "typescript": textwrap.dedent(
        """\
        // Generated TypeScript scaffold
        function main(): void {
            console.log("Hello from generated TypeScript code");
        }

        main();
        """
    ),
    "bash": textwrap.dedent(
        """\
        #!/usr/bin/env bash
        set -euo pipefail

        echo "Hello from generated bash script"
        """
    ),
}

_DEFAULT_LANG = "python"


class CodeExecutionAgent:
    """Generates (not executes) code from a textual context description.

    Task payload expected keys:
        context (str): Natural language description of what the code should do.
        language (str, optional): Target language — defaults to "python".
    """

    name = "code_execution"
    description = "Generates code snippets from a context description (no execution)."

    async def handle_task(self, task: Task) -> dict[str, Any]:
        context: str = task.payload.get("context", "")
        language: str = task.payload.get("language", _DEFAULT_LANG).lower()

        if not context:
            raise ValueError("Task payload must include 'context'.")

        logger.info("CodeExecutionAgent generating %s code for context: %s…", language, context[:80])

        # Try LLM generation first.
        code: str = await self._generate(context, language)

        return {
            "type": "generate_code",
            "language": language,
            "code": code,
            "chars": len(code),
        }

    # ------------------------------------------------------------------ #
    # private helpers                                                        #
    # ------------------------------------------------------------------ #

    async def _generate(self, context: str, language: str) -> str:
        if _llm_tool is not None:
            prompt = (
                f"Write a {language} code snippet that accomplishes the following task.\n"
                f"Return ONLY the raw code, no markdown fences.\n\n"
                f"Task description:\n{context}"
            )
            try:
                result = await _llm_tool.arun(prompt)  # type: ignore[attr-defined]
                if isinstance(result, str) and result.strip():
                    return result.strip()
            except Exception as exc:  # noqa: BLE001
                logger.warning("LLM code generation failed (%s); using template fallback.", exc)

        # Template fallback.
        template = _TEMPLATES.get(language, _TEMPLATES[_DEFAULT_LANG])
        return f"# Context: {context}\n\n{template}"
