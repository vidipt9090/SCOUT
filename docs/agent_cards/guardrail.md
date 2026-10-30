# Guardrail Agent

**Goal:** stop an unsafe plan, and say which rule and which checker stopped it.

**Inputs:** `MitigationPlan`, assessment, and facts it fetches itself through MCP.

**Outputs:** `GuardrailVerdict`: approve, counter or escalate.

**Prompt strategy:** Chain-of-Thought reflection (`guardrail_v1`) on top of deterministic rules.

**Tools:** none for the LLM. Code fetches vendors, stock, forecast and peer stock, so nothing is trusted from the Planner.

**State:** none beyond the run.

**Failure modes:** a missing plan escalates. POL-04 and POL-09 always escalate. A violation found only by the LLM escalates, since code cannot repair what it cannot check. If no compliant counter-plan exists, the run escalates.

**Why this design:** rules are exact, cheap and testable, with 20 tests and no LLM. The LLM answers only two questions rules cannot: does the action match the cited procedure, and does the rationale obey a command aimed at an AI (POL-08). An earlier version let it name any POL id, and it invented violations, so rule-checkable judgements were taken away from it. The counter-plan is built in code, limited to one round, and rechecked against the rules. In live testing the reviewer caught a Planner that chose `reorder` where the procedure said `switch_supplier`, which no rule checks.
