# SCOUT design

## 1. The problem

A supply chain planner usually learns about a disruption after it has reached them, then has to work out what it means for each product. SCOUT reverses that order. A scheduled poll of a news feed starts each run, so no one has to ask a question first. Agents detect a disruption, score it, revise demand, propose a mitigation and check it against policy.

## 2. Design thinking

| Stage | What we did |
|---|---|
| Empathise | Two people carry this risk differently. A plant planner fears a stopped line within days. A retail DC planner holds weeks of stock and fears overspending on a false alarm. Both read too much news to judge it all by hand. |
| Define | Given noisy news, produce a defensible action for a named SKU and role, with sources and policy checks, before anyone asks. |
| Ideate | We weighed one large agent, a pure rule system, and a pipeline of specialists. Specialists won, because each step needs a different kind of reasoning and can be checked on its own. |
| Prototype | Seven spikes tested the risky connections first: news, CrewAI, ADK, A2A, MCP, the blackboard and the LLM. Agents were then built against frozen data contracts. |
| Test | Scripted scenarios have answers fixed in git before any procedure text was written. Poison items attack the pipeline. The pilot measures accuracy, latency and cost. |

## 3. PEAS

| Element | Description |
|---|---|
| Performance | Action matches the answer key, quantity within policy, citations valid, unsafe plans stopped, end-to-end latency, tokens and cost |
| Environment | News feed, 15 SKUs, modelled network of four locations, vendors, contracts, procedures and policy |
| Actuators | Blackboard entries, a proposed `MitigationPlan`, a `GuardrailVerdict` (approve, counter or escalate). Nothing is executed: a human owns real orders |
| Sensors | News snapshots, MCP tools for sales, stock, vendors, policy, forecasts and document search |

## 4. Personas

**Priya, Plant planner.** Priya runs a just-in-time source that supplies the whole chain, with about two and a half days of stock. If stock falls under two days, a line can stop, and that is the most expensive thing that can happen in her week. She would rather place an order on a weak signal than explain a stoppage. She prefers suppliers she knows.

**Daniel, Retail DC planner.** Daniel runs a distribution centre for the four California stores and holds three to four weeks of stock. A short delay rarely reaches his shelves, so most alarms are not worth acting on. His emergency orders are capped at 15% above normal volume, and he is judged on cost. When trouble is serious he looks to a peer DC before a new supplier.

The same news should lead them to different correct actions. This is enforced through three channels, not prompt text alone: persona context in prompts, each location's own stock and demand through MCP, and persona limits in the Guardrail.

## 5. Architecture

- **Sensing (CrewAI).** Two Scouts classify headlines with Chain-of-Thought. The Theme Analyst scores severity by voting across three samples.
- **Decision (Google ADK).** The Demand Oracle uses ReAct to interpret forecasts. The Planner proposes an action by ReAct or CoT, and these are compared. The Guardrail applies deterministic rules, then a CoT review.
- **A2A** carries each run from Sensing to Decision and back. Both services run in separate environments.
- **Blackboard.** A standalone, append-only service reached through MCP. Each run has its own namespace, and every entry records author, source domain and trust level.
- **Architectures compared.** Sequential fixes the order. Hierarchical lets a coordinator delegate. Agent code and prompts are the same in both.
- **Messaging compared.** In blackboard mode the Decision core reads shared state from the blackboard. In direct mode the assessment travels in the A2A message.

One principle runs through the design: **the LLM supplies judgement, and code supplies facts.** Forecast numbers, cost, source domains, corroboration status and policy limits all come from code. Forecast values the model repeats are checked against the tool result.

## 6. Data: what is real and what is assumed

| Real | Modelled or synthetic |
|---|---|
| M5 daily sales and prices for 10 Walmart stores | The supply network: which stores each location serves |
| GNews articles | Stock levels: real demand x assumed days of cover |
| Forecasts fitted on real M5 sales | Vendors, contracts, procedures, policy, unit costs |
| | Demand multipliers and disruption horizons |
| | Planted headlines, poison items and the answer key |

**Supply network (modelled).** M5 gives real sales for 10 stores. Those sales roll up to four locations in `configs/network.yaml`. Retail DC serves the 4 California stores, the two peer DCs serve Texas and Wisconsin, and Plant is the upstream source for all 10. M5 does not say how stores are supplied, so this network is an assumption, and one Plant making food, hobby and household goods is a simplification. The two personas are positions in one chain, and each run takes one position's point of view.

**Time.** M5 sales end on 2016-05-22, which is treated as simulated today. News is current text from GNews snapshots plus planted scenario items, so news dates and sales dates do not align, by design. No GNews plan reaches M5's dates. Agents respond to what the text reports, not to when it was published.

**Stock.** M5 has no stock levels, so all stock is an assumption.

## 7. Safety

| Layer | Where | What it does |
|---|---|---|
| 1 Ingestion | `sensing/news/sanitise.py` | Strips HTML, caps length, quotes feed text as data |
| 2 Before model | `scout_platform/screen.py` | Pattern screen for injection and abusive language |
| 3 Before tool | `scout_platform/tool_guard.py` | Tool allowlist; arguments must match the run |
| 4 After tool | `scout_platform/tool_guard.py` | Type and range checks on returned data |
| 5 Output | `decision/guardrail_rules.py` | Pydantic validation and policy rules |
| 6 Corroboration | Guardrail rules | Severity 4 or higher needs two source domains; severity 5 goes to a human |

The main threat is indirect prompt injection, where feed text tries to act as instructions. Feed text is always data (POL-08).

## 8. Related work: OptiGuide

Microsoft's OptiGuide puts an LLM in front of supply chain optimisation, so a planner can ask what-if questions in plain language. It is reactive: a human asks, and the system explains. SCOUT is proactive: news starts the run with no query. The two are complementary, and SCOUT does not contain an optimiser. It chooses among procedures rather than solving for an optimal plan.

## 9. Known limits

- Accuracy is measured on scripted scenarios that were also used to tune prompts, so it is not an independent estimate.
- Theme grouping merges all stories of one type, so on real news unrelated events can inflate severity.
- The injection screen is a pattern list, and it misses paraphrases.
- The end-to-end 30-second target is missed. Most of the time is framework and connection overhead, not model time.
- The answer key treats each cell as having one correct action. A real planner has more options.
