"""Derive timing, tokens and cost from a trace. Wall-clock is used because a run's events come from two processes."""
import json
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]
LATENCY_TARGET_S = 30


def load_events(trace_path: str | Path) -> list[dict]:
    lines = Path(trace_path).read_text(encoding="utf-8").splitlines()
    return sorted((json.loads(x) for x in lines), key=lambda e: e["ts_wall"])


def _t(event: dict) -> float:
    return datetime.fromisoformat(event["ts_wall"]).timestamp()


def summarise(events: list[dict]) -> dict:
    """Model and tool time per agent are observed directly. Everything else in a run is overhead."""
    open_calls: dict[tuple, float] = {}
    per_agent: dict[str, float] = {}
    for e in events:
        kind = e["event_type"]
        if kind in ("model_start", "tool_start"):
            open_calls.setdefault((e["agent"], kind[:5], e["tool_name"]), _t(e))
        if kind in ("model_end", "tool_end"):
            start = open_calls.pop((e["agent"], kind[:5], e["tool_name"]), None)
            if start is not None:
                per_agent[e["agent"]] = per_agent.get(e["agent"], 0) + _t(e) - start
    wait = sum(float(e["payload_ref"]) for e in events if e["event_type"] == "rate_wait")
    tokens_in = sum(e["tokens_in"] or 0 for e in events)
    tokens_out = sum(e["tokens_out"] or 0 for e in events)
    return {
        "per_agent_latency_s": {k: round(v, 2) for k, v in per_agent.items()},
        "rate_wait_s": round(wait, 2),
        "model_calls": sum(e["event_type"] == "model_start" for e in events),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }


def estimated_cost(tokens_in: int, tokens_out: int, model: str) -> float | None:
    """Estimate only. None if the model has no price in configs/prices.yaml."""
    prices = yaml.safe_load((ROOT / "configs/prices.yaml").read_text(encoding="utf-8"))["models"]
    price = (prices or {}).get(model)
    if price is None:
        return None
    return round((tokens_in * price["input_per_mtok"] + tokens_out * price["output_per_mtok"]) / 1_000_000, 6)
