import asyncio
import logging
from typing import Any, Dict

from agents.coding_agent import CodingAgent
from agents.research_agent import ResearchAgent
from jobs.task_tree_store import upsert_task_node
from memory.memory_store import MemoryStore
from task_agent import TaskAgent
from tasks.celery_app import celery_app
from tools.llm_tool import LLMTool

logger = logging.getLogger(__name__)

# --- Performance Optimization ---
# Initialize heavyweight clients once per worker process, not per task.
# This avoids the overhead of creating new LLM and MemoryStore instances
# for every single task, which can be a significant bottleneck.
LLM_CLIENT = LLMTool()
MEMORY_STORE_CLIENT = MemoryStore(llm_tool=LLM_CLIENT)


def _run_agent(agent_class, thread_id, task_id, task_info):
    # Use the shared, pre-initialized clients for efficiency
    agent = agent_class(memory=MEMORY_STORE_CLIENT, llm=LLM_CLIENT)

    # The agent's `execute` method is async, so we run it in an event loop.
    result = asyncio.run(agent.execute(task_info))

    summary = result.get("summary") or result.get("output") or str(result)
    upsert_task_node(
        thread_id,
        task_id,
        thread_id,
        progress=100,
        status="completed",
        metadata={"result_summary": summary},
    )
    return summary


@celery_app.task(name="tasks.assistants.coding")
def coding_agent_task(thread_id: str, task_id: str, task_info: Dict[str, Any]):
    logger.info(f"[{thread_id}:{task_id}] Running CodingAgent")
    upsert_task_node(thread_id, task_id, parent_id=thread_id, status="running", progress=15)
    return _run_agent(CodingAgent, thread_id, task_id, task_info)


@celery_app.task(name="tasks.assistants.research")
def research_agent_task(thread_id: str, task_id: str, task_info: Dict[str, Any]):
    logger.info(f"[{thread_id}:{task_id}] Running ResearchAgent")
    upsert_task_node(thread_id, task_id, parent_id=thread_id, status="running", progress=15)
    return _run_agent(ResearchAgent, thread_id, task_id, task_info)


@celery_app.task(name="tasks.assistants.generic")
def generic_agent_task(thread_id: str, task_id: str, task_info: Dict[str, Any]):
    logger.info(f"[{thread_id}:{task_id}] Running Generic TaskAgent")
    upsert_task_node(thread_id, task_id, parent_id=thread_id, status="running", progress=15)
    # TaskAgent has a different constructor and run method
    agent = TaskAgent(
        task_name=task_info.get("title", "Generic Task"),
        task_input=task_info,
        memory=MEMORY_STORE_CLIENT,
        llm_tool=LLM_CLIENT,
    )
    result = asyncio.run(agent.run())

    summary = result.get("output") or str(result)
    agent_status = result.get("status")

    final_status = "completed" if agent_status == "complete" else agent_status
    final_progress = 100 if agent_status == "complete" else 80

    upsert_task_node(
        thread_id,
        task_id,
        thread_id,
        progress=final_progress,
        status=final_status,
        metadata={"result_summary": summary},
    )

    return result.get("output")