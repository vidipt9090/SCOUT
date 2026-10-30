"""ADK callbacks: shared trace events, tool caps, and capture of what tools really returned."""
import json
from typing import Any

from scout_platform.rate_limit import await_slot
from scout_platform.tool_guard import check_tool_call, check_tool_result
from scout_platform.tracing.writer import TraceWriter

SYNTHETIC_TOOL = "set_model_response"  # ADK's own tool for structured output, not one of ours
TOOL_CAPS = {"demand_oracle": 3, "planner_react": 4}
_writers: dict[str, TraceWriter] = {}


def writer_for(state) -> TraceWriter:
    run_id = state["run_id"]
    if run_id not in _writers:
        _writers[run_id] = TraceWriter(run_id, "adk")
    return _writers[run_id]


def _prompt_version(state, agent: str) -> str | None:
    return state.get("prompt_versions", {}).get(agent)


def before_agent(callback_context):
    writer_for(callback_context.state).event(callback_context.agent_name, "agent_start")


def after_agent(callback_context):
    writer_for(callback_context.state).event(callback_context.agent_name, "agent_end")


async def before_model(callback_context, llm_request):
    state = callback_context.state
    agent = callback_context.agent_name
    waited = await await_slot()
    if waited:
        writer_for(state).event(agent, "rate_wait", payload_ref=f"{waited:.1f}")
    writer_for(state).event(agent, "model_start", prompt_version=_prompt_version(state, agent))


def after_model(callback_context, llm_response):
    usage = llm_response.usage_metadata
    state = callback_context.state
    agent = callback_context.agent_name
    writer_for(state).event(
        agent,
        "model_end",
        tokens_in=usage.prompt_token_count if usage else None,
        tokens_out=usage.candidates_token_count if usage else None,
        prompt_version=_prompt_version(state, agent),
        error=llm_response.error_message,
    )


def on_model_error(callback_context, llm_request, error):
    writer_for(callback_context.state).event(callback_context.agent_name, "error", error=str(error)[:500])


def before_tool(tool, args: dict[str, Any], tool_context):
    if tool.name == SYNTHETIC_TOOL:
        return None
    state = tool_context.state
    agent = tool_context.agent_name
    writer_for(state).event(agent, "tool_start", tool_name=tool.name, args=args)
    reason = check_tool_call(agent, tool.name, args, state["sku"], state["persona"], json.loads(state["assessment_json"]))
    if reason:
        writer_for(state).event(agent, "guardrail", tool_name="layer3_before_tool", args=args, error=reason)
        return {"error": f"Blocked: {reason}."}
    cap = TOOL_CAPS.get(agent)
    if cap is None:
        return None
    key = f"tool_calls_{agent}"
    used = state.get(key, 0)
    if used >= cap:
        writer_for(state).event(agent, "guardrail", tool_name=tool.name, error=f"tool cap {cap} reached")
        return {"error": f"Tool limit of {cap} reached. Answer now with what you have."}
    state[key] = used + 1
    return None


def after_tool(tool, args: dict[str, Any], tool_context, tool_response):
    if tool.name == SYNTHETIC_TOOL:
        return None
    state = tool_context.state
    writer_for(state).event(tool_context.agent_name, "tool_end", tool_name=tool.name)
    if not isinstance(tool_response, dict) or "error" in tool_response:  # a specialist's text, or a refusal
        return None
    structured = tool_response.get("structuredContent")
    reason = check_tool_result(tool.name, structured)
    if reason:
        writer_for(state).event(tool_context.agent_name, "guardrail", tool_name="layer4_after_tool", error=reason)
        return {"error": f"Rejected: {reason}."}
    if tool.name == "forecast":
        state["forecast_tool_result"] = structured
    return None


def on_tool_error(tool, args: dict[str, Any], tool_context, error):
    """Return the failure to the model, which can correct itself. A malformed output must not end the run."""
    writer_for(tool_context.state).event(tool_context.agent_name, "error", tool_name=tool.name, error=str(error)[:500])
    return {"error": f"The call failed: {str(error)[:300]}. Correct it and call {tool.name} again with all required fields."}


AGENT_CALLBACKS = {
    "before_agent_callback": before_agent,
    "after_agent_callback": after_agent,
    "before_model_callback": before_model,
    "after_model_callback": after_model,
    "on_model_error_callback": on_model_error,
    "before_tool_callback": before_tool,
    "after_tool_callback": after_tool,
    "on_tool_error_callback": on_tool_error,
}
