import asyncio
from core.concurrency import AsyncConcurrencyManager
from task_agent import TaskAgent
from memory.memory_store import MemoryStore
from tools.vector_search_tool import VectorSearchTool
from tools.llm_tool import LLMTool


class AsyncSacredTimeline:
    def __init__(self):
        self.memory = MemoryStore()
        self.vector = VectorSearchTool(self.memory)
        self.concurrency = AsyncConcurrencyManager(max_agents=3)
        self.active_agents = {}

    async def handle_user_input(self, user_input: str):
        # minimal planner
        tasks_to_run = []
        if "task" in user_input:
            tasks_to_run.append("task1")
            tasks_to_run.append("task2")
        else:
            return f"Direct response to: {user_input}"

        results = []
        for task_name in tasks_to_run:
            llm = LLMTool()
            agent = TaskAgent(task_name, task_input=user_input, memory=self.memory, vector_tool=self.vector, max_iter=2)
            # inject an llm tool instance
            agent.llm_tool = llm
            agent_coro = agent.run()
            manager_id, future = await self.concurrency.register(agent_coro)
            self.active_agents[manager_id] = agent
            res = await future
            results.append(res)
        return results


async def main():
    timeline = AsyncSacredTimeline()
    output = await timeline.handle_user_input("run task")
    print("Async Test Output:", output)


if __name__ == "__main__":
    asyncio.run(main())