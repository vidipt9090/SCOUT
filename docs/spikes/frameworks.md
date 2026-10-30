# S2 CrewAI, S3 ADK, S7 Backbone

Backbone for the pilot: `gemini-3.1-flash-lite` (ADK) and `gemini/gemini-3.1-flash-lite` (CrewAI). `GOOGLE_API_KEY` works for both.

Probe of one small call per model:

| Model | Result |
|---|---|
| gemini-3.1-flash-lite | ok, 1.3 s |
| gemini-3.5-flash-lite | ok, 3.3 s |
| gemini-3.5-flash | ok, 2.2 s |
| gemini-3.8-flash | ok, 405.1 s, rejected |
| gemini-2.5-pro | 404, not available to new users |

Free-tier quota is not confirmed: the API does not report it in these responses. E1 smoke runs must measure it.

## S2 CrewAI 1.15.33

Pass. One agent with one tool returned a validated Pydantic object through `output_pydantic`. 16.0 s, 2 requests, 965 tokens.

Hooks: `before_llm_call`, `after_llm_call`, `before_tool_call`, `after_tool_call` from `crewai.hooks`.

Findings:
- `after_llm_call` fired once for two `before_llm_call` events: it did not fire on the turn that produced the tool call. Count calls at `before_llm_call`, and take tokens from `result.token_usage`.
- CrewAI warned that some input token counts are approximate.
- 16 s for one trivial task is far above the raw model latency. Three CrewAI agents may use up the 30 s target alone.

## S3 ADK 2.13.0

Pass. One agent used a custom tool and `output_schema` together, so the plan's separate formatting step is not needed. 6.8 s.

ADK adds a synthetic `set_model_response` tool to produce the schema output. It appears in tool callbacks and should be filtered out of tool-call counts.

Callbacks that fired: before and after for agent, model and tool. `on_model_error_callback` and `on_tool_error_callback` exist and are not yet exercised.
