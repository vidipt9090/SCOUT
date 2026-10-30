"""Pilot driver. Expands the grid, randomises within each block, and can resume: a finished condition is never rerun.

A quota failure is not a result, so that run is left to retry later and the driver stops. Other failures are recorded
as degraded runs and the pilot continues. Calls are counted at the model-callback layer, because frameworks can retry.
"""
import argparse
import itertools
import json
import random
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

from eval.run_one import run  # noqa: E402

GRID = Path("configs/pilot_grid.yaml")
MANIFEST = Path("runs/pilot/manifest.jsonl")
FACTORS = ("disruption_type", "severity", "persona", "architecture", "planner_strategy", "comm_mode", "scout_prompt")
QUOTA_MARKERS = ("RESOURCE_EXHAUSTED", "RateLimitError", "429")
MAX_QUOTA_STOPS = 2


def expand() -> list[dict]:
    grid = yaml.safe_load(GRID.read_text(encoding="utf-8"))
    rng = random.Random(grid["seed"])
    conditions = []
    for block, levels in grid["blocks"].items():
        cells = [dict(zip(FACTORS, values)) for values in itertools.product(*(levels[f] for f in FACTORS))]
        rng.shuffle(cells)
        conditions += [{"block": block, **c} for c in cells]
    return conditions


def key(condition: dict) -> str:
    return "|".join(str(condition[f]) for f in ("block", *FACTORS))


def finished() -> set[str]:
    if not MANIFEST.exists():
        return set()
    return {json.loads(line)["key"] for line in MANIFEST.read_text(encoding="utf-8").splitlines()}


def hit_quota(trace_path: str) -> bool:
    for line in Path(trace_path).read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event_type"] == "error" and any(m in (event["error"] or "") for m in QUOTA_MARKERS):
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="stop after this many runs")
    args = parser.parse_args()
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    conditions = expand()
    done = finished()
    todo = [c for c in conditions if key(c) not in done]
    print(f"conditions {len(conditions)}, done {len(done)}, to do {len(todo)}", flush=True)
    quota_stops = 0
    for i, c in enumerate(todo[: args.limit], 1):
        scenario = f"{c['disruption_type']}_{c['severity']}"
        start = time.time()
        out = run(scenario, c["persona"], c["architecture"], c["planner_strategy"], c["comm_mode"], c["scout_prompt"])
        if hit_quota(out["trace_path"]):
            quota_stops += 1
            print(f"quota error on {out['run_id']}, not recorded as a result", flush=True)
            if quota_stops >= MAX_QUOTA_STOPS:
                print("stopping: quota. Rerun later to resume.", flush=True)
                return
            time.sleep(90)
            continue
        row = {
            "key": key(c), **c, "scenario": scenario, "run_id": out["run_id"], "outcome": out["outcome"],
            "degraded": out["degraded"], "model_calls": out["model_calls"], "wall_clock_s": round(time.time() - start, 1),
        }
        with MANIFEST.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        print(f"{i}/{len(todo)} {key(c)} -> {out['outcome']} {out['total_latency_s']}s calls {out['model_calls']} degraded {out['degraded']}", flush=True)


if __name__ == "__main__":
    main()
