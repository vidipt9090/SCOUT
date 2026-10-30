"""Standalone append-only blackboard. Entries are namespaced by run_id and persisted to JSONL."""
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

STORE_DIR = Path(os.environ.get("BLACKBOARD_DIR", "runs/blackboard"))
_lock = threading.Lock()

app = FastAPI(title="SCOUT blackboard")


class EntryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    author: str
    topic: str
    payload: dict[str, Any]
    source_domain: str | None = None
    trust_level: Literal["trusted", "untrusted"]


def _path(run_id: str) -> Path:
    if not run_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("run_id must be alphanumeric with - or _")
    return STORE_DIR / f"{run_id}.jsonl"


def _load(run_id: str) -> list[dict]:
    path = _path(run_id)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/write")
def write(entry: EntryIn):
    record = {
        "entry_id": uuid.uuid4().hex,
        "ts": datetime.now(timezone.utc).isoformat(),
        **entry.model_dump(),
    }
    with _lock:
        path = _path(entry.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    return record


@app.get("/read")
def read(run_id: str, topic: str, cursor: int = 0):
    """Return entries on a topic after position `cursor` in the run's log, plus the next cursor."""
    with _lock:
        log = _load(run_id)
    return {
        "entries": [e for e in log[cursor:] if e["topic"] == topic],
        "cursor": len(log),
    }
