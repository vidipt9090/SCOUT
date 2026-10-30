# S4 A2A

Versions: a2a-sdk 0.3.26 on both sides, crewai 1.15.33, google-adk 2.13.0, Python 3.12.6.

Direction: the Decision side serves, the Sensing side calls.

Result: pass at SDK level. A fixture `DisruptionAssessment` went from the sensing environment to the decision environment over JSON-RPC, and a `GuardrailVerdict` came back. Both sides validated against the contracts.

APIs used: server `A2AStarletteApplication`, `DefaultRequestHandler`, `InMemoryTaskStore`, `AgentExecutor`; client `ClientFactory.connect`, `ClientConfig(streaming=False)`, `Client.send_message`.

Not proven: no CrewAI agent or ADK agent took part. Both sides were the a2a SDK running inside each framework's environment. To do in B4.1: serve the ADK agent with `google.adk.a2a.utils.agent_to_a2a.to_a2a`, and call it from the Sensing service. Requires an LLM key.

Run: `bash spikes/run_keyless.sh`

## Update at B4.1

The hop now carries real runs: Sensing calls `decision/service.py`, which runs the ADK agents. `run_id` crosses the hop, so one trace holds both frameworks' events. See `docs/deviations.md` item 38.
