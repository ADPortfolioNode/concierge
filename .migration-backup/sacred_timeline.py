"""Compatibility shim.

The real implementation now lives under :mod:`orchestration.sacred_timeline`.
This module exists so that imports from the project root continue to work
without modification.
"""
import logging

logger = logging.getLogger(__name__)
logger.warning(
    "The 'sacred_timeline' module is deprecated and will be removed in a future version. "
    "Please update imports to point to 'orchestration.sacred_timeline'."
)

# Re-export everything from the new location to maintain backward compatibility.
from orchestration.sacred_timeline import *
