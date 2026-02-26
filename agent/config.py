"""Configuration loading for the investment research agent."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    openai_api_key: str
    openai_model: str
    fmp_command: list[str]
    news_command: list[str]


def get_settings() -> Settings:
    """Load environment variables and return normalized settings."""
    logger.info("Loading environment variables from .env")
    load_dotenv()

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_api_key:
        logger.error("OPENAI_API_KEY is missing")
        raise RuntimeError("OPENAI_API_KEY is required")

    settings = Settings(
        openai_api_key=openai_api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        fmp_command=["python", "-m", "mcp_servers.fmp_server"],
        news_command=["python", "-m", "mcp_servers.news_server"],
    )
    logger.info("Settings loaded (model=%s)", settings.openai_model)
    return settings
