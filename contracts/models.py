"""Frozen data contracts shared by the Sensing crew, Decision core and platform.

Models are immutable: a change produces a new object. Validation failures
raise; nothing here coerces a bad value into a valid one.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class Signal(Contract):
    signal_id: str
    source_domain: str
    headline: str
    snippet: str  # HTML stripped, length capped
    published_at: datetime
    is_relevant: bool
    disruption_type: Literal["port_delay", "strike", "weather", "none"]
    confidence: float = Field(ge=0, le=1)
    reasoning: str  # CoT text, kept for provenance
    scout_id: Literal["A", "B"]


class DisruptionAssessment(Contract):
    assessment_id: str
    disruption_type: Literal["port_delay", "strike", "weather"]
    severity: int = Field(ge=1, le=5)
    severity_votes: list[int] = Field(min_length=1)
    vote_agreement: float = Field(ge=0, le=1)  # 1.0 = unanimous
    supporting_signal_ids: list[str]
    corroborating_domains: list[str]
    affected_skus: list[str]
    summary: str

    @model_validator(mode="after")
    def votes_in_range(self):
        if any(v < 1 or v > 5 for v in self.severity_votes):
            raise ValueError("severity_votes must all be 1..5")
        return self


class ForecastResult(Contract):
    assessment_id: str
    sku: str
    baseline_daily_demand: float = Field(ge=0)
    revised_daily_demand: float = Field(ge=0)
    delta_pct: float
    model_used: str
    horizon_days: int = Field(gt=0)
    interpretation: str  # must reference a persona constraint


class MitigationPlan(Contract):
    plan_id: str
    assessment_id: str
    persona: Literal["plant", "retail_dc"]
    action: Literal["reorder", "switch_supplier", "stock_transfer", "monitor"]
    sku: str
    vendor_id: str | None
    quantity: float | None
    rationale: str
    cited_doc_ids: list[str] = Field(min_length=1)
    estimated_cost: float | None
    strategy: Literal["react", "cot"]


class GuardrailVerdict(Contract):
    plan_id: str
    decision: Literal["approve", "counter", "escalate"]
    violated_rules: list[str]  # POL ids
    checker: Literal["rules", "llm", "both", "none"]
    counter_plan: MitigationPlan | None
    reasons: str

    @model_validator(mode="after")
    def counter_needs_plan(self):
        if (self.decision == "counter") != (self.counter_plan is not None):
            raise ValueError("counter_plan is required for 'counter' and only for 'counter'")
        return self


class RunRecord(Contract):
    run_id: str
    condition: dict  # every factor level, including prompt versions
    started_at: datetime
    ended_at: datetime
    total_latency_s: float = Field(ge=0)
    per_agent_latency_s: dict[str, float]
    tokens_in: int | None
    tokens_out: int | None
    estimated_cost: float | None
    outcome: str
    degraded: bool
    trace_path: str


ALL_MODELS = (
    Signal,
    DisruptionAssessment,
    ForecastResult,
    MitigationPlan,
    GuardrailVerdict,
    RunRecord,
)
