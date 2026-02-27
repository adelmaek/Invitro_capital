# DIFF SUMMARY:
# - Updated agent invocation inputs from ticker-only to prompt-only.
# - Human message forwards original prompt as: "User prompt: <prompt>".
"""Factory for creating the LangChain LLM and agent executor."""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents import create_agent as create_langchain_agent
from langchain_openai import ChatOpenAI

from .config import Settings
from .prompts import SYSTEM_MESSAGE

logger = logging.getLogger(__name__)


class _RunnableExecutorAdapter:
    """Normalize LangChain v1 agent graph interface to `ainvoke -> {'output': str}`."""

    def __init__(self, runnable: Any):
        self._runnable = runnable

    async def ainvoke(self, inputs: dict[str, Any]) -> dict[str, str]:
        prompt = inputs["prompt"]
        logger.info("Invoking LangChain v1 runnable agent prompt=%r", prompt)
        result = await self._runnable.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": f"User prompt: {prompt}",
                    }
                ]
            }
        )

        for msg in reversed(result.get("messages", [])):
            content = getattr(msg, "content", None)
            if isinstance(content, str) and content.strip():
                return {"output": content}
            if isinstance(content, list):
                text_parts = [part.get("text") for part in content if isinstance(part, dict) and part.get("text")]
                if text_parts:
                    logger.info("Received final agent output (multipart text)")
                    return {"output": "\n".join(text_parts)}

        logger.error("Agent returned no final text output")
        raise RuntimeError("Agent returned no final text output")


async def create_agent(settings: Settings, tools):
    """Create and return a configured LangChain v1 agent executor adapter."""
    logger.info("Creating agent executor (model=%s, tools=%d)", settings.openai_model, len(tools))
    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=0,
    )
    logger.info("Using LangChain v1 create_agent API")
    runnable = create_langchain_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_MESSAGE,
        debug=True,
    )
    return _RunnableExecutorAdapter(runnable)
