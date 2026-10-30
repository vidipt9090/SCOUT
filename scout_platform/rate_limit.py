"""Cross-process pacing of LLM calls, for the provider's free-tier limit. Both framework services share one window file."""
import asyncio
import json
import os
import time
from pathlib import Path

WINDOW_S = 60
MAX_CALLS = 12  # observed limit is about 15 a minute; a margin avoids hidden provider retries
STATE = Path("runs/llm_window.json")
LOCK = Path("runs/llm_window.lock")
LOCK_STALE_S = 5


def _lock() -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            os.close(os.open(LOCK, os.O_CREAT | os.O_EXCL))
            return
        except FileExistsError:
            try:
                if time.time() - LOCK.stat().st_mtime > LOCK_STALE_S:
                    LOCK.unlink(missing_ok=True)
            except FileNotFoundError:
                pass
            time.sleep(0.01)


def _take_slot() -> float:
    """Claim a slot and return 0, or return the seconds to wait before trying again."""
    _lock()
    try:
        now = time.time()
        calls = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else []
        calls = [t for t in calls if now - t < WINDOW_S]
        if len(calls) < MAX_CALLS:
            STATE.write_text(json.dumps([*calls, now]), encoding="utf-8")
            return 0.0
        return calls[0] + WINDOW_S - now + 0.05
    finally:
        LOCK.unlink(missing_ok=True)


def wait_for_slot() -> float:
    """Block until a call may go out. Returns the seconds waited, which are reported apart from inference time."""
    waited = 0.0
    while (delay := _take_slot()) > 0:
        time.sleep(delay)
        waited += delay
    return waited


async def await_slot() -> float:
    waited = 0.0
    while (delay := _take_slot()) > 0:
        await asyncio.sleep(delay)
        waited += delay
    return waited
