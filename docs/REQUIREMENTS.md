# Requirements status

Copied from plan section 2. Status here is the current state, not the Monday target. Nothing is Complete without evidence.

| # | Requirement | How SCOUT meets it | Status (target) | Evidence to record |
|---|---|---|---|---|
| 1a | Shared state, blackboard (must) | Blackboard service plus framework state | Complete | Blackboard log of a run; agent reads from it in trace |
| 1b | Compare messaging architectures | `comm-mode`: blackboard vs direct hand-off | Pending or stretch | Config flag; 8 runs per mode if built |
| 2 | MCP, at least 2 tools | Sales history, inventory, vendor, policy, forecast, RAG, blackboard | Complete | MCP server file, contract tests, tool calls in trace |
| 3 | Pydantic structured output | `MitigationPlan` as JSON and a Markdown table | Complete | `decision/render.py`, sample output |
| 4 | Agentic patterns, evaluated against others | CoT, ReAct, self-consistency, Guardrail reflection; sequential vs hierarchical | In progress | Pilot table by strategy and by architecture |
| 5 | Callback monitoring | ADK model, agent and tool callbacks; CrewAI hooks | Complete (basic) | Callback code; JSONL events including errors |
| 6 | A2A between CrewAI and ADK | Sensing to Decision hop | In progress | Spike note `docs/spikes/a2a.md`; one run if working |
| 7 | CrewAI and ADK only | Both used, nothing else | Complete | Dependency check in `docs/deviations.md` |
| 8 | Security, guardrails, prompt variance | Six safety layers; CoT vs few-shot; persona content | In progress | Poison test report; prompt variant ids in trace |
| 9 | Observability, provenance | JSONL traces citing signal ids and document ids; trace viewer | In progress | Trace of one run; viewer output |
| 10 | End-to-end evaluation, cost, runtime | Pilot with latency, tokens and estimated cost | In progress | `results/` table |
| 11 | Cloud deployment | Containers, one cloud target | Pending | Dockerfile; URL if reached |

## Current status (after G3, 2026-10-31)

| # | Status now | Evidence so far |
|---|---|---|
| 1a | In progress | Blackboard service and MCP access work; Sensing writes to it. The Decision core does not yet read from it |
| 1b | Pending | Required by the brief; built in B4.9 |
| 2 | Complete | `scout_platform/mcp_server/server.py`, 8 tools, contract tests in `tests/test_mcp_tools.py` |
| 3 | Complete | `decision/render.py`, `tests/test_guardrail_rules.py` |
| 4 | In progress | CoT, ReAct, self-consistency and reflection built; sequential and hierarchical run. Pilot table pending |
| 5 | In progress | ADK callbacks and CrewAI hooks write traces; viewer pending |
| 6 | In progress | SDK-level round trip only (`docs/spikes/a2a.md`); real agents connected in B4.1 |
| 7 | Complete | `docs/deviations.md`, dependency check |
| 8 | In progress | Layers 1, 3, 4 and 5 partly built; before-model screen and poison report pending |
| 9 | In progress | JSONL traces with prompt versions; viewer pending |
| 10 | Pending | Pilot not run |
| 11 | Pending | Docker not installed |
