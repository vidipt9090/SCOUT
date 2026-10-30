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
