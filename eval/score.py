"""Deterministic scorer. Reads the pilot manifest, records and ground truth, and writes results/results.csv (derived values only)."""
import json
from pathlib import Path

import pandas as pd
import yaml

MANIFEST = Path("runs/pilot/manifest.jsonl")
RECORDS = Path("runs/records")
OUT = Path("results/results.csv")


def _yaml(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def quantity_within_limits(plan: dict | None, assessment: dict | None, sku: str) -> bool | None:
    """Recompute the persona limit from config. None where the plan orders nothing."""
    if not plan or not assessment or plan.get("quantity") is None:
        return None
    effects = _yaml("configs/disruption_effects.yaml")
    severity = assessment["severity"]
    horizon = effects["horizon_days"][severity]
    baselines = json.loads(Path("data/forecasting/baselines.json").read_text(encoding="utf-8"))
    daily = baselines[sku][plan["persona"]]["daily_forecast"]
    baseline = sum(daily[: min(horizon, len(daily))]) / min(horizon, len(daily))
    if plan["persona"] == "retail_dc":
        return plan["quantity"] <= baseline * horizon * 115 / 100
    inventory = pd.read_csv("data/synth/inventory.csv")
    on_hand = inventory[(inventory["sku"] == sku) & (inventory["location"] == "plant")]["on_hand"].iloc[0]
    revised = baseline * effects["demand_multiplier"][assessment["disruption_type"]][severity]
    return (on_hand + plan["quantity"]) / revised >= 2


def score_row(row: dict, truth: dict, scenarios: dict) -> dict:
    record = json.loads((RECORDS / f"{row['run_id']}.json").read_text(encoding="utf-8"))
    result = json.loads((RECORDS / f"{row['run_id']}.result.json").read_text(encoding="utf-8"))
    level = row["severity"]
    expected = truth["cells"][row["disruption_type"]][level][row["persona"]]["action"]
    assessment, plan, verdict = result.get("assessment"), result.get("plan"), result.get("verdict")
    final = (verdict or {}).get("counter_plan") or plan
    decision = (verdict or {}).get("decision")
    agents = record["per_agent_latency_s"]
    wait = agents.get("rate_wait", 0)
    cited = set((plan or {}).get("cited_doc_ids", []))
    return {
        "run_id": row["run_id"], "block": row["block"], "disruption_type": row["disruption_type"], "severity": level,
        "persona": row["persona"], "architecture": row["architecture"], "planner_strategy": row["planner_strategy"],
        "comm_mode": row["comm_mode"], "scout_prompt": row["scout_prompt"],
        "expected_action": expected,
        "assessed_severity": assessment["severity"] if assessment else None,
        "severity_correct": bool(assessment) and assessment["severity"] == truth["severity_levels"][level],
        "vote_agreement": assessment["vote_agreement"] if assessment else None,
        "proposed_action": plan["action"] if plan else None,
        "final_action": final["action"] if final else None,
        "decision": decision,
        "checker": (verdict or {}).get("checker"),
        "violated_rules": ",".join((verdict or {}).get("violated_rules", [])),
        "proposed_correct": bool(plan) and plan["action"] == expected,
        # Correct and acted on: an escalated run waits for a human, so it does not count.
        "resolved_correct": bool(final) and final["action"] == expected and decision in ("approve", "counter"),
        "guardrail_fired": decision in ("counter", "escalate"),
        "quantity_ok": quantity_within_limits(final, assessment, scenarios[row["scenario"]]["affected_sku"]),
        "citations_ok": bool(plan) and bool(cited) and cited <= set(result.get("retrieved_doc_ids", [])),
        "degraded": record["degraded"],
        "total_latency_s": record["total_latency_s"],
        "rate_wait_s": wait,
        "latency_excl_wait_s": round(record["total_latency_s"] - wait, 2),
        "observed_model_tool_s": round(sum(v for k, v in agents.items() if k != "rate_wait"), 2),
        "model_calls": row["model_calls"],
        "tokens_in": record["tokens_in"],
        "tokens_out": record["tokens_out"],
        "estimated_cost_usd": record["estimated_cost"],
        "trace_path": record["trace_path"],
    }


def main() -> pd.DataFrame:
    rows = [json.loads(x) for x in MANIFEST.read_text(encoding="utf-8").splitlines()]
    truth = _yaml("data/scenarios/ground_truth.yaml")
    scenarios = _yaml("data/scenarios/scenarios.yaml")["scenarios"]
    frame = pd.DataFrame(score_row(r, truth, scenarios) for r in rows)
    OUT.parent.mkdir(exist_ok=True)
    frame.to_csv(OUT, index=False)
    print("scored", len(frame), "runs")
    return frame


if __name__ == "__main__":
    main()
