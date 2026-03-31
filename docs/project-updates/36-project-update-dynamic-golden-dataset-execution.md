# Project Update 36 — Dynamic Golden Dataset + Unified Eval Pipeline

**Date:** March 31, 2026
**Context:** Executed the dynamic golden dataset spec, then designed and built a unified eval pipeline replacing the 3 separate runners. Fixed IAM permissions, Brave API key propagation, and calibration logic.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/dynamic-golden-dataset/` — Dynamic Golden Dataset spec (EXECUTED, all 9 tasks complete)
- `.kiro/specs/unified-eval-pipeline/` — Unified Eval Pipeline spec (EXECUTED, tasks 1-10 complete, dashboard pending)

### Prerequisite Reading
- `docs/project-updates/35-project-update-dynamic-golden-dataset-spec.md` — Spec creation context

---

## What Happened

### Housekeeping
1. **Git credential audit** — Scanned recent commits for leaked Cognito credentials. All clean.
2. **Bashrc cleanup** — Removed `force_deactivate()`, auto-deactivate block, and `reset_venv()` from `~/.bashrc` to fix `(venv) W` prompt bleed.

### Dynamic Golden Dataset Spec Execution (9/9 tasks complete)
- Built `eval/generate_dynamic_dataset.py` — 16 templates (9 deterministic + 7 Brave Search) across all 4 verification modes
- Built `eval/dataset_merger.py` — `load_and_merge()` with time-sensitive replacement logic
- Added `time_sensitive: true` to base-010 in static dataset
- Extended all 3 eval runners with `--dynamic-dataset` CLI arg + `dataset_sources` metadata
- Extended `eval/validate_dataset.py` with `validate_dynamic_dataset()`
- Smoke tests passed across all 3 old runners

### Unified Eval Pipeline (Decision 147)
The user identified that running 3 separate eval runners was repetitive and slow. Designed and built `eval/unified_eval.py` — a single pipeline that mirrors production flow:

1. **Dataset audit** — filters predictions with null expected verdicts (47 of 70 excluded)
2. **Creation pass** — invokes creation agent via JWT, writes bundles to eval DDB table
3. **Verification timing** — computes exact wait from bundle verification_dates (skips immediate/recurring, caps at 5 min)
4. **Verification pass** — invokes verification agent via SigV4 with scanner pattern (reads/writes DDB)
5. **Evaluation** — runs all creation + verification evaluators + calibration metrics
6. **Report** — single unified JSON with creation_scores, verification_scores, calibration_scores

### IAM Permission Discovery
The creation agent's AgentCore execution role (`5a297cfdfd`) was different from the verification agent's role (`37c792a758`). The permissions script only targeted the verification role. Added eval table DDB permissions to both roles. Both agents required relaunch to pick up new IAM policies.

### Brave API Key Discovery
The verification agent relaunch without `--env BRAVE_API_KEY=...` caused all Brave-dependent predictions to return inconclusive. First full run: VA=0.47 (11 inconclusive). After relaunch with key: VA=0.89 (2 inconclusive).

### Calibration Logic Fix (Decision 148)
The original calibration logic assumed high verifiability score = expected to be confirmed. This is wrong — high score means "easy to verify," which includes predictions that are easy to refute. Fixed `is_calibration_correct()`: high + confirmed OR refuted = correct. High + inconclusive = wrong (agent couldn't resolve an easy one).

### CloudFormation Import
Imported the `calledit-v4-eval` DDB table into the `calledit-v4-persistent-resources` CloudFormation stack. Previously created ad-hoc, now managed as IaC alongside the production table and eval reports table.

### First Unified Baseline (March 31, 2026)

| Metric | Value | Notes |
|--------|-------|-------|
| Creation T1 | 1.00 | All 6 deterministic evaluators pass |
| Creation IP | 0.89 | Intent preservation |
| Creation PQ | 0.88 | Plan quality |
| Verification T1 | 1.00 | All 5 deterministic evaluators pass |
| Verification VA | 0.89 | 20/22 correct verdicts (1 creation error, 2 inconclusive) |
| Verification EQ | 0.59 | Evidence quality |
| Calibration Accuracy | 0.77 → ~0.91 | After calibration logic fix |
| Calibration MAE | 0.30 | |
| Duration | 2772s (~46 min) | 23 cases end-to-end |

Remaining failures:
- dyn-bfd-001: HTTP 500 creation error (transient)
- base-013: inconclusive (needs Browser for Wikipedia — broken in runtime)
- dyn-rec-003: inconclusive (Wikipedia accessibility — same Browser limitation)

### Comparison to Previous Baselines (Update 34, 3 separate runners)

| Metric | Old (3 runners) | New (unified) | Notes |
|--------|-----------------|---------------|-------|
| Creation IP | 0.79 | 0.89 | +0.10 (different cases) |
| Creation PQ | 0.56 | 0.88 | +0.32 (different cases) |
| Verification VA | 0.71 | 0.89 | +0.18 (Brave working) |
| Calibration CA | 0.86 | ~0.91 | +0.05 (logic fix + more cases) |
| Total duration | ~50 min (3 runs) | ~46 min (1 run) | Comparable, but one pipeline |

## Files Created/Modified

### Created
- `eval/unified_eval.py` — Unified eval pipeline (single file, ~500 lines)
- `eval/dataset_merger.py` — Dataset merger with time-sensitive replacement
- `eval/generate_dynamic_dataset.py` — Dynamic dataset generator (16 templates)
- `.kiro/specs/unified-eval-pipeline/` — Spec (requirements, design, tasks)
- `docs/project-updates/36-project-update-dynamic-golden-dataset-execution.md` — This update

### Modified
- `eval/golden_dataset.json` — Added `time_sensitive: true` to base-010
- `eval/creation_eval.py` — `--dynamic-dataset` arg, `load_and_merge()`, `dataset_sources`
- `eval/verification_eval.py` — Same changes
- `eval/calibration_eval.py` — Same changes + calibration logic fix
- `eval/validate_dataset.py` — Added `validate_dynamic_dataset()`
- `infrastructure/v4-persistent-resources/template.yaml` — Added `calledit-v4-eval` table + outputs
- `infrastructure/agentcore-permissions/setup_agentcore_permissions.sh` — Added creation agent role permissions
- `.gitignore` — Added `eval/dynamic_golden_dataset.json`
- `docs/project-updates/decision-log.md` — Decisions 146-148
- `docs/project-updates/project-summary.md` — Updated current state
- `docs/project-updates/common-commands.md` — Added dynamic dataset + unified eval commands

## What the Next Agent Should Do

### Priority 1: Build Preflight Check
Add `--preflight` flag to unified eval that tests each service dependency before the full run: DDB write/read, Cognito auth, creation agent invoke, verification agent invoke with Brave, Brave direct call. ~1 minute, catches all the IAM/env var issues we hit.

### Priority 2: Dashboard Integration
Task 11 in the unified eval spec — add "Unified" tab to the React dashboard with calibration scatter plot and score-vs-outcome curves.

### Priority 3: Debug AgentCore Browser Tool (Backlog Item 17)
base-013 and dyn-rec-003 need Browser. Still broken in deployed runtime.

### Priority 4: Curate Dataset
Remove or replace predictions that consistently return inconclusive due to tool limitations (base-013, dyn-rec-003). Per user direction: only keep cases we're confident our tools can handle.


### Dashboard Updates (end of session)
- Added "Unified Pipeline" tab as default tab in the eval dashboard
- Scatter plot moved above score sections — narrative lead: "Can Our Agents Verify What They Promise?"
- Fixed scatter plot colors: green = calibration correct (confirmed OR refuted), red = calibration wrong (inconclusive when score was high). Recomputed client-side per Decision 148.
- Fixed missing case IDs in unified case table (case_id vs id field mapping)
- Three-column score grid: Creation (blue), Verification (purple), Calibration (amber)
- Phase timing breakdown shown above scores
- Transparency on overlapping scatter points

### Backlog Items Added
- Item 18: Eval preflight check — test service dependencies before full run (~1 min)
- Item 19: Verifiability score accuracy — creation agent should match verification reality (dyn-atd-003 scored 0.65 but trivially verifiable)
