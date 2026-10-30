# Signal Scout A and B

**Goal:** turn raw news into typed, evidence-carrying signals.

**Inputs:** sanitised `FeedItem`s from snapshots, planted items or poison items.

**Outputs:** one `Signal` per item, written to the blackboard through MCP as `untrusted`.

**Prompt strategy:** Chain-of-Thought (`scout_cot_v1`), with a few-shot variant (`scout_few_shot_v1`) for the prompt comparison. Reasoning comes before the label.

**Tools:** none for the LLM. Code writes to the blackboard, so a signal cannot be skipped or altered by the model.

**State:** none between runs. Same class, two configurations: A covers ports and logistics, B covers weather, labour and geopolitics.

**Failure modes:** an unknown `item_id` raises. Source fields come from the feed, never from the model, so it cannot rewrite a headline or domain.

**Why this design:** a cheap keyword filter runs first to save calls. CoT makes each label auditable. Items are batched into one call to keep latency down. Scouts do not de-duplicate, because two scouts or sources reporting one event is corroboration.
