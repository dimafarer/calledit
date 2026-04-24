# Project Update 41 — Continuous Eval Dashboard Fixes Spec

**Date:** April 24, 2026
**Context:** Speccing three bugfixes in the Continuous Eval dashboard — all discovered during Update 40 integration testing.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/continuous-eval-dashboard-fixes/` — Bugfix spec (requirements COMPLETE, design + tasks PENDING)

### Prerequisite Reading
- `docs/project-updates/40-project-update-continuous-verification-eval-spec.md` — Full continuous eval implementation context
- `.kiro/specs/continuous-eval-dashboard-fixes/bugfix.md` — Bugfix requirements document

---

## What Happened

### The Problem

Update 40 delivered the full continuous verification eval system — 12 tasks, 129 tests, integration tested. But three display/data bugs surfaced during manual dashboard review:

1. **Resolution Rate Chart lines invisible at boundaries** — When `resolution_rate=1.0` the green line sits on the top border of the Y-axis `[0, 1]` domain and blends with the grid line. Same for `stale_inconclusive_rate=0.0` at the bottom. Both lines are technically rendered but visually invisible.

2. **Scatter plot missing inconclusive cases** — The CalibrationScatter chart requires both `verifiability_score` AND `actual_verdict` to be non-null. Inconclusive cases from the continuous eval have `cs.verdict = "inconclusive"` but `cs.status = "inconclusive"` (not `"resolved"`), so the `vresult` construction in `_run_verification_pass()` skips them. `actual_verdict` stays `None`, and the scatter plot filters them out.

3. **Pass numbering always "Pass 1"** — Each `--once --resume` or `--verify-only` invocation starts `pass_num` at 0 in the `run()` method, regardless of how many passes were previously completed. The state file saves `pass_number=1` after the first pass, but the next invocation ignores it and starts from 0 again.

### The Approach

Used Kiro's bugfix spec workflow to create a structured requirements document with three sections per the bug condition methodology:

- **Current Behavior (Defect)** — 5 clauses (1.1–1.5) documenting exactly what goes wrong and why
- **Expected Behavior (Correct)** — 5 clauses (2.1–2.5) documenting the fix behavior
- **Unchanged Behavior (Regression Prevention)** — 6 clauses (3.1–3.6) protecting existing working behavior

### Key Files

| Bug | File | Nature |
|-----|------|--------|
| 1 (chart lines) | `frontend-v4/src/pages/EvalDashboard/components/ResolutionRateChart.tsx` | Frontend — Y-axis domain + dot radius |
| 2 (scatter plot) | `eval/run_eval.py` — `_run_verification_pass()` | Backend — vresult construction condition |
| 3 (pass numbering) | `eval/run_eval.py` — `run()` | Backend — pass_num initialization from state |

### Decisions Made

**Decision 153: Dev Server DDB Projection Missing calibration_scores (Real Root Cause of Bug 1)**

The ResolutionRateChart was completely invisible — not because of Y-axis domain clipping, but because the Vite dev server's report list API (`frontend-v4/server/eval-api.ts`) only projected `run_metadata` and `aggregate_scores` from DDB. The chart reads `resolution_rate` and `stale_inconclusive_rate` from `calibration_scores`, which was never fetched. The production Lambda handler already had the correct projection. Fix: added `calibration_scores`, `creation_scores`, and `verification_scores` to the dev server's `ProjectionExpression`. Also applied Y-axis domain padding (`[-0.05, 1.05]`) and increased dot radius (4→6) as a secondary improvement for boundary visibility.

**Decision 154: Include Inconclusive Cases in Verification Result Construction**

The `_run_verification_pass()` vresult condition changes from `cs.status == "resolved"` to `cs.status in ("resolved", "inconclusive")`. Inconclusive is a valid verification outcome — the agent attempted verification and couldn't reach a definitive answer. The scatter plot should show these cases (at `y=0.5` for inconclusive) so users can see the full distribution of verification outcomes, not just the resolved ones. Cases with no verdict (`cs.verdict is None`, status `"pending"` or `"error"`) continue to be excluded.

**Decision 155: Resume Pass Numbering from Saved State**

When `--resume` loads existing state, `pass_num` starts from `self.state.pass_number` (the last completed pass) instead of hardcoded 0. Fresh state (no `--resume`) continues to start from 0, so the first pass is always numbered 1. This ensures sequential pass numbering across separate CLI invocations: if the last run completed pass 3, the next `--once --resume` run starts at pass 4.

## Current State

- Bugfix requirements: COMPLETE (5 defect clauses, 5 fix clauses, 6 regression prevention clauses)
- Bugfix design: COMPLETE
- Bugfix tasks: COMPLETE — all 4 tasks executed, 134/134 tests passing
- All three code fixes applied:
  - Bug 1: Y-axis domain `[-0.05, 1.05]` + dot radius 6 + **real root cause**: dev server DDB projection missing `calibration_scores` (Decision 153)
  - Bug 2: Status filter widened to `("resolved", "inconclusive")` in `_run_verification_pass()`
  - Bug 3: `pass_num = self.state.pass_number` in `run()`
- Dev server projection fix: `eval-api.ts` now matches production Lambda projection
- Continuous eval Pass 2 completed: pass numbering fix confirmed (labeled "Pass 2")
- Resolution Rate chart now rendering with visible data
- 155 architectural decisions documented

## Investigation: Verification Agent "No Prediction Statement" Issue

During Pass 2 review, discovered that base-004 (S&P 500) and other cases returned `inconclusive` with reasoning "No prediction statement or verification plan was provided." Investigation revealed:

1. **Not a prompt issue** — local Strands Agent test with the same prompt, model, and tools correctly verified base-004 as REFUTED (S&P 500 closed 0.03 points lower on April 20 vs April 19). The agent used 14 Brave Search calls, found specific closing prices from Reuters and CNBC, and produced a well-reasoned verdict.

2. **Not a data issue** — the DDB bundle has valid `parsed_claim.statement`, `verification_plan` with sources/criteria/steps, and `verification_date`. The `_build_user_message()` produces a 1128-char well-formed message.

3. **Likely a deployed runtime issue** — the AgentCore-deployed verification agent is returning "No prediction statement" while the identical code running locally works perfectly. Possible causes: stale deployment, missing env vars (BRAVE_API_KEY), or payload handling differences in the AgentCore runtime.

**Decision 156: Local Strands Script for Verification Agent Smoke Testing**

Before deploying prompt or code changes to AgentCore, test locally with a plain Strands Agent script (`eval/test_verification_prompt.py`). This bypasses AgentCore entirely — same model, same prompt, same tools, direct Bedrock invocation. Faster iteration (30-120s vs 5min timeout), no deployment needed, and isolates prompt/agent issues from runtime issues.

**Next step:** Test with `agentcore dev` locally to determine if the issue is in the AgentCore runtime packaging or the deployed version specifically. If `agentcore dev` works, the fix is a redeployment. If it fails the same way, the issue is in the AgentCore handler code.

## Verification Agent Redeployment — BRAVE_API_KEY Fix

**Root cause confirmed:** The deployed verification agent was missing the `BRAVE_API_KEY` environment variable (Decision 157). Every Brave Search call silently returned empty results, causing the LLM to produce vague "No prediction statement" reasoning.

**Diagnosis path:**
1. Local Strands script → REFUTED (correct) — proved prompt and agent logic work
2. `agentcore dev` locally → REFUTED (correct) — proved handler code works
3. Deployed agent → "No prediction statement" (wrong) — isolated to deployment
4. Redeployed with `--env "BRAVE_API_KEY=$BRAVE_API_KEY"` → REFUTED (correct)

**Code improvements applied:**
- `brave_search.py`: startup warning when `BRAVE_API_KEY` missing, clearer error message in tool response
- `main.py`: startup log error when `BRAVE_API_KEY` not set
- Removed stale TTY steering directive (was blocking `agentcore dev` usage)

**Verification result for base-004 (S&P 500):**
- Verdict: REFUTED (confidence 0.8)
- S&P 500 closed at 7,109.14 on April 20, 2026 (Monday)
- Previous trading day (April 17, Friday) closed at 7,126.06
- April 19 was a Sunday — no market data (creation agent quality signal: parser should handle weekends)

## Current State

- Bugfix spec: ALL TASKS COMPLETE, 134/134 tests passing
- Dashboard fixes: Resolution Rate chart rendering, Y-axis padding, dot radius, dev server projection
- Backend fixes: inconclusive vresult construction, pass numbering from state
- Verification agent: redeployed with BRAVE_API_KEY, base-004 verified correctly as REFUTED
- 157 architectural decisions documented

## What the Next Agent Should Do

1. Run continuous eval Pass 3 to validate all fixes end-to-end with the redeployed agent
2. Consider CDK migration for AgentCore deployment (declarative env vars, IaC)
3. Deploy frontend to production
4. Expand golden dataset (backlog item 21)
