# Project Update 31 — V4-7a Eval Completion + Dashboard Spec

**Date:** March 26, 2026
**Context:** Completed V4-7a-3 verification agent eval (all tiers), specced V4-7a-4 (cross-agent calibration + React dashboard with DDB-backed report storage). Resolved backlog item 1 by design.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/verification-agent-eval/` — V4-7a-3 spec (COMPLETE — all tiers run)
- `.kiro/specs/cross-agent-calibration-dashboard/` — V4-7a-4 spec (requirements + design + tasks COMPLETE, ready for execution)

### Prerequisite Reading
- `docs/project-updates/30-project-update-v4-7a-eval-framework-redesign.md` — V4-7a-1 through V4-7a-3 narrative, decisions 122-130
- `eval/reports/verification-eval-20260326-021040.json` — V4-7a-3 smoke+judges baseline
- `eval/reports/verification-eval-20260326-022007.json` — V4-7a-3 full baseline

---

## What Happened This Session

This session had two phases: completing the V4-7a-3 verification agent eval (the remaining smoke+judges and full tier runs), and speccing V4-7a-4 (the capstone dashboard spec). Along the way, a conversation about report storage led to a significant design decision that resolves months of accumulated technical debt.

### Phase 1: V4-7a-3 Completion — The Full Baseline

The smoke+judges run (2 cases, 163s) added Tier 2 evaluators to the existing smoke baseline. Results confirmed what the smoke-only run hinted at:

- verdict_accuracy: 0.50 — base-002 (Christmas Friday) got `confirmed` correctly, base-011 (Python 3.13) got `inconclusive` when it should be `confirmed`. The agent couldn't reach python.org (timeouts, AccessDeniedException).
- evidence_quality: 0.55 — base-002 scored 0.3 (vague source names like "calendar_arithmetic"), base-011 scored 0.8 (the agent documented its failed Browser attempts with specific error details, which the judge rated as honest and well-structured).

The full run (7 cases, 460.6s) told the complete story:

| Case | Prediction | Verdict | Expected | Accuracy | Evidence Quality |
|------|-----------|---------|----------|----------|-----------------|
| base-001 | Sun rises tomorrow NYC | confirmed | confirmed | ✓ | 0.2 |
| base-002 | Christmas 2026 Friday | confirmed | confirmed | ✓ | 0.3 |
| base-009 | US debt > $35T | inconclusive | confirmed | ✗ | 0.7 |
| base-010 | Full moon before Apr 1 | refuted | confirmed | ✗ | 0.2 |
| base-011 | Python 3.13 released | inconclusive | confirmed | ✗ | 0.7 |
| base-013 | Wikipedia AI > 500 refs | inconclusive | confirmed | ✗ | 0.8 |
| base-040 | Sun rises tomorrow | confirmed | confirmed | ✓ | 0.3 |

**Aggregate: verdict_accuracy=0.43, evidence_quality=0.46, all Tier 1=1.00**

Two patterns jumped out immediately:

**Pattern 1: Tool capability is the bottleneck, not agent reasoning.** 3/4 verdict failures (base-009, base-011, base-013) were caused by the Browser tool failing to reach external sites. The agent correctly returned `inconclusive` when it couldn't gather evidence — the reasoning was sound, the tool just couldn't execute. This is a tool capability issue, not an agent quality issue. The evidence quality judge actually rewarded these cases (0.7-0.8) because the agent honestly documented its failed attempts with specific error messages.

**Pattern 2: Evidence quality inversely correlates with verdict correctness for computational cases.** When the agent uses Code Interpreter to compute answers (base-001, base-002, base-040), it gets the right verdict but produces vague evidence (source names like "astronomical_calculations" instead of real URLs). The judge penalizes this (0.2-0.3). When the agent tries Browser and fails, it documents the failures specifically and the judge rewards the honesty (0.7-0.8). This is a real signal — the verification agent needs to produce better-structured evidence even when using Code Interpreter.

**The base-010 anomaly:** The full moon case returned `refuted` with 0.9 confidence when the expected answer is `confirmed`. This is either a lunar calculation bug in the agent's Code Interpreter usage, or the golden dataset's expected outcome needs review. Worth investigating separately.

This led to a new backlog item (16): tool action tracking for the verification agent. We need structured data on what tool actions the agent attempts, which succeed, and which fail — so we can see patterns like "Browser → python.org: always fails" and know exactly which tool to add or prompt to fix next.

### Phase 2: V4-7a-4 Spec — The DDB Pivot

The V4-7a-4 spec started as "cross-agent calibration runner + HTML dashboard." But a conversation about how the dashboard loads reports led to a fundamental question: why are we still storing eval reports as local JSON files?

Decision 29 (March 14) said "local eval results, not DynamoDB — yet." That was 12 days and 3 eval runners ago. We were about to build a fourth component (the dashboard) on top of local files, which would mean four things to refactor when we eventually moved to DDB. The user called it out: "sounds like we are causing the eval framework technical debt."

They were right. So V4-7a-4 became three components instead of two:

1. **DDB Report Store** (`eval/report_store.py`) — shared module for reading/writing eval reports to a new `calledit-v4-eval-reports` table. All three runners write here; the dashboard reads from here. Local JSON files become backup, not source of truth. This resolves backlog item 1 by design rather than as a separate migration.

2. **Calibration Runner** (`eval/calibration_eval.py`) — chains creation agent → verification agent per case, compares verifiability_score vs actual verdict. The bridge metric from Decision 122 Tier 3.

3. **React Dashboard** — integrated as a `/eval` route in the existing `frontend-v4` React app. Not Streamlit. The user pushed for React because it enables real interactive overlays — multi-series line charts where you toggle runs on/off, scatter plots with hover-to-drill, side-by-side comparison panels. Streamlit can't do that well. Since the React app, Cognito auth, Vite build, and CloudFront deployment already exist, the infrastructure cost is zero.

The dashboard design includes an extensibility principle: tabs, aggregate scores, case table columns, and metadata display are all data-driven. Adding a new evaluator or a new agent type means the dashboard renders it automatically — no frontend code change. This matters because the project is fundamentally about experimentation — trying new evals and comparisons to find what best points to root cause issues.

### The DDB Schema Decision

The `calledit-v4-eval-reports` table is separate from `calledit-v4-eval` (temporary bundles). Different lifecycles, different access patterns, never joined. PK=`AGENT#{agent_type}`, SK=ISO 8601 timestamp. The dashboard queries by agent type per tab, which maps directly to the PK. Reports are permanent; bundles are ephemeral. Clean separation.

## Decisions Made

### Decision 131: DDB as Source of Truth for Eval Reports (Resolves Decision 29)

**Source:** This update — V4-7a-4 spec discussion
**Date:** March 26, 2026

All eval reports (creation, verification, calibration) are stored in DynamoDB table `calledit-v4-eval-reports` as the source of truth. Local JSON files in `eval/reports/` are retained as backup. This resolves Decision 29 ("local eval results, not DynamoDB — yet") and backlog item 1 ("migrate all eval data storage to DynamoDB"). The trigger was the V4-7a-4 dashboard spec — building a fourth component on local files would have created more technical debt to migrate later. Better to do it now as part of the capstone spec.

Table schema: PK=`AGENT#{agent_type}` (creation/verification/calibration), SK=ISO 8601 timestamp. PAY_PER_REQUEST billing. Auto-created by `report_store.py` if not exists. Separate from `calledit-v4-eval` (temporary bundles) — different lifecycles, never joined.

### Decision 132: React Dashboard Instead of Streamlit

**Source:** This update — V4-7a-4 spec discussion
**Date:** March 26, 2026

The eval dashboard is a `/eval` route in the existing `frontend-v4` React app, not a Streamlit application. React provides genuinely interactive overlays (multi-series line charts with toggle, scatter plots with hover-to-drill, side-by-side comparison panels) that Streamlit's widget model can't match. The existing React app already has Cognito auth, Vite build tooling, and CloudFront deployment — zero infrastructure cost. New dependencies: `react-router-dom`, `recharts`, `@aws-sdk/client-dynamodb`, `@aws-sdk/lib-dynamodb`. The dashboard reads DDB directly from the browser using the user's Cognito credentials.

### Decision 133: Data-Driven Dashboard Extensibility

**Source:** This update — V4-7a-4 design discussion
**Date:** March 26, 2026

The dashboard renders data-driven, not hardcoded. Tabs come from distinct `agent` values in the Reports_Table. Aggregate scores render whatever keys exist in `aggregate_scores`. Case table columns are derived from the `scores` keys in the first case result. Metadata display iterates over all `run_metadata` keys. This means adding a new evaluator, a new metadata field, or a new agent type requires zero dashboard code changes — the data drives the rendering. This is critical for a learning project where the eval framework will evolve as we experiment with new ways to measure and improve agent quality.

### Decision 134: Tool Action Tracking as Next Priority After Dashboard

**Source:** This update — V4-7a-3 full baseline analysis
**Date:** March 26, 2026

The V4-7a-3 full baseline revealed that 4/7 verdict failures were caused by Browser tool failures (permission denied, timeout, network unreachable). We need structured tracking of tool actions (what the agent attempted, what succeeded, what failed, failure modes) to answer two questions: (1) which prompt improvements would help the agent use its existing tools better, and (2) which new tool would have the biggest impact on verification success. Tracked as backlog item 16. The dashboard's extensibility principle means it will render this data automatically once it appears in reports.

## V4-7a-3 Final Results

### Smoke+Judges Baseline (2 cases, 163.2s)
- Report: `eval/reports/verification-eval-20260326-021040.json`
- Tier 1: all 1.00
- verdict_accuracy: 0.50 (base-002 correct, base-011 inconclusive)
- evidence_quality: 0.55 (base-002: 0.3, base-011: 0.8)

### Full Baseline (7 cases, 460.6s)
- Report: `eval/reports/verification-eval-20260326-022007.json`
- Tier 1: all 1.00
- verdict_accuracy: 0.43 (3/7 correct — base-001, base-002, base-040)
- evidence_quality: 0.46
- 3 inconclusive (Browser failures), 1 refuted (lunar calc error), 3 confirmed (correct)

## V4-7a-4 Spec Created

Requirements (12), design (17 correctness properties), and tasks (11 top-level, 27 sub-tasks) all complete. Three components:
1. DDB Report Store — `eval/report_store.py`, new `calledit-v4-eval-reports` table
2. Calibration Runner — `eval/calibration_eval.py`, chains creation→verification
3. React Dashboard — `/eval` route in `frontend-v4`, Recharts, DDB reads via Cognito

## Files Created/Modified

### Created
- `.kiro/specs/cross-agent-calibration-dashboard/` — V4-7a-4 spec (requirements, design, tasks)
- `docs/project-updates/31-project-update-v4-7a-eval-completion-and-dashboard-spec.md` — this update

### Modified
- `docs/project-updates/backlog.md` — added item 16 (tool action tracking)
- `docs/project-updates/decision-log.md` — decisions 131-134 (to be added)
- `docs/project-updates/project-summary.md` — update 31 entry (to be added)

## Spec Plan Status

| Spec | Name | Status |
|------|------|--------|
| V4-7a-1 | Golden Dataset Reshape | ✅ COMPLETE |
| V4-7a-2 | Creation Agent Eval | ✅ COMPLETE (IP=0.88, PQ=0.57) |
| V4-7a-3 | Verification Agent Eval | ✅ COMPLETE (VA=0.43, EQ=0.46, T1=1.00) |
| V4-7a-4 | Cross-Agent Calibration + Dashboard | 📋 SPECCED (ready for execution) |

## What the Next Agent Should Do

### Priority 1: Execute V4-7a-4 Tasks
The spec is ready. Build order: report store → backfill runners → calibration runner → React dashboard. Start with task 1.1 (report_store.py).

### Priority 2: Investigate base-010 (Full Moon) Verdict
The agent returned `refuted` with 0.9 confidence for "next full moon before April 1, 2026" — expected `confirmed`. Either the agent's lunar calculation is wrong or the golden dataset expected outcome needs review.

### Priority 3: Document V4-7a-3 Completion
Update the V4-7a-3 tasks.md to mark remaining tasks complete (tasks 5 and 11 checkpoints).

### Key Files
- `.kiro/specs/cross-agent-calibration-dashboard/tasks.md` — V4-7a-4 implementation plan
- `eval/report_store.py` — first file to create (task 1.1)
- `eval/reports/verification-eval-20260326-022007.json` — full baseline (7 cases)
- `frontend-v4/src/App.tsx` — needs react-router-dom integration (task 6.1)
- `docs/project-updates/backlog.md` — item 16 (tool action tracking) added
