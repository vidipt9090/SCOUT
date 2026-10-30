"""S4, decision side (ADK environment): an A2A server taking a DisruptionAssessment, returning a GuardrailVerdict."""
import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message

from contracts import DisruptionAssessment, GuardrailVerdict

PORT = 8103


class FixtureExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        assessment = DisruptionAssessment.model_validate_json(context.get_user_input())
        verdict = GuardrailVerdict(
            plan_id=f"plan-for-{assessment.assessment_id}",
            decision="approve",
            violated_rules=[],
            checker="none",
            counter_plan=None,
            reasons="spike fixture",
        )
        await event_queue.enqueue_event(
            new_agent_text_message(verdict.model_dump_json(), context.context_id, context.task_id)
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError


card = AgentCard(
    name="scout-decision-spike",
    description="Fixture decision core",
    url=f"http://127.0.0.1:{PORT}/",
    version="0.1.0",
    capabilities=AgentCapabilities(streaming=False),
    default_input_modes=["application/json"],
    default_output_modes=["application/json"],
    skills=[AgentSkill(id="decide", name="decide", description="Assess a disruption", tags=["supply-chain"])],
)
handler = DefaultRequestHandler(agent_executor=FixtureExecutor(), task_store=InMemoryTaskStore())
app = A2AStarletteApplication(agent_card=card, http_handler=handler).build()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
