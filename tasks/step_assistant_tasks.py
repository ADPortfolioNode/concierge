"""
Step-based assistant tasks that run sequentially via Celery.
"""
import asyncio
import logging
import time
from typing import Any, Dict

from celery import Task

from agents.coding_agent import CodingAgent
from agents.research_agent import ResearchAgent
from agents.task_agent import TaskAgent
from jobs.task_tree_store import upsert_task_node
from memory.memory_store import MemoryStore
from tools.llm_tool import LLMTool

from .celery_app import celery_app

logger = logging.getLogger(__name__)


class StepAssistant(Task):
    """
    Base class for step-based assistants that run as Celery tasks.
    Each step runs one at a time chronologically, ensuring reliability.
    """

    soft_time_limit = 360  # 6 minutes
    time_limit = 420  # 7 minutes

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed: {exc}", exc_info=True)
        thread_id = kwargs.get("thread_id")
        step_task_id = kwargs.get("task", {}).get("task_id")
        if thread_id and step_task_id:
            upsert_task_node(
                thread_id=thread_id,
                task_id=step_task_id,
                status="error",
                progress=100,
                color="#ef4444",
                metadata={"result_summary": str(exc), "celery_task_id": task_id},
            )

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.info(f"Task {task_id} finished with status {status}.")


def _route_task_to_agent(task: Dict[str, Any], memory: MemoryStore, llm: LLMTool):
    """Deterministically select an agent based on task keywords."""
    title = (task.get("title", "") or "").lower()
    instr = (task.get("instructions", "") or "").lower()
    text = f"{title} {instr}"

    coding_keywords = ["code", "script", "function", "implement", "generate code"]
    research_keywords = ["research", "analyze", "investigate", "web", "search"]

    if any(k in text for k in coding_keywords):
        return CodingAgent(memory, llm=llm)
    if any(k in text for k in research_keywords):
        return ResearchAgent(memory, llm=llm)
    return TaskAgent(
        task_name=task.get("title") or task.get("task_id"),
        task_input=task,
        memory=memory,
        llm_tool=llm,
    )


@celery_app.task(base=StepAssistant, bind=True)
def execute_step_task(self, task: dict, thread_id: str, context: dict):
    """A Celery task to execute a single step from a plan."""
    task_id = task.get("task_id")
    task_name = task.get("title") or task_id
    celery_task_id = self.request.id

    upsert_task_node(
        thread_id=thread_id,
        task_id=task_id,
        parent_id=task.get("depends_on")[0] if task.get("depends_on") else thread_id,
        status="running",
        progress=10,
        color="#fbbf24",
        metadata={"task_name": task_name, "start_time": time.time(), "celery_task_id": celery_task_id},
    )

    llm = LLMTool()
    memory = MemoryStore(llm_tool=llm)
    agent = _route_task_to_agent(task, memory, llm)
    task_with_context = {**task, "context": context}

    result = asyncio.run(agent.execute(task_with_context) if hasattr(agent, "execute") else agent.run())
    summary = result.get("summary") or result.get("output") or str(result)

    upsert_task_node(thread_id=thread_id, task_id=task_id, status="done", progress=100, color="#22c55e", metadata={"result_summary": summary, "end_time": time.time(), "celery_task_id": celery_task_id})
    return {"task_id": task_id, "result": result, "summary": summary}