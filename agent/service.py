# DIFF SUMMARY:
# - Simplified run_analysis signature to prompt (+ optional job_id).
# - Kept logging focused on original_prompt while ticker extraction is delegated to the agent.
"""High-level orchestration service for one-shot ticker analysis runs."""

from __future__ import annotations

import logging

from .config import get_settings
from .factory import create_agent
from .toolkit import create_toolkits

logger = logging.getLogger(__name__)


async def run_analysis(prompt: str, job_id: str | None = None) -> str:
    """Run a single analysis request and return only the agent's JSON output."""
    logger.info(
        "run_analysis invoked prompt=%r job_id=%s",
        prompt,
        job_id,
    )
    settings = get_settings()
    tool_data = await create_toolkits(settings)
    sessions = tool_data["sessions"]
    tools = tool_data["tools"]
    logger.info("Toolkits ready (sessions=%d, tools=%d)", len(sessions), len(tools))

    executor = await create_agent(settings, tools)
    logger.info("Agent executor created")

    try:
        logger.info("Executing agent")
        result = await executor.ainvoke({"prompt": prompt})
        logger.info("Agent execution completed")
        return result["output"]
    finally:
        logger.info("Stopping MCP sessions")
        for session in sessions:
            await session.stop()
        logger.info("All MCP sessions stopped")
