# AI Outputs

Generated artifacts from the AI-assisted TDD workflow.

Typical files:

- `notebooklm_session_latest.json`: session manifest from the NotebookLM bridge.
- `*.md`: extracted NotebookLM Markdown outputs for human review.
- `reporte_fase_actual.md`: current phase report used as a session context gate.

Rules:

1. Review NotebookLM Markdown before using it as context.
2. Treat NotebookLM output as a research aid, not as source of truth.
3. Do not modify business logic after NotebookLM without explicit human approval.
4. Update `docs/roadmap.md` only after relevant tests pass.
