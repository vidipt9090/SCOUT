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

## Current status (after G4, 2026-10-31)

| # | Status now | Evidence so far |
|---|---|---|
| 1a | Complete | `runs/blackboard/run-strike-low-823098f6.jsonl`: signals, assessment, forecast, plan, verdict. Decision reads it in `decision/service.py` |
| 1b | In progress | `COMM_MODE` flag and one run per mode; comparison runs in the pilot |
| 2 | Complete | `scout_platform/mcp_server/server.py`, 8 tools, `tests/test_mcp_tools.py` |
| 3 | Complete | `decision/render.py`, `runs/records/*.result.json` |
| 4 | In progress | Patterns built, both architectures run. Pilot table pending |
| 5 | Complete (basic) | `decision/callbacks.py`, `sensing/hooks.py`; JSONL events include errors |
| 6 | In progress | Real A2A hop between the CrewAI and ADK services, through an SDK executor (`docs/deviations.md` item 38). Not called from inside a CrewAI agent |
| 7 | Complete | `docs/deviations.md`, dependency check |
| 8 | In progress | Six layers built, `results/poison_report.md`. Scripted later layers, and the ablation showed no difference |
| 9 | In progress | Traces, `scout_platform/tracing/view.py`, signal and document ids. Scorer pending |
| 10 | In progress | Latency, tokens and cost per run; pilot not run |
| 11 | Pending | Docker not installed |
