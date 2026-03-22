# Requirements Document — Spec B3: Verification Eval Integration

## Introduction

Extend the existing eval framework (`eval_runner.py`, `evaluators/`, `eval/golden_dataset.json`, `eval/dashboard/`) with a `--verify` mode and four new evaluators that measure plan-execution alignment — how well the Verification Builder writes plans that the Verification Executor can actually execute.

This spec depends on Spec B1 (`verification-execution-agent`) which provides the `run_verification()` entry point. It does NOT depend on Spec B2 (triggers/storage) — the eval runner invokes `run_verification` directly, bypassing the production trigger path.

This is the third of three specs split from the original Spec B:
- **Spec B1** (`verification-execution-agent`): Verification Executor agent — PREREQUISITE
- **Spec B2** (`verification-triggers`): DynamoDB storage, immediate trigger, scheduled scanner
- **Spec B3** (this spec): Eval framework extension with `--verify` mode and 4 new evaluators

Verification comparison data flows through the existing evaluator pipeline, report format, reasoning store (`calledit-eval-reasoning` DDB table), and Streamlit dashboard (`eval/dashboard/`). This feeds into composite score recalibration (Backlog item 11) and connects to the eval framework integration roadmap (Backlog item 7).

This spec does NOT cover: the Verification Executor agent itself (Spec B1), production triggers (Spec B2), AgentCore migration, or frontend display.

## Glossary

- **Verification_Plan**: The output of the Verification Builder agent — a dict with `source`, `criteria`, and `steps`
- **Verification_Outcome**: The output of the Verification_Executor — a dict with `status`, `confidence`, `evidence`, `reasoning`, `verified_at`, and `tools_used`
- **Eval_Runner**: The existing evaluation runner (`backend/calledit-backend/handlers/strands_make_call/eval_runner.py`) that loads the golden dataset, executes test cases through pluggable backends, applies evaluators, and produces a scored report
- **Evaluator_Pipeline**: The existing set of evaluator modules in `evaluators/` (e.g., `category_match.py`, `json_validity.py`, `intent_preservation.py`) that score prediction outputs
- **Golden_Dataset**: The existing golden dataset (`eval/golden_dataset.json`) containing `BasePrediction` and `FuzzyPrediction` test cases with ground truth metadata
- **Eval_Reasoning_Store**: The existing DynamoDB table (`calledit-eval-reasoning`) that stores full model reasoning traces, per-test scores, and run-level aggregates
- **Dashboard**: The existing Streamlit dashboard (`eval/dashboard/`) with pages for trends, heatmap, architecture comparison, prompt correlation, reasoning explorer, coherence, and fuzzy convergence
- **ToolAlignmentEvaluator**: A new deterministic evaluator in `evaluators/tool_alignment.py` scoring overlap between planned tools and actually-used tools
- **CriteriaQualityEvaluator**: A new LLM-as-judge evaluator in `evaluators/criteria_quality.py` scoring whether VB criteria led to clear verdicts
- **SourceAccuracyEvaluator**: A new deterministic evaluator in `evaluators/source_accuracy.py` scoring whether evidence sources match planned sources
- **StepFidelityEvaluator**: A new LLM-as-judge evaluator in `evaluators/step_fidelity.py` scoring whether execution followed planned steps
- **Delta_Classification**: Root cause classification for plan-execution mismatches: `plan_error`, `new_information`, or `tool_drift`. Requires LLM judgment to classify the WHY behind a delta, even on otherwise-deterministic evaluators.
- **Verification_Readiness**: A field on golden dataset test cases (`immediate` or `future`) indicating whether the test case can be fully verified now or only plan-evaluated

## Requirements

### Requirement 1: Eval Runner --verify Mode

**User Story:** As a pipeline developer, I want a `--verify` flag on the existing eval runner that also runs the Verification Executor after the prediction pipeline, so that both VB plan and executor outcome are captured in the same eval run.

#### Acceptance Criteria

1. THE Eval_Runner SHALL accept a `--verify` CLI flag that, when set, runs the Verification_Executor via `run_verification` after the prediction pipeline completes for each base prediction test case whose `verification_readiness` is `immediate`, regardless of expected category — the eval runner does not pre-filter by `auto_verifiable` because the evaluators should score the result even when the categorizer misroutes
2. WHEN `--verify` is set, THE Eval_Runner SHALL capture both the Verification_Plan (from the prediction pipeline's `verification_method` output) and the Verification_Outcome (from `run_verification`) in the same test result dict, alongside existing per-agent outputs
3. FOR test cases where `verification_readiness` is `future` or unset, THE Eval_Runner SHALL record the Verification_Plan in the test result and mark the verification evaluators as `skipped` with reason `future_dated`, using the existing `_skipped_evaluators` pattern
4. WHEN `--verify` is not set, THE Eval_Runner SHALL skip all verification execution and verification evaluators, preserving the existing eval behavior with no performance or cost impact
5. THE `--verify` flag SHALL compose with existing filters (`--name`, `--category`, `--layer`, `--difficulty`) so that developers can run verification on a single test case for fast iteration, since each verification invocation costs ~20-120s depending on MCP cold start state

### Requirement 2: Verification Alignment Evaluators

**User Story:** As a pipeline developer, I want four new evaluators that measure plan-execution alignment across different dimensions, so that I can identify where the VB writes plans the executor can't faithfully execute.

#### Acceptance Criteria

1. THE ToolAlignmentEvaluator SHALL be implemented in `evaluators/tool_alignment.py` as a deterministic evaluator following the existing evaluator function signature pattern (returns `{"score": float, "evaluator": str, ...}`) and SHALL return a score measuring the set overlap between tools referenced in the Verification_Plan's `steps` field and the tools listed in the Verification_Outcome's `tools_used` field
2. THE CriteriaQualityEvaluator SHALL be implemented in `evaluators/criteria_quality.py` as an LLM-as-judge evaluator using the Strands Evals SDK `OutputEvaluator` pattern (same as `intent_preservation.py`) and SHALL return a score measuring whether each criterion in the Verification_Plan's `criteria` field contributed to a clear verdict, flagging criteria that were too vague or unmeasurable
3. THE SourceAccuracyEvaluator SHALL be implemented in `evaluators/source_accuracy.py` as a deterministic evaluator and SHALL return a score measuring whether the evidence sources in the Verification_Outcome's `evidence` list correspond to the sources suggested in the Verification_Plan's `source` field
4. THE StepFidelityEvaluator SHALL be implemented in `evaluators/step_fidelity.py` as an LLM-as-judge evaluator using the Strands Evals SDK `OutputEvaluator` pattern and SHALL return a score measuring whether the Verification_Executor's execution followed the sequence and intent of the Verification_Plan's `steps` field
5. WHEN a delta exists between the Verification_Plan and the Verification_Outcome, THE ToolAlignmentEvaluator, SourceAccuracyEvaluator, and StepFidelityEvaluator SHALL each include a `delta_classification` field in their return dict with one of: `plan_error`, `new_information`, or `tool_drift`. For the deterministic evaluators (ToolAlignment, SourceAccuracy), delta classification requires a lightweight LLM judge call to determine the WHY behind the mismatch — the deterministic score measures WHAT diverged, the judge classifies WHY.
6. THE verification evaluator scores SHALL be included in the existing `evaluator_scores` dict for each test result, following the same score pattern used by existing evaluators, so that the existing dashboard can display verification alignment data alongside prediction pipeline scores
7. THE four new verification evaluators SHALL NOT be added to the `EVALUATOR_WEIGHTS` dict initially — per Decision 62, composite score weights need empirical grounding from actual verification outcomes before weighting can be calibrated. The evaluators will report scores but not affect the VB-centric composite until a future calibration spec.

### Requirement 3: Golden Dataset Extension

**User Story:** As an eval framework user, I want the golden dataset extended with verification readiness metadata, so that the eval runner knows which test cases can be fully verified now vs which are future-dated.

#### Acceptance Criteria

1. THE `BasePrediction` dataclass in `golden_dataset.py` SHALL be extended with an optional `verification_readiness` field accepting values `immediate` or `future`, added to the dataclass, validator, and serializer
2. THE golden dataset SHALL include a mix of `immediate` test cases (verifiable now — e.g., established facts, current data) and `future` test cases (verification date in the future — e.g., weather predictions, event outcomes)
3. IF `verification_readiness` is not specified on a test case, THE Eval_Runner SHALL default to `future` (conservative — don't attempt verification unless explicitly marked as immediate)
4. THE golden dataset schema version SHALL remain at "3.0" since `verification_readiness` is an optional field with a safe default — no breaking change to existing dataset consumers

### Requirement 4: Report and Dashboard Extension

**User Story:** As a pipeline developer, I want verification alignment data visible in the existing eval reports and dashboard, so that I can track plan-execution quality alongside prediction pipeline quality.

#### Acceptance Criteria

1. THE `_aggregate_report` function in `eval_runner.py` SHALL be extended to include a `verification_alignment_aggregates` section containing mean, min, and max for each of the four verification evaluator scores, plus a breakdown of delta classifications by root cause category
2. THE Eval_Reasoning_Store SHALL be extended with a `verification_outcome#{test_case_id}` record type that stores the Verification_Plan, Verification_Outcome, and all four verification evaluator scores for each test case processed in `--verify` mode
3. THE Dashboard SHALL include a new page (`eval/dashboard/pages/verification_alignment.py`) that visualizes the four alignment dimensions, delta classification breakdown, and per-prediction comparison details
4. THE Dashboard sidebar SHALL be updated to include "Verification Alignment" in the page navigation list, and the `app.py` page routing SHALL import and dispatch to the new page module
