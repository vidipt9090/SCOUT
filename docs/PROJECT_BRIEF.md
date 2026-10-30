# Project review: minimum requirements

Course brief as supplied by the student, 2026-10-30. Lightly formatted, wording unchanged in substance.

1. **Context sharing and state updates.** Intermediate output from one agent must feed into another. Use state for sharing context. Different messaging architectures need to be tried and compared. However, blackboard architecture is a must.
2. **Tool integration using MCP.** At least two external tools (library or custom) must be used (for example web search API, database lookup, file parser, calculator).
3. **Structured output using Pydantic.** Final output must be generated in a structured form (Markdown, table or JSON).
4. **Agentic design patterns.** Implement suitable agentic design patterns as found suitable and relevant for your specific goals. Evaluate with other agentic patterns.
5. **Task monitoring and logging using callback functions.** Agents must include a monitoring mechanism that tracks intermediate outputs, execution flows and errors for transparency and debugging.
6. **Agent to agent communication using the A2A protocol.** Use interoperability, for example one agent defined using ADK and another using CrewAI.
7. **Frameworks.** You must use both CrewAI and ADK as the agentic framework for the implementation. Do not use any agentic framework other than CrewAI and ADK.
8. **Secure the agentic system.** Use guardrails for validation, and callbacks for data validation (for example type checking from a tool's return, user prompt parsing for toxic or abusive language or prompt injection attacks). Try to use multiple prompts with variances. Variances can be induced from changes in architecture (ReAct prompt vs few-shot) or content or persona.
9. **Observability.** Implement a suitable observability mechanism for tracing (auditability and provenance).
10. **Evaluation.** Perform end-to-end performance evaluation, cost and running time estimates for multiple runs. There can be variance in prompts, such as different architecture (ReAct based) vs different content originating from different personas.
11. **Deployment.** Deploy the project on a cloud platform.
