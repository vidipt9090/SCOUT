# Viva notes: why this and not that

Each answer is a short spoken version. Fill in pilot numbers from `results/summary.md` before the viva.

| They may ask | Our choice | Short answer |
|---|---|---|
| Why two frameworks? | CrewAI for Sensing, ADK for Decision | The brief requires both. CrewAI suits a team of role-based classifiers. ADK gives fine-grained callbacks and tool control, which the Decision core needs. |
| Why ChromaDB, not FAISS or BM25? | ChromaDB | It has metadata filters built in, so we narrow to persona and SKU before similarity. FAISS would need that built by hand. Hybrid search could help on exact ids, but SKU filtering already handles those. |
| Why CoT, ReAct and self-consistency? | One per job | Scouts need an auditable reason, so CoT. The Oracle and Planner need facts from tools, so ReAct. Severity is noisy and high-stakes, so voting. We did not use Reflexion or Tree-of-Thought, because extra calls cost quota and latency. |
| Why a blackboard? | Standalone service | Agents in two frameworks need shared state neither framework owns. It also gives an audit log. We compare it with direct hand-off. |
| Why A2A, not plain HTTP? | A2A | The brief requires it, and it gives a standard agent card and message format across frameworks. It does run over HTTP. |
| Why MCP, not native function calling? | MCP | One tool server serves both frameworks, with one validation point. |
| Why sequential and hierarchical? | Both compared | Sequential is cheap and predictable. Hierarchical adds a coordinator and extra LLM calls. Event-driven was cut for time. |
| Why a simple forecast? | Better of seasonal naive and fixed SARIMA | The project is about agents, not forecasting. Fitting offline keeps timed runs clean. |
| Why is the LLM not allowed to produce numbers? | Code supplies facts | A wrong number looks as confident as a right one. Code-sourced numbers are testable. |
| Why not clamp a bad Planner quantity? | No clamping | A clamp would hide the violation we want to detect. The Guardrail reports it, then builds a counter-plan as a new object. |
| Why did you restrict the reviewer LLM? | Two yes-or-no questions | When it could name any rule, it invented violations. Rules that code can check stay with code. |
| Why is retrieval not an LLM tool? | Fixed queries in code | ReAct and CoT must see identical documents, or the comparison is not fair. |
| Why 10 stores? | Rolled up to four locations | It gives Plant and the peer DCs real demand. The network is our assumption, and we say so. |
| Do news dates match M5? | No | No GNews plan reaches M5's dates. Agents respond to content, and the last M5 day is simulated today. |

## Questions to expect, with honest answers

**Is your accuracy real?** It is measured on scripted scenarios that we also used to fix bugs and tune prompts. It shows the pipeline works on those cases. It is not a generalisation estimate.

**Why did you miss the 30-second target?** Model time is a small part of a run. Most of the rest is framework start-up and tool connections. A faster model would not fix that.

**Is A2A really between agents?** The protocol and framework boundary are real, and the ADK agents run behind it. It is called from a Python runner in the Sensing service, not from inside a CrewAI agent, and uses an SDK executor rather than ADK's `to_a2a`.

**Does your safety work?** All 12 poison items were stopped. Be precise: later layers were tested by scripted replays, the pattern screen misses paraphrases, and turning early layers off made no difference on this set, because the Scout prompt also resisted.

**What does Kruskal-Wallis show?** Whether latency distributions differ across groups. With about 40 runs it is underpowered and descriptive, and it says nothing about cause.

**What would you do next?** Test on unseen scenarios, add a second LLM, improve theme grouping, reduce connection overhead, and deploy.

## Swap drill

For each component, be ready to say what would change if it were replaced.

| Replace | What changes |
|---|---|
| Gemini | `configs/llm.yaml`, prices and the rate limiter. Agents stay the same |
| GNews | `sensing/news/fetch.py` only. Replay works from snapshots |
| ChromaDB | `data/rag/` only. The MCP tool's shape stays the same |
| Blackboard store | `sensing/blackboard_service/app.py` only |
| A2A | `decision/service.py` and `sensing/a2a_client.py` |
| A Guardrail rule | `decision/guardrail_rules.py` and its test |
