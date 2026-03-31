# Project Update 34 — DDB Cleanup + Eval Isolation + Brave Search + Architecture Audit

**Date:** March 30, 2026
**Context:** First session after the massive Update 33 (verification modes + TTY fix + prompt pinning). Started with a user observation — "I only see 5 predictions, not 53" — which led to a full infrastructure audit, DDB cleanup across two tables, a golden dataset addition, a fix for eval data leaking into the production table, and the addition of Brave Search as a verification tool that nearly doubled verdict accuracy.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- None — this was investigative work, targeted fixes, and a tool addition. No formal spec.

### Prerequisite Reading
- `docs/project-updates/33-project-update-verification-modes.md` — Previous session context
- `docs/architecture-v4-infrastructure.md` — Architecture diagram created this session

---

## What Happened This Session

The user noticed they could only see 5 predictions in the frontend, despite the scanner having processed 53. This led to a deep infrastructure investigation that uncovered multiple issues: v3 data in the wrong table, eval data leaking into production, missing Browser IAM permissions, and ultimately the discovery that the AgentCore Browser tool doesn't work in the deployed runtime at all. The session pivoted to adding Brave Search as an alternative, which nearly doubled verification accuracy.

### Phase 1: The PK Format Investigation

The user suspected v3 and v4 used different DynamoDB partition key formats. Investigation confirmed:

- **v3 format** (`calledit-db` table): `PK=USER:{cognito_sub}`, `SK=PREDICTION#{timestamp}`
- **v4 format** (`calledit-v4` table): `PK=PRED#{prediction_id}`, `SK=BUNDLE`, with `user_id` as a GSI attribute

The v4 ListPredictions Lambda queries the `user_id-created_at-index` GSI on `calledit-v4`, filtering by the Cognito sub from the JWT. The user's 5 real predictions were correctly visible. The 53 "processed" predictions from the scanner were eval artifacts with `user_id=eval-runner` or `user_id=anonymous`.

### Phase 2: v3 Table Cleanup + Golden Dataset Addition

The `calledit-db` table had 18 items: 9 v3-format predictions and 9 v4-format test leftovers. Reviewed all 9 v3 predictions against the golden dataset. One unique case found: "friday will be a beach day" — multi-criteria weather (temp ≥70°F + wind ≤10mph) at Jones Beach NY, with user clarification that transformed a vague subjective prediction into an objective one. Added as **base-055** to the golden dataset. Deleted all 18 items from `calledit-db`.

### Phase 3: Architecture Audit

Created `docs/architecture-v4-infrastructure.md` — a full diagram of all CloudFormation stacks, DDB tables, and data flows. Key findings:

- 6 CF stacks (CalledIt-related), 6 DDB tables
- Cognito lives in the v3 `calledit-backend` stack (shared with v4)
- `calledit-verification-scanner` (old v3 stack) is still deployed but dead
- `calledit-v4-eval` table exists and is correctly separate from production

### Phase 4: The Eval Data Leak Fix (Decision 143)

The architecture audit revealed the creation eval runner was writing bundles to `calledit-v4` (production) because the creation agent always writes to its configured table. Fixed by adding `table_name` payload override to the creation agent's HTTP handler, matching the verification agent's pattern. The eval runner now passes `calledit-v4-eval`. Post-eval cleanup deletes bundles from the eval table. Verified: production table stays clean during eval runs.

Cleaned 64 junk items from `calledit-v4` (50 eval-runner + 13 anonymous + 1 eval-debug).

### Phase 5: Browser IAM Investigation

The verification agent's Browser tool was failing with "access restrictions." Investigation revealed the AgentCore execution role had Code Interpreter permissions but zero Browser permissions. Added Browser IAM policy via `infrastructure/agentcore-permissions/setup_agentcore_permissions.sh`. However, even after adding permissions and relaunching the verification agent, the Browser tool still failed in the deployed runtime. The Browser works fine when called directly via the AgentCore MCP power (local credentials), confirming it's a runtime-specific issue, not an IAM issue.

Root cause: unclear. The Strands `AgentCoreBrowser` wrapper inside the AgentCore Runtime container fails silently. This remains an open investigation item.

### Phase 6: Brave Search Tool (Decision 145)

Pivoted to Brave Search API as the primary web search tool. Built `calleditv4-verification/src/brave_search.py` — a simple `@tool` function that calls the Brave Search API via HTTP GET. Wired into the verification agent's TOOLS list ahead of Browser. Updated the verification executor prompt to prefer `brave_web_search` for fact-finding and use Browser only as a fallback for interactive pages.

Deployed with `agentcore launch --env BRAVE_API_KEY=...`. Also deployed updated prompt via CloudFormation.

### Phase 7: Full Eval Baselines

Ran all three eval frameworks with `--tier full` (all cases + judges):

**Creation Agent (55 cases):**
- IP=0.79 (0.86 excluding 5 judge JSON parse failures)
- PQ=0.56 (0.58 excluding 2 judge failures)
- All T1=1.00
- 7 LLM judge failures (empty response → JSON parse error → score 0)

**Verification Agent (7 immediate cases):**
- VA=0.71 (was 0.43) — **+65% improvement**
- EQ=0.56 (was 0.46)
- 5/7 correct verdicts (was 3/7)
- base-010: `refuted` — actually CORRECT (see analysis below)
- base-013: `inconclusive` — real failure (needs URL fetch tool)
- **Corrected VA: 6/7 = 0.86** (base-010 is a false failure)

**Calibration (7 cases, creation→verification chain):**
- CA=0.86 (was 0.43) — **+100% improvement**
- 6/7 calibrated correctly
- Only failure: base-013 (Wikipedia, same as verification)

### Phase 8: Deep Analysis of Remaining Failures

**base-010 (full moon before April 1) — FALSE FAILURE in golden dataset:**
The golden dataset expected `confirmed` because when written, the next full moon was March 3, 2026 (before April 1). But the eval ran on March 30-31 — the March 3 full moon has passed, and the next one is April 2, 2026 (after April 1). The prediction is now false. The agent correctly returned `refuted`. The golden dataset needs updating — this is a time-sensitive ground truth that expired. **Action: update base-010 expected_verdict to `refuted` or mark as time-sensitive.**

**base-013 (Wikipedia AI article > 500 refs) — TOOL LIMITATION:**
Brave search finds the Wikipedia article but can't count references. The Browser tool (which could fetch and parse the page) doesn't work in the runtime. This case needs either a working Browser or a dedicated URL fetch tool. **Action: add a URL fetch `@tool` function, similar to brave_search.py but for fetching page content.**

**LLM judge JSON parse failures (7 cases):**
The judge model (Opus 4.6) occasionally returns empty responses instead of JSON. This is intermittent — the same cases succeed on other runs. The evaluator catches the error and scores 0, which drags down averages. **Action: add a single retry on empty response in the judge evaluators.**

## Decisions Made

### Decision 143: Creation Agent Accepts table_name Override for Eval Isolation

**Source:** This update — eval data leak investigation
**Date:** March 30, 2026

The creation agent's HTTP handler accepts an optional `table_name` field in the payload, defaulting to `DYNAMODB_TABLE_NAME` env var. Matches the verification agent's pattern (Decision 130). The WebSocket handler does NOT accept this override. The eval runner passes `calledit-v4-eval` and cleans up after.

### Decision 144: Browser IAM Permissions Added (But Browser Still Broken in Runtime)

**Source:** This update — Browser investigation
**Date:** March 30, 2026

Added full Browser IAM permissions to the AgentCore execution role via `setup_agentcore_permissions.sh`. The Browser API works when called directly but fails inside the deployed AgentCore Runtime. Root cause unknown. Browser remains in the TOOLS list as a fallback but is not relied upon.

### Decision 145: Brave Search as Primary Web Search Tool for Verification

**Source:** This update — Browser workaround
**Date:** March 30, 2026

Added `brave_web_search` as a Strands `@tool` function in the verification agent. Calls the Brave Search API via HTTP GET with the free-tier API key. Placed first in the TOOLS list, ahead of Browser. The verification executor prompt was updated to prefer `brave_web_search` for all fact-finding. This single change improved verdict accuracy from 0.43 to 0.86 (corrected).

## Files Created/Modified

### Created
- `calleditv4-verification/src/brave_search.py` — Brave Search `@tool` function
- `docs/project-updates/34-project-update-ddb-cleanup-and-eval-isolation.md` — this update
- `docs/architecture-v4-infrastructure.md` — full infrastructure diagram
- `infrastructure/agentcore-permissions/setup_agentcore_permissions.sh` — consolidated permissions script

### Modified
- `calleditv4/src/main.py` — `table_name` payload override in `handler()`
- `calleditv4-verification/src/main.py` — added `brave_web_search` to TOOLS, `AgentCoreBrowser(region="us-west-2")`
- `eval/backends/agentcore_backend.py` — `table_name` parameter on `AgentCoreBackend`
- `eval/creation_eval.py` — `EVAL_TABLE_NAME`, backend with eval table, post-eval cleanup
- `eval/golden_dataset.json` — added base-055 (beach day), metadata updated (55 base, 31 at_date)
- `infrastructure/prompt-management/template.yaml` — verification executor prompt updated with Brave search priority
- `docs/project-updates/decision-log.md` — Decisions 143-145

### Deleted
- `infrastructure/agentcore-permissions/setup_eval_table_permissions.sh` — replaced by consolidated script
- `calledit-db`: all 18 items (9 v3 + 9 test leftovers)
- `calledit-v4`: 64 eval/test items (50 eval-runner + 13 anonymous + 1 eval-debug)

## Eval Baselines (March 30, 2026)

| Metric | Previous | Current | Change |
|--------|----------|---------|--------|
| Creation IP | 0.88 | 0.79 (0.86 adj) | -0.02 adj (judge noise) |
| Creation PQ | 0.57 | 0.56 (0.58 adj) | +0.01 adj |
| Verification VA | 0.43 | 0.71 (0.86 adj) | **+0.43 adj** |
| Verification EQ | 0.46 | 0.56 | +0.10 |
| Calibration CA | 0.43 | 0.86 | **+0.43** |

*adj = adjusted for false failures (base-010) and judge JSON parse errors*

## What the Next Agent Should Do

### Priority 1: Fix base-010 Golden Dataset Entry
Update `expected_verification_outcome` for base-010 to `refuted` (or add a `time_sensitive` flag). The agent is getting the right answer — the eval is scoring it wrong.

### Priority 2: Add URL Fetch Tool
base-013 (Wikipedia ref counting) needs page content, not just search results. A simple `@tool` function that fetches a URL and returns the text content would fix this.

### Priority 3: Fix LLM Judge JSON Parse Failures
Add a single retry on empty response in `eval/evaluators/intent_preservation.py` and `eval/evaluators/plan_quality.py`.

### Priority 4: Investigate Browser Runtime Issue
The AgentCore Browser tool works via direct API calls but fails inside the deployed runtime. Low priority since Brave covers the primary use case.

### Priority 5: Verification Planner Self-Report Plans (Backlog Item 15)
Plan quality is still 0.56-0.58. Teaching the planner to build self-report plans remains the highest-impact prompt change for creation quality.

### Key Files
- `calleditv4-verification/src/brave_search.py` — Brave Search tool
- `calleditv4-verification/src/main.py` — TOOLS list with brave_web_search first
- `infrastructure/prompt-management/template.yaml` — verification executor prompt (Brave priority)
- `infrastructure/agentcore-permissions/setup_agentcore_permissions.sh` — all AgentCore IAM permissions
- `eval/reports/creation-eval-20260330-234209.json` — full creation baseline (55 cases)
- `eval/reports/verification-eval-20260331-000757.json` — full verification baseline (7 cases)
- `eval/reports/calibration-eval-20260331-005832.json` — full calibration baseline (7 cases)
