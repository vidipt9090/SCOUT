"""Deterministic policy checks and counter-plans. Pure functions, so every rule is testable without an LLM.

Baseline volume for POL-01 is defined as baseline daily demand x disruption horizon. MOQ is a contract term, so a
breach is reported as CON-MOQ rather than a POL id.
"""
import math
from dataclasses import dataclass, field

from contracts import DisruptionAssessment, MitigationPlan

REPAIRABLE_BY_VENDOR = {"POL-03", "POL-05", "VENDOR"}
RULE_IDS = tuple(f"POL-{i:02d}" for i in range(1, 10))


@dataclass(frozen=True)
class RuleContext:
    vendors: list[dict]
    on_hand: float
    avg_daily_demand: float
    baseline_daily: float
    revised_daily: float
    horizon_days: int
    peers: dict[str, dict] = field(default_factory=dict)  # peer DC name -> get_inventory result
    po_limit: float = 10000
    max_over_baseline_pct: float = 15
    min_days_of_supply: float = 2
    min_donor_cover_days: float = 10
    min_domains: int = 2


@dataclass(frozen=True)
class Violation:
    rule: str
    detail: str


def _vendor(ctx: RuleContext, vendor_id: str | None) -> dict | None:
    return next((v for v in ctx.vendors if v["vendor_id"] == vendor_id), None)


def _retail_cap(ctx: RuleContext) -> float:
    return ctx.baseline_daily * ctx.horizon_days * (100 + ctx.max_over_baseline_pct) / 100


def _check_vendor_action(plan: MitigationPlan, ctx: RuleContext) -> list[Violation]:
    found = []
    vendor = _vendor(ctx, plan.vendor_id)
    if vendor is None:
        return [Violation("VENDOR", f"{plan.vendor_id} does not supply {plan.sku}")]
    quantity = plan.quantity or 0
    if vendor["tier"] == 3 and (plan.persona == "retail_dc" or vendor["plant_critical"]):
        found.append(Violation("POL-03", f"Tier 3 vendor {vendor['vendor_id']} not allowed here"))
    if quantity * vendor["unit_cost_usd"] > ctx.po_limit:
        found.append(Violation("POL-04", f"order value above {ctx.po_limit}"))
    if plan.action == "switch_supplier":
        if vendor["role"] != "alternate":
            found.append(Violation("POL-05", f"{vendor['vendor_id']} is not an alternate"))
        elif not vendor["approved_contract"]:
            found.append(Violation("POL-05", "contract not approved"))
        elif vendor["lead_time_days"] >= ctx.horizon_days:
            found.append(Violation("POL-05", f"lead time {vendor['lead_time_days']} not under horizon {ctx.horizon_days}"))
    if quantity < vendor["moq"]:
        found.append(Violation("CON-MOQ", f"quantity {quantity} below MOQ {vendor['moq']}"))
    return found


def _check_transfer(plan: MitigationPlan, ctx: RuleContext) -> list[Violation]:
    if plan.persona == "plant":
        return [Violation("POL-06", "stock transfer is not available to Plant")]
    donor = ctx.peers.get(plan.vendor_id or "")
    if donor is None:
        return [Violation("POL-06", f"{plan.vendor_id} is not a peer DC")]
    left = (donor["on_hand"] - (plan.quantity or 0)) / donor["avg_daily_demand_90d"]
    if left < ctx.min_donor_cover_days:
        return [Violation("POL-06", f"donor left with {left:.1f} days of cover")]
    return []


def check_rules(plan: MitigationPlan, assessment: DisruptionAssessment, ctx: RuleContext) -> list[Violation]:
    """POL-08 needs judgement, so the LLM reviewer handles it."""
    found = []
    if assessment.severity == 5:
        found.append(Violation("POL-09", "severity 5 always goes to a human"))
    if assessment.severity >= 4 and len(assessment.corroborating_domains) < ctx.min_domains and plan.action != "monitor":
        found.append(Violation("POL-07", f"{len(assessment.corroborating_domains)} source domain at severity {assessment.severity}"))
    if plan.action in ("reorder", "switch_supplier"):
        found += _check_vendor_action(plan, ctx)
    if plan.action == "stock_transfer":
        found += _check_transfer(plan, ctx)
    quantity = plan.quantity or 0
    if plan.persona == "retail_dc" and plan.action in ("reorder", "switch_supplier") and quantity > _retail_cap(ctx):
        found.append(Violation("POL-01", f"quantity {quantity} above cap {_retail_cap(ctx):.0f}"))
    if plan.persona == "plant" and plan.action != "monitor" and ctx.revised_daily > 0:
        supply = (ctx.on_hand + quantity) / ctx.revised_daily
        if supply < ctx.min_days_of_supply:
            found.append(Violation("POL-02", f"{supply:.1f} days of supply"))
    return found


def _citing(plan: MitigationPlan, *rules: str) -> list[str]:
    return list(dict.fromkeys([*plan.cited_doc_ids, *(r for r in rules if r in RULE_IDS)]))


def _repair(plan: MitigationPlan, v: Violation, assessment: DisruptionAssessment, ctx: RuleContext) -> MitigationPlan | None:
    cited = _citing(plan, v.rule)
    if v.rule == "POL-07":
        return plan.model_copy(update={"action": "monitor", "vendor_id": None, "quantity": None, "estimated_cost": 0.0, "cited_doc_ids": cited})
    if v.rule in REPAIRABLE_BY_VENDOR:
        options = [
            o for o in ctx.vendors
            if o["role"] == "alternate" and o["tier"] <= 2 and o["approved_contract"] and o["lead_time_days"] < ctx.horizon_days
        ]
        if not options:
            return None
        best = min(options, key=lambda o: (o["lead_time_days"], o["vendor_id"]))
        return plan.model_copy(update={"action": "switch_supplier", "vendor_id": best["vendor_id"], "cited_doc_ids": cited})
    if v.rule == "POL-01":
        return plan.model_copy(update={"quantity": float(math.floor(_retail_cap(ctx))), "cited_doc_ids": cited})
    if v.rule == "POL-02":
        needed = math.ceil(ctx.min_days_of_supply * ctx.revised_daily - ctx.on_hand)
        return plan.model_copy(update={"quantity": float(needed), "cited_doc_ids": cited})
    if v.rule == "POL-06":
        if plan.persona == "plant" or not ctx.peers:
            return None
        spare = {
            name: p["on_hand"] - ctx.min_donor_cover_days * p["avg_daily_demand_90d"] for name, p in ctx.peers.items()
        }
        donor = max(sorted(spare), key=spare.get)
        if spare[donor] < 1:
            return None
        quantity = min(plan.quantity or spare[donor], float(math.floor(spare[donor])))
        return plan.model_copy(update={"vendor_id": donor, "quantity": quantity, "cited_doc_ids": cited})
    if v.rule == "CON-MOQ":
        vendor = _vendor(ctx, plan.vendor_id)
        return plan.model_copy(update={"quantity": float(vendor["moq"]), "cited_doc_ids": cited})
    return None


def build_counter(plan: MitigationPlan, violations: list[Violation], assessment: DisruptionAssessment, ctx: RuleContext) -> MitigationPlan | None:
    """One revision round, producing a new object. None means no compliant plan was found, so a human decides."""
    current = plan
    for v in violations:
        current = _repair(current, v, assessment, ctx)
        if current is None:
            return None
    vendor = _vendor(ctx, current.vendor_id)
    cost = round((current.quantity or 0) * vendor["unit_cost_usd"], 2) if vendor else 0.0
    current = current.model_copy(update={"plan_id": f"{plan.plan_id}-counter", "estimated_cost": cost})
    return None if check_rules(current, assessment, ctx) else current
