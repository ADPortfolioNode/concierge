"""Training scores and server time endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.training_scores import (
    list_training_runs,
    record_training_run,
    server_time_payload,
    verify_training_dates,
)

router = APIRouter(prefix="/api/v1/concierge", tags=["training"])


def _api_response(data: Any) -> dict[str, Any]:
    return {"data": data}


class TrainingRunIn(BaseModel):
    id: str | None = None
    suite_name: str = "regression_check"
    suites_passed: int = Field(ge=0)
    suites_total: int = Field(ge=0)
    exit_code: int = 0
    duration_ms: int = Field(ge=0, default=0)
    scores: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/time")
async def get_server_time():
    """Return authoritative server clock for test/training runs."""
    return _api_response(server_time_payload())


@router.get("/server-time")
async def get_server_time_alias():
    return await get_server_time()


@router.get("/training-scores")
async def get_training_scores(limit: int = 20):
    return _api_response(list_training_runs(limit=min(max(limit, 1), 100)))


@router.get("/training-scores/verify")
async def verify_training_score_dates():
    return _api_response(verify_training_dates())


@router.post("/training-scores")
async def post_training_run(body: TrainingRunIn):
    run = record_training_run(
        suite_name=body.suite_name,
        suites_passed=body.suites_passed,
        suites_total=body.suites_total,
        exit_code=body.exit_code,
        duration_ms=body.duration_ms,
        scores=body.scores,
        metadata=body.metadata,
        run_id=body.id,
    )
    return _api_response({"run": run, "verification": verify_training_dates()})