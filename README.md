# AI-assisted TDD Portable Kit

Universal copy-paste kit for applying an AI-assisted TDD workflow to a new or existing project.

## What this kit contains

```text
.clinerules
docs/
  roadmap.md
  ai/
    00_orquestacion_arquitectura_ia.md
    notebook_context_index.md
    outputs/
      reporte_fase_actual.md
tools-ai/
  notebooklm/
    notebook_bridge.py
    requirements.txt
    run_browser.sh
    run_browser.bat
```

The kit is project-agnostic. It does not contain domain-specific rules, database assumptions, or UI constraints.

## Use in a new project

Copy the whole kit into the project root:

```text
your-project/
  .clinerules
  docs/
  tools-ai/
```

Then install the NotebookLM bridge dependency:

```bash
cd tools-ai/notebooklm
pip install -r requirements.txt
```

Launch Chrome with CDP:

```bash
./run_browser.sh
```

Or on Windows:

```bat
run_browser.bat
```

Run the bridge:

```bash
python notebook_bridge.py \
  --notebook-url "https://notebooklm.google.com/notebook/..." \
  --chat-prompt "Analyze the project context and summarize risks, decisions, and next TDD targets."
```

## Use in an existing project

Do not overwrite blindly. Merge the kit into the existing project:

1. Merge [` .clinerules`](.clinerules) with the existing agent rules.
2. Add or merge `docs/roadmap.md`.
3. Add or merge `docs/ai/00_orquestacion_arquitectura_ia.md`.
4. Add or merge `docs/ai/notebook_context_index.md`.
5. Add or merge `docs/ai/outputs/reporte_fase_actual.md`.
6. Copy `tools-ai/notebooklm/`.
7. Add local runtime paths to `.gitignore`.

Recommended `.gitignore` entries:

```gitignore
tools-ai/notebooklm/chrome_profile/
__pycache__/
*.pyc
```

## Environment variables

Optional environment variables can be copied to `.env` or passed directly to the launcher/bridge:

```env
NOTEBOOKLM_CDP_ENDPOINT=http://localhost:9222
NOTEBOOKLM_NOTEBOOK_URL=
NOTEBOOKLM_NOTEBOOK_TITLE=Project Notebook
NOTEBOOKLM_OUTPUT_DIR=docs/ai/outputs
NOTEBOOKLM_SESSION_FILE=docs/ai/outputs/notebooklm_session_latest.json
NOTEBOOKLM_CHROME_PROFILE=tools-ai/notebooklm/chrome_profile
CDP_PORT=9222
CHROME_BIN=
```

## AI context prompt

Paste this into the AI agent before starting work in the target project:

```text
I am applying the AI-assisted TDD Portable Kit.

Before changing business logic:
1. Read docs/roadmap.md.
2. Read docs/ai/outputs/reporte_fase_actual.md.
3. Read the relevant architecture or technical docs.
4. Find existing tests near the target behavior.
5. If NotebookLM was used, review the generated Markdown and docs/ai/outputs/notebooklm_session_latest.json.
6. Treat NotebookLM as a research aid, not as source of truth.
7. Present a concise plan and wait for explicit human approval before modifying code.

For every behavior change:
1. Write the spec first.
2. Run the test and verify a controlled red failure.
3. Implement the minimal production change.
4. Run the test and verify green.
5. Refactor only after green.
6. Update docs/roadmap.md only after the relevant tests pass.
```

## Required human gates

- NotebookLM output must be reviewed before being used.
- Code changes after NotebookLM require explicit human approval.
- Business logic changes require the TDD loop.
- Roadmap updates require passing tests.
- Destructive operations require explicit confirmation.

## Validation

After copying into a project, validate the bridge syntax:

```bash
python -m py_compile tools-ai/notebooklm/notebook_bridge.py
```

Then use the project's normal test command, for example:

```bash
npm test
npm run typecheck
pytest
go test ./...
```

## Operational checklist

```text
[ ] Copy or merge kit files.
[ ] Merge .clinerules rules.
[ ] Install Playwright dependency.
[ ] Add chrome_profile/ and __pycache__/ to .gitignore.
[ ] Set NOTEBOOKLM_NOTEBOOK_URL or NOTEBOOKLM_NOTEBOOK_TITLE.
[ ] Launch Chrome with CDP.
[ ] Run notebook_bridge.py.
[ ] Review generated Markdown.
[ ] Review notebooklm_session_latest.json.
[ ] Apply TDD before changing code.
[ ] Update roadmap only after green tests.
```
