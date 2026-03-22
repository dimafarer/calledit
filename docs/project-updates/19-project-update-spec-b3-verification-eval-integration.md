# Project Update 19 — Spec B3: Verification Eval Integration

**Date:** March 22, 2026
**Context:** Extended the eval framework with --verify mode, 4 new verification alignment evaluators, golden dataset verification_readiness field, report aggregation, DDB storage, and dashboard page. End-to-end verified with real Bedrock + MCP.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending — includes B3 implementation + README rewrite

### Referenced Kiro Specs
- `.kiro/specs/verification-eval-integration/` — Spec B3 (COMPLETE)
- `.kiro/specs/verification-execution-agent/` — Spec B1 (COMPLETE, prerequisite)
- `.kiro/specs/verification-triggers/` — Spec B2 (COMPLETE)

### Prerequisite Reading
- `docs/project-updates/18-project-update-spec-b2-verification-triggers.md` — Spec B2
- `docs/project-updates/decision-log.md` — Decisions through 85

---

## What Happened This Session

### Requirements Review Caught Issues
Before design, reviewed B3 requirements against the actual codebase and found several gaps:
1. Req 1 AC1 originally said "for each auto_verifiable test case" — but the eval runner processes ALL base predictions regardless of category. Fixed to run on any `immediate` test case regardless of expected category, so evaluators score even when the categorizer misroutes.
2. Requirements didn't specify which evaluators are deterministic vs LLM judge. Clarified: ToolAlignment and SourceAccuracy are deterministic, CriteriaQuality and StepFidelity are LLM judges.
3. Delta classification on deterministic evaluators needs LLM judgment to classify WHY — the deterministic score measures WHAT diverged, the judge classifies WHY.
4. New evaluators should NOT be added to EVALUATOR_WEIGHTS per Decision 62 — scores reported but don't affect composite until empirical calibration.
5. Golden dataset schema stays at 3.0 since verification_readiness is optional with safe default.
6. Added AC for --verify composing with existing filters for single-case iteration.
7. Added AC for dashboard sidebar and routing updates.

### Strands SDK Research
Reviewed Strands Evals SDK documentation for OutputEvaluator, TrajectoryEvaluator, and ToolSelectionAccuracyEvaluator patterns. Confirmed the existing project pattern (direct OutputEvaluator with EvaluationData, not the Experiment wrapper) is the right approach for B3's judge evaluators.

### Spec B3 Implemented
12 tasks completed:

1. **Golden dataset extension** — Added optional `verification_readiness` field to `BasePrediction` dataclass, validator, and serializer. Tagged 10 of 45 base predictions as `immediate` (established facts verifiable now). Remaining 35 default to `future`.

2. **Delta classifier** — Shared `evaluators/delta_classifier.py` module with `classify_delta()` function. Uses direct Bedrock converse call (not Strands Evals SDK) for lightweight classification of plan-execution mismatches into `plan_error`, `new_information`, or `tool_drift`.

3. **ToolAlignment evaluator** — Deterministic Jaccard similarity between planned tools (extracted from plan steps via keyword matching) and used tools. When score < 1.0, calls classify_delta() for root cause.

4. **SourceAccuracy evaluator** — Deterministic coverage score measuring proportion of planned sources that fuzzy-match evidence sources. Domain-level matching (extracts domain from URLs). When score < 1.0, calls classify_delta().

5. **CriteriaQuality evaluator** — LLM judge using Strands Evals SDK OutputEvaluator. Rubric evaluates whether each criterion is specific/checkable, evidence maps to criteria, no criteria ignored.

6. **StepFidelity evaluator** — LLM judge using Strands Evals SDK OutputEvaluator. Rubric evaluates step sequence, completeness, and intent fidelity. Includes delta_classification in judge output.

7. **Eval runner --verify mode** — Added `--verify` CLI flag, `use_verify` parameter, `_evaluate_verification()` dispatch function, and `_skip_verification_evaluators()` helper. Wired into the BasePrediction processing loop. Composes with all existing filters.

8. **Report aggregation** — Extended `_aggregate_report()` with `verification_alignment_aggregates` section: mean/min/max per evaluator, delta classification breakdown, verification/skipped counts. Added `verification_alignment` to evaluator_groups.

9. **DDB storage** — Added `write_verification_outcome()` to EvalReasoningStore. Record key: `verification_outcome#{test_case_id}`. Wired into eval runner loop.

10. **Dashboard page** — Created `eval/dashboard/pages/verification_alignment.py` with alignment score bar chart, delta classification breakdown, per-prediction expandable details, and skipped cases section.

11. **Sidebar/routing** — Added "Verification Alignment" to sidebar page list and app.py routing.

### End-to-End Integration Test
Ran `--verify` on base-002 ("Christmas 2026 will fall on a Friday"):
- Prediction pipeline produced verification plan (no tools — pure reasoning prediction)
- Verification Executor used `brave_web_search` and `fetch_txt` to confirm Christmas 2026 is Friday
- Status: `confirmed`, confidence: 0.9
- ToolAlignment: 0.0 (plan had no tools, executor used tools) → `new_information`
- SourceAccuracy: 0.0 (plan had no sources, executor found its own) → `new_information`
- This is correct behavior — base-002 has empty `tool_manifest_config`, so VB doesn't reference tools. The executor adaptively used tools anyway.

### Import Path Fix
The `tool_alignment.py` evaluator initially failed to import `delta_classifier` when run from outside the `strands_make_call` directory. Fixed with try/except fallback to relative import — works both when `strands_make_call/` is on sys.path (eval_runner context) and when imported as a package.

## Decisions Made

- Decision 84: Verification evaluators NOT added to EVALUATOR_WEIGHTS — per Decision 62, composite weights need empirical grounding. Scores are reported but don't affect VB-centric composite until a future calibration spec.
- Decision 85: Golden dataset schema stays at 3.0 — verification_readiness is optional with safe default ("future"), no breaking change to existing consumers.

## Files Created/Modified

### Created
- `backend/calledit-backend/handlers/strands_make_call/evaluators/tool_alignment.py` — ToolAlignment deterministic evaluator
- `backend/calledit-backend/handlers/strands_make_call/evaluators/source_accuracy.py` — SourceAccuracy deterministic evaluator
- `backend/calledit-backend/handlers/strands_make_call/evaluators/criteria_quality.py` — CriteriaQuality LLM judge evaluator
- `backend/calledit-backend/handlers/strands_make_call/evaluators/step_fidelity.py` — StepFidelity LLM judge evaluator
- `backend/calledit-backend/handlers/strands_make_call/evaluators/delta_classifier.py` — Shared delta classification helper
- `eval/dashboard/pages/verification_alignment.py` — Verification Alignment dashboard page
- `docs/project-updates/19-project-update-spec-b3-verification-eval-integration.md` — this file

### Modified
- `backend/calledit-backend/handlers/strands_make_call/golden_dataset.py` — Added verification_readiness field to BasePrediction, validator, serializer
- `backend/calledit-backend/handlers/strands_make_call/eval_runner.py` — Added --verify flag, _evaluate_verification(), _skip_verification_evaluators(), verification_alignment_aggregates in _aggregate_report(), DDB write wiring
- `backend/calledit-backend/handlers/strands_make_call/eval_reasoning_store.py` — Added write_verification_outcome() method
- `eval/golden_dataset.json` — Added verification_readiness to 10 base predictions
- `eval/dashboard/app.py` — Added verification_alignment import and page routing
- `eval/dashboard/sidebar.py` — Added "Verification Alignment" to page list
- `.kiro/specs/verification-eval-integration/requirements.md` — Updated with review findings
- `.kiro/specs/verification-eval-integration/design.md` — Created
- `.kiro/specs/verification-eval-integration/tasks.md` — Created

## What the Next Agent Should Do

### Immediate
1. Run a full `--verify --judge` eval to get CriteriaQuality and StepFidelity scores alongside the deterministic evaluators
2. Consider running on a test case with tools in its manifest (e.g., base-008 "current temperature") to see non-zero ToolAlignment/SourceAccuracy scores

### After Verification Eval Data
3. Start composite score recalibration (Backlog item 11) — now have real verification outcomes to derive empirical weights
4. Consider AgentCore migration (Decision 68) — the 30s cold start on MCP is the main bottleneck for --verify runs

### Key Files
- `backend/calledit-backend/handlers/strands_make_call/eval_runner.py` — eval runner with --verify
- `backend/calledit-backend/handlers/strands_make_call/evaluators/` — 15 evaluator modules (11 existing + 4 new)
- `eval/golden_dataset.json` — golden dataset with verification_readiness
- `eval/dashboard/pages/verification_alignment.py` — dashboard page

### Important Notes
- `--verify` without `--judge` runs only deterministic evaluators (ToolAlignment, SourceAccuracy) — fast, no Opus cost
- `--verify --judge` adds CriteriaQuality and StepFidelity — slower, uses Opus 4.6 as judge
- `--verify` composes with `--name` for single-case iteration
- Delta classification uses Sonnet 4 (not Opus) for lightweight classification
- All Python commands: `/home/wsluser/projects/calledit/venv/bin/python`
- `source .env` needed for BRAVE_API_KEY
