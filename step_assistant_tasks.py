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


def _run_agent(agent_class, thread_id, task_id, task_info, context):
    llm = LLMTool()
    memory = MemoryStore(llm_tool=llm)
    agent = agent_class(memory=memory, llm=llm)
    
    # The agent's `execute` method is async, so we run it in an event loop.
    result = asyncio.run(agent.execute(task_info))
    
    summary = result.get("summary") or result.get("output") or str(result)
    upsert_task_node(thread_id, task_id, thread_id, progress=80, metadata={"result_summary": summary})
    return summary


@celery_app.task(name="tasks.assistants.coding")
def coding_agent_task(thread_id: str, task_id: str, task_info: Dict[str, Any], context: Dict[str, Any]):
    logger.info(f"[{thread_id}:{task_id}] Running CodingAgent")
    return _run_agent(CodingAgent, thread_id, task_id, task_info, context)


@celery_app.task(name="tasks.assistants.research")
def research_agent_task(thread_id: str, task_id: str, task_info: Dict[str, Any], context: Dict[str, Any]):
    logger.info(f"[{thread_id}:{task_id}] Running ResearchAgent")
    return _run_agent(ResearchAgent, thread_id, task_id, task_info, context)


@celery_app.task(name="tasks.assistants.generic")
def generic_agent_task(thread_id: str, task_id: str, task_info: Dict[str, Any], context: Dict[str, Any]):
    logger.info(f"[{thread_id}:{task_id}] Running Generic TaskAgent")
    # TaskAgent has a different constructor
    agent = TaskAgent(task_name=task_info.get("title"), task_input=task_info)
    result = asyncio.run(agent.run())
    return result.get("output")