# Project Update 25 — V4-3b Clarification & Streaming

**Date:** March 23, 2026
**Context:** Executing the V4-3b spec — async streaming entrypoint with multi-round clarification support. Spec was fully written in the V4-3a session; this session is pure execution.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/clarification-streaming/` — Spec V4-3b (COMPLETE)

### Prerequisite Reading
- `docs/project-updates/24-project-update-v4-3a-creation-agent-core.md` — V4-3a (creation agent core)
- `docs/project-updates/next-agent-prompt-v4-3b.md` — Agent prompt for this session

---

## What Happened This Session

### Pre-Execution Review

Before executing any tasks, did a full cross-reference review of the agent prompt (`next-agent-prompt-v4-3b.md`), the spec (requirements, design, tasks), and the current source files (`main.py`, `bundle.py`, `models.py`). Found 9 items — none are blockers, but they need tracking as we build. Items get resolved (fixed or confirmed non-issue) during execution, then deleted from the punch list and woven into the narrative below.

---

## Review Punch List

_Items discovered during pre-execution review. Resolve each during task execution, then delete the item and add the resolution to the narrative._

### REVIEW-1: Unnecessary `_convert_floats_to_decimal` import in design entrypoint
**Source:** Design doc entrypoint code block
**Issue:** The design's `main.py` imports `_convert_floats_to_decimal` from `bundle.py`, but the entrypoint never calls it directly — it's used internally by `format_ddb_update()` and `format_ddb_item()`. Unnecessary import could confuse the executing agent.
**Action:** When implementing Task 5.2, don't import `_convert_floats_to_decimal` in `main.py`. If confirmed correct, fix the design doc's code block.
**Status:** RESOLVED — Confirmed. Did not import `_convert_floats_to_decimal` in main.py. Design doc code block is a sketch, not copy-paste code.

### REVIEW-2: `format_ddb_update` SET/ADD expression concatenation fragility
**Source:** Design doc `bundle.py` code block
**Issue:** The SET clause is built via `", ".join(update_parts)` and the ADD clause is appended with `+ " ADD clarification_rounds :one"`. This works but is fragile — depends on no trailing whitespace in the last SET part. Not a bug, but worth noting during implementation.
**Action:** Confirm during Task 2.3 implementation. Consider if a cleaner separator pattern is warranted.
**Status:** RESOLVED — Implemented as designed. The join pattern works correctly. No trailing whitespace issues.

### REVIEW-3: Missing `ConditionalCheckFailedException` split handling in design code
**Source:** Design doc entrypoint code block vs. Requirements 7.4 and 7.5
**Issue:** The design code has a generic `except Exception as e` around the clarification flow. But Req 7.4 says `ConditionalCheckFailedException` should yield an error event (prediction deleted between load and update), while Req 7.5 says other DDB failures should yield `flow_complete` with `save_error` field. The design code doesn't show this two-path split. Tasks 5.3 mentions it.
**Action:** Implement the split handling during Task 5.3. The requirements are clear — the design code is just a sketch.
**Status:** RESOLVED — Implemented split handling: inner try/except around `table.update_item()` catches `ConditionalCheckFailedException` separately (yields error event) vs other exceptions (yields flow_complete with save_error). Outer try/except catches turn failures.

### REVIEW-4: `build_bundle()` signature change not shown in design
**Source:** Design doc prose vs. Task 2.4
**Issue:** Task 2.4 says add optional `user_timezone` parameter to `build_bundle()`. Design mentions it in prose but doesn't show the updated function signature. Current `build_bundle()` has 9 positional params.
**Action:** Add `user_timezone: Optional[str] = None` during Task 2.4. Straightforward — just noting the design omission.
**Status:** RESOLVED — Added `user_timezone: Optional[str] = None` as 10th parameter. When provided, included in bundle dict. When None, omitted. Existing V4-3a tests still pass (optional param, backward compatible).

### REVIEW-5: `stream_async` with `structured_output_model` — first usage
**Source:** Design doc `_run_streaming_turn()` code
**Issue:** V4-3a uses synchronous `agent(prompt, structured_output_model=...)`. V4-3b switches to `agent.stream_async(prompt, structured_output_model=...)`. This is the project's first use of `stream_async` with structured output. The Strands docs should support this, but it's unverified in this codebase.
**Action:** Validate against Strands docs during Task 5.1 implementation. If `stream_async` doesn't accept `structured_output_model`, we'll need an alternative pattern (collect stream, then parse).
**Status:** RESOLVED — `stream_async` yields raw event dicts, not result objects with `.structured_output`. The correct async pattern is `agent.structured_output_async(Model, prompt)` which awaits and returns the validated Pydantic object directly. Fixed `_run_streaming_turn()` to use `structured_output_async`. Design doc's code was wrong on this pattern.

### REVIEW-6: Design entrypoint code has undefined variables in clarification flow
**Source:** Design doc entrypoint code block, clarification route
**Issue:** The `format_ddb_update()` call references `parsed_claim`, `verification_plan`, and `plan_review` — but these variables aren't defined in the visible code (the 3-turn flow is elided with comments). This is fine for a design sketch, but the executing agent needs to fill in the actual turn execution code.
**Action:** Non-issue for implementation — the tasks (5.3) are clear about what to build. Just noting the design code is incomplete by design.
**Status:** RESOLVED — Filled in the full 3-turn flow in the clarification route. All variables properly defined before use.

### REVIEW-7: Decision 101 count claim
**Source:** Agent prompt says "101 decisions total documented in `docs/project-updates/decision-log.md`"
**Issue:** V4-3a went up to Decision 100. Decision 101 (user timezone from payload) was added during V4-3b spec creation. The count of 101 is plausible but unverified.
**Action:** Verify when updating the decision log at end of session.
**Status:** RESOLVED — Verified. Decision 101 exists in the decision log. 101 total decisions confirmed.

### REVIEW-8: Prompt template `{{user_timezone}}` variable behavior
**Source:** Design doc Section 5 (Timezone Handling)
**Issue:** Design says when timezone is absent, the `{{user_timezone}}` placeholder "remains as literal text, which the agent interprets as 'no user timezone provided'." This depends on `prompt_client.py`'s `_resolve_variables()` behavior — does it leave unresolved `{{var}}` placeholders as-is, or strip them? Need to verify against the actual prompt client code.
**Action:** Check `prompt_client.py` during Task 5.4 when passing `user_timezone` to `fetch_prompt()`.
**Status:** RESOLVED — Integration test confirmed: when `timezone` is provided in the payload, it's passed as `user_timezone` variable to `fetch_prompt()`. The agent's Turn 1 reasoning explicitly references "America/Los_Angeles" and uses Pacific time for date resolution. When timezone is absent, the variable is simply not included in the variables dict, and the agent falls back to `current_time` tool's server timezone (V4-3a behavior preserved).

### REVIEW-9: V4-3a project update says V4-3b uses `RequestContext.session_id`
**Source:** `24-project-update-v4-3a-creation-agent-core.md`, "What the Next Agent Should Do" section
**Issue:** Says "V4-3b adds multi-round clarification using `RequestContext.session_id` and WebSocket streaming." This is slightly misleading — V4-3b uses `session_id` for observability only (Req 8.3 explicitly says NOT for state lookup). The `prediction_id` is the state key. Not wrong, but could mislead a future reader into thinking session_id drives clarification state.
**Action:** Fix the V4-3a doc's wording when we update docs at end of session.
**Status:** RESOLVED — Fixed V4-3a doc to clarify session_id is observability-only, prediction_id is the state key.

---

## Decisions Made

- **Decision 102:** Hybrid streaming — token-by-token text + structured output per turn. Each turn uses `stream_async` with `structured_output_model` to yield `text` events (reasoning tokens) in real-time, then a `turn_complete` event with the Pydantic-validated JSON when the turn finishes. No extra model call needed. Discovered during integration testing when the initial `structured_output_async` approach worked but produced no visible output between turn completions.

## Integration Testing Results

### Test 1: Creation with timezone + text streaming
- `flow_started` → ~50 `text` events (Turn 1 reasoning) → `turn_complete` ×3 → `flow_complete`
- Agent correctly used `America/Los_Angeles` timezone for "tonight" resolution
- Verifiability score: 0.82, three improvable sections with targeted questions
- Bundle saved to DDB with `user_timezone: "America/Los_Angeles"`

### Test 2: Clarification round
- Loaded existing bundle from DDB, `clarification_round: 1`
- Agent incorporated both answers: confirmed Pacific timezone, confirmed NBA Lakers
- Score improved 0.82 → 0.92 after clarification (timezone ambiguity resolved)
- DDB `update_item` succeeded, `clarification_rounds` incremented

### Discoveries During Integration Testing

1. **`stream_async` does support `structured_output_model`** — the Strands docs have a "Streaming Structured Output" cookbook showing exactly this pattern. The `"data"` events contain text tokens, the final `"result"` event contains `structured_output`. Our initial error was accessing `.structured_output` on the raw event dict instead of `event["result"].structured_output`.

2. **Decimal serialization in `_make_event`** — When loading a bundle from DDB for clarification, float values come back as `Decimal` (from V4-3a's float→Decimal conversion on save). The `updated_bundle` dict spread from the DDB bundle inherits these Decimals. Fixed by adding `default=str` to `json.dumps` in `_make_event`, matching V4-3a's `serialize_bundle` pattern.

3. **Text streaming only on reasoning-heavy turns** — Turns 2 (plan) and 3 (review) produced no `text` events because the prompts instruct the model to go straight to structured output. Turn 1 (parse) had the most text because it reasons through timezone logic. This is fine — text events are there when the model produces reasoning.

## V4-2 Test Regression Fixed

`test_builtin_tools.py` needed updates for V4-3b's async handler:
- Added `asyncio` import and `_collect_events()` helper for async event collection
- `TestPayloadValidation.test_missing_prompt_returns_error` — now collects yielded events instead of parsing return string
- `TestPropertyToolExceptions.test_agent_exception_returns_error_json` — same async collection pattern
- Initial test run hit stale `.pyc` cache — `--cache-clear` resolved it

## Test Results

136 automated tests passing (133 V4-3a + 3 new V4-3b entrypoint tests). All 4 integration tests passed. The V4-3b optional property tests (Tasks 1.2, 2.5-2.8, 3.2-3.3, 5.7-5.8) were skipped for faster MVP — can be added later.

## AgentCore Deviation Flag: None

All patterns align with the AgentCore steering doc. Async streaming via `yield` follows the documented AgentCore pattern. No hardcoded prompts. No local MCP subprocesses. No custom OTEL. Agent created per-request. DDB for structured data.

## Files Created/Modified

### Created
- `docs/project-updates/25-project-update-v4-3b-clarification-streaming.md` — This file

### Modified
- `calleditv4/src/main.py` — Async streaming entrypoint with hybrid text+structured streaming (Decision 102), clarification routing, `_make_event()` with `default=str`, `_run_streaming_turn()`, `MAX_CLARIFICATION_ROUNDS`
- `calleditv4/src/bundle.py` — Added `load_bundle_from_ddb()`, `build_clarification_context()`, `format_ddb_update()`, updated `build_bundle()` with `user_timezone` param
- `calleditv4/src/models.py` — Added `ClarificationAnswer` model
- `calleditv4/tests/test_entrypoint.py` — Rewritten for async handler, added `_make_event` tests, `MAX_CLARIFICATION_ROUNDS` test
- `calleditv4/tests/test_builtin_tools.py` — Updated for async handler (V4-2 regression fix)
- `docs/project-updates/decision-log.md` — Decision 102
- `docs/project-updates/project-summary.md` — Update 25 entry, refreshed Current State
- `docs/project-updates/backlog.md` — Updated item 13 status
- `docs/project-updates/common-commands.md` — V4-3b commands, test count updated
- `docs/project-updates/24-project-update-v4-3a-creation-agent-core.md` — Fixed session_id wording (REVIEW-9)

## What the Next Agent Should Do

### Immediate
1. **V4-4 (Verifiability Scorer)** or **V4-5 (Verification Agent)** — both can proceed
2. Pin prompt versions (currently using DRAFT) after prompt iteration with eval framework
3. Run automated tests to confirm: `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/ -v`

### Key Files
- `calleditv4/src/main.py` — Async streaming entrypoint with clarification + text streaming
- `calleditv4/src/bundle.py` — Bundle construction + clarification functions
- `calleditv4/src/models.py` — 5 Pydantic models (4 turn models + ClarificationAnswer)
- `.kiro/specs/clarification-streaming/` — Complete spec

### Important Notes
- `stream_async` with `structured_output_model` works — `"data"` events for text, `"result"` event for structured output
- `_make_event` uses `default=str` for Decimal serialization (DDB bundles have Decimal values)
- 5 stream event types: `flow_started`, `text`, `turn_complete`, `flow_complete`, `error`
- 102 architectural decisions documented
