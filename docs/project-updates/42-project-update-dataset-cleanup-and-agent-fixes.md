# Project Update 42 — Dataset Cleanup & Verification Agent Fixes

**Date:** April 24, 2026
**Context:** Fixing continuous eval dashboard bugs, diagnosing and fixing verification agent BRAVE_API_KEY issue, deploying CDK permissions stack, planning golden dataset v5 cleanup.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/continuous-eval-dashboard-fixes/` — Dashboard bugfix spec (COMPLETE)
- `.kiro/specs/agentcore-cdk-migration/` — CDK migration spec (PARTIAL — deploy scripts + CDK stack done, agentcore.json deferred)
- `.kiro/specs/golden-dataset-v5/` — Dataset cleanup spec (PENDING)

### Prerequisite Reading
- `docs/project-updates/41-project-update-continuous-eval-dashboard-fixes-spec.md` — Dashboard fixes context
- `.kiro/specs/continuous-eval-dashboard-fixes/bugfix.md` — Three dashboard bugs
- `docs/architecture-v4-infrastructure.md` — Current infrastructure

---

## What Happened

### Session 1: Dashboard Bugfixes

Fixed three bugs in the Continuous Eval dashboard tab:

1. **Resolution Rate chart invisible** — Real root cause was the Vite dev server's `eval-api.ts` DDB projection missing `calibration_scores`. The production Lambda already had it. Secondary fix: Y-axis padding `[-0.05, 1.05]` + dot radius 4→6.

2. **Scatter plot missing inconclusive cases** — `_run_verification_pass()` only built `vresult` for `status == "resolved"`. Widened to `status in ("resolved", "inconclusive")`. Pass 2 showed 10 cases on scatter (up from 2).

3. **Pass numbering always "Pass 1"** — `pass_num` hardcoded to 0 on every invocation. Changed to `self.state.pass_number` for resume. Pass 2 correctly labeled.

134/134 tests passing (5 new property-based + preservation tests).

### Session 2: Verification Agent Diagnosis

Investigated why most continuous eval cases returned `inconclusive` with reasoning "No prediction statement or verification plan was provided."

**Diagnosis path:**
1. Local Strands script → base-004 correctly REFUTED (S&P 500 closed lower on April 20)
2. `agentcore dev` locally → also REFUTED correctly
3. Deployed agent → "No prediction statement" (wrong)
4. Root cause: `BRAVE_API_KEY` missing from deployed AgentCore runtime

The `brave_web_search` tool silently returned `{"error": "BRAVE_API_KEY not configured", "results": []}` on every call. The LLM had no evidence and produced vague reasoning.

**Fix:** Redeployed with `agentcore deploy --env BRAVE_API_KEY=$BRAVE_API_KEY`. Resolution rate jumped 0.25 → 0.50 on Pass 3.

### Session 3: CDK Permissions Stack

Built and deployed `infrastructure/agentcore-cdk/` — a CDK TypeScript stack that manages IAM inline policies on both AgentCore execution roles. Replaces the manual `setup_agentcore_permissions.sh` shell script with IaC.

Also created deploy helper scripts:
- `calleditv4/deploy.sh` — simple wrapper
- `calleditv4-verification/deploy.sh` — validates BRAVE_API_KEY before deploying

Deferred the full npm CLI migration (`agentcore.json`) — the Python toolkit works and the deploy scripts solve the env var problem.

### Session 4: Dataset Analysis

Audited the golden dataset for the planned full continuous eval run. Findings:

**Redundancies:**
- base-004 / base-046: both "S&P 500 will close higher today than yesterday"
- base-009 / base-052: both "US national debt exceeds $35 trillion"
- base-011 / dyn-imm-005: both "Python 3.13 has been officially released"

**Far-future cases (won't resolve during testing):**
- base-014: "Bitcoin $150K by December 2026" (8 months)
- base-050: "SpaceX Mars before 2030" (4 years)
- Should shorten to 1-2 weeks out

**Missing coverage:**
- No recently-happened sports scores, political events, or social events
- These test the verification agent's core capability (finding historical facts via Brave Search)

**Personal/subjective cases (keep all):**
- Sad-path baselines now (low v-score, quick inconclusive)
- Future memory integration test cases (when AgentCore Memory is wired up)

## Decisions Made

- Decision 153: Dev server DDB projection missing calibration_scores (real root cause of Bug 1)
- Decision 154: Include inconclusive cases in verification result construction
- Decision 155: Resume pass numbering from saved state
- Decision 156: Local Strands script for verification agent smoke testing
- Decision 157: Missing BRAVE_API_KEY was root cause of verification agent failures
- Decision 158: Migrate AgentCore deployment to CDK-based permissions with deploy scripts

## Current State

- Dashboard bugfix spec: COMPLETE (all tasks, 134/134 tests)
- CDK migration spec: PARTIAL (CDK stack deployed, deploy scripts created, agentcore.json deferred)
- Verification agent: redeployed with BRAVE_API_KEY, Pass 3 resolution_rate=0.50
- Continuous eval: 3 passes on smoke tier, 6/12 resolved
- 158 architectural decisions documented across 42 project updates
- TTY steering directive removed (was stale since March 27 fix)

## What the Next Agent Should Do

1. Execute golden dataset v5 cleanup (spec: golden-dataset-v5)
2. Run full continuous eval with cleaned dataset
3. Review each inconclusive/pending case — fix agent or fix case
4. Consider scheduling continuous eval (cron or EventBridge) so future-dated cases resolve automatically
