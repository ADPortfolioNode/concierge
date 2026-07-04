"""Persist regression / training run scores with accurate timestamps."""
from __future__ import annotations

import json
import socket
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import get_settings

_MAX_RUNS = 200


def server_time_payload() -> dict[str, Any]:
    """Authoritative server clock for test runs."""
    utc = datetime.now(timezone.utc)
    local = datetime.now().astimezone()
    return {
        "utc": utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "unix_ms": int(utc.timestamp() * 1000),
        "local": local.isoformat(timespec="seconds"),
        "timezone": str(local.tzinfo) if local.tzinfo else "UTC",
        "epoch_seconds": utc.timestamp(),
    }


def _scores_path() -> Path:
    settings = get_settings()
    path = getattr(settings, "training_scores_file", None)
    if path is None:
        path = settings.media_dir.parent / "data" / "training_scores.json"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_store() -> dict[str, Any]:
    path = _scores_path()
    if not path.exists():
        return {"runs": [], "updated_at_utc": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("runs"), list):
            return data
    except Exception:
        pass
    return {"runs": [], "updated_at_utc": None}


def _save_store(data: dict[str, Any]) -> None:
    path = _scores_path()
    data["updated_at_utc"] = server_time_payload()["utc"]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _parse_run_time(run: dict[str, Any]) -> datetime | None:
    raw = run.get("recorded_at_utc") or run.get("utc")
    if not raw:
        ms = run.get("unix_ms")
        if isinstance(ms, (int, float)):
            return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
        return None
    text = str(raw).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def verify_training_dates(runs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Validate stored run timestamps are parseable, not in the future, newest-first."""
    store = _load_store() if runs is None else {"runs": runs}
    items = store.get("runs") or []
    issues: list[str] = []
    now = datetime.now(timezone.utc)
    parsed: list[tuple[datetime, dict[str, Any]]] = []

    for i, run in enumerate(items):
        if not isinstance(run, dict):
            issues.append(f"run[{i}] is not an object")
            continue
        dt = _parse_run_time(run)
        if dt is None:
            issues.append(f"run[{i}] missing or invalid recorded_at_utc/unix_ms")
            continue
        if dt > now:
            issues.append(f"run[{i}] timestamp is in the future: {dt.isoformat()}")
        parsed.append((dt, run))

    if len(parsed) >= 2:
        for j in range(len(parsed) - 1):
            if parsed[j][0] < parsed[j + 1][0]:
                issues.append("runs are not stored newest-first by training date")
                break

    return {
        "ok": len(issues) == 0,
        "run_count": len(items),
        "issues": issues,
        "newest_utc": parsed[0][0].strftime("%Y-%m-%dT%H:%M:%SZ") if parsed else None,
        "oldest_utc": parsed[-1][0].strftime("%Y-%m-%dT%H:%M:%SZ") if parsed else None,
    }


def list_training_runs(*, limit: int = 20) -> dict[str, Any]:
    store = _load_store()
    runs = list(store.get("runs") or [])
    verification = verify_training_dates(runs)
    return {
        "runs": runs[:limit],
        "total": len(runs),
        "updated_at_utc": store.get("updated_at_utc"),
        "verification": verification,
        "server_time": server_time_payload(),
    }


def record_training_run(
    *,
    suite_name: str,
    suites_passed: int,
    suites_total: int,
    exit_code: int,
    duration_ms: int,
    scores: dict[str, int] | None = None,
    metadata: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Append a training/regression run with server timestamps and metadata."""
    clock = server_time_payload()
    run = {
        "id": run_id or f"run_{uuid.uuid4().hex[:12]}",
        "suite_name": suite_name,
        "recorded_at_utc": clock["utc"],
        "recorded_at_local": clock["local"],
        "unix_ms": clock["unix_ms"],
        "suites_passed": suites_passed,
        "suites_total": suites_total,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "scores": scores or {},
        "metadata": {
            "hostname": socket.gethostname(),
            **(metadata or {}),
        },
    }
    store = _load_store()
    runs = store.get("runs") or []
    if run_id:
        runs = [r for r in runs if not (isinstance(r, dict) and r.get("id") == run_id)]
    runs.insert(0, run)
    store["runs"] = runs[:_MAX_RUNS]
    _save_store(store)
    return run