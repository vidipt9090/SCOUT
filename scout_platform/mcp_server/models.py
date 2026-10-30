"""Return shapes for MCP tools. Every tool validates what it returns (safety layer 4)."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ToolModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SalesDay(ToolModel):
    date: str
    units: int = Field(ge=0)


class SalesHistory(ToolModel):
    sku: str
    days: list[SalesDay]


class Inventory(ToolModel):
    location: str
    sku: str
    on_hand: int = Field(ge=0)
    safety_floor_days: int = Field(ge=0)
    days_of_cover: float = Field(ge=0)
    avg_daily_demand_90d: float = Field(ge=0)


class Vendor(ToolModel):
    vendor_id: str
    role: Literal["primary", "alternate"]
    tier: int = Field(ge=1, le=3)
    lead_time_days: int = Field(gt=0)
    moq: int = Field(gt=0)
    penalty_pct: float = Field(ge=0)
    contract_id: str
    approved_contract: bool
    unit_cost_usd: float = Field(gt=0)
    plant_critical: bool


class VendorList(ToolModel):
    sku: str
    vendors: list[Vendor] = Field(min_length=1)


class PolicyRule(ToolModel):
    rule_id: str
    text: str


class PolicyLimits(ToolModel):
    persona: Literal["plant", "retail_dc"]
    currency: str
    po_approval_limit: float
    hard_constraint: dict[str, float]
    rules: list[PolicyRule]


class Forecast(ToolModel):
    sku: str
    baseline_daily_demand: float = Field(ge=0)
    revised_daily_demand: float = Field(ge=0)
    delta_pct: float
    multiplier: float = Field(gt=0)
    model_used: str
    horizon_days: int = Field(gt=0)
    disruption_horizon_days: int = Field(gt=0)


class RagHit(ToolModel):
    chunk_id: str
    doc_id: str
    doc_class: str
    text: str
    distance: float


class RagResults(ToolModel):
    query: str
    hits: list[RagHit]


class BlackboardEntry(ToolModel):
    entry_id: str
    ts: str
    run_id: str
    author: str
    topic: str
    payload: dict
    source_domain: str | None
    trust_level: Literal["trusted", "untrusted"]


class BlackboardPage(ToolModel):
    entries: list[BlackboardEntry]
    cursor: int = Field(ge=0)
