"""Safety layers 3 and 4: tool allowlist, argument validation, and type checks on returned data."""
from pydantic import ValidationError

from scout_platform.mcp_server import models

ALLOWED_TOOLS = {
    "demand_oracle": {"forecast", "get_inventory", "get_sales_history"},
    "planner_react": {"lookup_vendor", "get_inventory", "get_policy_limits"},
    "coordinator": {"demand_oracle", "mitigation_planner", "guardrail"},
}
PEER_LOCATIONS = {"peer_dc_1", "peer_dc_2"}
RETURN_MODELS = {
    "forecast": models.Forecast,
    "get_inventory": models.Inventory,
    "get_sales_history": models.SalesHistory,
    "lookup_vendor": models.VendorList,
    "get_policy_limits": models.PolicyLimits,
}


def check_tool_call(agent: str, tool: str, args: dict, sku: str, persona: str, assessment: dict) -> str | None:
    """Return a reason to block, or None. Values must match the run, so feed text cannot steer an argument."""
    if tool not in ALLOWED_TOOLS.get(agent, set()):
        return f"{tool} is not allowed for {agent}"
    if "sku" in args and args["sku"] != sku:
        return f"sku {args['sku']!r} is not this run's SKU"
    if "persona" in args and args["persona"] != persona:
        return f"persona {args['persona']!r} is not this run's persona"
    if "location" in args:
        allowed = {persona} | (PEER_LOCATIONS if agent == "planner_react" and persona == "retail_dc" else set())
        if args["location"] not in allowed:
            return f"location {args['location']!r} is not allowed"
    if tool == "forecast":
        if args.get("severity") != assessment["severity"]:
            return "severity differs from the assessment"
        if args.get("disruption_type") != assessment["disruption_type"]:
            return "disruption_type differs from the assessment"
    return None


def check_tool_result(tool: str, structured: dict | None) -> str | None:
    """Return a reason to reject the result, or None."""
    model = RETURN_MODELS.get(tool)
    if model is None:
        return None
    try:
        model.model_validate(structured)
    except ValidationError as e:
        return f"{tool} returned a bad shape: {str(e)[:200]}"
    return None
