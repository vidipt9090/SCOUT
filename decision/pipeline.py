"""Run the Decision core under either architecture. Sequential fixes the order; hierarchical lets a coordinator delegate."""
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools import AgentTool
from google.genai import types
from pydantic import BaseModel, ConfigDict

from contracts import DisruptionAssessment, ForecastResult, GuardrailVerdict, MitigationPlan
from decision import facts
from decision.agents import CONFIG, build_guardrail, build_oracle, build_planner
from decision.callbacks import AGENT_CALLBACKS
from scout_platform.prompts import prompt
from scout_platform.tracing.writer import TraceWriter

APP = "scout_decision"


class DecisionResult(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    forecast: ForecastResult | None
    forecast_issues: list[str]
    plan: MitigationPlan | None
    verdict: GuardrailVerdict | None
    retrieved_doc_ids: list[str]
    degraded: bool


def build_root(architecture: str, strategy: str):
    agents = [build_oracle(), build_planner(strategy), build_guardrail()]
    if architecture == "sequential":
        return SequentialAgent(name="decision_core", sub_agents=agents)
    return LlmAgent(
        name="coordinator",
        model=facts.adk_model(),
        instruction=prompt("coordinator_v1"),
        tools=[AgentTool(agent=a, skip_summarization=False) for a in agents],
        generate_content_config=CONFIG,
        **AGENT_CALLBACKS,
    )


async def run_decision(
    assessment: DisruptionAssessment, sku: str, persona: str, architecture: str, strategy: str, run_id: str
) -> DecisionResult:
    root = build_root(architecture, strategy)
    runner = InMemoryRunner(agent=root, app_name=APP)
    state = {
        "run_id": run_id,
        "persona": persona,
        "persona_context": facts.persona_context(persona),
        "assessment_json": assessment.model_dump_json(),
        "sku": sku,
        "prompt_versions": {
            "demand_oracle": "oracle_v1",
            "planner_react": "planner_react_v1",
            "planner_cot": "planner_cot_v1",
            "guardrail_review": "guardrail_v1",
            "coordinator": "coordinator_v1",
        },
    }
    session = await runner.session_service.create_session(app_name=APP, user_id="scout", state=state)
    message = types.Content(role="user", parts=[types.Part(text="A disruption assessment is ready. Proceed.")])
    try:
        try:
            async for _ in runner.run_async(user_id="scout", session_id=session.id, new_message=message):
                pass
        except Exception as e:  # a failed agent gives a degraded record and the pilot continues
            TraceWriter(run_id, "adk").event("decision_core", "error", error=f"{type(e).__name__}: {str(e)[:500]}")
        final = await runner.session_service.get_session(app_name=APP, user_id="scout", session_id=session.id)
    finally:
        await runner.close()
    s = final.state
    forecast = s.get("forecast_result")
    plan, verdict = s.get("plan_json"), s.get("verdict_json")
    issues = s.get("forecast_issues", [])
    return DecisionResult(
        forecast=ForecastResult.model_validate(forecast) if forecast else None,
        forecast_issues=issues,
        plan=MitigationPlan.model_validate_json(plan) if plan else None,
        verdict=GuardrailVerdict.model_validate_json(verdict) if verdict else None,
        retrieved_doc_ids=s.get("retrieved_doc_ids", []),
        degraded=bool(issues) or not plan or not verdict or bool(s.get("planner_degraded")),
    )
