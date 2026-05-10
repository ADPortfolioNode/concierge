"""Base tool interface for Quesarc tools.

Tools are small pluggable components that TaskAgent may call. This file
defines the expected interface and a simple helper base class.
"""
from typing import Protocol


class Tool(Protocol):
    """Protocol that tools should follow."""

    def run(self, input_data: str) -> str:
        ...


class BaseTool:
    """Lightweight base tool providing a default run implementation."""

    def run(self, input_data: str) -> str:  # pragma: no cover - trivial
        return f"BaseTool echo: {input_data}"
