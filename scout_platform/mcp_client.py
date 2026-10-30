"""Call the MCP server from service code. Used where the code, not an LLM, decides a tool call must happen."""
import asyncio
import os
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8102/mcp")


class ToolCallError(RuntimeError):
    pass


async def acall_tools(calls: list[tuple[str, dict[str, Any]]]) -> list[dict]:
    """Run calls in order over one session."""
    results = []
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for name, args in calls:
                result = await session.call_tool(name, args)
                if result.isError:
                    text = " ".join(c.text for c in result.content if hasattr(c, "text"))
                    raise ToolCallError(f"{name}: {text}")
                results.append(result.structuredContent)
    return results


def call_tools(calls: list[tuple[str, dict[str, Any]]]) -> list[dict]:
    return asyncio.run(acall_tools(calls))
