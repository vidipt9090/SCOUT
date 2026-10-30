# SCOUT

Supply Chain Operations Under Threat: a proactive multi-agent system for supply chain disruption detection and mitigation. CSE3101 Agentic AI, BML Munjal University.

The build plan is [docs/SCOUT_IMPLEMENTATION_PLAN.md](docs/SCOUT_IMPLEMENTATION_PLAN.md). Current status is in [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md).

## Setup

Needs Python 3.12, GNU make and bash (Git Bash on Windows).

```bash
cp .env.example .env     # then fill in the keys
make setup PYTHON312=<path to python 3.12>
make test
```
