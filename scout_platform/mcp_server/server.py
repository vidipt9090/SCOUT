"""SCOUT MCP server. Stateless: every call reads files or the services."""
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

BLACKBOARD_URL = os.environ.get("BLACKBOARD_URL", "http://127.0.0.1:8101")

mcp = FastMCP("scout", host="127.0.0.1", port=int(os.environ.get("MCP_PORT", "8102")))


@mcp.tool()
def blackboard_write(
    run_id: str,
    author: str,
    topic: str,
    payload: dict[str, Any],
    trust_level: str,
    source_domain: str | None = None,
) -> dict:
    """Append one entry to the run's blackboard and return the stored entry."""
    resp = httpx.post(
        f"{BLACKBOARD_URL}/write",
        json={
            "run_id": run_id,
            "author": author,
            "topic": topic,
            "payload": payload,
            "trust_level": trust_level,
            "source_domain": source_domain,
        },
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def blackboard_read(run_id: str, topic: str, cursor: int = 0) -> dict:
    """Read a run's blackboard entries on a topic since a cursor."""
    resp = httpx.get(f"{BLACKBOARD_URL}/read", params={"run_id": run_id, "topic": topic, "cursor": cursor})
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def get_policy_limits(persona: str) -> dict:
    """Stub: return the persona's policy limits."""
    return {"persona": persona, "stub": True}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
