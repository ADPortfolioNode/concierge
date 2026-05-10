"""Configuration settings for Concierge.

This module provides a small Settings class to centralize configuration.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_path(env_name: str, default: str) -> Path:
    raw = os.getenv(env_name, default)
    path = Path(raw)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


@dataclass
class Settings:
    """Runtime settings for Concierge."""
    max_concurrent_agents: int = int(os.getenv("MAX_CONCURRENT_AGENTS", "3"))
    memory_collection: str = os.getenv("MEMORY_COLLECTION", "quesarc_memory")
    # priority score weights
    relevance_weight: float = float(os.getenv("RELEVANCE_WEIGHT", "1.0"))
    confidence_weight: float = float(os.getenv("CONFIDENCE_WEIGHT", "1.0"))
    recency_weight: float = float(os.getenv("RECENCY_WEIGHT", "0.5"))
    impact_weight: float = float(os.getenv("IMPACT_WEIGHT", "0.5"))
    contradiction_weight: float = float(os.getenv("CONTRADICTION_WEIGHT", "2.0"))
    # phase9 additional parameters
    priority_weight: float = float(os.getenv("PRIORITY_WEIGHT", "1.0"))
    autonomous_task_priority: float = float(os.getenv("AUTONOMOUS_TASK_PRIORITY", "2.0"))
    contradiction_risk_threshold: float = float(os.getenv("CONTRADICTION_RISK_THRESHOLD", "0.5"))
    low_confidence_threshold: float = float(os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.3"))
    # how many user requests may be processed concurrently by the timeline
    max_concurrent_requests: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "2"))
    # media storage configuration
    media_dir: Path = field(default_factory=lambda: _resolve_path("MEDIA_DIR", "media"))
    media_max_age_seconds: int = int(os.getenv("MEDIA_MAX_AGE_SECONDS", str(60 * 60 * 24 * 7)))
    media_cleanup_interval: int = int(os.getenv("MEDIA_CLEANUP_INTERVAL", "3600"))
    media_url_prefix: str = os.getenv("MEDIA_URL_PREFIX", "/media")
    media_fallback_dir: Path = field(default_factory=lambda: _resolve_path("MEDIA_DIR_FALLBACK", "/tmp/media"))

    def __post_init__(self) -> None:
        self.media_images_dir = self.media_dir / "images"


def get_settings() -> Settings:
    return Settings()


if __name__ == "__main__":
    s = get_settings()
    print("Settings:", s)
