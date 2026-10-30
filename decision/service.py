"""Decision service: an A2A server in front of the ADK Decision core. Sensing (CrewAI) calls it across the framework boundary."""
import asyncio
import json
import os
from typing import Literal

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

load_dotenv()

from contracts import DisruptionAssessment  # noqa: E402
from decision.pipeline import run_decision  # noqa: E402
from scout_platform.blackboard import ASSESSMENT_TOPIC  # noqa: E402
from scout_platform.mcp_client import acall_tools  # noqa: E402

PORT = int(os.environ.get("DECISION_PORT", "8103"))


class DecisionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: str
    persona: Literal["plant", "retail_dc"]
    sku: str
    architecture: Literal["sequential", "hierarchical"]
    strategy: Literal["react", "cot"]
    comm_mode: Literal["blackboard", "direct"]
    assessment: DisruptionAssessment | None = None  # sent only in direct mode


async def resolve_assessment(req: DecisionRequest) -> DisruptionAssessment:
    if req.comm_mode == "direct":
        if req.assessment is None:
            raise ValueError("direct mode needs the assessment in the message")
        return req.assessment
    page = (await acall_tools([("blackboard_read", {"run_id": req.run_id, "topic": ASSESSMENT_TOPIC})]))[0]
    if not page["entries"]:
        raise ValueError(f"no assessment on the blackboard for {req.run_id}")
    return DisruptionAssessment.model_validate_json(json.dumps(page["entries"][-1]["payload"]))


class DecisionExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        req = DecisionRequest.model_validate_json(context.get_user_input())
        assessment = await resolve_assessment(req)
        result = await run_decision(
            assessment, req.sku, req.persona, req.architecture, req.strategy, req.run_id, req.comm_mode
        )
        await event_queue.enqueue_event(
            new_agent_text_message(result.model_dump_json(), context.context_id, context.task_id)
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError


CARD = AgentCard(
    name="scout-decision-core",
    description="ADK Demand Oracle, Mitigation Planner and Guardrail. Takes a disruption, returns a plan and verdict.",
    url=f"http://127.0.0.1:{PORT}/",
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=False),
    default_input_modes=["application/json"],
    default_output_modes=["application/json"],
    skills=[AgentSkill(id="decide", name="decide", description="Plan and validate a mitigation", tags=["supply-chain"])],
)
handler = DefaultRequestHandler(agent_executor=DecisionExecutor(), task_store=InMemoryTaskStore())
app = A2AStarletteApplication(agent_card=CARD, http_handler=handler).build()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
