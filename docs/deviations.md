# Deviations, versions and API record

## Versions (B0.2, 2026-10-30)

Python 3.12.6 in all three environments, installed from `<service>/requirements.in` and pinned in `<service>/requirements.txt`.

| Package | sensing | decision | scout_platform |
|---|---|---|---|
| crewai | 1.15.33 (`a2a`, `google-genai` extras) | | |
| google-adk | | 2.13.0 (`a2a`, `mcp` extras) | |
| mcp | 1.30.0 | 1.30.0 | 1.30.0 |
| a2a-sdk | 0.3.26 | 0.3.26 | |
| chromadb | 1.5.9 | | 1.5.9 |
| pydantic | 2.12.5 | 2.14.2 | 2.14.2 |

Python support from package metadata: CrewAI `>=3.10,<3.14`, ADK `>=3.11`. They overlap, so one interpreter version serves all three. The machine default (3.14) is not supported by CrewAI.

## Dependency check (B0.3)

Requirement 7: no LangChain, LangGraph, LangSmith, AutoGen, LlamaIndex, Semantic Kernel, Haystack or smolagents in any environment. Checked by scanning the pinned files and `pipdeptree -r -p "langchain*,langgraph*,langsmith*"` (no match, before the extras were added; the pinned-file scan was repeated after). CrewAI's own `crewai-cli` and `crewai-core` are part of CrewAI.

## Deviations from the plan

1. `platform/` is named `scout_platform/`. A package called `platform` on the path shadows the Python standard library module of that name, which many dependencies import.
2. `mcp` is held below 2 everywhere, because CrewAI 1.15.33 requires `mcp>=1.30.0,<2`. Unconstrained, the platform environment resolved to 2.3.0.
3. `a2a-sdk` is held to 0.3.x in the decision environment to match CrewAI's `~=0.3.10`. ADK alone allows up to `<2`.
4. Pydantic differs between sensing (2.12.5) and decision (2.14.2). Contracts cross as JSON, and the contract tests pass in both environments.
5. Contract models are stricter than the draft: frozen, `extra="forbid"`, strict types, ranges on `confidence`, `vote_agreement` and `severity_votes`, non-empty `cited_doc_ids`, and `counter_plan` present only for a `counter` decision. Because of strict mode, values are read with `model_validate_json`.
6. Branches are `a/dev`, `b/dev`, `c/dev`. Git cannot name a branch `a/` alone.
7. Requirement files are per service, inside the service directory.
8. The repo sits in `scout/` inside the course folder, with a copy of the plan at `docs/SCOUT_IMPLEMENTATION_PLAN.md`.

9. Solo build. One person builds the whole project (decided 2026-10-30), so the member split in plan section 4, the `a/`, `b/`, `c/` branches, PR review and the own-it checkpoints between members do not apply. `main` protection is not set. `a/dev`, `b/dev` and `c/dev` were deleted. Work goes on feature branches.
10. The blackboard runs in the `scout_platform` environment, because FastAPI is pinned there. Its code stays in `sensing/blackboard_service/`.
11. `spikes/` holds throwaway spike code and was not in the plan's layout.
12. CrewAI has the `google-genai` extra, which it needs to reach Gemini. It pins `google-genai~=1.65.0`, while ADK has its own newer version. The separate environments keep these apart.

13. The brief says different messaging architectures "need to be tried and compared", so B4.9 is treated as required and removed from the cut order in plan section 9.
14. The Signal `snippet` uses newsdata.io `description`, because `content` is paid only.

15. News source is GNews, not newsdata.io (project owner's decision, 2026-10-30). GNews cannot reach M5 dates; see `docs/spikes/news.md`. Plan references to newsdata.io and `NEWSDATA_API_KEY` now mean GNews and `GNEWS_API_KEY`.
16. M5 sales end on 2016-05-22 (d_1941). The calendar runs to 2016-06-19, but those days have no sales. 2016-05-22 is simulated today.
17. D8 (one store) is replaced: all 10 stores roll up to four locations (`configs/network.yaml`), decided 2026-10-30 so that Plant and the peer DCs have real demand. 268 SKUs qualify; the 15 are 7 FOODS, 5 HOBBIES and 3 HOUSEHOLD, capped at 7 per category. The extract keeps the last 1095 days. `get_sales_history` and `forecast` gain a `location` argument, and MOQs scale to Retail DC demand.
18. Retail DC and peer DC safety floors (7 and 10 days) and peer cover (35 to 45 days) are assumptions, not plan values.
19. Vendor MOQs in plan 6.4 (200 to 1000 units) are too large for these SKUs, which sell about 4 to 17 units a day. B2.3 must scale MOQs to demand, or every order breaches POL-01 and Plant over-orders by months.
20. The M5 extract and inventory are git-ignored until M5 terms are checked. `make m5-extract` and `make inventory` rebuild them from the raw files.

21. RAG precision at 5 is 0.64 against the plan's default target of 0.8. The target cannot be met on this probe: many queries have one relevant chunk, so the ceiling is 0.68. Hit rate is 1.00, and the exact procedure clause is in the top 5 for 18 of 18 cells, which is the measure the Planner depends on.
22. `vendors.csv` adds `approved_contract`, `unit_cost_usd` and `plant_critical`, which POL-03, POL-04 and POL-05 need. Plant critical means FOODS. Unit cost is 60% of the shelf price, an assumption.
23. Two SKUs have a third agreement, so a trap alternate (Tier 3, or 25-day lead time) exists beside a compliant one, and one correct action remains.
24. `strike` at medium for Plant is `switch_supplier`, not `reorder`, because a wider strike stops the primary. This differs from the port-delay row by design.
25. Forecast baseline per SKU and location is the better of seasonal naive and a fixed SARIMA(1,0,1)(0,1,1,7) on a 28-day holdout.
26. Disruption horizons and demand multipliers in `configs/disruption_effects.yaml` are assumptions.
27. `data/forecasting/` and `data/rag/probe.py`, `retrieve.py` were added to the layout. Scenario definitions are in `data/scenarios/scenarios.yaml`, and poison labels in `eval/poison_labels.yaml`.
28. Real news in the snapshot is thin for weather: `typhoon port` returned no articles inside the 30-day window. Scenarios use planted text, so this affects only realism.

29. Vendors are 8 shared suppliers (V01 to V08), with one supply agreement per vendor and SKU: 32 agreements. Tier and penalty belong to the vendor; lead time, MOQ and unit cost belong to the agreement. This replaces one invented vendor per agreement, which was unrealistic.

30. Planner retrieval runs in code with fixed queries before both variants, and `rag_search` is not an LLM tool. The plan listed it as a Planner tool, but LLM-chosen queries would break its retrieval-equality rule. Persona policy rules are always part of the retrieved set.
31. The LLM drafts a `PlanDraft`; code adds ids and computes cost. Same pattern in the Scouts: the LLM supplies judgement, code copies source fields.
32. Counter-plans are built deterministically and rechecked against the rules. The plan did not fix how they are generated.
33. The LLM reviewer does not name POL ids. It answers `action_matches_procedure` and `obeys_embedded_command`. A failed match is reported as `UNSUPPORTED-ACTION`, and always escalates.
34. POL-01 baseline volume is defined as baseline daily demand x disruption horizon. POL-02 applies only to plans that place an order, because `monitor` cannot add stock. POL-03 treats any single-vendor Tier 3 plan as over Retail DC's 10% share. `MitigationPlan.vendor_id` holds the donor for `stock_transfer`, because `contracts-v1` has no donor field. MOQ breaches are reported as `CON-MOQ`.
35. The Sensing crew writes to the blackboard from code through MCP, not as an LLM tool, so a Signal cannot be skipped. The Decision core uses MCP tools natively through `McpToolset`.
36. Gemini's free tier allows about 15 calls a minute on `gemini-3.1-flash-lite`, observed from 429 errors. `scout_platform/rate_limit.py` paces both services to 12 a minute, and waits are logged as `rate_wait`. The daily limit is unknown. CrewAI's `after_llm_call` is unreliable, as S2 found.
37. Planner prompts were tuned on the 12 G3 cases, which are the same scenarios the pilot uses. Results on them are not an independent test.

38. The A2A server is a2a-sdk `AgentExecutor` code in `decision/service.py` that runs the ADK agents, rather than ADK's `to_a2a`. `to_a2a` maps a chat message to one agent, and this hop needs a structured request and run state. The protocol and the framework boundary are real. Sensing calls from a Python orchestrator (`eval/run_one.py`), not from inside a CrewAI agent.
39. `COMM_MODE=blackboard` passes only a reference in the A2A message: the Decision core reads the assessment and forecast from the blackboard and posts plan and verdict there. `direct` passes the assessment in the message and uses ADK state. The mode is a real data path, not a flag on a trace.
40. Safety layer 2 is a regex pattern list (`scout_platform/screen.py`). It flagged 0 of 29 real articles and 0 planted headlines, but it misses paraphrases by design.
41. In the poison test, later layers are scripted replays of the attempted tool call or plan, labelled as such in `results/poison_report.md`, because attacks rarely survive to reach them live.
42. The ablation showed no difference: with sanitiser, screen and keyword filter off, Scout A still marked 0 of 12 poison items relevant. On this set the Scout prompt alone resisted, so the ablation is not evidence that the earlier layers are needed. One item, a fabricated catastrophe, was marked relevant with layers on and relies on the corroboration gate.
43. Theme grouping merges every story of one type. On real news it merged unrelated port stories into one severity 5 assessment, unanimously, and the run correctly escalated. This is a known limit of deterministic grouping, accepted for this evaluation.
44. Prices in `configs/prices.yaml` are third-party reports of Google's list price, because Google's pricing page could not be loaded. The daily free-tier limit is unconfirmed: sources say 500 to 1,500 a day. 492 calls were logged without a daily block.
45. The CoT Planner can output a fractional quantity (678.477). It is left unrounded, because the Planner's output is not altered.

## Open gaps

- M5 and GNews redistribution terms are unchecked, so generated data and snapshots are git-ignored. A clean clone needs the raw M5 files and a GNews key.

- Docker is not installed on this machine. K1 needs it.
- Environments were tested from the pinned files on this machine only, with a pip dry-run in fresh environments. The second-machine check in G0 is still to do.
