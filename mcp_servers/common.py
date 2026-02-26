"""Shared helpers for MCP servers."""

from __future__ import annotations

from datetime import datetime, timezone
import os

import httpx
from dotenv import load_dotenv

load_dotenv()


def get_env(name: str, default: str | None = None) -> str:
    """Read an environment variable, raising if a required one is missing."""
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def build_http_client() -> httpx.AsyncClient:
    """Create an async HTTP client with configured timeout."""
    timeout_raw = get_env("HTTP_TIMEOUT_SECONDS", "20")
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid HTTP_TIMEOUT_SECONDS value: {timeout_raw!r}. Expected number."
        ) from exc
    return httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds))


def safe_float(value: object) -> float | None:
    """Convert values to float when possible; otherwise return None."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()
