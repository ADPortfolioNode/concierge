"""Sandboxed code execution tool.

This provides a restricted execution environment for small Python snippets.
It forbids imports and access to builtins like open, and runs with a timeout.
"""

from __future__ import annotations

import asyncio
import ast
import sys
import io
import tempfile
import subprocess
import os
import platform
from typing import Any

from .base_tool import BaseTool


class CodeExecutionTool(BaseTool):
    name = "code_exec"
    description = "Execute short Python snippets in a restricted sandbox."

    def __init__(self, allowed_dir: str | None = None) -> None:
        self.allowed_dir = allowed_dir

    def _is_safe(self, code: str) -> bool:
        try:
            tree = ast.parse(code)
        except Exception:
            return False
        for node in ast.walk(tree):
            # disallow import statements and attribute access to dunders
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return False
            if isinstance(node, ast.Attribute) and getattr(node.attr, "startswith", lambda s: False)("__"):
                return False
            if isinstance(node, ast.Name) and node.id.startswith("__"):
                return False
        return True

    def _exec_code(self, code: str) -> str:
        # Very restricted globals and locals
        if not self._is_safe(code):
            return "ERROR: unsafe code (imports or dunders not allowed)"
        # Execute in a subprocess for isolation. We still disallow imports
        # via AST check above. The runner script will set restricted builtins
        # and execute the user code.

        runner_py = (
            "import sys, json\n"
            "code_path = sys.argv[1]\n"
            "with open(code_path, 'r', encoding='utf-8') as fh:\n"
            "    code = fh.read()\n"
            "safe_builtins = {'len': len, 'min': min, 'max': max, 'sum': sum, 'range': range, 'print': print}\n"
            "restricted_globals = {'__builtins__': safe_builtins}\n"
            "restricted_locals = {}\n"
            "try:\n"
            "    exec(compile(code, '<usercode>', 'exec'), restricted_globals, restricted_locals)\n"
            "except Exception as e:\n"
            "    print('__EXEC_ERROR__' + str(e), file=sys.stderr)\n"
        )

        tmp_code = None
        tmp_runner = None
        try:
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.py') as cf:
                cf.write(code)
                tmp_code = cf.name

            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.py') as rf:
                rf.write(runner_py)
                tmp_runner = rf.name

            cmd = [sys.executable, tmp_runner, tmp_code]
            creationflags = 0
            if platform.system() == 'Windows':
                # hide console windows
                creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5, creationflags=creationflags)
            if proc.returncode != 0:
                stderr = (proc.stderr or '').strip()
                if stderr.startswith('__EXEC_ERROR__'):
                    return f"ERROR during execution: {stderr[len('__EXEC_ERROR__'):]}"
                return f"ERROR: subprocess failed: {stderr or proc.stdout}"
            return proc.stdout or "<no-output>"
        except subprocess.TimeoutExpired:
            return "ERROR: execution timed out"
        except Exception as exc:
            return f"ERROR during execution: {exc}"
        finally:
            try:
                if tmp_code and os.path.exists(tmp_code):
                    os.unlink(tmp_code)
                if tmp_runner and os.path.exists(tmp_runner):
                    os.unlink(tmp_runner)
            except Exception:
                pass

    async def arun(self, input_data: str) -> str:
        loop = asyncio.get_running_loop()
        try:
            # execute with timeout
            return await asyncio.wait_for(loop.run_in_executor(None, self._exec_code, input_data), timeout=5.0)
        except asyncio.TimeoutError:
            return "ERROR: execution timed out"
