# SCOUT

Supply Chain Operations Under Threat: a proactive multi-agent system that reads supply chain news, assesses a disruption, revises demand, proposes a mitigation and validates it against policy, with no user prompt.

CSE3101 Agentic AI, BML Munjal University.

| Read this | For |
|---|---|
| [docs/design.md](docs/design.md) | Design thinking, PEAS, personas, architecture, related work |
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | Status and evidence for the 11 requirements |
| [results/summary.md](results/summary.md) | Pilot results |
| [docs/deviations.md](docs/deviations.md) | Every change from the plan, with versions |
| [docs/agent_cards/](docs/agent_cards/) | One card per agent |
| [docs/SCOUT_IMPLEMENTATION_PLAN.md](docs/SCOUT_IMPLEMENTATION_PLAN.md) | The original build plan |

## How it works

```
GNews snapshot + planted scenarios + poison items
        |  sanitiser and injection screen
        v
+-------------------------+    A2A    +--------------------------------+
| SENSING CREW (CrewAI)   |---------->| DECISION CORE (Google ADK)     |
| Signal Scout A, B (CoT) |<----------| Demand Oracle (ReAct)          |
| Theme Analyst (voting)  |  verdict  | Mitigation Planner (ReAct/CoT) |
+-------------------------+           | Guardrail (rules + CoT review) |
        |                             +--------------------------------+
        +--------> BLACKBOARD <------------------+   through MCP tools
        +--------> MCP SERVER (8 tools) <--------+
all agents -> callbacks -> JSONL traces -> scorer and report
```

Each run takes the point of view of a Plant or a Retail DC, and the same news should lead to different correct actions.

## Run it from a clean clone

On Windows, clone to a short path: some dependencies exceed the 260-character path limit. You need Python 3.12, GNU make and bash (Git Bash on Windows), a [GNews](https://gnews.io) key, a [Google AI Studio](https://aistudio.google.com) key, and the M5 Forecasting Accuracy files from Kaggle. M5 data, news snapshots and generated files are not in this repo, because their redistribution terms are unconfirmed.

```bash
cp .env.example .env     # add GNEWS_API_KEY, GOOGLE_API_KEY and M5_DATA_DIR
make setup PYTHON312=<path to python 3.12>
make data                # about a minute: extract, stock, vendors, documents, forecasts, RAG index
make test
make news-snapshot       # uses 6 GNews requests
make up
make run-one SCENARIO=port_delay_low PERSONA=plant
make view RUN=<run id printed above>   # writes runs/reports/<run id>.html
make down
```

`make run-one` also takes `ARCH=sequential|hierarchical`, `STRATEGY=react|cot`, `COMM_MODE=blackboard|direct` and `SCOUT_PROMPT=scout_cot_v1|scout_few_shot_v1`. Scenarios are listed in [data/scenarios/scenarios.yaml](data/scenarios/scenarios.yaml), and `SCENARIO=real_news` uses the saved snapshot.

| Command | What it does |
|---|---|
| `make pilot` | Runs the 48-condition grid, resumably. `LIMIT=n` stops after n runs |
| `make report` | Regenerates `results/` from finished runs |
| `make poison` | Runs the poison set through the safety layers |
| `make rag-probe` | Reports retrieval quality |
| `make check` | Confirms MCP tools and the blackboard are reachable |

The Gemini free tier allows 500 requests a day and about 15 a minute. A run uses about 12 calls, and `scout_platform/rate_limit.py` paces them.

## Layout

| Path | Contents |
|---|---|
| `contracts/` | Pydantic models shared by all agents, tagged `contracts-v1` |
| `sensing/` | CrewAI crew, news pipeline, blackboard service |
| `decision/` | ADK agents, Guardrail rules, A2A service, rendering |
| `scout_platform/` | MCP server, tracing, safety checks, rate limiter |
| `data/` | M5 extract, synthetic data, scenarios, RAG, forecasts |
| `eval/` | Single runs, pilot, scorer, report, poison test |
| `configs/` | Personas, policy, network, prompts, pilot grid |
| `deploy/` | Service runner, Dockerfiles and compose file |
