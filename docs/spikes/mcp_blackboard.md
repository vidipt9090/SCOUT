# S5 MCP and S6 Blackboard

Versions: mcp 1.30.0 in all environments, crewai 1.15.33, google-adk 2.13.0.

Result: pass. Both frameworks have native MCP clients, so no wrapper is needed. The server runs FastMCP over streamable HTTP at `/mcp`. Each framework discovered the tools and wrote to the blackboard, and a read through MCP returned both entries.

APIs used:
- ADK: `McpToolset(connection_params=StreamableHTTPConnectionParams(url=...))`, `get_tools()`, `McpTool.run_async`.
- CrewAI: `Agent(mcps=[MCPServerHTTP(url=...)])`, `Agent.get_mcp_tools`, `tool.run`.

Observations:
- CrewAI opens a new MCP session for every tool call, adding about a second per call in this spike. Count this in the 30 s latency target.
- ADK logs a harmless mTLS credentials warning when no Google default credentials exist.
- The tools were called directly from code, not chosen by an LLM. The ADK call used a mock tool context. An LLM-driven call is covered by S2 and S3.

The blackboard store is one JSONL file per `run_id`, under `runs/blackboard/`.

Run: `bash spikes/run_keyless.sh`
