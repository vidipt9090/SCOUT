# Mitigation Planner

**Goal:** propose one action for one SKU, grounded in cited documents.

**Inputs:** assessment, forecast tool result, persona context, retrieved chunks.

**Outputs:** `MitigationPlan`. The LLM returns a `PlanDraft`; code adds ids and computes cost from vendor data.

**Prompt strategy:** ReAct (`planner_react_v1`, cap of 4 tool calls) or CoT (`planner_cot_v1`, one pass, no tools, facts given up front).

**Tools (MCP):** ReAct uses `lookup_vendor`, `get_inventory`, `get_policy_limits`.

**State:** `retrieved_doc_ids`, which bounds what may be cited.

**Failure modes:** citations must be a non-empty subset of retrieved documents. One retry, then the run is degraded and the Guardrail escalates. Quantities are never clamped, because a clamp would hide violations from the Guardrail.

**Why this design:** retrieval runs in code before either variant, with fixed queries, so ReAct and CoT see identical documents and any difference comes from the strategy. This is why `rag_search` is not an LLM tool here, unlike the plan's first draft.
