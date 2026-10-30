"""Render the final result as JSON and a Markdown table (Requirement 3)."""
import json

from contracts import GuardrailVerdict, MitigationPlan


def final_plan(plan: MitigationPlan, verdict: GuardrailVerdict) -> MitigationPlan:
    return verdict.counter_plan or plan


def to_json(plan: MitigationPlan, verdict: GuardrailVerdict) -> str:
    return json.dumps(
        {"proposed_plan": plan.model_dump(mode="json"), "verdict": verdict.model_dump(mode="json")},
        indent=2,
    )


def to_markdown(plan: MitigationPlan, verdict: GuardrailVerdict) -> str:
    chosen = final_plan(plan, verdict)
    rows = [
        ("Decision", verdict.decision),
        ("Persona", chosen.persona),
        ("SKU", chosen.sku),
        ("Action", chosen.action),
        ("Vendor or donor", chosen.vendor_id or "none"),
        ("Quantity", "none" if chosen.quantity is None else f"{chosen.quantity:g}"),
        ("Estimated cost", "none" if chosen.estimated_cost is None else f"{chosen.estimated_cost:.2f} USD"),
        ("Rules violated", ", ".join(verdict.violated_rules) or "none"),
        ("Checker", verdict.checker),
        ("Cited documents", ", ".join(chosen.cited_doc_ids)),
        ("Reasons", verdict.reasons.replace("|", "/")),
    ]
    return "\n".join(["| Field | Value |", "|---|---|", *(f"| {k} | {v} |" for k, v in rows)])
