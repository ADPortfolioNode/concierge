"""FastAPI application exposing the async SacredTimeline endpoint.

This app creates the necessary async components on startup and exposes a
single POST endpoint `/ask` which accepts JSON payload `{"input": "..."}`.
"""
from __future__ import annotations

import logging
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sacred_timeline import SacredTimeline
from concurrency import AsyncConcurrencyManager
from memory.memory_store import MemoryStore
from config.settings import get_settings

logging.basicConfig(level=logging.INFO)
app = FastAPI()


class AskPayload(BaseModel):
    input: str


@app.on_event("startup")
async def _startup():
    settings = get_settings()
    app.state.concurrency = AsyncConcurrencyManager(max_agents=settings.max_concurrent_agents)
    app.state.memory = MemoryStore(collection_name=settings.memory_collection)
    app.state.timeline = SacredTimeline(concurrency_manager=app.state.concurrency, memory_store=app.state.memory)


@app.post("/ask")
async def ask(payload: AskPayload):
    if not payload.input:
        raise HTTPException(status_code=400, detail="input required")
    result = await app.state.timeline.handle_user_input(payload.input)
    return {"response": result}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
