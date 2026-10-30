"""One full traversal: feed -> Sensing crew -> A2A -> Decision core. Writes a RunRecord and a trace. Sensing environment."""
import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

from contracts import RunRecord  # noqa: E402
from scout_platform.tracing.summary import LATENCY_TARGET_S, estimated_cost, load_events, summarise  # noqa: E402
from scout_platform.tracing.writer import TraceWriter  # noqa: E402
from sensing import hooks  # noqa: E402
from sensing.a2a_client import request_decision  # noqa: E402
from sensing.crew import MODEL, run_scout, run_theme_analyst, screen_feed  # noqa: E402
from sensing.news import replay  # noqa: E402

RECORDS = Path("runs/records")
REAL_NEWS = "real_news"
REAL_NEWS_SKU = "FOODS_3_363"


def scenario_feed(scenario: str):
    if scenario == REAL_NEWS:
        return replay.replay_snapshot(), REAL_NEWS_SKU
    config = yaml.safe_load(Path("data/scenarios/scenarios.yaml").read_text(encoding="utf-8"))["scenarios"][scenario]
    return replay.planted(scenario), config["affected_sku"]


def run(scenario: str, persona: str, arch: str, strategy: str, comm_mode: str, scout_prompt: str) -> dict:
    run_id = f"run-{scenario.replace('_', '-')}-{uuid.uuid4().hex[:8]}"
    tracer = TraceWriter(run_id, "crewai")
    started = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    condition = {
        "scenario": scenario, "persona": persona, "architecture": arch, "planner_strategy": strategy,
        "comm_mode": comm_mode, "scout_prompt": scout_prompt, "temperature": 0, "severity_temperature": 0.7,
        "complexity_level": None, "model": MODEL,
    }

    feed, sku = scenario_feed(scenario)
    tracer.event("ingestion", "guardrail", tool_name="layer1_ingestion", payload_ref=f"{len(feed)} items sanitised")
    feed = screen_feed(feed, tracer)
    hooks.use_trace(tracer, scout_prompt)
    result: dict = {"assessment": None, "plan": None, "verdict": None}
    degraded = False
    try:
        run_scout("A", feed, run_id, tracer, scout_prompt)
        run_scout("B", feed, run_id, tracer, scout_prompt)
        hooks.use_trace(tracer, "theme_v1")
        assessment = run_theme_analyst(run_id, [sku], tracer)
        if assessment is None:
            outcome = "no_disruption"
        else:
            result["assessment"] = assessment.model_dump(mode="json")
            request = {
                "run_id": run_id, "persona": persona, "sku": sku, "architecture": arch, "strategy": strategy,
                "comm_mode": comm_mode, "assessment": result["assessment"] if comm_mode == "direct" else None,
            }
            result.update(request_decision(request))
            degraded = result["degraded"]
            outcome = result["verdict"]["decision"] if result.get("verdict") else "no_verdict"
    except Exception as e:  # a failed run is a record, and the pilot keeps going
        tracer.event("run_one", "error", error=f"{type(e).__name__}: {str(e)[:500]}")
        degraded, outcome = True, "failed"

    total = time.perf_counter() - t0
    summary = summarise(load_events(tracer.path))
    model = MODEL.split("/", 1)[-1]
    record = RunRecord(
        run_id=run_id,
        condition=condition,
        started_at=started,
        ended_at=datetime.now(timezone.utc),
        total_latency_s=round(total, 2),
        per_agent_latency_s={**summary["per_agent_latency_s"], "rate_wait": summary["rate_wait_s"]},
        tokens_in=summary["tokens_in"],
        tokens_out=summary["tokens_out"],
        estimated_cost=estimated_cost(summary["tokens_in"], summary["tokens_out"], model),
        outcome=outcome,
        degraded=degraded,
        trace_path=str(tracer.path),
    )
    RECORDS.mkdir(parents=True, exist_ok=True)
    (RECORDS / f"{run_id}.json").write_text(record.model_dump_json(indent=1), encoding="utf-8")
    (RECORDS / f"{run_id}.result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return {**record.model_dump(mode="json"), "model_calls": summary["model_calls"], "over_target": total > LATENCY_TARGET_S, "result": result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--persona", required=True, choices=["plant", "retail_dc"])
    parser.add_argument("--arch", required=True, choices=["sequential", "hierarchical"])
    parser.add_argument("--strategy", required=True, choices=["react", "cot"])
    parser.add_argument("--comm-mode", default="blackboard", choices=["blackboard", "direct"])
    parser.add_argument("--scout-prompt", default="scout_cot_v1")
    a = parser.parse_args()
    out = run(a.scenario, a.persona, a.arch, a.strategy, a.comm_mode, a.scout_prompt)
    verdict = out["result"].get("verdict") or {}
    plan = verdict.get("counter_plan") or out["result"].get("plan") or {}
    print(
        f"{out['run_id']} outcome={out['outcome']} action={plan.get('action')} vendor={plan.get('vendor_id')} qty={plan.get('quantity')} "
        f"rules={verdict.get('violated_rules')} degraded={out['degraded']}"
    )
    print(
        f"latency {out['total_latency_s']}s (over 30 s: {out['over_target']}) calls {out['model_calls']} "
        f"tokens {out['tokens_in']}/{out['tokens_out']} cost {out['estimated_cost']} agents {out['per_agent_latency_s']}"
    )
