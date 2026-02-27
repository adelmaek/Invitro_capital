"""Explicit MCP server session lifecycle management."""

from __future__ import annotations

import inspect
import logging
from contextlib import AsyncExitStack
from typing import Any

logger = logging.getLogger(__name__)


def _split_command(command: list[str]) -> tuple[str, list[str]]:
    if not command:
        raise ValueError("MCP command must not be empty")
    return command[0], command[1:]


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _enter_if_needed(stack: AsyncExitStack, obj: Any) -> Any:
    if hasattr(obj, "__aenter__") and hasattr(obj, "__aexit__"):
        return await stack.enter_async_context(obj)
    if hasattr(obj, "__enter__") and hasattr(obj, "__exit__"):
        return stack.enter_context(obj)
    return obj


class _StaticToolkit:
    """Minimal toolkit adapter exposing `get_tools()` for preloaded MCP tools."""

    def __init__(self, tools: list[Any]):
        self._tools = tools

    def get_tools(self) -> list[Any]:
        return list(self._tools)


class MCPSession:
    """Manage a single MCP stdio server lifecycle and expose its toolkit/client."""

    def __init__(self, command: list[str]):
        self._command = command
        self._toolkit: Any | None = None
        self._stack: AsyncExitStack | None = None

    async def start(self) -> None:
        """Start the MCP session and initialize the toolkit/client."""
        if self._toolkit is not None:
            return

        stack = AsyncExitStack()
        await stack.__aenter__()
        try:
            try:
                from langchain_mcp import MCPToolkit  # type: ignore

                toolkit = MCPToolkit(command=self._command)
                toolkit = await _enter_if_needed(stack, toolkit)
            except ImportError:
                from langchain_mcp_adapters.tools import load_mcp_tools  # type: ignore

                cmd, args = _split_command(self._command)
                connection = {
                    "transport": "stdio",
                    "command": cmd,
                    "args": args,
                }
                tools = await load_mcp_tools(None, connection=connection)
                toolkit = _StaticToolkit(tools)

            self._toolkit = toolkit
            self._stack = stack
        except Exception:
            logger.exception("Failed to start MCP session: %s", " ".join(self._command))
            await stack.aclose()
            raise

    async def stop(self) -> None:
        """Stop the MCP session and close any underlying subprocess resources."""
        if self._stack is not None:
            try:
                await self._stack.aclose()
            except RuntimeError as exc:
                message = str(exc)
                if "cancel scope" not in message:
                    logger.exception("Failed while closing MCP session: %s", " ".join(self._command))
                    raise
                logger.warning("Ignoring known anyio cancel-scope shutdown error: %s", message)
        self._stack = None
        self._toolkit = None

    def get_toolkit(self):
        """Return the initialized toolkit/client for tool discovery."""
        if self._toolkit is None:
            logger.error("get_toolkit called before start(): %s", " ".join(self._command))
            raise RuntimeError("MCPSession has not been started")
        return self._toolkit
