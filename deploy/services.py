"""Start, stop and check the local services. `make up`, `make down`, `make check`."""
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parents[1]
PID_FILE = ROOT / "runs/services.json"
LOG_DIR = ROOT / "runs/logs"
SERVICES = {
    "blackboard": (8101, ["-m", "uvicorn", "sensing.blackboard_service.app:app", "--port", "8101", "--log-level", "warning"]),
    "mcp": (8102, ["-m", "scout_platform.mcp_server.server"]),
}


def listening(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def up():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    pids = {}
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONUTF8": "1"}
    for name, (port, args) in SERVICES.items():
        if listening(port):
            raise SystemExit(f"port {port} is already in use, run make down first")
        log = (LOG_DIR / f"{name}.log").open("a", encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, *args], cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=flags
        )
        pids[name] = proc.pid
    PID_FILE.write_text(json.dumps(pids), encoding="utf-8")
    deadline = time.time() + 60
    while time.time() < deadline:
        if all(listening(port) for port, _ in SERVICES.values()):
            print("services up", pids)
            return
        time.sleep(0.5)
    down()
    raise SystemExit("services did not start in 60 s; see runs/logs/")


def down():
    if not PID_FILE.exists():
        print("no services recorded")
        return
    for name, pid in json.loads(PID_FILE.read_text(encoding="utf-8")).items():
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
        else:
            subprocess.run(["kill", str(pid)], capture_output=True)
    PID_FILE.unlink()
    print("services down")


async def _check():
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client("http://127.0.0.1:8102/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = sorted(t.name for t in (await session.list_tools()).tools)
            print("tools", tools)
            run_id = f"check-{int(time.time())}"
            await session.call_tool(
                "blackboard_write",
                {"run_id": run_id, "author": "check", "topic": "t", "payload": {"ok": True}, "trust_level": "trusted"},
            )
            page = await session.call_tool("blackboard_read", {"run_id": run_id, "topic": "t"})
            entries = page.structuredContent["entries"]
            print("blackboard through MCP, entries", len(entries))
            if len(tools) != 8 or len(entries) != 1:
                raise SystemExit("check failed")


if __name__ == "__main__":
    {"up": up, "down": down, "check": lambda: asyncio.run(_check())}[sys.argv[1]]()
