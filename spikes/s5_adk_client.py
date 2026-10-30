"""S5, ADK side: discover tools through McpToolset and call one, no LLM."""
import asyncio
from unittest.mock import MagicMock

import google.adk
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams


async def main():
    toolset = McpToolset(connection_params=StreamableHTTPConnectionParams(url="http://127.0.0.1:8102/mcp"))
    tools = {t.name: t for t in await toolset.get_tools()}
    print("adk", google.adk.__version__, "tools", sorted(tools))
    args = {"run_id": "spike-s5", "author": "adk", "topic": "t", "payload": {"from": "adk"}, "trust_level": "trusted"}
    print("S5 ADK write", await tools["blackboard_write"].run_async(args=args, tool_context=MagicMock()))
    await toolset.close()


asyncio.run(main())
