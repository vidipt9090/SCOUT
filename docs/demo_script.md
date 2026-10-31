# Five-minute demo

Before starting: `make up`, then keep a browser tab open on a saved viewer report. A live run takes about a minute, so talk through the steps while it runs.

| Time | Show | Say |
|---|---|---|
| 0:00 | README diagram | "News starts the run, with no user prompt. CrewAI senses, ADK decides, A2A connects them, and MCP and the blackboard are shared." |
| 0:45 | `make run-one SCENARIO=port_delay_low PERSONA=plant` | "Three headlines about a one-berth closure. Scouts classify, the Theme Analyst votes on severity, and it crosses to ADK." |
| 2:00 | The printed result, then the viewer | "Each event is here from both frameworks, with the documents and signals behind the plan." |
| 2:45 | A saved `PERSONA=retail_dc` run of the same scenario | "Same news, different role. Plant reorders, Retail DC monitors, because stock and limits differ." |
| 3:15 | `results/poison_report.md` and a trace row for `layer2_before_model` | "This feed item told the agent to ignore its rules. It never reached a model. Here is the layer that stopped it." |
| 3:50 | A saved counter-plan run | "The Planner over-ordered, and the Guardrail named POL-01 and built a compliant plan." |
| 4:20 | `results/summary.md` and the latency figure | "Pilot results, with degraded runs counted. We missed the 30-second target, and this shows why." |
| 4:50 | `docs/REQUIREMENTS.md` | "This is what is complete, in progress and pending." |

## Backup

If an API is down or quota has run out, use saved traces and reports in `runs/reports/`, and say plainly that they are saved runs. Keep the free-tier limit in mind: rehearsals use about 12 calls per live run, out of 500 a day.

## Before the demo

- Generate and save the viewer reports listed above.
- Keep at least 50 calls of quota free for the day.
- Do not change prompts or configs after the pilot.
