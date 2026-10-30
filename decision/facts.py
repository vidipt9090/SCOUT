"""Facts fetched by code through MCP. Both Planner variants share this, so retrieval is identical between them."""
import json
from pathlib import Path

import yaml
from google.adk.models import Gemini
from google.genai import types

from contracts import DisruptionAssessment
from decision.guardrail_rules import RuleContext
from scout_platform.mcp_client import acall_tools

ROOT = Path(__file__).parents[1]
TYPE_NAMES = {"port_delay": "a port delay", "strike": "a labour strike", "weather": "a weather disruption"}
PERSONA_NAMES = {"plant": "Plant", "retail_dc": "Retail DC"}
PEERS = ("peer_dc_1", "peer_dc_2")
VENDOR_QUERY = "lead time, minimum order quantity, penalty and contract status"
PROCEDURE_K = 5
VENDOR_K = 3


def _yaml(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def persona_context(persona: str) -> str:
    p = _yaml(f"configs/personas/{persona}.yaml")
    return (
        f"{p['persona']}: {p['profile']} Risk tolerance {p['risk_tolerance']}. Stockout cost {p['stockout_cost']}. "
        f"Hard constraint {p['hard_constraint']}. {p['soft_constraint']}."
    )


def procedure_query(assessment: DisruptionAssessment, persona: str) -> str:
    return f"{PERSONA_NAMES[persona]} procedure for {TYPE_NAMES[assessment.disruption_type]} at severity {assessment.severity}"


async def retrieve(assessment: DisruptionAssessment, persona: str, sku: str) -> list[dict]:
    """Fixed retrieval: the procedure clauses, then the SKU's agreements. No LLM chooses these queries."""
    procedure, vendor, limits = await acall_tools(
        [
            ("rag_search", {"query": procedure_query(assessment, persona), "persona": persona, "sku": sku, "k": PROCEDURE_K}),
            ("rag_search", {"query": VENDOR_QUERY, "persona": persona, "sku": sku, "k": VENDOR_K}),
            ("get_policy_limits", {"persona": persona}),
        ]
    )
    # Policy rules are always in scope, so they count as retrieved and may be cited.
    rules = [{"chunk_id": f"{r['rule_id']}#c1", "doc_id": r["rule_id"], "text": r["text"]} for r in limits["rules"]]
    hits = {h["chunk_id"]: h for h in [*procedure["hits"], *vendor["hits"], *rules]}
    return list(hits.values())


def format_hits(hits: list[dict]) -> str:
    """The first hit is the top-ranked procedure clause, and is marked as the best match."""
    lines = [f"[{h['doc_id']}] {h['text']}" for h in hits]
    return "\n".join([f"Best match: {lines[0]}", "Other documents:", *lines[1:]] if lines else [])


async def planner_facts(persona: str, sku: str) -> str:
    """Tool results handed to the CoT Planner in one block, because it has no action loop."""
    vendors, inventory, limits = await acall_tools(
        [
            ("lookup_vendor", {"sku": sku}),
            ("get_inventory", {"sku": sku, "location": persona}),
            ("get_policy_limits", {"persona": persona}),
        ]
    )
    return json.dumps({"vendors": vendors["vendors"], "inventory": inventory, "policy": limits})


async def rule_context(assessment: DisruptionAssessment, persona: str, sku: str) -> RuleContext:
    """Everything the Guardrail checks against, fetched fresh rather than trusted from the Planner."""
    effects = _yaml("configs/disruption_effects.yaml")
    policy = _yaml("configs/policy.yaml")
    horizon = effects["horizon_days"][assessment.severity]
    vendors, inventory, forecast, peer_1, peer_2 = await acall_tools(
        [
            ("lookup_vendor", {"sku": sku}),
            ("get_inventory", {"sku": sku, "location": persona}),
            (
                "forecast",
                {
                    "sku": sku,
                    "location": persona,
                    "horizon_days": horizon,
                    "disruption_type": assessment.disruption_type,
                    "severity": assessment.severity,
                },
            ),
            ("get_inventory", {"sku": sku, "location": PEERS[0]}),
            ("get_inventory", {"sku": sku, "location": PEERS[1]}),
        ]
    )
    rules = policy["rules"]
    return RuleContext(
        vendors=vendors["vendors"],
        on_hand=inventory["on_hand"],
        avg_daily_demand=inventory["avg_daily_demand_90d"],
        baseline_daily=forecast["baseline_daily_demand"],
        revised_daily=forecast["revised_daily_demand"],
        horizon_days=horizon,
        peers={PEERS[0]: peer_1, PEERS[1]: peer_2},
        po_limit=policy["PO_APPROVAL_LIMIT"],
        max_over_baseline_pct=rules["POL-01"]["max_over_baseline_pct"],
        min_days_of_supply=rules["POL-02"]["min_days_of_supply"],
        min_donor_cover_days=rules["POL-06"]["min_donor_cover_days"],
        min_domains=rules["POL-07"]["min_domains"],
    )


def policy_text() -> str:
    return "\n".join(f"{k}: {v['text']}" for k, v in _yaml("configs/policy.yaml")["rules"].items())


def adk_model() -> Gemini:
    retries = types.HttpRetryOptions(attempts=4, initial_delay=5, exp_base=2, http_status_codes=[429, 500, 503])
    return Gemini(model=_yaml("configs/llm.yaml")["adk_model"], retry_options=retries)


def corroboration_status(assessment: DisruptionAssessment) -> str:
    """Computed here so the model never has to count domains."""
    if assessment.severity < 4:
        return "not required at this severity"
    if len(assessment.corroborating_domains) >= 2:
        return "met"
    return "NOT met: choose monitor and cite the corroboration rule"
