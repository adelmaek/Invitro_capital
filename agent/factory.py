# DIFF SUMMARY:
# - Updated agent invocation inputs from ticker-only to prompt-only.
# - Human message forwards original prompt as: "User prompt: <prompt>".
"""Factory for creating the LangChain LLM and agent executor."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain.agents import create_agent as create_langchain_agent
from langchain_openai import ChatOpenAI

from .config import Settings
from .prompts import SYSTEM_MESSAGE

logger = logging.getLogger(__name__)


def _shorten(text: str, max_len: int = 220) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3] + "..."


def _tool_result_preview(content: Any) -> str:
    if isinstance(content, str):
        return _shorten(content)
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
                else:
                    text_parts.append(json.dumps(item, default=str))
            else:
                text_parts.append(str(item))
        return _shorten(" ".join(text_parts))
    return _shorten(str(content))


class _RunnableExecutorAdapter:
    """Normalize LangChain v1 agent graph interface to `ainvoke -> {'output': str}`."""

    def __init__(self, runnable: Any):
        self._runnable = runnable

    async def ainvoke(self, inputs: dict[str, Any]) -> dict[str, str]:
        prompt = inputs["prompt"]
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
        messages = list(result.get("messages", []))
        agent_iterations = 0

        for msg in messages:
            class_name = msg.__class__.__name__
            if class_name == "AIMessage":
                agent_iterations += 1
                for call in getattr(msg, "tool_calls", []) or []:
                    if isinstance(call, dict) and call.get("name"):
                        name = str(call["name"])
                        args = call.get("args", {})
                        args_str = json.dumps(args, ensure_ascii=True, default=str)
                        print(f"[STEP] Tool call detected: {name} args={args_str}", flush=True)
            elif class_name == "ToolMessage":
                name = getattr(msg, "name", None)
                if name:
                    preview = _tool_result_preview(getattr(msg, "content", ""))
                    print(f"[STEP] Tool call result: {name} -> {preview}", flush=True)
        print(f"[STEP] Agent iterations: {agent_iterations}", flush=True)

        for msg in reversed(messages):
            content = getattr(msg, "content", None)
            if isinstance(content, str) and content.strip():
                return {"output": content}
            if isinstance(content, list):
                text_parts = [part.get("text") for part in content if isinstance(part, dict) and part.get("text")]
                if text_parts:
                    return {"output": "\n".join(text_parts)}

        logger.error("Agent returned no final text output")
        raise RuntimeError("Agent returned no final text output")


async def create_agent(settings: Settings, tools):
    """Create and return a configured LangChain v1 agent executor adapter."""
    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=0,
    )
    runnable = create_langchain_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_MESSAGE,
        debug=False,
    )
    return _RunnableExecutorAdapter(runnable)
