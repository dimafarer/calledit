# Requirements Document

## Introduction

The CalledIt project currently uses three separate eval runners (`creation_eval.py`, `verification_eval.py`, `calibration_eval.py`) that each invoke agents independently. The calibration runner duplicates work the other two do and uses a synthetic inline flow instead of the real production DynamoDB-based flow. This feature replaces all three with a single unified pipeline that mirrors production: creation pass → DDB write → verification pass (scanner pattern) → evaluation → one unified report. The golden dataset is audited so every prediction is resolvable within the eval window, and the retry policy only covers timing (verification date approaching), never tool flakiness.

## Glossary

- **Unified_Pipeline**: The single eval runner (`eval/unified_eval.py`) that replaces the three separate runners and orchestrates all phases sequentially.
- **Creation_Pass**: The first phase of the pipeline where all golden dataset predictions are fed through the Creation Agent and the resulting bundles are written to the Eval_Table.
- **Verification_Pass**: The second phase where bundles in the Eval_Table are picked up and run through the Verification Agent using the scanner pattern (read bundle from DDB, gather evidence, write verdict back to DDB).
- **Eval_Table**: The DynamoDB table `calledit-v4-eval`, isolated from the production table `calledit-v4`, used to store prediction bundles and verdicts during an eval run.
- **Scanner_Pattern**: The production flow where the Verification Agent reads a pending bundle from DDB by prediction_id, gathers evidence via tools, and writes the verdict back to DDB.
- **Golden_Dataset**: The merged dataset produced by `eval/dataset_merger.py` from `eval/golden_dataset.json` (static) and `eval/dynamic_golden_dataset.json` (dynamic).
- **Creation_Agent**: The AgentCore-deployed agent that parses prediction text into a structured bundle (parsed claim, verification plan, verifiability score, verification mode). Uses JWT auth via Cognito.
- **Verification_Agent**: The AgentCore-deployed agent that reads a bundle from DDB, gathers evidence via Brave Search and Code Interpreter, and produces a verdict (confirmed/refuted/inconclusive). Uses SigV4 auth.
- **Verifiability_Score**: A float 0.0–1.0 produced by the Creation_Agent indicating how verifiable a prediction is.
- **Score_Tier**: Classification of Verifiability_Score into "high" (≥0.7), "moderate" (≥0.4), or "low" (<0.4).
- **Calibration_Metrics**: Metrics measuring whether Verifiability_Score predicts verification success (calibration accuracy, MAE, high-score confirmation rate, low-score failure rate).
- **Unified_Report**: A single JSON report containing creation metrics, verification metrics, and calibration metrics for all cases in one run.
- **Report_Store**: The DynamoDB table `calledit-v4-eval-reports` where eval reports are persisted for the dashboard.
- **Timing_Retry**: A re-scan of bundles whose verification date is slightly in the future, performed after a short wait. Distinct from tool-flakiness retry, which is not performed.
- **Run_Manifest**: Metadata block in the Unified_Report recording dataset version, case count, duration, phase durations, git commit, and prompt versions.

## Requirements

### Requirement 1: Dataset Audit and Curation

**User Story:** As an eval operator, I want every prediction in the merged golden dataset to be resolvable within the eval window, so that null expected verdicts do not pollute metrics.

#### Acceptance Criteria

1. THE Unified_Pipeline SHALL only include predictions from the Golden_Dataset where `expected_verification_outcome` is non-null.
2. WHEN a prediction has a null `expected_verification_outcome`, THE Unified_Pipeline SHALL exclude that prediction from the eval run and log a warning with the prediction id.
3. THE Unified_Pipeline SHALL report the count of included and excluded predictions at the start of each run.

### Requirement 2: Creation Pass

**User Story:** As an eval operator, I want the pipeline to feed all qualifying predictions through the Creation Agent and write the resulting bundles to the Eval_Table, so that the verification pass can use real bundles.

#### Acceptance Criteria

1. WHEN the Creation_Pass begins, THE Unified_Pipeline SHALL authenticate with Cognito and obtain a JWT token for the Creation_Agent.
2. THE Unified_Pipeline SHALL invoke the Creation_Agent for each qualifying prediction and capture the returned bundle (parsed claim, verification plan, verifiability score, verification mode, prediction_id).
3. WHEN the Creation_Agent returns a bundle, THE Unified_Pipeline SHALL write the bundle to the Eval_Table with `status=pending` and the prediction_id as the DDB key (`PK=PRED#{prediction_id}`, `SK=BUNDLE`).
4. IF the Creation_Agent invocation fails for a prediction, THEN THE Unified_Pipeline SHALL record the error in the case result, skip that prediction for subsequent phases, and continue with the remaining predictions.
5. THE Unified_Pipeline SHALL record the duration of the Creation_Pass in the Run_Manifest.

### Requirement 3: Verification Pass Using Scanner Pattern

**User Story:** As an eval operator, I want the verification pass to use the same scanner pattern as production (read bundle from DDB, invoke Verification Agent with prediction_id and table_name), so that the eval exercises the real production flow.

#### Acceptance Criteria

1. WHEN the Verification_Pass begins, THE Unified_Pipeline SHALL iterate over all prediction_ids that were successfully written to the Eval_Table during the Creation_Pass.
2. THE Unified_Pipeline SHALL invoke the Verification_Agent with each prediction_id and `table_name=calledit-v4-eval`, matching the production scanner pattern.
3. WHEN the Verification_Agent returns a verdict, THE Unified_Pipeline SHALL read the full verdict (including evidence and reasoning) back from the Eval_Table.
4. IF the Verification_Agent invocation fails for a prediction, THEN THE Unified_Pipeline SHALL record the error in the case result and continue with the remaining predictions.
5. THE Unified_Pipeline SHALL record the duration of the Verification_Pass in the Run_Manifest.

### Requirement 4: Verification Timing

**User Story:** As an eval operator, I want the pipeline to compute the exact wait time from the prediction bundles' verification dates before running the verification pass, so that all time-gated predictions are verifiable without guessing or arbitrary retries.

#### Acceptance Criteria

1. AFTER the Creation_Pass completes, THE Unified_Pipeline SHALL read the `verification_date` field from every bundle in the Eval_Table.
2. THE Unified_Pipeline SHALL compute the latest `verification_date` across all bundles and determine the exact wait time needed (latest verification_date minus current time, plus a 30-second buffer).
3. IF the computed wait time is positive (some verification dates are in the future), THEN THE Unified_Pipeline SHALL log the wait duration and sleep until all verification dates have passed before starting the Verification_Pass.
4. IF the computed wait time is zero or negative (all verification dates are already in the past), THEN THE Unified_Pipeline SHALL proceed to the Verification_Pass immediately.
5. THE Unified_Pipeline SHALL NOT retry any prediction that failed due to tool errors (Brave Search failures, Code Interpreter errors, agent invocation errors). Only timing is handled; tool flakiness is not masked.

### Requirement 5: Evaluation Phase

**User Story:** As an eval operator, I want the pipeline to evaluate all results using the existing evaluator modules, so that creation quality, verification quality, and calibration are all measured in one pass.

#### Acceptance Criteria

1. WHEN the Verification_Pass (and any Timing_Retry) completes, THE Unified_Pipeline SHALL run all creation evaluators (schema_validity, field_completeness, score_range, date_resolution, dimension_count, tier_consistency) against each creation bundle.
2. WHEN the run tier is `smoke+judges` or `full`, THE Unified_Pipeline SHALL additionally run Tier 2 creation evaluators (intent_preservation, plan_quality) against each creation bundle.
3. THE Unified_Pipeline SHALL run all verification evaluators (schema_validity, verdict_validity, confidence_range, evidence_completeness, evidence_structure) against each verification result.
4. WHEN the run tier is `smoke+judges` or `full` and the source is `golden`, THE Unified_Pipeline SHALL additionally run verdict_accuracy and evidence_quality evaluators against each verification result.
5. THE Unified_Pipeline SHALL select verification evaluators per case based on verification_mode (immediate, at_date, before_date, recurring), matching the existing mode-aware routing logic.
6. THE Unified_Pipeline SHALL compute Calibration_Metrics (calibration_accuracy, mean_absolute_error, high_score_confirmation_rate, low_score_failure_rate, verdict_distribution) from the paired creation scores and verification verdicts.

### Requirement 6: Unified Report

**User Story:** As an eval operator, I want one report containing creation metrics, verification metrics, and calibration metrics, so that I can assess the full system in a single artifact.

#### Acceptance Criteria

1. THE Unified_Pipeline SHALL produce a single JSON report file named `unified-eval-{YYYYMMDD-HHMMSS}.json` in the output directory.
2. THE Unified_Report SHALL contain a `run_metadata` section with: description, timestamp, duration_seconds, case_count, dataset_version, dataset_sources, run_tier, git_commit, prompt_versions, phase_durations (creation_seconds, verification_seconds, evaluation_seconds), and ground_truth_limitation.
3. THE Unified_Report SHALL contain a `creation_scores` section with per-evaluator averages and overall Tier 1 pass rate, matching the format of the existing creation eval report.
4. THE Unified_Report SHALL contain a `verification_scores` section with per-evaluator averages and overall Tier 1 pass rate, matching the format of the existing verification eval report.
5. THE Unified_Report SHALL contain a `calibration_scores` section with calibration_accuracy, mean_absolute_error, high_score_confirmation_rate, low_score_failure_rate, and verdict_distribution.
6. THE Unified_Report SHALL contain a `case_results` array where each entry includes: prediction_id, prediction_text, creation_scores, verification_scores, verifiability_score, score_tier, expected_verdict, actual_verdict, calibration_correct, creation_duration_seconds, verification_duration_seconds, and any error.
7. WHEN the Unified_Report is generated, THE Unified_Pipeline SHALL write the report to the Report_Store with `agent_type=unified`.
8. THE Unified_Report SHALL include per-verification-mode breakdowns in both the creation_scores and verification_scores sections.

### Requirement 7: Eval Table Lifecycle

**User Story:** As an eval operator, I want a clear lifecycle for the Eval_Table (create all → verify all → evaluate all → clean up), with support for restart if interrupted.

#### Acceptance Criteria

1. WHEN the Unified_Pipeline starts, THE Unified_Pipeline SHALL create the Eval_Table if it does not exist (PK=String HASH, SK=String RANGE, PAY_PER_REQUEST billing).
2. WHEN the pipeline completes (successfully or with errors), THE Unified_Pipeline SHALL delete all items written during the run from the Eval_Table.
3. THE Unified_Pipeline SHALL support a `--resume` flag that skips the Creation_Pass for prediction_ids that already have bundles in the Eval_Table with `status=pending` or `status=verified`.
4. IF cleanup fails for any item, THEN THE Unified_Pipeline SHALL log a warning and continue cleanup for remaining items.

### Requirement 8: CLI Interface

**User Story:** As an eval operator, I want a single CLI entry point with familiar flags, so that I can run the unified pipeline with the same ease as the old runners.

#### Acceptance Criteria

1. THE Unified_Pipeline SHALL accept the following CLI arguments: `--dataset`, `--dynamic-dataset`, `--tier` (smoke, smoke+judges, full), `--description`, `--output-dir`, `--dry-run`, `--case`, `--resume`, `--skip-cleanup`.
2. WHEN `--dry-run` is specified, THE Unified_Pipeline SHALL list all qualifying cases with their prediction_id, difficulty, expected verdict, and verification mode, without invoking any agents.
3. WHEN `--case` is specified, THE Unified_Pipeline SHALL execute only the specified case through all phases.
4. WHEN `--skip-cleanup` is specified, THE Unified_Pipeline SHALL leave bundles in the Eval_Table after the run completes (useful for debugging).
5. THE Unified_Pipeline SHALL print a summary to stdout after each run showing creation metrics, verification metrics, calibration metrics, and per-case results.

### Requirement 9: Dashboard Integration

**User Story:** As an eval operator, I want the React dashboard to display unified pipeline reports alongside the existing per-agent reports, so that I can visualize the full system performance.

#### Acceptance Criteria

1. THE Report_Store SHALL accept `agent_type=unified` for writes and queries, following the same PK/SK schema as existing agent types.
2. THE Dashboard SHALL display a fourth tab for unified reports, showing creation scores, verification scores, and calibration scores in a single view.
3. THE Dashboard SHALL render a calibration scatter plot showing verifiability_score (x-axis) vs. binary verification outcome (y-axis, 1=confirmed, 0=refuted/inconclusive) for all cases in a unified run.
4. THE Dashboard SHALL render score-vs-outcome correlation curves grouped by Score_Tier (high, moderate, low) with case counts per tier.

### Requirement 10: Backward Compatibility

**User Story:** As an eval operator, I want the old eval runners to remain functional during the transition period, so that I can compare results between old and new pipelines.

#### Acceptance Criteria

1. THE Unified_Pipeline SHALL be implemented as a new file (`eval/unified_eval.py`) without modifying the existing `creation_eval.py`, `verification_eval.py`, or `calibration_eval.py`.
2. THE Unified_Pipeline SHALL reuse the existing backend classes (`AgentCoreBackend`, `VerificationBackend`), evaluator modules, dataset merger, and report store without modifying their interfaces.
3. THE Unified_Pipeline SHALL reuse the existing `classify_score_tier` and `is_calibration_correct` functions from `calibration_eval.py`.
