# Demand Oracle

**Goal:** explain what the disruption means for demand on one SKU, for one persona.

**Inputs:** `DisruptionAssessment`, persona context, SKU.

**Outputs:** `ForecastResult`.

**Prompt strategy:** ReAct, with a hard cap of 3 tool calls enforced in a callback.

**Tools (MCP):** `forecast`, `get_inventory`, `get_sales_history`, always for the persona's own location.

**State:** the real `forecast` tool result is captured in a callback.

**Failure modes:** after the run, code compares the output with the captured tool result. A mismatch, a missing call or an interpretation that never mentions the persona's constraint is flagged and marks the run degraded. It is never repaired.

**Why this design:** the LLM interprets numbers and never produces them. Forecasts are fitted offline and multipliers come from config, so a timed run has no model fitting and no invented demand.
