# Requirements Document

## Introduction

Migrate the entire custom eval framework to the Strands Evals SDK. This is a clean break — all custom eval orchestration, evaluator interfaces, and report formats are replaced by SDK equivalents. The golden dataset format (JSON with `base_predictions`) and DDB report store are preserved but adapted for the SDK's data model. The React dashboard is updated to consume the new report shape. Old eval code is deleted with no backward compatibility.

## Glossary

- **Eval_Pipeline**: The `eval/unified_eval.py` orchestration that chains creation → wait → verification → evaluation → report. Replaced by `Experiment.run_evaluations()`.
- **Case**: A Strands Evals SDK test case object with `input`, `expected_output`, `metadata`, and `session_id`. Each golden dataset prediction maps to one Case.
- **Experiment**: A Strands Evals SDK collection of Cases and Evaluators. Provides `run_evaluations(task_function)` to orchestrate execution.
- **Evaluator**: The Strands Evals SDK base class with `evaluate(evaluation_case: EvaluationData) -> list[EvaluationOutput]`. All evaluators (deterministic and LLM) implement this interface.
- **EvaluationOutput**: Standardized SDK result with `score` (0.0–1.0), `test_pass` (bool), `reason` (str), `label` (optional str).
- **OutputEvaluator**: SDK built-in LLM judge evaluator that accepts a custom rubric. Replaces hand-rolled `intent_preservation.py`, `plan_quality.py`, and `verification_evidence_quality.py`.
- **Task_Function**: A callable passed to `Experiment.run_evaluations()` that takes a Case and returns the agent output. For CalledIt, this function chains creation agent invocation → verification wait → verification agent invocation.
- **Golden_Dataset**: The `eval/golden_dataset.json` (54 static) and `eval/dynamic_golden_dataset.json` (16 dynamic) files containing prediction test cases with ground truth.
- **Dataset_Merger**: The `eval/dataset_merger.py` module that combines static and dynamic datasets. Preserved but output feeds into Case construction.
- **Report_Store**: The `eval/report_store.py` module that reads/writes eval reports to the `calledit-v4-eval-reports` DDB table. Preserved but adapted for SDK report format.
- **Dashboard**: The React eval dashboard at `frontend-v4/src/pages/EvalDashboard/` that visualizes eval reports from DDB.
- **Creation_Agent**: The CalledIt prediction creation agent invoked via Cognito JWT auth through AgentCore.
- **Verification_Agent**: The CalledIt verification agent invoked via SigV4 auth.
- **Calibration_Metrics**: Cross-agent analysis measuring whether the creation agent's verifiability score predicts verification success. Computed as a post-experiment step.
- **Tier**: Eval run depth — `smoke` (deterministic only), `smoke+judges` (deterministic + LLM judges), `full` (all evaluators + calibration).

## Requirements

### Requirement 1: Golden Dataset to Case Conversion

**User Story:** As an eval developer, I want golden dataset predictions loaded as Strands Evals SDK Case objects, so that the SDK's Experiment can orchestrate evaluation runs.

#### Acceptance Criteria

1. WHEN the static golden dataset file is loaded, THE Case_Loader SHALL parse each `base_predictions` entry into a Case object with `input` set to the `prediction_text`, `expected_output` set to the `expected_verification_outcome`, and `metadata` containing `id`, `difficulty`, `verification_mode`, `smoke_test`, `ground_truth`, and `expected_verifiability_score_range`.
2. WHEN a dynamic golden dataset file is provided, THE Case_Loader SHALL use the Dataset_Merger to combine static and dynamic predictions before constructing Case objects.
3. WHEN a prediction has `expected_verification_outcome` set to null, THE Case_Loader SHALL still include the prediction as a Case with `expected_output` set to None, and SHALL set `metadata.qualifying` to false.
4. THE Case_Loader SHALL assign each Case a `session_id` derived from the prediction `id` field to enable trace correlation.
5. WHEN the `--case` CLI argument is provided, THE Case_Loader SHALL filter Cases to include only the specified prediction id.
6. WHEN the `--tier smoke` CLI argument is provided, THE Case_Loader SHALL filter Cases to include only those with `metadata.smoke_test` set to true.

### Requirement 2: Deterministic Creation Evaluators

**User Story:** As an eval developer, I want the 6 deterministic creation evaluators converted to Strands Evals SDK Evaluator subclasses, so that they integrate with the SDK's evaluation pipeline.

#### Acceptance Criteria

1. THE Schema_Validity_Evaluator SHALL extend the SDK Evaluator base class and SHALL validate the creation bundle against the ParsedClaim, VerificationPlan, and PlanReview Pydantic models, returning an EvaluationOutput with `score` 1.0 on success and 0.0 on validation failure.
2. THE Field_Completeness_Evaluator SHALL extend the SDK Evaluator base class and SHALL check that `sources`, `criteria`, and `steps` fields in the verification plan are non-empty lists, returning an EvaluationOutput with `score` 1.0 when all fields are present and 0.0 when any field is empty.
3. THE Score_Range_Evaluator SHALL extend the SDK Evaluator base class and SHALL verify the verifiability score is between 0.0 and 1.0 inclusive, returning an EvaluationOutput with `score` 1.0 when in range and 0.0 when out of range.
4. THE Date_Resolution_Evaluator SHALL extend the SDK Evaluator base class and SHALL verify the verification date is a valid ISO 8601 datetime string, returning an EvaluationOutput with `score` 1.0 when valid and 0.0 when invalid.
5. THE Dimension_Count_Evaluator SHALL extend the SDK Evaluator base class and SHALL verify at least 1 dimension assessment exists in the plan review, returning an EvaluationOutput with `score` 1.0 when present and 0.0 when absent.
6. THE Tier_Consistency_Evaluator SHALL extend the SDK Evaluator base class and SHALL verify the score tier label (high/medium/low) matches the numeric verifiability score, returning an EvaluationOutput with `score` 1.0 when consistent and 0.0 when inconsistent.

### Requirement 3: Deterministic Verification Evaluators

**User Story:** As an eval developer, I want the 5 deterministic verification evaluators converted to Strands Evals SDK Evaluator subclasses, so that verification output quality is assessed through the SDK pipeline.

#### Acceptance Criteria

1. THE Verification_Schema_Evaluator SHALL extend the SDK Evaluator base class and SHALL check that the verification result contains `verdict` (str), `confidence` (float), `evidence` (list), and `reasoning` (str) fields with correct types, returning an EvaluationOutput with `score` 1.0 when valid and 0.0 when invalid.
2. THE Verdict_Validity_Evaluator SHALL extend the SDK Evaluator base class and SHALL check that the verdict value is one of `confirmed`, `refuted`, or `inconclusive`, returning an EvaluationOutput with `score` 1.0 when valid and 0.0 when invalid.
3. THE Confidence_Range_Evaluator SHALL extend the SDK Evaluator base class and SHALL verify the confidence value is between 0.0 and 1.0 inclusive, returning an EvaluationOutput with `score` 1.0 when in range and 0.0 when out of range.
4. THE Evidence_Completeness_Evaluator SHALL extend the SDK Evaluator base class and SHALL verify the evidence list contains at least 1 item, returning an EvaluationOutput with `score` 1.0 when non-empty and 0.0 when empty.
5. THE Evidence_Structure_Evaluator SHALL extend the SDK Evaluator base class and SHALL verify each evidence item contains `source`, `finding`, and `relevant_to_criteria` fields, returning an EvaluationOutput with `score` 1.0 when all items are valid and 0.0 when any item is missing required fields.

### Requirement 4: Mode-Specific Verification Evaluators

**User Story:** As an eval developer, I want the 3 mode-specific verification evaluators converted to SDK Evaluator subclasses that use Case metadata to determine verification mode, so that mode-specific correctness criteria are enforced.

#### Acceptance Criteria

1. THE At_Date_Verdict_Evaluator SHALL extend the SDK Evaluator base class and SHALL use `metadata.verification_mode` and `metadata.verification_date` from the Case to determine temporal context, returning `score` 1.0 when the verdict is `inconclusive` before the verification date and when the verdict matches `expected_output` at or after the verification date.
2. THE Before_Date_Verdict_Evaluator SHALL extend the SDK Evaluator base class and SHALL accept `confirmed` and `inconclusive` as valid verdicts before the deadline, returning `score` 0.0 only when the verdict is `refuted` before the deadline, and SHALL use exact match against `expected_output` at or after the deadline.
3. THE Recurring_Freshness_Evaluator SHALL extend the SDK Evaluator base class and SHALL verify that evidence items exist and have non-empty `source` fields, returning an EvaluationOutput with `score` proportional to the fraction of evidence items with source fields.
4. WHEN a Case has `metadata.verification_mode` set to a specific mode, THE Experiment SHALL include only the evaluators applicable to that mode in the evaluation run for that Case.

### Requirement 5: LLM Judge Evaluators via OutputEvaluator

**User Story:** As an eval developer, I want the 3 LLM judge evaluators (intent preservation, plan quality, evidence quality) converted to use the SDK's OutputEvaluator with custom rubrics, so that LLM-based evaluation uses the standardized SDK interface and eliminates hand-rolled JSON parsing.

#### Acceptance Criteria

1. THE Intent_Preservation_Evaluator SHALL use the SDK OutputEvaluator configured with the existing intent preservation rubric (fidelity, temporal intent, scope, assumptions dimensions) and the `us.anthropic.claude-sonnet-4-20250514-v1:0` judge model, returning an EvaluationOutput with `score` between 0.0 and 1.0 and `test_pass` set to true when score is at least 0.5.
2. THE Plan_Quality_Evaluator SHALL use the SDK OutputEvaluator configured with the existing plan quality rubric (criteria specificity, source accessibility, step executability, language precision dimensions) and the `us.anthropic.claude-sonnet-4-20250514-v1:0` judge model, returning an EvaluationOutput with `score` between 0.0 and 1.0 and `test_pass` set to true when score is at least 0.5.
3. THE Evidence_Quality_Evaluator SHALL use the SDK OutputEvaluator configured with the existing evidence quality rubric (source authenticity, finding specificity, criteria linkage dimensions) and the `us.anthropic.claude-sonnet-4-20250514-v1:0` judge model, returning an EvaluationOutput with `score` between 0.0 and 1.0 and `test_pass` set to true when score is at least 0.5.
4. THE Verdict_Accuracy_Evaluator SHALL extend the SDK Evaluator base class and SHALL perform deterministic exact match of the actual verdict against the Case's `expected_output`, returning an EvaluationOutput with `score` 1.0 on match and 0.0 on mismatch, and SHALL return no output when `expected_output` is None.

### Requirement 6: Task Function — Two-Agent Pipeline

**User Story:** As an eval developer, I want a task function that chains creation agent → verification wait → verification agent for each Case, so that the SDK's `Experiment.run_evaluations()` can orchestrate the full pipeline.

#### Acceptance Criteria

1. WHEN `Experiment.run_evaluations()` invokes the Task_Function with a Case, THE Task_Function SHALL invoke the Creation_Agent via AgentCore with Cognito JWT auth using the Case's `input` as the prediction text, and SHALL write the resulting bundle to the eval DDB table (`calledit-v4-eval`).
2. WHEN the Creation_Agent returns a bundle with a verification date in the future, THE Task_Function SHALL wait until the verification date has passed (with a 30-second buffer), capped at 300 seconds.
3. WHEN the creation bundle is available, THE Task_Function SHALL invoke the Verification_Agent via SigV4 auth using the prediction ID from the creation bundle.
4. THE Task_Function SHALL return a structured result containing both the creation bundle and the verification result, so that evaluators can access both agent outputs.
5. IF the Creation_Agent invocation fails, THEN THE Task_Function SHALL return an error result with the creation error message and SHALL skip the verification step.
6. IF the Verification_Agent invocation fails, THEN THE Task_Function SHALL return a partial result containing the creation bundle and the verification error message.

### Requirement 7: Experiment Construction and Tiered Execution

**User Story:** As an eval developer, I want the Experiment constructed with the appropriate evaluator sets based on the run tier, so that smoke runs are fast and cheap while full runs are comprehensive.

#### Acceptance Criteria

1. WHEN the `--tier smoke` argument is provided, THE Experiment SHALL include only the 6 deterministic creation evaluators and 5 deterministic verification evaluators (plus mode-specific evaluators based on Case metadata).
2. WHEN the `--tier smoke+judges` argument is provided, THE Experiment SHALL include all smoke evaluators plus the 3 LLM judge evaluators (intent preservation, plan quality, evidence quality) and the verdict accuracy evaluator.
3. WHEN the `--tier full` argument is provided, THE Experiment SHALL include all smoke+judges evaluators plus calibration post-analysis.
4. THE Experiment SHALL support the `--dry-run` flag to list qualifying Cases without executing the Task_Function or evaluators.
5. THE Experiment SHALL support the `--case <id>` flag to execute a single Case by prediction id.
6. THE Experiment SHALL support the `--description` flag to attach a human-readable description to the run metadata.
7. THE Experiment SHALL support the `--resume` flag to skip creation for prediction IDs already present in the eval DDB table.

### Requirement 8: Calibration Post-Analysis

**User Story:** As an eval developer, I want calibration metrics computed as a post-experiment analysis step after the SDK Experiment completes, so that cross-agent score-vs-outcome analysis is preserved.

#### Acceptance Criteria

1. WHEN the Experiment completes with `--tier full`, THE Calibration_Analyzer SHALL compute `calibration_accuracy` as the fraction of cases where the score tier correctly predicted verification resolution (high score + resolved = correct, high score + inconclusive = wrong).
2. THE Calibration_Analyzer SHALL compute `mean_absolute_error` as the average distance between the verifiability score and the binary verification outcome (1.0 for resolved, 0.0 for inconclusive).
3. THE Calibration_Analyzer SHALL compute `high_score_confirmation_rate` as the percentage of high-score predictions that received a resolved verdict (confirmed or refuted).
4. THE Calibration_Analyzer SHALL compute `low_score_failure_rate` as the percentage of low-score predictions that received an inconclusive verdict.
5. THE Calibration_Analyzer SHALL compute `verdict_distribution` as a count of each verdict value (confirmed, refuted, inconclusive, error) across all cases.
6. THE Calibration_Analyzer SHALL read verifiability scores from the creation bundle and verdicts from the verification result within the Experiment's evaluation data.

### Requirement 9: Report Store Adaptation

**User Story:** As an eval developer, I want the DDB report store updated to write SDK-format reports, so that historical and new reports coexist in the same table and the dashboard can read both.

#### Acceptance Criteria

1. WHEN an Experiment completes, THE Report_Store SHALL write the SDK's EvaluationReport to the `calledit-v4-eval-reports` DDB table with `PK` set to `AGENT#unified` and `SK` set to the ISO 8601 timestamp.
2. THE Report_Store SHALL include `run_metadata` containing `description`, `run_tier`, `timestamp`, `duration_seconds`, `case_count`, `dataset_sources`, `git_commit`, and `prompt_versions`.
3. THE Report_Store SHALL include `creation_scores`, `verification_scores`, and `calibration_scores` as aggregate score dictionaries with per-evaluator averages and overall pass rates.
4. THE Report_Store SHALL include `case_results` as an array of per-case results with evaluator scores, agent outputs, and error information.
5. IF the DDB item exceeds 390KB, THEN THE Report_Store SHALL split `case_results` into a separate item with `SK` set to `{timestamp}#CASES`, consistent with the existing split strategy.
6. THE Report_Store SHALL preserve the existing `list_reports()` and `get_report()` read interfaces so that the dashboard API contract is maintained.

### Requirement 10: Dashboard Adaptation

**User Story:** As an eval developer, I want the React dashboard updated to consume SDK-format reports, so that eval results are visualized correctly after the migration.

#### Acceptance Criteria

1. WHEN the Dashboard loads reports from DDB, THE Dashboard SHALL parse the SDK report format including `creation_scores`, `verification_scores`, `calibration_scores`, and `case_results` fields.
2. THE Dashboard SHALL render the unified pipeline tab with calibration scatter plot, three-column score grid (creation, verification, calibration), phase timing breakdown, and per-case results table.
3. THE Dashboard SHALL render per-evaluator scores with pass/fail indicators for both creation and verification evaluator sets.
4. THE Dashboard SHALL render calibration metrics including `calibration_accuracy`, `mean_absolute_error`, `high_score_confirmation_rate`, `low_score_failure_rate`, and `verdict_distribution`.
5. THE Dashboard TypeScript interfaces SHALL be updated to reflect the SDK report schema while maintaining backward compatibility with any historical reports already in DDB.

### Requirement 11: Old Code Deletion

**User Story:** As an eval developer, I want all old custom eval code deleted, so that there is no technical debt or confusion about which eval system is active.

#### Acceptance Criteria

1. WHEN the migration is complete, THE Codebase SHALL have the following files deleted: `eval/creation_eval.py`, `eval/verification_eval.py`, `eval/calibration_eval.py`, `eval/compare_runs.py`, `eval/analyze_v3_scores.py`, `eval/inject_v3_fields.py`, `eval/reshape_v4.py`, `eval/validate_v4.py`, `eval/debug_loader.py`, `eval/test_new_evaluators.py`, `eval/update_subjective_ground_truth.py`.
2. WHEN the migration is complete, THE Codebase SHALL have all 19 files in `eval/evaluators/` deleted (the old evaluator implementations are replaced by SDK evaluator classes in the new module structure).
3. WHEN the migration is complete, THE Codebase SHALL have the old Streamlit dashboard at `eval/dashboard/` deleted (replaced by the React dashboard reading SDK reports).
4. THE Codebase SHALL retain `eval/golden_dataset.json`, `eval/dynamic_golden_dataset.json`, `eval/generate_dynamic_dataset.py`, `eval/dataset_merger.py`, `eval/report_store.py`, `eval/backends/`, and `eval/reports/` (historical report files).
5. THE Codebase SHALL retain `eval/validate_dataset.py` and `eval/score_history.json` as dataset utilities.

### Requirement 12: Baseline Comparison

**User Story:** As an eval developer, I want a baseline comparison run that executes both the old pipeline and the new SDK pipeline on the same cases, so that I can verify the migration produces equivalent results.

#### Acceptance Criteria

1. WHEN the baseline comparison is executed, THE Comparison_Runner SHALL run the old `eval/unified_eval.py` pipeline on the smoke test subset (12 cases) and record all evaluator scores.
2. WHEN the baseline comparison is executed, THE Comparison_Runner SHALL run the new SDK-based pipeline on the same smoke test subset and record all evaluator scores.
3. THE Comparison_Runner SHALL produce a comparison report showing per-evaluator score differences between old and new pipelines, with a tolerance of ±0.05 for LLM judge scores (non-deterministic) and exact match for deterministic evaluator scores.
4. WHEN all deterministic evaluator scores match exactly and all LLM judge scores are within ±0.05, THE Comparison_Runner SHALL report the migration as validated.

### Requirement 13: CLI Interface

**User Story:** As an eval developer, I want a single CLI entry point for the new SDK-based eval pipeline, so that running evaluations is straightforward.

#### Acceptance Criteria

1. THE CLI SHALL accept `--dataset` (path to static golden dataset, default `eval/golden_dataset.json`) and `--dynamic-dataset` (optional path to dynamic golden dataset) arguments.
2. THE CLI SHALL accept `--tier` with choices `smoke`, `smoke+judges`, `full` (default `smoke`).
3. THE CLI SHALL accept `--description` for a human-readable run description.
4. THE CLI SHALL NOT write local JSON report files by default. DDB is the primary and only report store. THE CLI MAY accept `--local-backup` to optionally write a local JSON copy to `eval/reports/` for debugging.
5. THE CLI SHALL accept `--dry-run` to list qualifying cases without execution.
6. THE CLI SHALL accept `--case <id>` to execute a single case.
7. THE CLI SHALL accept `--resume` to skip creation for prediction IDs already in the eval DDB table.
8. THE CLI SHALL accept `--skip-cleanup` to leave eval bundles in the DDB table after the run.
9. THE CLI SHALL print a summary to stdout showing per-evaluator scores, calibration metrics, phase durations, and per-case results, matching the format of the current `unified_eval.py` output.
10. THE CLI SHALL write the report to the DDB report store. Local JSON backup is only written when `--local-backup` is explicitly passed.
