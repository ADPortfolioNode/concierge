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


def get_settings() -> Settings:
    return Settings()


if __name__ == "__main__":
    s = get_settings()
    print("Settings:", s)
