"""Simple feature flag helper backed by environment variable.

Usage: set the env var `FEATURE_FLAGS` to a comma-separated list of
enabled flags, e.g. `FEATURE_FLAGS=media_absolute_urls,experiment_x`.
"""
import os
from typing import Set


def _load_flags() -> Set[str]:
    raw = os.getenv("FEATURE_FLAGS", "")
    parts = [p.strip() for p in raw.split(",") if p and p.strip()]
    return set(parts)


def is_enabled(name: str) -> bool:
    flags = _load_flags()
    return name in flags


def list_flags() -> Set[str]:
    return _load_flags()
