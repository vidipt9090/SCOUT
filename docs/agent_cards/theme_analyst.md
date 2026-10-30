# Theme Analyst

**Goal:** turn many signals into one scored disruption.

**Inputs:** relevant signals read from the blackboard through MCP.

**Outputs:** a `DisruptionAssessment`, written to the blackboard as `trusted`, or nothing if no signal is relevant.

**Prompt strategy:** self-consistency. Three samples at temperature 0.7 against fixed severity anchors. Majority vote, or the median on a three-way split. All votes and the agreement ratio are kept.

**Tools:** none for the LLM. `corroborating_domains` is computed in code.

**State:** reads the run's blackboard namespace only.

**Failure modes:** a slow sample delays the whole step, as one 26 s call showed. A failed sample raises and is logged.

**Why this design:** severity is the most consequential judgement and one sample is noisy, so voting makes it stabler and shows the disagreement. Grouping is deterministic (largest disruption type) rather than a topic model, because scenarios are single-event and it is easy to explain. Domain counts are code, so the model cannot claim corroboration it does not have.
