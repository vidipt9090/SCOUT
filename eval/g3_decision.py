"""G3 check, Decision core: run against a fixture assessment and a live LLM. Run in the decision environment."""
import asyncio
import json
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from contracts import DisruptionAssessment  # noqa: E402
from decision.pipeline import run_decision  # noqa: E402
from decision.render import to_markdown  # noqa: E402

CASES = {
    "port_low": ("port_delay", 2, ["a.example", "b.example"], "FOODS_3_363"),
    "strike_medium": ("strike", 3, ["a.example", "b.example"], "HOBBIES_1_178"),
    "port_high": ("port_delay", 4, ["a.example", "b.example"], "FOODS_3_230"),
    "strike_high": ("strike", 4, ["a.example", "b.example"], "HOUSEHOLD_1_306"),
    "single_domain": ("port_delay", 4, ["a.example"], "FOODS_3_681"),
    "severity_5": ("port_delay", 5, ["a.example", "b.example"], "FOODS_2_059"),
}


def assessment(case: str, run_id: str) -> DisruptionAssessment:
    dtype, severity, domains, sku = CASES[case]
    return DisruptionAssessment(
        assessment_id=f"asm-{run_id}", disruption_type=dtype, severity=severity, severity_votes=[severity] * 3,
        vote_agreement=1.0, supporting_signal_ids=["sig-1"], corroborating_domains=domains, affected_skus=[sku],
        summary=f"{dtype} at severity {severity}.",
    )


async def main():
    case, persona, arch, strategy = sys.argv[1:5]
    run_id = f"g3-dec-{case.replace('_', '-')}-{int(time.time())}"
    a = assessment(case, run_id)
    start = time.perf_counter()
    result = await run_decision(a, a.affected_skus[0], persona, arch, strategy, run_id)
    print(f"{case} {persona} {arch} {strategy}: {time.perf_counter() - start:.1f}s degraded={result.degraded} issues={result.forecast_issues}")
    print("retrieved", json.dumps(result.retrieved_doc_ids))
    if result.plan and result.verdict:
        print("rationale:", result.plan.rationale)
        print(to_markdown(result.plan, result.verdict))
    elif result.verdict:
        print(result.verdict.model_dump_json())


if __name__ == "__main__":
    asyncio.run(main())
