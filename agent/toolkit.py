"""Toolkit composition utilities for MCP-backed LangChain tools."""

from __future__ import annotations

import inspect
import logging
from typing import Any

from .config import Settings
from .mcp_session import MCPSession

logger = logging.getLogger(__name__)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _get_tools(toolkit: Any) -> list:
    if hasattr(toolkit, "get_tools"):
        return list(await _maybe_await(toolkit.get_tools()))
    if hasattr(toolkit, "aget_tools"):
        return list(await _maybe_await(toolkit.aget_tools()))
    raise RuntimeError("MCP toolkit does not expose get_tools()/aget_tools()")


async def create_toolkits(settings: Settings):
    """Start MCP sessions and return combined tools plus session handles."""
    logger.info("Creating MCP toolkits")
    fmp_session = MCPSession(settings.fmp_command)
    news_session = MCPSession(settings.news_command)

    started_sessions: list[MCPSession] = []
    try:
        await fmp_session.start()
        started_sessions.append(fmp_session)
        await news_session.start()
        started_sessions.append(news_session)

        fmp_tools = await _get_tools(fmp_session.get_toolkit())
        news_tools = await _get_tools(news_session.get_toolkit())
        logger.info(
            "Discovered tools (fmp=%d, news=%d, total=%d)",
            len(fmp_tools),
            len(news_tools),
            len(fmp_tools) + len(news_tools),
        )

        return {
            "sessions": [fmp_session, news_session],
            "tools": fmp_tools + news_tools,
        }
    except Exception:
        logger.exception("Failed to create MCP toolkits")
        for session in reversed(started_sessions):
            await session.stop()
        raise
