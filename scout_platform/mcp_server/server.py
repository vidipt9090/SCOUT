"""SCOUT MCP server. Stateless: every call reads files or the services, and validates what it returns."""
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import httpx
import pandas as pd
import yaml
from mcp.server.fastmcp import FastMCP

from data.rag.retrieve import collection, search
from scout_platform.mcp_server.models import (
    BlackboardEntry,
    BlackboardPage,
    Forecast,
    Inventory,
    PolicyLimits,
    PolicyRule,
    RagResults,
    SalesDay,
    SalesHistory,
    Vendor,
    VendorList,
)

ROOT = Path(__file__).parents[2]
BLACKBOARD_URL = os.environ.get("BLACKBOARD_URL", "http://127.0.0.1:8101")
RECENT_DAYS = 90
MAX_HISTORY_DAYS = 1095
LOCATIONS = ("plant", "retail_dc", "peer_dc_1", "peer_dc_2")

mcp = FastMCP("scout", host="127.0.0.1", port=int(os.environ.get("MCP_PORT", "8102")))


def _yaml(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def _sales() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data/m5/derived/sales.csv")


def _check_sku(sales: pd.DataFrame, sku: str) -> None:
    if sku not in set(sales["sku"]):
        raise ValueError(f"unknown sku: {sku!r}")


@lru_cache(maxsize=1)
def _rag_collection():
    return collection()


@mcp.tool()
def get_sales_history(sku: str, days: int) -> SalesHistory:
    """Daily unit sales for a SKU, most recent `days` days, up to simulated today."""
    if not 1 <= days <= MAX_HISTORY_DAYS:
        raise ValueError(f"days must be 1..{MAX_HISTORY_DAYS}")
    sales = _sales()
    _check_sku(sales, sku)
    rows = sales[sales["sku"] == sku].sort_values("date").tail(days)
    return SalesHistory(
        sku=sku,
        days=[SalesDay(date=r.date, units=int(r.units)) for r in rows.itertuples()],
    )


@mcp.tool()
def get_inventory(sku: str, location: Literal["plant", "retail_dc", "peer_dc_1", "peer_dc_2"]) -> Inventory:
    """Stock on hand, safety floor and days of cover for a SKU at a location."""
    if location not in LOCATIONS:
        raise ValueError(f"unknown location: {location!r}")
    sales = _sales()
    _check_sku(sales, sku)
    inventory = pd.read_csv(ROOT / "data/synth/inventory.csv")
    row = inventory[(inventory["sku"] == sku) & (inventory["location"] == location)].iloc[0]
    daily = float(sales[sales["sku"] == sku].sort_values("date").tail(RECENT_DAYS)["units"].mean())
    return Inventory(
        location=location,
        sku=sku,
        on_hand=int(row["on_hand"]),
        safety_floor_days=int(row["safety_floor_days"]),
        days_of_cover=round(float(row["on_hand"]) / daily, 2),
        avg_daily_demand_90d=round(daily, 2),
    )


@mcp.tool()
def lookup_vendor(sku: str) -> VendorList:
    """All vendors for a SKU, with tier, lead time, MOQ, penalty, contract and unit cost."""
    vendors = pd.read_csv(ROOT / "data/synth/vendors.csv")
    rows = vendors[vendors["sku"] == sku].drop(columns="sku")
    if rows.empty:
        raise ValueError(f"unknown sku: {sku!r}")
    return VendorList(sku=sku, vendors=[Vendor(**r) for r in rows.to_dict("records")])


@mcp.tool()
def get_policy_limits(persona: Literal["plant", "retail_dc"]) -> PolicyLimits:
    """Policy rules and hard limits that apply to a persona."""
    if persona not in ("plant", "retail_dc"):
        raise ValueError(f"unknown persona: {persona!r}")
    policy = _yaml("configs/policy.yaml")
    profile = _yaml(f"configs/personas/{persona}.yaml")
    rules = [
        PolicyRule(rule_id=rule_id, text=rule["text"])
        for rule_id, rule in policy["rules"].items()
        if rule.get("persona", persona) == persona
    ]
    return PolicyLimits(
        persona=persona,
        currency=policy["CURRENCY"],
        po_approval_limit=policy["PO_APPROVAL_LIMIT"],
        hard_constraint=profile["hard_constraint"],
        rules=rules,
    )


@mcp.tool()
def forecast(
    sku: str,
    horizon_days: int,
    disruption_type: Literal["port_delay", "strike", "weather"],
    severity: int,
) -> Forecast:
    """Cached baseline demand, revised by the configured severity multiplier. The numbers are not LLM-made."""
    if not 1 <= severity <= 5:
        raise ValueError("severity must be 1..5")
    if not 1 <= horizon_days <= 30:
        raise ValueError("horizon_days must be 1..30")
    effects = _yaml("configs/disruption_effects.yaml")
    if disruption_type not in effects["demand_multiplier"]:
        raise ValueError(f"unknown disruption_type: {disruption_type!r}")
    baselines = json.loads((ROOT / "data/forecasting/baselines.json").read_text(encoding="utf-8"))
    if sku not in baselines:
        raise ValueError(f"unknown sku: {sku!r}")
    entry = baselines[sku]
    baseline = sum(entry["daily_forecast"][:horizon_days]) / horizon_days
    multiplier = effects["demand_multiplier"][disruption_type][severity]
    return Forecast(
        sku=sku,
        baseline_daily_demand=round(baseline, 3),
        revised_daily_demand=round(baseline * multiplier, 3),
        delta_pct=round((multiplier - 1) * 100, 2),
        multiplier=multiplier,
        model_used=entry["model"],
        horizon_days=horizon_days,
        disruption_horizon_days=effects["horizon_days"][severity],
    )


@mcp.tool()
def rag_search(query: str, persona: Literal["plant", "retail_dc"], sku: str, k: int = 5) -> RagResults:
    """Search contracts, SOPs and policy, filtered to the persona and SKU before similarity."""
    if persona not in ("plant", "retail_dc"):
        raise ValueError(f"unknown persona: {persona!r}")
    if not 1 <= k <= 10:
        raise ValueError("k must be 1..10")
    return RagResults(query=query, hits=search(_rag_collection(), query, persona, sku, k))


@mcp.tool()
def blackboard_write(
    run_id: str,
    author: str,
    topic: str,
    payload: dict[str, Any],
    trust_level: Literal["trusted", "untrusted"],
    source_domain: str | None = None,
) -> BlackboardEntry:
    """Append one entry to the run's blackboard and return the stored entry."""
    resp = httpx.post(
        f"{BLACKBOARD_URL}/write",
        json={
            "run_id": run_id,
            "author": author,
            "topic": topic,
            "payload": payload,
            "trust_level": trust_level,
            "source_domain": source_domain,
        },
    )
    resp.raise_for_status()
    return BlackboardEntry.model_validate(resp.json())


@mcp.tool()
def blackboard_read(run_id: str, topic: str, cursor: int = 0) -> BlackboardPage:
    """Read a run's blackboard entries on a topic since a cursor."""
    resp = httpx.get(f"{BLACKBOARD_URL}/read", params={"run_id": run_id, "topic": topic, "cursor": cursor})
    resp.raise_for_status()
    return BlackboardPage.model_validate(resp.json())


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
