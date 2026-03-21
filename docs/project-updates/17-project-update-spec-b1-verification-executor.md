# Project Update 17 — Spec B1: Verification Executor Agent

**Date:** March 21, 2026
**Context:** Built and tested the Verification Executor Agent — a Strands agent that invokes MCP tools to verify predictions. All integration tests pass with real Bedrock + MCP calls.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/verification-execution-agent/` — Spec B1 (COMPLETE)
- `.kiro/specs/verification-triggers/` — Spec B2 (requirements complete, next)
- `.kiro/specs/verification-eval-integration/` — Spec B3 (requirements complete, after B2)

### Prerequisite Reading
- `docs/project-updates/16-project-update-spec-b-planning.md` — Spec B planning, B1/B2/B3 split
- `docs/project-updates/decision-log.md` — Decisions through 80

---

## What Happened This Session

### Spec B1 Implemented
- Created `verification_executor_agent.py` with:
  - `VERIFICATION_EXECUTOR_SYSTEM_PROMPT` (~34 lines, focused on tool invocation + verdict rules)
  - `create_verification_executor_agent()` factory — gets real MCP tools via `mcp_manager.get_mcp_tools()`, passes to `Agent(tools=[...])`
  - `_get_executor_agent()` lazy singleton — avoids triggering MCP connections at import time
  - `run_verification(prediction_record)` entry point — extracts plan, builds prompt, invokes agent, validates output, never raises
  - `_validate_outcome()` defensive normalizer — ensures structural validity even with malformed agent output
  - `_make_inconclusive()` helper for error paths

### Architecture Correction
User caught that the design diagram showed verification triggered by the VB output, which would short-circuit the HITL review loop. Corrected: the trigger is the user clicking "Log Call" (DynamoDB write), not the prediction pipeline completing. The prediction pipeline can run multiple rounds of clarification before the user logs it.

### No-Mocks Policy (Decision 78)
User rejected the mock-based test approach. All tests must hit real services — real Bedrock, real MCP servers, real DynamoDB. Created steering doc `.kiro/steering/no-mocks-policy.md`. Tests are slower (~75s for integration suite) but test the actual system.

### Test Results
- 24 pure function tests: all pass (instant, test `_validate_outcome`, `_make_inconclusive`, prompt content, error paths)
- 7 integration tests: all pass (real Bedrock + MCP, ~75s)
  - fetch: 4 tools connected
  - brave_search: 2 tools connected (needs `source .env` for BRAVE_API_KEY)
  - playwright: fails locally (needs browser deps, works in Docker Lambda)
  - Agent correctly confirmed "Christmas 2025 is Thursday" and refuted "Christmas 2025 is Monday"
  - Agent used brave_web_search to gather evidence

### Key Design Decisions
- Lazy singleton (`_get_executor_agent()`) instead of module-level initialization — prevents MCP connections at import time, critical for testing
- `.replace()` for prompt template substitution (Decision 72 pattern)
- Non-dict/None input guard in `run_verification` — returns inconclusive without invoking agent
- Empty plan guard — returns inconclusive if verification_method is missing, None, empty dict, or has all-empty fields

## Decisions Made

- Decision 78: No-mocks policy — all tests must hit real services
- Decision 79: Lazy singleton for verification executor — avoids MCP connections at import time
- Decision 80: Verification trigger is "Log Call" (DynamoDB write), not prediction pipeline completion

## Files Created/Modified

### Created
- `backend/calledit-backend/handlers/strands_make_call/verification_executor_agent.py` — the executor agent module
- `backend/calledit-backend/tests/test_verification_executor.py` — 24 pure + 7 integration tests
- `.kiro/steering/no-mocks-policy.md` — mandatory no-mocks steering doc
- `docs/project-updates/17-project-update-spec-b1-verification-executor.md` — this file

### Modified
- `.kiro/specs/verification-execution-agent/design.md` — corrected architecture diagram (trigger is Log Call, not VB output)
- `.kiro/specs/verification-triggers/requirements.md` — updated Req 2 to trigger on Log Call, added AC 7

## What the Next Agent Should Do

### Immediate (Spec B2)
1. Design and implement Spec B2 (`verification-triggers`): DynamoDB result storage, immediate verification trigger, EventBridge scheduled scanner
2. The trigger point is the "Log Call" action — when user logs a prediction to DynamoDB
3. Check `verification_date` against current time: past/within 5 min → immediate verify, future → leave for scanner

### After B2
4. Design and implement Spec B3 (`verification-eval-integration`): `--verify` flag on eval runner, 4 new evaluators

### Key Files
- `backend/calledit-backend/handlers/strands_make_call/verification_executor_agent.py` — the executor (B1 output)
- `backend/calledit-backend/handlers/strands_make_call/mcp_manager.py` — MCP Manager singleton (reused)
- `backend/calledit-backend/handlers/strands_make_call/strands_make_call_graph.py` — prediction pipeline handler (B2 will modify)
- `backend/calledit-backend/template.yaml` — SAM template (B2 will add EventBridge scanner)

### Important Notes
- Integration tests need `source .env` for BRAVE_API_KEY
- Playwright MCP server fails locally (needs browser deps) — works in Docker Lambda
- All Python commands: `/home/wsluser/projects/calledit/venv/bin/python`
- NO MOCKS — see `.kiro/steering/no-mocks-policy.md`
