import json
from pathlib import Path

import pytest

from contracts import DisruptionAssessment, GuardrailVerdict, MitigationPlan
from decision.guardrail_rules import RuleContext, build_counter, check_rules
from decision.render import to_json, to_markdown

FIXTURES = Path(__file__).parent.parent / "contracts/fixtures"
VENDORS = [
    {"vendor_id": "V1", "role": "primary", "tier": 1, "lead_time_days": 7, "moq": 50, "approved_contract": True, "unit_cost_usd": 2.0, "plant_critical": True},
    {"vendor_id": "V2", "role": "alternate", "tier": 3, "lead_time_days": 8, "moq": 50, "approved_contract": True, "unit_cost_usd": 2.0, "plant_critical": True},
    {"vendor_id": "V3", "role": "alternate", "tier": 2, "lead_time_days": 12, "moq": 50, "approved_contract": True, "unit_cost_usd": 2.0, "plant_critical": True},
    {"vendor_id": "V4", "role": "alternate", "tier": 2, "lead_time_days": 25, "moq": 50, "approved_contract": True, "unit_cost_usd": 2.0, "plant_critical": True},
]
PEERS = {"peer_dc_1": {"on_hand": 1000, "avg_daily_demand_90d": 20}}


def ctx(**kw):
    base = dict(vendors=VENDORS, on_hand=100, avg_daily_demand=40, baseline_daily=40, revised_daily=48, horizon_days=21, peers=PEERS)
    return RuleContext(**{**base, **kw})


def assessment(severity=4, domains=("a.example", "b.example")):
    data = json.loads((FIXTURES / "DisruptionAssessment.json").read_text(encoding="utf-8"))
    return DisruptionAssessment.model_validate({**data, "severity": severity, "corroborating_domains": list(domains), "severity_votes": [severity]})


def plan(**kw):
    data = json.loads((FIXTURES / "MitigationPlan.json").read_text(encoding="utf-8"))
    base = {"action": "switch_supplier", "vendor_id": "V3", "quantity": 500.0, "persona": "plant"}
    return MitigationPlan.model_validate({**data, **base, **kw})


def rules(p, a=None, c=None):
    return {v.rule for v in check_rules(p, a or assessment(), c or ctx())}


def test_compliant_plan_passes():
    assert rules(plan()) == set()


def test_pol01_retail_quantity_above_cap():
    assert "POL-01" in rules(plan(persona="retail_dc", quantity=1000.0))


def test_pol02_plant_below_two_days():
    assert "POL-02" in rules(plan(action="reorder", vendor_id="V1", quantity=1.0), c=ctx(on_hand=50))
    assert "POL-02" not in rules(plan(action="monitor", vendor_id=None, quantity=None), c=ctx(on_hand=50))


def test_pol03_tier3_blocked_for_plant_critical_and_retail():
    assert "POL-03" in rules(plan(vendor_id="V2"))
    assert "POL-03" in rules(plan(vendor_id="V2", persona="retail_dc", quantity=100.0))


def test_pol04_over_finance_limit():
    assert "POL-04" in rules(plan(quantity=6000.0))


def test_pol05_lead_time_not_under_horizon_and_primary_is_not_alternate():
    assert "POL-05" in rules(plan(vendor_id="V4"))
    assert "POL-05" in rules(plan(vendor_id="V1"))


def test_pol06_transfer_rules():
    assert "POL-06" in rules(plan(action="stock_transfer", vendor_id="peer_dc_1"))
    retail = dict(action="stock_transfer", persona="retail_dc", vendor_id="peer_dc_1")
    assert rules(plan(**retail, quantity=500.0)) == set()
    assert "POL-06" in rules(plan(**retail, quantity=900.0))


def test_pol07_single_domain():
    assert "POL-07" in rules(plan(), assessment(domains=("a.example",)))
    assert "POL-07" not in rules(plan(action="monitor", vendor_id=None, quantity=None), assessment(domains=("a.example",)))


def test_pol09_severity_five():
    assert "POL-09" in rules(plan(), assessment(severity=5))


def test_unknown_vendor_and_low_moq():
    assert "VENDOR" in rules(plan(vendor_id="V99"))
    assert "CON-MOQ" in rules(plan(quantity=10.0))


def test_quantity_is_not_clamped_by_the_check():
    p = plan(persona="retail_dc", quantity=1000.0)
    check_rules(p, assessment(), ctx())
    assert p.quantity == 1000.0


@pytest.mark.parametrize(
    "kw,expected_vendor",
    [({"vendor_id": "V2"}, "V3"), ({"vendor_id": "V4"}, "V3"), ({"vendor_id": "V99"}, "V3")],
)
def test_counter_moves_to_compliant_vendor(kw, expected_vendor):
    p = plan(**kw)
    counter = build_counter(p, check_rules(p, assessment(), ctx()), assessment(), ctx())
    assert counter.vendor_id == expected_vendor and counter.plan_id.endswith("-counter")
    assert counter is not p and p.vendor_id == kw["vendor_id"]
    assert check_rules(counter, assessment(), ctx()) == []


def test_counter_cuts_retail_quantity_to_cap():
    p = plan(persona="retail_dc", quantity=1000.0)
    counter = build_counter(p, check_rules(p, assessment(), ctx()), assessment(), ctx())
    assert counter.quantity == 966.0


def test_counter_cuts_transfer_to_what_the_donor_can_spare():
    p = plan(action="stock_transfer", persona="retail_dc", vendor_id="peer_dc_1", quantity=900.0)
    counter = build_counter(p, check_rules(p, assessment(), ctx()), assessment(), ctx())
    assert counter.quantity == 800.0 and counter.vendor_id == "peer_dc_1"


def test_no_counter_for_plant_transfer():
    p = plan(action="stock_transfer", vendor_id="peer_dc_1")
    assert build_counter(p, check_rules(p, assessment(), ctx()), assessment(), ctx()) is None


def test_counter_for_single_domain_is_monitor():
    a = assessment(domains=("a.example",))
    p = plan()
    counter = build_counter(p, check_rules(p, a, ctx()), a, ctx())
    assert counter.action == "monitor" and counter.quantity is None and "POL-07" in counter.cited_doc_ids


def test_no_compliant_alternate_gives_no_counter():
    only_bad = [v for v in VENDORS if v["vendor_id"] in ("V1", "V2", "V4")]
    c = ctx(vendors=only_bad)
    p = plan(vendor_id="V2")
    assert build_counter(p, check_rules(p, assessment(), c), assessment(), c) is None


def test_render_outputs_json_and_table():
    p = plan()
    v = GuardrailVerdict(plan_id=p.plan_id, decision="approve", violated_rules=[], checker="none", counter_plan=None, reasons="ok")
    assert json.loads(to_json(p, v))["verdict"]["decision"] == "approve"
    assert "| Action | switch_supplier |" in to_markdown(p, v)
