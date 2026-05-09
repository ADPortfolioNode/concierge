"""Example tool implementation.

This is a trivial tool used to demonstrate how TaskAgent might call tools.
"""
from .base_tool import BaseTool


class ExampleTool(BaseTool):
    def run(self, input_data: str) -> str:
        # Perform a tiny transformation to showcase behavior
        return input_data[::-1]


if __name__ == "__main__":
    import asyncio

    async def _demo():
        t = ExampleTool()
        print(await t.arun("hello"))

    asyncio.run(_demo())
