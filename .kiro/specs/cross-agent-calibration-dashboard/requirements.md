# Requirements Document

## Introduction

V4-7a-4 is the capstone spec for the CalledIt v4 eval framework. It delivers three components: (1) a DynamoDB-backed eval report storage layer that replaces local JSON files as the source of truth (resolving backlog item 1 and Decision 29's "not DynamoDB — yet"), (2) a cross-agent calibration runner that feeds creation agent output into the verification agent and measures whether the verifiability_score accurately predicts verification success, and (3) a dashboard with three tabs covering creation agent eval, verification agent eval, and cross-agent calibration. The dashboard replaces the v3 Streamlit dashboard (`eval/dashboard/app.py`) and reads reports from DDB via a Python data loader. This spec connects the two separate agent eval experiments (Decision 123) into a unified view and delivers the Tier 3 calibration metric (Decision 122). All three eval runners (creation, verification, calibration) write to DDB; local JSON files are retained as optional backup.

## Glossary

- **Calibration_Runner**: The Python script (`eval/calibration_eval.py`) that orchestrates cross-agent calibration runs by invoking the creation agent on prediction text, then feeding the resulting bundle to the verification agent, and comparing the verifiability_score against the actual verification outcome.
- **Creation_Backend**: The existing `eval/backends/agentcore_backend.py` module that invokes the deployed creation agent via HTTPS with JWT bearer token authentication (Decision 121).
- **Verification_Backend**: The existing `eval/backends/verification_backend.py` module that invokes the deployed verification agent via HTTPS with SigV4 authentication.
- **Calibration_Report**: An eval report containing run metadata, per-case calibration results (verifiability_score vs actual verdict), and aggregate calibration metrics. Stored in the Reports_Table as the source of truth, with a local JSON backup at `eval/reports/calibration-eval-{timestamp}.json`.
- **Reports_Table**: The DynamoDB table `calledit-v4-eval-reports` that stores all eval reports (creation, verification, calibration) as the source of truth. Separate from the Eval_Table which holds temporary prediction bundles. PK=`AGENT#{agent_type}`, SK=ISO 8601 timestamp. Each item contains `run_metadata`, `aggregate_scores`, and `case_results`.
- **Report_Loader**: A Python module (`eval/report_store.py`) that provides read/write access to the Reports_Table, used by all three eval runners (write) and the dashboard data loader (read).
- **Dashboard**: A React-based `/eval` route in the existing `frontend-v4` app that reads eval reports from the Reports_Table via AWS SDK and renders three tabs for creation, verification, and calibration results with interactive Recharts visualizations.
- **Run_Selector**: A dropdown UI element in the Dashboard that displays available eval runs formatted as `timestamp | agent | tier | description` per Decision 127.
- **Verifiability_Score**: A float between 0.0 and 1.0 produced by the creation agent's plan reviewer, representing the predicted likelihood that the verification agent will successfully verify the prediction.
- **Verdict**: The verification agent's output classification: `confirmed`, `refuted`, or `inconclusive`.
- **Calibration_Accuracy**: The proportion of cases where the Verifiability_Score correctly predicted the verification outcome — high scores (≥0.7) should correlate with `confirmed` verdicts, low scores (<0.4) should correlate with `refuted` or `inconclusive` verdicts.
- **Eval_Table**: The DynamoDB table `calledit-v4-eval` used by the verification agent eval to store temporary prediction bundles during golden dataset evaluation.
- **Score_Tier**: The categorical mapping of Verifiability_Score: high (≥0.7), moderate (≥0.4), low (<0.4).

## Requirements

### Requirement 1: Calibration Runner End-to-End Pipeline

**User Story:** As an eval engineer, I want to run a single command that invokes the creation agent on prediction text and then feeds the resulting bundle to the verification agent, so that I can measure whether the creation agent's verifiability_score accurately predicts verification success.

#### Acceptance Criteria

1. WHEN the eval engineer runs `python eval/calibration_eval.py --tier smoke --description "description"`, THE Calibration_Runner SHALL invoke the Creation_Backend on each qualifying golden dataset case to produce a prediction bundle, write that bundle to the Eval_Table, invoke the Verification_Backend with the resulting prediction_id, and collect the Verdict and confidence.
2. THE Calibration_Runner SHALL reuse the existing Creation_Backend (JWT auth) and Verification_Backend (SigV4 auth) without duplicating authentication or invocation logic.
3. WHEN a creation agent invocation fails for a case, THE Calibration_Runner SHALL record the case as `creation_error` with the error message and continue processing remaining cases.
4. WHEN a verification agent invocation fails for a case, THE Calibration_Runner SHALL record the case as `verification_error` with the error message and continue processing remaining cases.
5. THE Calibration_Runner SHALL clean up all temporary bundles written to the Eval_Table after the run completes, regardless of success or failure of individual cases.

### Requirement 2: Calibration Report Schema and DDB Storage

**User Story:** As an eval engineer, I want calibration run results saved to DynamoDB as the source of truth with a local JSON backup, so that the dashboard can query reports from any machine and I have a local fallback.

#### Acceptance Criteria

1. THE Calibration_Runner SHALL write each run to the Reports_Table with PK=`AGENT#calibration` and SK=ISO 8601 timestamp, and also save a local backup as `eval/reports/calibration-eval-{timestamp}.json`.
2. THE Calibration_Report SHALL include a `run_metadata` object containing: `description`, `prompt_versions`, `model_id`, `agent_runtime_arn`, `git_commit`, `run_tier`, `dataset_version`, `agent` (value: `"calibration"`), `timestamp`, `duration_seconds`, `case_count`, `features`, and `ground_truth_limitation`.
3. THE Calibration_Report SHALL include an `aggregate_scores` object containing: `calibration_accuracy` (proportion of cases where Score_Tier prediction aligned with Verdict outcome), `mean_absolute_error` (average absolute difference between Verifiability_Score and a binary verification success indicator), `high_score_confirmation_rate` (proportion of high-tier cases that received `confirmed` verdicts), `low_score_failure_rate` (proportion of low-tier cases that received `refuted` or `inconclusive` verdicts), and `verdict_distribution` (counts of `confirmed`, `refuted`, `inconclusive`, and error cases).
4. THE Calibration_Report SHALL include a `case_results` array where each entry contains: `id`, `prediction_text`, `verifiability_score`, `score_tier`, `expected_verdict` (from golden dataset), `actual_verdict`, `actual_confidence`, `calibration_correct` (boolean), `creation_duration_seconds`, `verification_duration_seconds`, and `error` (null when successful).
5. THE Calibration_Report SHALL include a `bias_warning` field that surfaces dataset bias when all qualifying cases share the same expected outcome, referencing the known limitation that all 7 qualifying verification cases have `confirmed` expected outcomes.

### Requirement 3: Calibration Runner CLI Interface

**User Story:** As an eval engineer, I want the calibration runner to follow the same CLI conventions as the creation and verification eval runners, so that I can use familiar flags and workflows.

#### Acceptance Criteria

1. THE Calibration_Runner SHALL accept `--tier` with values `smoke` and `full`, where `smoke` uses the smoke test subset and `full` uses all qualifying cases (cases with `expected_verification_outcome` and `verification_mode: "immediate"`).
2. THE Calibration_Runner SHALL accept `--description` for a one-line run description, with an auto-generated default if omitted.
3. THE Calibration_Runner SHALL accept `--dry-run` to list qualifying cases and their expected outcomes without invoking any agents.
4. THE Calibration_Runner SHALL accept `--case` to run a single case by ID.
5. WHEN the run completes, THE Calibration_Runner SHALL print a summary table showing aggregate calibration metrics and per-case results to stdout.
6. THE Calibration_Runner SHALL require Cognito credentials (COGNITO_USERNAME, COGNITO_PASSWORD environment variables) for the creation agent and AWS credentials for the verification agent, and SHALL fail with a clear error message if either credential set is missing.

### Requirement 4: Dashboard Structure with Three Tabs

**User Story:** As an eval engineer, I want a dashboard that reads eval reports from DynamoDB and displays creation, verification, and calibration results in separate tabs, so that I can view results from any machine without needing local report files.

#### Acceptance Criteria

1. THE Dashboard SHALL be implemented as a `/eval` route in the existing `frontend-v4` React application, using React Router for navigation and Recharts for interactive charts.
2. THE Dashboard SHALL display three tabs: "Creation Agent", "Verification Agent", and "Cross-Agent Calibration".
3. WHEN the user selects the "Creation Agent" tab, THE Dashboard SHALL query the Reports_Table with PK=`AGENT#creation` and display matching reports.
4. WHEN the user selects the "Verification Agent" tab, THE Dashboard SHALL query the Reports_Table with PK=`AGENT#verification` and display matching reports.
5. WHEN the user selects the "Cross-Agent Calibration" tab, THE Dashboard SHALL query the Reports_Table with PK=`AGENT#calibration` and display matching reports.
6. THE Dashboard SHALL authenticate DDB requests using the existing Cognito auth context from the React app.

### Requirement 5: Run Selector and Metadata Display

**User Story:** As an eval engineer, I want to select from available eval runs using a dropdown that shows meaningful context, so that I can quickly identify which run to inspect.

#### Acceptance Criteria

1. THE Dashboard SHALL display a Run_Selector dropdown for each tab showing available runs formatted as `timestamp | agent | tier | description` per Decision 127.
2. WHEN the user selects a run from the Run_Selector, THE Dashboard SHALL display the run's metadata including: description, prompt_versions, model_id, git_commit, run_tier, dataset_version, duration_seconds, and case_count.
3. WHEN a run's metadata includes a `ground_truth_limitation` or `bias_warning` field, THE Dashboard SHALL display the limitation text as a visible warning banner.
4. THE Dashboard SHALL sort runs in the Run_Selector by timestamp descending (newest first).

### Requirement 6: Creation Agent Tab Content

**User Story:** As an eval engineer, I want the creation agent tab to show aggregate scores and per-case detail, so that I can understand creation agent quality at a glance and drill into individual cases.

#### Acceptance Criteria

1. WHEN a creation agent run is selected, THE Dashboard SHALL display aggregate scores as a summary bar showing each evaluator name and its score, with color coding: green for scores ≥ 0.8, yellow for scores ≥ 0.5, red for scores < 0.5.
2. WHEN a creation agent run is selected, THE Dashboard SHALL display a case results table with columns: case ID, input text (truncated to 60 characters), and one column per evaluator showing the score with pass/fail indicator.
3. WHEN the user clicks a case row in the results table, THE Dashboard SHALL expand an inline detail view showing the full input text and each evaluator's score, pass status, and reason text.

### Requirement 7: Verification Agent Tab Content

**User Story:** As an eval engineer, I want the verification agent tab to show aggregate scores and per-case detail including verdict accuracy, so that I can understand verification agent quality.

#### Acceptance Criteria

1. WHEN a verification agent run is selected, THE Dashboard SHALL display aggregate scores as a summary bar, using the same color coding as the creation agent tab.
2. WHEN a verification agent run is selected, THE Dashboard SHALL display a case results table with columns: case ID, prediction text (truncated to 60 characters), expected verdict, actual verdict (from the verdict_accuracy evaluator reason text when available), and one column per evaluator showing the score.
3. WHEN a verification agent run includes `ground_truth_limitation` in its metadata, THE Dashboard SHALL display the limitation text as a warning banner above the results table.

### Requirement 8: Calibration Tab Content

**User Story:** As an eval engineer, I want the calibration tab to show whether the creation agent's verifiability_score accurately predicts verification success, so that I can assess the calibration between both agents.

#### Acceptance Criteria

1. WHEN a calibration run is selected, THE Dashboard SHALL display aggregate calibration metrics: calibration_accuracy, mean_absolute_error, high_score_confirmation_rate, and low_score_failure_rate.
2. WHEN a calibration run is selected, THE Dashboard SHALL display a scatter plot (or equivalent visualization) with Verifiability_Score on the x-axis and verification outcome (1.0 for confirmed, 0.5 for inconclusive, 0.0 for refuted) on the y-axis, with each case as a labeled point.
3. WHEN a calibration run is selected, THE Dashboard SHALL display a case results table with columns: case ID, prediction text (truncated), verifiability_score, score_tier, expected verdict, actual verdict, actual confidence, and calibration_correct.
4. WHEN the calibration report includes a `bias_warning`, THE Dashboard SHALL display the bias warning prominently above the results.
5. WHEN a calibration run contains error cases (creation_error or verification_error), THE Dashboard SHALL display error cases in the table with the error message and a distinct visual indicator.

### Requirement 9: Multi-Run Comparison

**User Story:** As an eval engineer, I want to compare metrics across multiple runs filtered by different dimensions, so that I can track the impact of model changes, prompt iterations, and code changes.

#### Acceptance Criteria

1. THE Dashboard SHALL provide filter controls allowing the user to select multiple runs for overlay comparison within each tab.
2. WHEN multiple runs are selected for comparison, THE Dashboard SHALL display a trend line chart showing aggregate scores across the selected runs ordered by timestamp.
3. THE Dashboard SHALL allow filtering runs by `run_tier` to compare only runs of the same tier.
4. WHEN comparing runs with different `prompt_versions`, THE Dashboard SHALL highlight which prompt versions changed between runs.

### Requirement 10: Per-Case Detail View

**User Story:** As an eval engineer, I want to drill into individual case results to see evaluator scores and judge reasoning, so that I can diagnose specific failures.

#### Acceptance Criteria

1. WHEN the user clicks a case row in any tab's results table, THE Dashboard SHALL expand an inline detail panel showing all evaluator scores with their full reason text.
2. WHEN a case has an error (creation_error or verification_error), THE Dashboard SHALL display the full error message in the detail panel.
3. THE Dashboard SHALL allow collapsing the detail panel by clicking the case row again.

### Requirement 11: DDB Report Store Module

**User Story:** As an eval engineer, I want a shared Python module that handles reading and writing eval reports to DynamoDB, so that all three eval runners and the dashboard use the same storage layer without duplicating DDB logic.

#### Acceptance Criteria

1. THE Report_Loader module (`eval/report_store.py`) SHALL provide a `write_report(agent_type: str, report: dict)` function that writes a report to the Reports_Table with PK=`AGENT#{agent_type}` and SK=the report's ISO 8601 timestamp.
2. THE Report_Loader module SHALL provide a `list_reports(agent_type: str) -> list[dict]` function that queries the Reports_Table for all reports matching PK=`AGENT#{agent_type}`, returning `run_metadata` and `aggregate_scores` for each (without `case_results` to minimize read cost).
3. THE Report_Loader module SHALL provide a `get_report(agent_type: str, timestamp: str) -> dict` function that retrieves a full report including `case_results` by PK and SK.
4. THE Report_Loader module SHALL create the Reports_Table (`calledit-v4-eval-reports`) automatically if it does not exist, using PAY_PER_REQUEST billing mode with PK (String) and SK (String) key schema.
5. THE Report_Loader module SHALL handle DynamoDB Decimal serialization for float values in reports, converting floats to Decimal on write and Decimal back to float on read.

### Requirement 12: Backfill Existing Eval Runners to Write to DDB

**User Story:** As an eval engineer, I want the existing creation and verification eval runners to also write reports to DynamoDB, so that all historical and future runs are available in the dashboard without manual import.

#### Acceptance Criteria

1. THE existing `eval/creation_eval.py` SHALL be updated to call `report_store.write_report("creation", report)` after saving the local JSON file, using the Report_Loader module.
2. THE existing `eval/verification_eval.py` SHALL be updated to call `report_store.write_report("verification", report)` after saving the local JSON file, using the Report_Loader module.
3. WHEN a DDB write fails, THE eval runner SHALL log a warning and continue — DDB write failure SHALL NOT abort the eval run or prevent local JSON file saving.
4. THE Report_Loader module SHALL provide a `backfill_from_files(directory: str)` function that reads all existing `eval/reports/*.json` files and writes them to the Reports_Table, skipping any that already exist (idempotent). This enables importing historical reports.
