"""Shared JSONL trace writer. Standard library only, so both framework environments can import it."""
import hashlib
import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVENT_TYPES = frozenset(
    {
        "model_start",
        "model_end",
        "tool_start",
        "tool_end",
        "agent_start",
        "agent_end",
        "guardrail",
        "error",
        "rate_wait",
    }
)


def args_hash(args: Any) -> str:
    return hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()[:16]


class TraceWriter:
    """Appends one event per line to runs/traces/<run_id>.jsonl. Safe across threads and across writers."""

    def __init__(self, run_id: str, framework: str, trace_dir: str | Path = "runs/traces"):
        self.run_id = run_id
        self.framework = framework
        self.path = Path(trace_dir) / f"{run_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def event(
        self,
        agent: str,
        event_type: str,
        tool_name: str | None = None,
        args: Any = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        prompt_version: str | None = None,
        payload_ref: str | None = None,
        error: str | None = None,
    ) -> dict:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event_type: {event_type}")
        record = {
            "run_id": self.run_id,
            "ts_wall": datetime.now(timezone.utc).isoformat(),
            "ts_perf": time.perf_counter(),
            "framework": self.framework,
            "agent": agent,
            "event_type": event_type,
            "tool_name": tool_name,
            "args_hash": None if args is None else args_hash(args),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "prompt_version": prompt_version,
            "payload_ref": payload_ref,
            "error": error,
        }
        with self._lock, self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record
