# Project Update 22 — V4-1 AgentCore Foundation Complete

**Date:** March 22, 2026
**Context:** Executed the first v4 spec — AgentCore Foundation. Installed toolkit, scaffolded project, wrote entrypoint, ran tests, validated via dev server. Also tightened the no-mocks policy.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/agentcore-foundation/` — Spec V4-1 (COMPLETE)

### Prerequisite Reading
- `docs/project-updates/20-project-update-v4-agentcore-architecture-planning.md` — v4 architecture and spec plan
- `.kiro/steering/agentcore-architecture.md` — Architecture guardrails

---

## What Happened This Session

### V4-1 Spec Execution (8 tasks, all complete)

1. **Installed AgentCore starter toolkit** — `bedrock-agentcore-starter-toolkit` v0.3.3 installed in the project venv. The `agentcore` CLI is available. Also installed `bedrock-agentcore` v1.4.7 runtime.

2. **Scaffolded the project** — `agentcore create --non-interactive --project-name calleditv4 --template basic --agent-framework Strands --model-provider Bedrock` created `calleditv4/` with the standard AgentCore structure: `src/main.py` entrypoint, `.bedrock_agentcore.yaml` config, `test/` directory, `pyproject.toml`. The scaffold also created its own `.venv/` (we use the project-level venv instead).

3. **Verified scaffolding** — Config file confirmed with correct agent name, Python language, Strands framework. Generated entrypoint had `BedrockAgentCoreApp`, `@app.entrypoint`, and `app.run()`. The generated template was more complex than needed (included MCP client, code interpreter, async streaming) — replaced in Task 4.

4. **Replaced entrypoint** — Wrote the design's `main.py`: `BedrockAgentCoreApp` wrapper, `handler(payload, context)` with `@app.entrypoint`, Claude Sonnet 4 model (`us.anthropic.claude-sonnet-4-20250514-v1:0`), minimal system prompt, payload validation (missing `prompt` key returns structured error JSON), try/except around agent invocation with `logger.error(..., exc_info=True)`, agent created per-invocation (no shared state). Used `json.dumps()` for error responses instead of f-string JSON (cleaner, no escaping issues).

5. **Wrote tests** — Created `calleditv4/tests/test_entrypoint.py` with 6 pure-logic tests (no mocks): MODEL_ID constant check, SYSTEM_PROMPT content check, empty payload error, wrong key error, None prompt key-existence check, extra keys ignored. Originally wrote mocked unit tests and property tests — user caught the mock usage and we removed them (see Decision 96).

6. **Ran tests** — 6 passed in 0.79s. All pure logic, no external service calls.

7. **Started dev server** — User ran `agentcore dev` from `calleditv4/`. Dev server started successfully with hot reload.

8. **Invoked agent** — User ran all 3 test invocations:
   - `{"prompt": "Hello, are you working?"}` — non-empty text response ✓
   - `{"prompt": "What model are you running on?"}` — non-empty text response ✓
   - `{"not_prompt": "test"}` — structured error response about missing prompt ✓

### No-Mocks Policy Tightened (Decision 96)

The original tasks.md specified mocked unit tests and property tests (citing Decision 78 which allowed mocks for unit/property tests). User caught the mock usage and pushed back — mocked tests test mock behavior, not real behavior. The real validation happens via `agentcore invoke --dev` with real Bedrock calls.

Updated `.kiro/steering/no-mocks-policy.md` with a tighter policy:
- Default: NO mocks
- Mocks only allowed if the agent can prove concrete value AND gets explicit user approval before writing any mock code
- Never implement a mock silently

The test file was rewritten to keep only the 6 pure-logic tests (constants + payload validation) that don't need mocks. The property tests (prompt passthrough, response type, exception handling, missing key) were dropped — they only had value with mocks, and the real validation is `agentcore invoke --dev`.

### AgentCore Deviation Flag: None

No deviations from AgentCore recommended patterns in this spec. The entrypoint follows the mandatory `BedrockAgentCoreApp` + `@app.entrypoint` + `app.run()` pattern exactly. Hardcoded system prompt is intentional for V4-1 (Prompt Management wiring comes in V4-3a, per the steering doc).

## Decisions Made

- Decision 96: Zero mocks in v4 by default. Mocks require proven value + explicit user approval before implementation. Updated `.kiro/steering/no-mocks-policy.md`. Supersedes the Decision 78 exception for unit/property tests. Pure function tests and real integration tests only.

## Files Created/Modified

### Created
- `calleditv4/` — Full AgentCore project directory (scaffolded by `agentcore create`)
- `calleditv4/src/main.py` — Agent entrypoint (replaced scaffold's generated code)
- `calleditv4/tests/__init__.py` — Test package init
- `calleditv4/tests/test_entrypoint.py` — 6 pure-logic tests (no mocks)
- `docs/project-updates/22-project-update-v4-1-agentcore-foundation.md` — This file

### Modified
- `requirements.txt` — Added `bedrock-agentcore-starter-toolkit`
- `.kiro/steering/no-mocks-policy.md` — Tightened policy (Decision 96)
- `docs/project-updates/decision-log.md` — Added Decision 96
- `docs/project-updates/project-summary.md` — Added Update 22 entry
- `docs/project-updates/backlog.md` — Updated item 13 status
- `docs/project-updates/common-commands.md` — Added v4 commands

## What the Next Agent Should Do

### Immediate
1. If `--verify --judge` eval results are available, log as Run 19 and fill in Update 21
2. Begin V4-2 spec (Built-in Tools) — next on the critical path

### Key Files
- `calleditv4/src/main.py` — The working entrypoint
- `calleditv4/.bedrock_agentcore.yaml` — Project config
- `.kiro/specs/agentcore-foundation/` — Complete spec (requirements, design, tasks)
- `.kiro/steering/agentcore-architecture.md` — Architecture guardrails
- `.kiro/steering/no-mocks-policy.md` — Updated mock policy

### Important Notes
- The `calleditv4/.venv/` was created by `agentcore create` — we use the project-level venv at `/home/wsluser/projects/calledit/venv` instead
- `agentcore dev` requires TTY — always ask the user to run it
- `agentcore create` also requires TTY (timed out when run programmatically)
- The scaffold's generated `src/model/`, `src/mcp_client/` directories are still present from the template — they're unused by our entrypoint but harmless. Can clean up later.
- v3 Lambda backend is untouched (Decision 95)
