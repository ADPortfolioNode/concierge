"""Facade to shared concurrency logic.

Orchestration modules previously imported this class directly from
``orchestration.concurrency``.  Moving the implementation into ``core``
namespaced package lets us share it widely, so this file now simply
re-exports from the new location.
"""

from __future__ import annotations

# re-export everything for backwards compatibility
from core.concurrency import *


__all__ = ["AsyncConcurrencyManager"]
