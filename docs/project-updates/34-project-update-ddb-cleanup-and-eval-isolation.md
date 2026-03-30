# Project Update 34 — DDB Cleanup + Eval Table Isolation + Architecture Audit

**Date:** March 30, 2026
**Context:** First session after the massive Update 33 (verification modes + TTY fix + prompt pinning). Started with a user observation — "I only see 5 predictions, not 53" — which led to a full infrastructure audit, DDB cleanup across two tables, a golden dataset addition, and a fix for eval data leaking into the production table.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- None — this was investigative work and targeted fixes, no formal spec

### Prerequisite Reading
- `docs/project-updates/33-project-update-verification-modes.md` — Previous session context
- `docs/architecture-v4-infrastructure.md` — Architecture diagram created this session

---

## What Happened This Session

The user noticed they could only see 5 predictions in the frontend, despite the scanner having processed 53. The initial hypothesis was a PK format mismatch between v3 and v4. That turned out to be partially right — but the real story was more interesting.

### Phase 1: The PK Format Investigation

The user suspected the v3 and v4 systems used different DynamoDB partition key formats, causing predictions to be invisible. Investigation confirmed:

- **v3 format** (`calledit-db` table): `PK=USER:{cognito_sub}`, `SK=PREDICTION#{timestamp}`
- **v4 format** (`calledit-v4` table): `PK=PRED#{prediction_id}`, `SK=BUNDLE`, with `user_id` as a GSI attribute

The v4 ListPredictions Lambda queries the `user_id-created_at-index` GSI on `calledit-v4`, filtering by the Cognito sub from the JWT. The user's 5 real predictions (user_id `f8f16330-f021-7089-e876-7eb886472fb1`) were correctly visible. The 53 "processed" predictions from the scanner were actually eval artifacts with `user_id=eval-runner` or `user_id=anonymous` — invisible to the frontend but consuming scanner cycles.

### Phase 2: v3 Table Cleanup + Golden Dataset Addition

The `calledit-db` table had 18 items: 9 v3-format predictions and 9 v4-format test leftovers. We reviewed all 9 v3 predictions against the golden dataset (54 cases) to identify any unique coverage:

1. "I'll enjoy the movie I'm seeing tonight" — covered by base-027
2. "It will rain in Seattle tomorrow" — covered by base-005 (London rain)
3. "The Yankees will win their game this weekend" — covered by base-047 (Lakers)
4. "I'll enjoy the movie I'm seeing tonight got" — duplicate of #1 with typo
5. "DR will win the Game tonight" — covered by base-018 (DR WBC) and base-047
6. "Bitcoin will hit 10,00000 by 2030" — covered by base-014 and base-053
7. **"friday will be a beach day"** — UNIQUE. Multi-criteria weather (temp ≥70°F + wind ≤10mph) at Jones Beach NY, with user clarification that transformed a vague subjective prediction into an objective one. Not covered by any existing case.
8. "Next friday is a beach day" — same concept as #7, second round
9. "Christmas 2025 was on a Thursday" — covered by base-002

Added the beach day prediction as **base-055** to the golden dataset. It covers a unique pattern: compound weather criteria + clarification-driven objectification. Updated metadata: `expected_base_count=55`, `at_date` mode count from 30→31.

Deleted all 18 items from `calledit-db`. The table is now empty. This cleanup was correct but ultimately irrelevant to v4 — the v4 frontend never reads from `calledit-db`.

### Phase 3: Architecture Audit

The user asked for a full infrastructure diagram to make sure we were aligned. Traced all CloudFormation stacks, DDB tables, and data flows. Key findings documented in `docs/architecture-v4-infrastructure.md`:

**6 CloudFormation stacks** (CalledIt-related):
- `calledit-v4-persistent-resources` — S3 bucket + `calledit-v4` table + `calledit-v4-eval-reports` table
- `calledit-v4-frontend` — CloudFront, HTTP API, 4 Lambdas (PresignedUrl, ListPredictions, ListEvalReports, GetEvalReport)
- `calledit-v4-scanner` — EventBridge + Scanner Lambda → `calledit-v4` GSI → SigV4 to AgentCore
- `calledit-prompts` — Bedrock Prompt Management (shared v3/v4)
- `calledit-backend` — v3 legacy, but owns Cognito (shared with v4)
- `calledit-verification-scanner` — old v3 scanner, effectively dead (`VERIFICATION_AGENT_ID=""`)

**6 DDB tables** (CalledIt-related):
- `calledit-v4` — main production predictions (now 5 items, clean)
- `calledit-v4-eval-reports` — eval dashboard data
- `calledit-v4-eval` — temp eval bundles (separate from production, 0 items)
- `calledit-db` — v3 legacy (now empty)
- `calledit-eval-reasoning` — v3 eval traces (legacy)

### Phase 4: The Eval Data Leak

The architecture audit revealed the real problem: **the creation eval runner was writing bundles to `calledit-v4` (the production table)**, not the eval table. Here's why:

- The **verification eval** runner writes temp bundles to `calledit-v4-eval` and passes a `table_name` override to the verification agent. Clean separation.
- The **creation eval** runner invokes the real AgentCore creation agent via HTTPS+JWT. The agent's handler always writes to its configured `DYNAMODB_TABLE_NAME` env var (`calledit-v4`). The eval runner had no way to override this.
- The **calibration eval** chains both — creation writes to `calledit-v4`, then calibration copies to `calledit-v4-eval` for verification. So the main table still gets the creation artifact.

This is how 50 `eval-runner` + 13 `anonymous` + 1 `eval-debug` items ended up in the production table. The scanner then found them all and verified them — that's where the "53 predictions processed" came from.

### Phase 5: The Fix — table_name Override for Creation Agent

Applied the same pattern the verification agent already uses (Decision 130):

1. **`calleditv4/src/main.py`** — Added `table_name = payload.get("table_name", DYNAMODB_TABLE_NAME)` at the top of `handler()`. All 4 DDB references in the HTTP handler now use `table_name` instead of the hardcoded constant. The `websocket_handler()` (browser-facing) was intentionally NOT changed — browser payloads should not control which table gets written to.

2. **`eval/backends/agentcore_backend.py`** — Added `table_name` parameter to `AgentCoreBackend.__init__()`. When set, it's included in the payload sent to the agent. The creation eval runner passes `calledit-v4-eval`.

3. **`eval/creation_eval.py`** — Backend now constructed with `table_name=EVAL_TABLE_NAME`. Added post-eval cleanup that deletes bundles from the eval table after scoring (matching the calibration eval pattern).

4. **IAM** — Already covered. The AgentCore execution role (`AmazonBedrockAgentCoreSDKRuntime-us-west-2-37c792a758`) already had `calledit-v4-eval-dynamodb` policy from the verification eval setup.

Verified: ran a single-case smoke eval (base-002). `calledit-v4` stayed at 5 items, `calledit-v4-eval` went to 1 during the run and back to 0 after cleanup. All 148 creation agent tests pass.

### Phase 6: Production Table Cleanup

Deleted 64 junk items from `calledit-v4`:
- 50 `user_id=eval-runner` (from creation eval runs, then scanner-verified)
- 13 `user_id=anonymous` (from test predictions)
- 1 `user_id=eval-debug` (debug test)

Kept the 5 real predictions (`user_id=f8f16330-f021-7089-e876-7eb886472fb1`). The scanner will no longer waste invocations on eval artifacts.

## Decisions Made

### Decision 143: Creation Agent Accepts table_name Override for Eval Isolation

**Source:** This update — eval data leak investigation
**Date:** March 30, 2026

The creation agent's HTTP handler (`handler()` in `calleditv4/src/main.py`) accepts an optional `table_name` field in the payload, defaulting to `DYNAMODB_TABLE_NAME` env var. This matches the verification agent's pattern (Decision 130). The eval runner passes `calledit-v4-eval` to isolate eval bundles from production data. The WebSocket handler (browser-facing) does NOT accept this override — browser payloads should not control DDB routing. The eval runner also cleans up bundles from the eval table after scoring.

## Files Created/Modified

### Created
- `docs/project-updates/34-project-update-ddb-cleanup-and-eval-isolation.md` — this update
- `docs/architecture-v4-infrastructure.md` — full infrastructure diagram with all stacks, tables, and data flows

### Modified
- `calleditv4/src/main.py` — `table_name` payload override in `handler()` (4 DDB references updated)
- `eval/backends/agentcore_backend.py` — `table_name` parameter on `AgentCoreBackend`, included in agent payload
- `eval/creation_eval.py` — `EVAL_TABLE_NAME` constant, backend constructed with eval table, post-eval cleanup
- `eval/golden_dataset.json` — added base-055 (beach day, multi-criteria weather + clarification), metadata updated (55 base, 31 at_date)

### Deleted (DDB, not files)
- `calledit-db`: all 18 items (9 v3 predictions + 9 test leftovers) — table now empty
- `calledit-v4`: 64 eval/test items (50 eval-runner + 13 anonymous + 1 eval-debug) — table now has 5 real predictions only

## What the Next Agent Should Do

### Priority 1: Run Full Eval Baselines
Run smoke+judges on creation eval to get the first baseline with mode classification data and the new eval isolation. Verify `calledit-v4` stays clean after the run.

### Priority 2: Verification Planner Self-Report Plans (Backlog Item 15)
Plan quality baseline is 0.57. The 5 personal/subjective cases average ~0.26. Teaching the planner to build self-report plans is the highest-impact prompt change. Target: PQ ≥ 0.75.

### Priority 3: Tool Action Tracking (Backlog Item 16)
4/7 verification failures are Browser tool inability. Structured tracking would identify which tool to add or prompt to fix next.

### Priority 4: Dead Stack Cleanup
`calledit-verification-scanner` (old v3 scanner) is still deployed but dead — `VERIFICATION_AGENT_ID=""`, points to empty `calledit-db`. Should be deleted. `calledit-db` table itself could also be deleted since it's now empty and nothing reads from it.

### Key Files
- `docs/architecture-v4-infrastructure.md` — infrastructure diagram (reference for any future infra questions)
- `calleditv4/src/main.py` — `table_name` override at line ~225
- `eval/backends/agentcore_backend.py` — `table_name` parameter
- `eval/creation_eval.py` — `EVAL_TABLE_NAME` + cleanup logic
- `eval/golden_dataset.json` — 55 base predictions (base-055 = beach day)
