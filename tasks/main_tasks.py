from __future__ import annotations

import logging
import time
from typing import Any, Dict

from celery import Task

from orchestration.sacred_timeline import SacredTimeline
from agents.planner import Planner
from agents.summarizer import Summarizer
from memory.memory_store import MemoryStore
from tools.llm_tool import LLMTool
from tools.vector_search_tool import VectorSearchTool

from .celery_app import celery_app
from task_tree_store import initialize_thread, upsert_task_node

logger = logging.getLogger(__name__)

# Initialize heavyweight clients lazily per worker process, not per task.
_LLM_CLIENT = None
_MEMORY_STORE_CLIENT = None
_PLANNER_CLIENT = None
_SUMMARIZER_CLIENT = None
_VECTOR_TOOL_CLIENT = None
_SACRED_TIMELINE_CLIENT = None

def _get_timeline_components():
    global _LLM_CLIENT, _MEMORY_STORE_CLIENT, _PLANNER_CLIENT, _SUMMARIZER_CLIENT, _VECTOR_TOOL_CLIENT, _SACRED_TIMELINE_CLIENT
    if _LLM_CLIENT is None:
        _LLM_CLIENT = LLMTool()
    if _MEMORY_STORE_CLIENT is None:
        _MEMORY_STORE_CLIENT = MemoryStore(llm_tool=_LLM_CLIENT)
    if _PLANNER_CLIENT is None:
        _PLANNER_CLIENT = Planner(llm=_LLM_CLIENT)
    if _SUMMARIZER_CLIENT is None:
        _SUMMARIZER_CLIENT = Summarizer() # Summarizer also uses LLMTool internally
    if _VECTOR_TOOL_CLIENT is None:
        _VECTOR_TOOL_CLIENT = VectorSearchTool(_MEMORY_STORE_CLIENT)
    if _SACRED_TIMELINE_CLIENT is None:
        _SACRED_TIMELINE_CLIENT = SacredTimeline(
            memory_store=_MEMORY_STORE_CLIENT,
            planner=_PLANNER_CLIENT,
            summarizer=_SUMMARIZER_CLIENT,
            vector_tool=_VECTOR_TOOL_CLIENT,
        )
    return _SACRED_TIMELINE_CLIENT

class AutonomousTask(Task):
    """
    Base class for the main autonomous task.
    """
    soft_time_limit = 1800  # 30 minutes
    time_limit = 1900       # ~31 minutes

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Autonomous task {task_id} failed: {exc}", exc_info=True)
        thread_id = kwargs.get("thread_id")
        goal = kwargs.get("goal")
        if thread_id:
            upsert_task_node(
                thread_id=thread_id,
                task_id=thread_id, # Root task
                status="error",
                progress=100,
                color="#ef4444",
                metadata={"result_summary": f"Autonomous task failed: {str(exc)}", "celery_task_id": task_id, "goal": goal},
            )

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.info(f"Autonomous task {task_id} finished with status {status}.")
        thread_id = kwargs.get("thread_id")
        if thread_id:
            # Mark the root task as complete
            upsert_task_node(
                thread_id=thread_id,
                task_id=thread_id, # Root task
                status="complete",
                progress=100,
                color="#22c55e",
                metadata={"result_summary": "Autonomous goal completed.", "celery_task_id": task_id},
            )


@celery_app.task(base=AutonomousTask, bind=True)
def run_autonomous_task(self, goal: str, thread_id: str):
    """
    Celery task to run the full autonomous orchestration for a given goal.
    """
    logger.info(f"Celery autonomous task {self.request.id} started for goal: {goal}, thread_id: {thread_id}")

    # Initialize the root task node for the thread
    initialize_thread(thread_id, {
        'task_name': f'Goal: {goal[:80]}',
        'start_time': time.time(),
        'metadata': {'goal': goal},
    })

    timeline = _get_timeline_components()

    # The SacredTimeline.run_autonomous method now handles creating the chain
    # of execute_step_task and dispatches it.
    # It returns a dict with status and thread_id.
    result = asyncio.run(timeline.run_autonomous(goal=goal, thread_id=thread_id))

    logger.info(f"Celery autonomous task {self.request.id} completed for goal: {goal}, thread_id: {thread_id} with result: {result}")
    return result
from __future__ import annotations

import logging
import time
from typing import Any, Dict

from celery import Task

from orchestration.sacred_timeline import SacredTimeline
from agents.planner import Planner
from agents.summarizer import Summarizer
from memory.memory_store import MemoryStore
from tools.llm_tool import LLMTool
from tools.vector_search_tool import VectorSearchTool

from .celery_app import celery_app
from task_tree_store import initialize_thread, upsert_task_node

logger = logging.getLogger(__name__)

# Initialize heavyweight clients lazily per worker process, not per task.
_LLM_CLIENT = None
_MEMORY_STORE_CLIENT = None
_PLANNER_CLIENT = None
_SUMMARIZER_CLIENT = None
_VECTOR_TOOL_CLIENT = None
_SACRED_TIMELINE_CLIENT = None

def _get_timeline_components():
    global _LLM_CLIENT, _MEMORY_STORE_CLIENT, _PLANNER_CLIENT, _SUMMARIZER_CLIENT, _VECTOR_TOOL_CLIENT, _SACRED_TIMELINE_CLIENT
    if _LLM_CLIENT is None:
        _LLM_CLIENT = LLMTool()
    if _MEMORY_STORE_CLIENT is None:
        _MEMORY_STORE_CLIENT = MemoryStore(llm_tool=_LLM_CLIENT)
    if _PLANNER_CLIENT is None:
        _PLANNER_CLIENT = Planner(llm=_LLM_CLIENT)
    if _SUMMARIZER_CLIENT is None:
        _SUMMARIZER_CLIENT = Summarizer() # Summarizer also uses LLMTool internally
    if _VECTOR_TOOL_CLIENT is None:
        _VECTOR_TOOL_CLIENT = VectorSearchTool(_MEMORY_STORE_CLIENT)
    if _SACRED_TIMELINE_CLIENT is None:
        _SACRED_TIMELINE_CLIENT = SacredTimeline(
            memory_store=_MEMORY_STORE_CLIENT,
            planner=_PLANNER_CLIENT,
            summarizer=_SUMMARIZER_CLIENT,
            vector_tool=_VECTOR_TOOL_CLIENT,
        )
    return _SACRED_TIMELINE_CLIENT

class AutonomousTask(Task):
    """
    Base class for the main autonomous task.
    """
    soft_time_limit = 1800  # 30 minutes
    time_limit = 1900       # ~31 minutes

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Autonomous task {task_id} failed: {exc}", exc_info=True)
        thread_id = kwargs.get("thread_id")
        goal = kwargs.get("goal")
        if thread_id:
            upsert_task_node(
                thread_id=thread_id,
                task_id=thread_id, # Root task
                status="error",
                progress=100,
                color="#ef4444",
                metadata={"result_summary": f"Autonomous task failed: {str(exc)}", "celery_task_id": task_id, "goal": goal},
            )

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        logger.info(f"Autonomous task {task_id} finished with status {status}.")
        thread_id = kwargs.get("thread_id")
        if thread_id:
            # Mark the root task as complete
            upsert_task_node(
                thread_id=thread_id,
                task_id=thread_id, # Root task
                status="complete",
                progress=100,
                color="#22c55e",
                metadata={"result_summary": "Autonomous goal completed.", "celery_task_id": task_id},
            )


@celery_app.task(base=AutonomousTask, bind=True)
def run_autonomous_task(self, goal: str, thread_id: str):
    """
    Celery task to run the full autonomous orchestration for a given goal.
    """
    logger.info(f"Celery autonomous task {self.request.id} started for goal: {goal}, thread_id: {thread_id}")

    # Initialize the root task node for the thread
    initialize_thread(thread_id, {
        'task_name': f'Goal: {goal[:80]}',
        'start_time': time.time(),
        'metadata': {'goal': goal},
    })

    timeline = _get_timeline_components()

    # The SacredTimeline.run_autonomous method now handles creating the chain
    # of execute_step_task and dispatches it.
    # It returns a dict with status and thread_id.
    result = asyncio.run(timeline.run_autonomous(goal=goal, thread_id=thread_id))

    logger.info(f"Celery autonomous task {self.request.id} completed for goal: {goal}, thread_id: {thread_id} with result: {result}")
    return result