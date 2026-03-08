"""Configuration settings for Quesarc.

This module provides a small Settings class to centralize configuration.
"""
from dataclasses import dataclass


@dataclass
class Settings:
    """Runtime settings for Quesarc.

    Keep this simple; later this can be replaced with pydantic/BaseSettings.
    """
    max_concurrent_agents: int = 3
    memory_collection: str = "quesarc_memory"
    # priority score weights
    relevance_weight: float = 1.0
    confidence_weight: float = 1.0
    recency_weight: float = 0.5
    impact_weight: float = 0.5
    contradiction_weight: float = 2.0
    # phase9 additional parameters
    priority_weight: float = 1.0  # external multiplier for explicit priority flags
    autonomous_task_priority: float = 2.0  # priority assigned to self-generated tasks
    contradiction_risk_threshold: float = 0.5
    low_confidence_threshold: float = 0.3
    # how many user requests may be processed concurrently by the timeline
    # default throttle is intentionally low to avoid overload; override
    # via settings or environment if needed.
    max_concurrent_requests: int = 2


def get_settings() -> Settings:
    return Settings()


if __name__ == "__main__":
    s = get_settings()
    print("Settings:", s)
