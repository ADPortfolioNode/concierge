"""Async TaskAgent that integrates RAG context via a VectorSearchTool.

The agent queries `VectorSearchTool` for context before executing, includes
that context in its run, and stores its final output to `MemoryStore`.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from memory.memory_store import MemoryStore
from tools.vector_search_tool import VectorSearchTool
from tools.llm_tool import LLMTool
from tools.tool_router import ToolRouter
from tools.tool_registry import register_tool, registry
from tools.web_search_tool import WebSearchTool
from tools.file_memory_tool import FileMemoryTool
from tools.code_execution_tool import CodeExecutionTool
from tools.image_generation_tool import ImageGenerationTool

logger = logging.getLogger(__name__)


class TaskAgent:
    def __init__(
        self,
        task_name: str,
        task_input: Any,
        memory: MemoryStore,
        vector_tool: Optional[VectorSearchTool] = None,
        max_iter: int = 5,
        llm_tool: Optional[LLMTool] = None,
    ) -> None:
        """task_input may be a string or a structured dict with keys like
        'task_id', 'title', 'instructions', 'metadata'.
        """
        self.id: str = str(uuid.uuid4())
        self.task_name = task_name
        self.task_input = task_input
        self.memory = memory
        self.vector_tool = vector_tool
        self.max_iter = max_iter
        self.iteration = 0
        self.status = "initialized"
        self.output_lines: List[str] = []
        self.llm_tool: Optional[LLMTool] = llm_tool

    async def _fetch_context(self, top_k: int = 3) -> List[Dict[str, Any]]:
        # Build a query string from task input
        if isinstance(self.task_input, dict):
            query = self.task_input.get("instructions") or str(self.task_input)
        else:
            query = str(self.task_input)

        if self.vector_tool is not None:
            try:
                results = await self.vector_tool.search(query, top_k=top_k)
                return results
            except Exception:
                logger.exception("Vector tool query failed")
                return []

        # fallback to direct memory query - ensure we pass a string query
        try:
            results = await self.memory.query(query, top_k=top_k)
            return results
        except Exception:
            logger.exception("Memory query failed")
            return []

    async def run(self) -> Dict[str, Any]:
        """Run the agent asynchronously and store its output in memory.

        Returns a dict with `agent_id`, `status`, and `output`.
        """
        logger.info("Agent %s starting task '%s'", self.id, self.task_name)
        self.status = "running"
        # Retrieve RAG context
        context_hits = await self._fetch_context()
        ctx_str = ""
        if context_hits:
            ctx_str = " | ".join(h.get("summary", "") for h in context_hits)
            self.output_lines.append(f"context: {ctx_str}")

        # Register default tools into global registry (idempotent)
        reg = registry()
        if "web_search" not in reg.list_tools():
            register_tool(WebSearchTool())
        if "file_memory" not in reg.list_tools():
            register_tool(FileMemoryTool())
        if "code_exec" not in reg.list_tools():
            register_tool(CodeExecutionTool())
        if "image_gen" not in reg.list_tools():
            register_tool(ImageGenerationTool())

        # Select a tool for this task via the ToolRouter
        router = ToolRouter(llm=self.llm_tool)

        # Build instruction text from structured input if needed
        if isinstance(self.task_input, dict):
            instr = self.task_input.get("instructions") or self.task_input.get("details") or ""
            title = self.task_input.get("title") or self.task_input.get("task_id") or self.task_name
            metadata_in = self.task_input.get("metadata") or {}
        else:
            instr = str(self.task_input)
            title = self.task_name
            metadata_in = {}

        # Detect image generation tasks and short-circuit directly to the plugin
        _image_keywords = ("image generation", "generate image", "submit the prompt", "image plugin",
                           "dall-e", "dall_e", "image of", "picture of", "generate an image")
        _is_image_task = any(k in instr.lower() for k in _image_keywords) or \
                         any(k in title.lower() for k in ("generate image", "image gen", "prepare image prompt"))

        if _is_image_task:
            try:
                img_tool = ImageGenerationTool()
                img_url = await img_tool.run(instr)
                if img_url:
                    output = img_url
                    self.status = "complete"
                    await self.memory.store_summary(task_name=title, summary=f"Image URL: {img_url}", metadata={"agent_id": self.id, **metadata_in})
                    return {"agent_id": self.id, "status": self.status, "output": output,
                            "task_id": (self.task_input.get("task_id") if isinstance(self.task_input, dict) else None)}
            except Exception:
                logger.exception("Image task short-circuit failed; falling through to LLM")

        # Ask router which tool to use
        selected_tool_name = await router.select_tool(instr, available_tools=reg.list_tools())
        selected_tool = registry().get(selected_tool_name) if selected_tool_name else None

        # Store a snapshot marking the task start
        try:
            await self.memory.store_summary(task_name=title, summary="task_started", metadata={"agent_id": self.id, **metadata_in})
        except Exception:
            logger.exception("Failed storing start snapshot")

        # Use LLM (if provided) to generate final output using context
        try:
            prompt = f"{title}: {instr}\nProvide a concise result."
            context_text = ctx_str if context_hits else None

            # If a tool was selected, call it and include its output into the prompt
            tool_output = None
            if selected_tool is not None:
                try:
                    logger.info("Agent %s calling tool %s", self.id, selected_tool.name)
                    # prefer async `run` if available
                    if hasattr(selected_tool, "run"):
                        tool_output = await selected_tool.run(instr)
                    else:
                        tool_output = await selected_tool.arun(instr)
                    logger.info("Agent %s tool %s completed", self.id, selected_tool.name)
                    # persist tool usage
                    await self.memory.store_summary(task_name=title, summary=f"tool:{selected_tool.name}", metadata={"agent_id": self.id, "tool": selected_tool.name})
                except Exception:
                    logger.exception("Tool %s failed", getattr(selected_tool, "name", "unknown"))

            # prefer injected LLM tool; otherwise construct one lazily
            if self.llm_tool is None:
                self.llm_tool = LLMTool()

            # augment prompt with tool output if any
            if tool_output:
                prompt = prompt + f"\nTool output:\n{tool_output}\nUse this in your concise result."

            llm_out = await self.llm_tool.generate(prompt, context=context_text)

            self.status = "complete"
            # Use the raw LLM output as the task result; log separately with prefix for memory
            output = llm_out
            memory_summary = f"Task '{title}' LLM output: {llm_out}"

            # Store result into memory with metadata
            metadata = {"task_name": title, "status": self.status, "agent_id": self.id}
            metadata.update(metadata_in or {})
            await self.memory.store_summary(task_name=title, summary=memory_summary, metadata=metadata)

            logger.info("Agent %s completed (LLM)", self.id)
            return {"agent_id": self.id, "status": self.status, "output": output, "task_id": (self.task_input.get("task_id") if isinstance(self.task_input, dict) else None)}

        except Exception as exc:  # pragma: no cover - defensive
            self.status = "failed"
            logger.exception("Agent %s failed (LLM): %s", self.id, exc)
            metadata = {"task_name": title, "status": self.status, "agent_id": self.id}
            await self.memory.store_summary(task_name=title, summary=str(exc), metadata=metadata)
            return {"agent_id": self.id, "status": self.status, "output": str(exc), "task_id": (self.task_input.get("task_id") if isinstance(self.task_input, dict) else None)}


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    async def _demo():
        ms = MemoryStore()
        vector = VectorSearchTool(ms)
        agent = TaskAgent("demo", "find cats", memory=ms, vector_tool=vector, max_iter=3)
        res = await agent.run()
        print(res)

    asyncio.run(_demo())