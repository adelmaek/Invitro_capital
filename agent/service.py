# DIFF SUMMARY:
# - Simplified run_analysis signature to prompt (+ optional job_id).
# - Kept logging focused on original_prompt while ticker extraction is delegated to the agent.
"""High-level orchestration service for one-shot ticker analysis runs."""

from __future__ import annotations

from .config import get_settings
from .factory import create_agent
from .toolkit import create_toolkits


async def run_analysis(prompt: str, job_id: str | None = None) -> str:
    """Run a single analysis request and return only the agent's JSON output."""
    print(f"[STEP] Agent received prompt (job_id={job_id})", flush=True)
    settings = get_settings()
    tool_data = await create_toolkits(settings)
    sessions = tool_data["sessions"]
    tools = tool_data["tools"]

    executor = await create_agent(settings, tools)

    try:
        print(f"[STEP] Agent started iterations with {len(tools)} tools", flush=True)
        result = await executor.ainvoke({"prompt": prompt})
        return result["output"]
    finally:
        for session in sessions:
            await session.stop()
