"""Sensing side of the A2A hop: send a run to the Decision service and return its JSON result."""
import asyncio
import json
import os
import uuid

import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import Message, Part, Role, TextPart
from a2a.utils import get_message_text

DECISION_URL = os.environ.get("DECISION_URL", "http://127.0.0.1:8103")
TIMEOUT_S = 420


async def _send(request: dict) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as http:
        client = await ClientFactory.connect(DECISION_URL, client_config=ClientConfig(httpx_client=http, streaming=False))
        message = Message(
            role=Role.user,
            message_id=uuid.uuid4().hex,
            parts=[Part(root=TextPart(text=json.dumps(request)))],
        )
        async for event in client.send_message(message):
            return json.loads(get_message_text(event))
    raise RuntimeError("no reply from the Decision service")


def request_decision(request: dict) -> dict:
    return asyncio.run(_send(request))
