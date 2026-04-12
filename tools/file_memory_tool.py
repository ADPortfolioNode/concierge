"""Tool for storing and retrieving structured JSON files under a safe directory.

Commands (input strings):
- STORE {"key": "k", "value": {...}}  -> stores value under key as JSON
- GET k                                   -> returns stored value for key

Files are stored under `./data/` by default. Directory traversal is prevented
and file operations are executed in a threadpool to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
from typing import Any, Optional

from .base_tool import BaseTool

logger = logging.getLogger(__name__)


_SAFE_KEY_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class FileMemoryTool(BaseTool):
    name = "file_memory"
    description = "Store and retrieve structured JSON-like data on disk (./data)."

    def __init__(self, base_dir: Optional[str] = None) -> None:
        fallback_dir = os.path.join(tempfile.gettempdir(), "concierge_file_memory")
        self.base_dir = os.path.abspath(base_dir or os.path.join(os.getcwd(), "data"))
        try:
            os.makedirs(self.base_dir, exist_ok=True)
        except Exception:
            self.base_dir = fallback_dir
            os.makedirs(self.base_dir, exist_ok=True)
            logger.warning("FileMemoryTool base directory is not writable; using fallback %s", self.base_dir)

    def _safe_key(self, key: str) -> Optional[str]:
        key = key.strip()
        if not _SAFE_KEY_RE.match(key):
            return None
        return key

    def _path_for_key(self, key: str) -> str:
        safe = self._safe_key(key)
        if not safe:
            raise ValueError("Invalid key")
        return os.path.join(self.base_dir, f"{safe}.json")

    def _write(self, path: str, data: Any) -> None:
        # blocking write executed in threadpool
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)

    def _read(self, path: str) -> Any:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    async def run(self, input_data: str) -> str:
        cmd = input_data.strip()
        loop = asyncio.get_running_loop()

        if cmd.upper().startswith("STORE"):
            rest = cmd[5:].strip()
            try:
                obj = json.loads(rest)
            except Exception as exc:
                return f"ERROR parsing JSON: {exc}"
            key = obj.get("key") or obj.get("id") or f"k{abs(hash(rest))}"
            safe = self._safe_key(key)
            if not safe:
                return "ERROR: invalid key; allowed chars A-Za-z0-9._-"
            value = obj.get("value") or obj
            path = self._path_for_key(safe)
            try:
                await loop.run_in_executor(None, self._write, path, value)
                logger.info("FileMemoryTool stored key=%s at %s", safe, path)
                return f"STORED {safe} -> {path}"
            except Exception as exc:
                logger.exception("FileMemoryTool write failed: %s", exc)
                return f"ERROR writing file: {exc}"

        if cmd.upper().startswith("GET"):
            key = cmd[3:].strip()
            safe = self._safe_key(key)
            if not safe:
                return "ERROR: invalid key"
            path = self._path_for_key(safe)
            if not os.path.exists(path):
                return f"NOT FOUND {safe}"
            try:
                data = await loop.run_in_executor(None, self._read, path)
                return f"FOUND {safe}: {data}"
            except Exception as exc:
                logger.exception("FileMemoryTool read failed: %s", exc)
                return f"ERROR reading file: {exc}"

        return "UNKNOWN COMMAND"


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.DEBUG)

    async def _demo():
        t = FileMemoryTool()
        print(await t.run('STORE {"key":"test1","value":{"hello":"world"}}'))
        print(await t.run('GET test1'))

    asyncio.run(_demo())
