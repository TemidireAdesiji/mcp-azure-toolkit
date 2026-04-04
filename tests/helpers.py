"""Shared test helpers for the Azure MCP toolkit."""
from typing import Any

from mcp.server.fastmcp import FastMCP


async def call(server: FastMCP, name: str, arguments: dict[str, Any] | None = None) -> Any:
    """Call an MCP tool and return its structured result.

    FastMCP.call_tool returns ``(content_blocks, structured)`` where structured is
    ``{"result": <value>}`` for tools that return a value. This unwraps to that value.
    """
    _content, structured = await server.call_tool(name, arguments or {})
    return structured["result"]


async def tool_names(server: FastMCP) -> set[str]:
    return {t.name for t in await server.list_tools()}
