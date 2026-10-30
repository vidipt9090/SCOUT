"""S3: one ADK agent with a custom tool, all callbacks, and tools plus output_schema on the same agent."""
import asyncio
import time

import google.adk
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel

load_dotenv()
MODEL = "gemini-3.1-flash-lite"
events = []


def get_inventory(sku: str) -> dict:
    """Return on-hand units and days of cover for a SKU."""
    return {"sku": sku, "on_hand": 120, "days_of_cover": 3.0}


class Decision(BaseModel):
    action: str
    quantity: float
    rationale: str


def before_model(callback_context, llm_request):
    events.append("model_start")


def after_model(callback_context, llm_response):
    u = llm_response.usage_metadata
    events.append(f"model_end tokens={u.total_token_count if u else None}")


def before_tool(tool, args, tool_context):
    events.append(f"tool_start:{tool.name}")


def after_tool(tool, args, tool_context, tool_response):
    events.append(f"tool_end:{tool.name}")


def before_agent(callback_context):
    events.append("agent_start")


def after_agent(callback_context):
    events.append("agent_end")


agent = LlmAgent(
    name="planner_spike",
    model=MODEL,
    instruction="Call get_inventory for the SKU first. Then decide: reorder or monitor, with a quantity.",
    tools=[get_inventory],
    output_schema=Decision,
    output_key="decision",
    before_model_callback=before_model,
    after_model_callback=after_model,
    before_tool_callback=before_tool,
    after_tool_callback=after_tool,
    before_agent_callback=before_agent,
    after_agent_callback=after_agent,
)


async def main():
    runner = InMemoryRunner(agent=agent, app_name="spike")
    session = await runner.session_service.create_session(app_name="spike", user_id="u")
    start = time.perf_counter()
    message = types.Content(role="user", parts=[types.Part(text="SKU FOODS_3_090, port delay expected.")])
    async for _ in runner.run_async(user_id="u", session_id=session.id, new_message=message):
        pass
    print("adk", google.adk.__version__, "model", MODEL, f"latency {time.perf_counter() - start:.1f}s")
    session = await runner.session_service.get_session(app_name="spike", user_id="u", session_id=session.id)
    output = session.state.get("decision")
    print("output", output)
    print("events", events)
    Decision.model_validate(output)
    called = any(e.startswith("tool_end") for e in events)
    print("S3", "PASS" if called else "FAIL", "tool and output_schema together:", called)


asyncio.run(main())
