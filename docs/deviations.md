# Deviations, versions and API record

## Versions (B0.2, 2026-10-30)

Python 3.12.6 in all three environments, installed from `<service>/requirements.in` and pinned in `<service>/requirements.txt`.

| Package | sensing | decision | scout_platform |
|---|---|---|---|
| crewai | 1.15.33 (`a2a` extra) | | |
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

## Open gaps

- `docs/PROJECT_BRIEF.md` is not written: the brief was not available in the workspace.
- `make` and Docker are not installed on this machine. `make test` was run as its underlying command. K1 needs Docker.
- Environments were tested from the pinned files on this machine only, with a pip dry-run in fresh environments. The second-machine check in G0 is still to do.
