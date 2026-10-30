"""S4, sensing side (CrewAI environment): send a fixture assessment, validate the verdict."""
import asyncio
import uuid
from pathlib import Path

import crewai
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import Message, Part, Role, TextPart
from a2a.utils import get_message_text

from contracts import DisruptionAssessment, GuardrailVerdict

FIXTURE = Path("contracts/fixtures/DisruptionAssessment.json").read_text(encoding="utf-8")


async def main():
    assessment = DisruptionAssessment.model_validate_json(FIXTURE)
    async with httpx.AsyncClient(timeout=30) as http:
        client = await ClientFactory.connect(
            "http://127.0.0.1:8103", client_config=ClientConfig(httpx_client=http, streaming=False)
        )
        msg = Message(
            role=Role.user,
            message_id=uuid.uuid4().hex,
            parts=[Part(root=TextPart(text=assessment.model_dump_json()))],
        )
        async for event in client.send_message(msg):
            verdict = GuardrailVerdict.model_validate_json(get_message_text(event))
            print("S4 PASS crewai", crewai.__version__, "verdict", verdict.model_dump_json())


asyncio.run(main())
