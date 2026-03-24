"""Facade pointing to core concurrency implementation.

The real logic lives in :mod:`core.concurrency`. This module exists to
preserve backward-compatibility for imports such as ``from concurrency
import AsyncConcurrencyManager`` while the codebase transitions to a
package-based layout.
"""

from __future__ import annotations

# re-export all public names from core.concurrency
from core.concurrency import *


__all__ = ["AsyncConcurrencyManager"]