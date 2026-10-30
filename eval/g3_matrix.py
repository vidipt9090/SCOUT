"""G3 check: Decision core against the answer key. Evaluation only, so it may read ground truth. Prints one line per run."""
import asyncio
import json
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

from decision.pipeline import run_decision  # noqa: E402
from eval.g3_decision import CASES, assessment  # noqa: E402

TRUTH = yaml.safe_load(Path("data/scenarios/ground_truth.yaml").read_text(encoding="utf-8"))
LEVELS = {2: "low", 3: "medium", 4: "high"}


def expected(case: str, persona: str) -> tuple[str, str | None]:
    if case == "single_domain":
        return "monitor", "counter"
    if case == "severity_5":
        return "any", "escalate"
    dtype, severity, _, _ = CASES[case]
    return TRUTH["cells"][dtype][LEVELS[severity]][persona]["action"], None


async def one(case: str, persona: str, arch: str, strategy: str) -> dict:
    run_id = f"g3m-{case.replace('_', '-')}-{persona.replace('_', '-')}-{arch[:3]}-{strategy}-{int(time.time())}"
    a = assessment(case, run_id)
    start = time.perf_counter()
    r = await run_decision(a, a.affected_skus[0], persona, arch, strategy, run_id)
    latency = round(time.perf_counter() - start, 1)
    final = r.verdict.counter_plan if r.verdict and r.verdict.counter_plan else r.plan
    want_action, want_decision = expected(case, persona)
    action = final.action if final else None
    decision = r.verdict.decision if r.verdict else None
    ok = (want_action == "any" or action == want_action) and decision != "escalate" if want_decision != "escalate" else decision == "escalate"
    row = {
        "case": case, "persona": persona, "arch": arch, "strategy": strategy, "latency_s": latency,
        "proposed": r.plan.action if r.plan else None, "final": action, "vendor": final.vendor_id if final else None,
        "qty": final.quantity if final else None, "decision": decision,
        "rules": r.verdict.violated_rules if r.verdict else None, "checker": r.verdict.checker if r.verdict else None,
        "expected": want_action, "ok": ok, "degraded": r.degraded, "issues": r.forecast_issues,
        "retrieved": r.retrieved_doc_ids,
    }
    print(json.dumps(row), flush=True)
    return row


async def main():
    mode = sys.argv[1]
    rows = []
    if mode == "core":
        for case in CASES:
            for persona in ("plant", "retail_dc"):
                rows.append(await one(case, persona, "sequential", "react"))
    if mode == "variants":
        for case, persona in (("port_low", "retail_dc"), ("strike_high", "plant")):
            for arch in ("sequential", "hierarchical"):
                for strategy in ("react", "cot"):
                    rows.append(await one(case, persona, arch, strategy))
        pairs = {}
        for r in rows:
            if r["retrieved"]:
                pairs.setdefault((r["case"], r["persona"]), set()).add(tuple(r["retrieved"]))
        print("retrieval identical across variants:", all(len(v) == 1 for v in pairs.values()))
    print(f"correct {sum(r['ok'] for r in rows)}/{len(rows)}  degraded {sum(r['degraded'] for r in rows)}")


asyncio.run(main())
