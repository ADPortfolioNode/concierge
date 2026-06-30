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
    vector_db: str = os.getenv("VECTOR_DB", "chroma")
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
    vector_db_init_timeout: int = int(os.getenv("VECTOR_DB_INIT_TIMEOUT", "8"))
    redis_init_timeout: int = int(os.getenv("REDIS_INIT_TIMEOUT", "5"))
    # Resilience / production config flags
    redis_enabled: bool = os.getenv("REDIS_ENABLED", "true").lower() != "false"
    celery_enabled: bool = os.getenv("CELERY_ENABLED", "true").lower() != "false"
    use_inline_tasks: bool = os.getenv("USE_INLINE_TASKS", "false").lower() == "true"
    # how many user requests may be processed concurrently by the timeline
    max_concurrent_requests: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "2"))
    # media storage configuration
    media_dir: Path = field(default_factory=lambda: _resolve_path("MEDIA_DIR", "media"))
    media_max_age_seconds: int = int(os.getenv("MEDIA_MAX_AGE_SECONDS", str(60 * 60 * 24 * 7)))
    media_cleanup_interval: int = int(os.getenv("MEDIA_CLEANUP_INTERVAL", "3600"))
    media_url_prefix: str = os.getenv("MEDIA_URL_PREFIX", "/media")
    media_fallback_dir: Path = field(default_factory=lambda: _resolve_path("MEDIA_DIR_FALLBACK", "/tmp/media"))

    # LLM / API keys (loaded from .env or environment — never hard-coded)
    # IMPORTANT: All literal .env key name strings for secrets live ONLY in this file.
    # All other code MUST obtain values via get_settings().xxx (e.g. settings.openai_api_key)
    # This was done via search/replace refactor to avoid scattering key names in source.
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "") or os.getenv("AI_INTEGRATIONS_OPENAI_API_KEY", "")
    openai_api_keys: str = os.getenv("OPENAI_API_KEYS", "")
    openai_api_base: str = (
        os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        or os.getenv("AI_INTEGRATIONS_OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    gemini_models: str = os.getenv("GEMINI_MODELS", "")
    gemini_image_models: str = os.getenv(
        "GEMINI_IMAGE_MODELS",
        "gemini-2.5-flash-image,gemini-3.1-flash-image",
    )
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_image_models: str = os.getenv(
        "OLLAMA_IMAGE_MODELS",
        "x/flux2-klein,x/z-image-turbo",
    )
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))

    # Integration secrets (centralized so key names are not repeated elsewhere in code)
    slack_bot_token: str = os.getenv("SLACK_BOT_TOKEN", "")
    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")

    # Common model default overrides (non-secret but useful to centralize)
    openai_default_chat_model: str = os.getenv("OPENAI_DEFAULT_CHAT_MODEL", "gpt-4o-mini")
    openai_default_embed_model: str = os.getenv("OPENAI_DEFAULT_EMBED_MODEL", "text-embedding-3-small")
    openai_default_moderate_model: str = os.getenv("OPENAI_DEFAULT_MODERATE_MODEL", "") or ""

    def __post_init__(self) -> None:
        self.media_images_dir = self.media_dir / "images"


def get_settings() -> Settings:
    return Settings()


if __name__ == "__main__":
    s = get_settings()
    print("Settings:", s)
