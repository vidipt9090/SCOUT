"""Decision core agents. The same factories build both architectures, so only call order and delegation differ."""
import json
import os
from typing import AsyncGenerator, Literal

from google.adk.agents import BaseAgent, InvocationContext, LlmAgent
from google.adk.events import Event, EventActions
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.genai import types
from pydantic import BaseModel, Field

from contracts import DisruptionAssessment, ForecastResult, GuardrailVerdict, MitigationPlan
from decision import facts
from decision.callbacks import AGENT_CALLBACKS, writer_for
from decision.guardrail_rules import build_counter, check_rules
from scout_platform.blackboard import FORECAST_TOPIC, PLAN_TOPIC, VERDICT_TOPIC
from scout_platform.mcp_client import acall_tools
from scout_platform.prompts import prompt

MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8102/mcp")
PLANNER_ATTEMPTS = 2
ESCALATING_RULES = {"POL-04", "POL-09"}
UNSUPPORTED = "UNSUPPORTED-ACTION"  # the reviewer's finding when an action contradicts the cited procedure
PERSONA_TERMS = {"plant": ("safety", "2 day", "2-day", "two day", "floor"), "retail_dc": ("15%", "15 %", "baseline", "emergency")}
LLM_TIMEOUT_MS = 45_000
CONFIG = types.GenerateContentConfig(temperature=0, http_options=types.HttpOptions(timeout=LLM_TIMEOUT_MS))


class PlanDraft(BaseModel):
    """What the LLM decides. Code adds ids and cost to build the MitigationPlan."""

    reasoning: str
    binding_constraint: str
    action: Literal["reorder", "switch_supplier", "stock_transfer", "monitor"]
    vendor_id: str | None = None
    quantity: float | None = None
    rationale: str
    cited_doc_ids: list[str] = Field(min_length=1)


class Review(BaseModel):
    """Only what code cannot check. Numeric and vendor rules stay with the rule checker."""

    reasoning: str
    action_matches_procedure: bool
    obeys_embedded_command: bool


def _toolset(names: list[str]) -> McpToolset:
    return McpToolset(connection_params=StreamableHTTPConnectionParams(url=MCP_URL), tool_filter=names)


def _event(agent: BaseAgent, ctx: InvocationContext, text: str, delta: dict) -> Event:
    return Event(
        invocation_id=ctx.invocation_id,
        author=agent.name,
        actions=EventActions(state_delta=delta),
        content=types.Content(role="model", parts=[types.Part(text=text)]),
    )


async def _post(state, author: str, topic: str, payload: dict) -> None:
    """Share an intermediate result on the blackboard. In direct mode, framework state alone carries it."""
    if state.get("comm_mode") == "blackboard":
        await acall_tools(
            [("blackboard_write", {"run_id": state["run_id"], "author": author, "topic": topic, "payload": payload, "trust_level": "trusted"})]
        )


async def _latest(state, topic: str) -> dict | None:
    page = (await acall_tools([("blackboard_read", {"run_id": state["run_id"], "topic": topic})]))[0]
    return page["entries"][-1]["payload"] if page["entries"] else None


async def _check_forecast(callback_context):
    """The Oracle copies numbers from the forecast tool. A mismatch or generic interpretation is flagged, not repaired."""
    state = callback_context.state
    AGENT_CALLBACKS["after_agent_callback"](callback_context)
    tool, output = state.get("forecast_tool_result"), state.get("forecast_result")
    issues = []
    if not tool:
        issues.append("forecast tool not called")
    elif output:
        result = ForecastResult.model_validate(output)
        for name in ("baseline_daily_demand", "revised_daily_demand"):
            if abs(getattr(result, name) - tool[name]) > 0.01:
                issues.append(f"{name} differs from tool")
        text = result.interpretation.lower()
        if not any(term in text for term in PERSONA_TERMS[state["persona"]]):
            issues.append("generic interpretation")
    else:
        issues.append("no forecast output")
    state["forecast_issues"] = issues
    if issues:
        writer_for(state).event("demand_oracle", "guardrail", tool_name="layer5_output", error="; ".join(issues))
    if tool:
        await _post(state, "demand_oracle", FORECAST_TOPIC, tool)


def build_oracle() -> LlmAgent:
    callbacks = {**AGENT_CALLBACKS, "after_agent_callback": _check_forecast}
    return LlmAgent(
        name="demand_oracle",
        model=facts.adk_model(),
        description="Interprets demand for the affected SKU under the disruption.",
        instruction=prompt("oracle_v1"),
        tools=[_toolset(["forecast", "get_inventory", "get_sales_history"])],
        output_schema=ForecastResult,
        output_key="forecast_result",
        generate_content_config=CONFIG,
        **callbacks,
    )


class PlannerAgent(BaseAgent):
    """Fetches shared material, runs the chosen variant, and enforces citations. One retry, then degraded."""

    strategy: str
    inner: LlmAgent

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        assessment = DisruptionAssessment.model_validate_json(state["assessment_json"])
        persona, sku = state["persona"], state["sku"]
        hits = await facts.retrieve(assessment, persona, sku)
        retrieved_ids = list(dict.fromkeys(h["doc_id"] for h in hits))
        if state.get("comm_mode") == "blackboard":
            forecast = await _latest(state, FORECAST_TOPIC)
        else:
            forecast = state.get("forecast_tool_result")
        delta = {
            "retrieved_text": facts.format_hits(hits),
            "retrieved_doc_ids": retrieved_ids,
            "forecast_facts": json.dumps(forecast),
            "facts_text": await facts.planner_facts(persona, sku) if self.strategy == "cot" else "",
        }
        delta["planner_context"] = prompt("planner_context_v1").format(
            persona_context=state["persona_context"],
            assessment_json=state["assessment_json"],
            sku=sku,
            forecast_facts=delta["forecast_facts"],
            retrieved_text=delta["retrieved_text"],
            corroboration=facts.corroboration_status(assessment),
        )
        yield _event(self, ctx, "retrieved", delta)

        for attempt in range(1, PLANNER_ATTEMPTS + 1):
            try:
                async for event in self.inner.run_async(ctx):
                    yield event
            except Exception as e:  # prose instead of the schema, or a timed-out model call
                writer_for(state).event(self.name, "error", error=f"attempt {attempt}: {type(e).__name__}: {str(e)[:200]}")
                continue
            draft = ctx.session.state.get("plan_draft")
            cited = set((draft or {}).get("cited_doc_ids", []))
            if draft and cited and cited <= set(retrieved_ids):
                break
            bad = sorted(cited - set(retrieved_ids))
            writer_for(state).event(self.name, "guardrail", error=f"citation check failed on attempt {attempt}: {bad}")
            draft = None
        else:
            draft = None
        if draft is None:
            yield _event(self, ctx, "planner degraded", {"planner_degraded": True})
            return
        cost = await self._cost(draft, sku)
        plan = MitigationPlan(
            plan_id=f"plan-{state['run_id']}",
            assessment_id=assessment.assessment_id,
            persona=persona,
            action=draft["action"],
            sku=sku,
            vendor_id=draft.get("vendor_id"),
            quantity=draft.get("quantity"),
            rationale=draft["rationale"],
            cited_doc_ids=draft["cited_doc_ids"],
            estimated_cost=cost,
            strategy=self.strategy,
        )
        await _post(state, self.name, PLAN_TOPIC, plan.model_dump(mode="json"))
        yield _event(self, ctx, plan.model_dump_json(), {"plan_json": plan.model_dump_json()})

    @staticmethod
    async def _cost(draft: dict, sku: str) -> float | None:
        vendors = (await acall_tools([("lookup_vendor", {"sku": sku})]))[0]["vendors"]
        vendor = next((v for v in vendors if v["vendor_id"] == draft.get("vendor_id")), None)
        if vendor is None or draft.get("quantity") is None:
            return None
        return round(draft["quantity"] * vendor["unit_cost_usd"], 2)


def build_planner(strategy: str) -> PlannerAgent:
    if strategy == "react":
        inner = LlmAgent(
            name="planner_react",
            model=facts.adk_model(),
            instruction=prompt("planner_react_v1"),
            tools=[_toolset(["lookup_vendor", "get_inventory", "get_policy_limits"])],
            output_schema=PlanDraft,
            output_key="plan_draft",
            generate_content_config=CONFIG,
            **AGENT_CALLBACKS,
        )
    else:
        inner = LlmAgent(
            name="planner_cot",
            model=facts.adk_model(),
            instruction=prompt("planner_cot_v1"),
            output_schema=PlanDraft,
            output_key="plan_draft",
            generate_content_config=CONFIG,
            **AGENT_CALLBACKS,
        )
    return PlannerAgent(
        name="mitigation_planner",
        description="Proposes one mitigation action for the SKU.",
        strategy=strategy,
        inner=inner,
    )


class GuardrailAgent(BaseAgent):
    """Rule checker first, then an LLM review of the justification. At most one counter-plan."""

    reviewer: LlmAgent

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        writer = writer_for(state)
        assessment = DisruptionAssessment.model_validate_json(state["assessment_json"])
        if not state.get("plan_json"):
            verdict = GuardrailVerdict(
                plan_id=f"plan-{state['run_id']}", decision="escalate", violated_rules=[], checker="none",
                counter_plan=None, reasons="Planner produced no valid plan.",
            )
            yield _event(self, ctx, verdict.model_dump_json(), {"verdict_json": verdict.model_dump_json()})
            return
        plan = MitigationPlan.model_validate_json(state["plan_json"])
        rule_ctx = await facts.rule_context(assessment, plan.persona, plan.sku)
        violations = check_rules(plan, assessment, rule_ctx)
        rule_hits = [v.rule for v in violations]
        writer.event(self.name, "guardrail", tool_name="layer5_output", error=", ".join(rule_hits) or None)
        if {"POL-07", "POL-09"} & set(rule_hits):
            writer.event(self.name, "guardrail", tool_name="layer6_corroboration", error=", ".join(rule_hits))

        hits = await facts.retrieve(assessment, plan.persona, plan.sku)
        # The top procedure clause always goes to the reviewer, so a plan cannot hide it by not citing it.
        cited = [hits[0], *(h for h in hits[1:] if h["doc_id"] in plan.cited_doc_ids)]
        delta = {"cited_text": facts.format_hits(cited)}
        yield _event(self, ctx, "rules checked", delta)
        async for event in self.reviewer.run_async(ctx):
            yield event
        review = ctx.session.state.get("guardrail_review") or {}
        llm_hits = []
        if review.get("obeys_embedded_command"):
            llm_hits.append("POL-08")
        if not review.get("action_matches_procedure", True) and assessment.severity < 5 and not rule_hits:
            llm_hits.append(UNSUPPORTED)
        all_hits = rule_hits + llm_hits
        checker = {(True, True): "both", (True, False): "rules", (False, True): "llm", (False, False): "none"}[
            (bool(rule_hits), bool(llm_hits))
        ]
        if all_hits:
            reasons = "; ".join(v.detail for v in violations) or review.get("reasoning", "")
        else:
            reasons = "No policy violation found."
        counter = None
        if not all_hits:
            decision = "approve"
        elif ESCALATING_RULES & set(all_hits) or llm_hits:
            decision = "escalate"
        else:
            counter = build_counter(plan, violations, assessment, rule_ctx)
            decision = "counter" if counter else "escalate"
        verdict = GuardrailVerdict(
            plan_id=plan.plan_id, decision=decision, violated_rules=all_hits, checker=checker,
            counter_plan=counter, reasons=reasons,
        )
        writer.event(self.name, "guardrail", tool_name="verdict", payload_ref=decision)
        await _post(state, self.name, VERDICT_TOPIC, verdict.model_dump(mode="json"))
        yield _event(self, ctx, verdict.model_dump_json(), {"verdict_json": verdict.model_dump_json()})


def build_guardrail() -> GuardrailAgent:
    reviewer = LlmAgent(
        name="guardrail_review",
        model=facts.adk_model(),
        instruction=prompt("guardrail_v1"),
        output_schema=Review,
        output_key="guardrail_review",
        generate_content_config=CONFIG,
        **AGENT_CALLBACKS,
    )
    return GuardrailAgent(
        name="guardrail",
        description="Validates the plan against policy and returns a verdict.",
        reviewer=reviewer,
    )
