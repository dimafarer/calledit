# Requirements Document

## Introduction

The continuous verification evaluation system extends the existing batched eval pipeline (`eval/run_eval.py`) to mirror production's continuous verification behavior. Today, the eval runs creation and verification in a single batch, but only evaluates the ~22 golden dataset cases that have hardcoded expected outcomes. The remaining 48 cases are created but never meaningfully verified because they represent non-deterministic future events (sports scores, stock prices, weather) whose outcomes are unknown at dataset creation time.

In production, the scanner Lambda runs every 15 minutes via EventBridge, finds predictions whose verification date has passed, and the verification agent researches the outcome. This system brings that same continuous pattern to the eval framework: create all 70 predictions once, then repeatedly re-verify inconclusive predictions as real-world events resolve, scoring the system's evolving performance over time.

## Glossary

- **Eval_Runner**: The Python CLI entry point that orchestrates creation, verification, and evaluation phases (`eval/run_eval.py`)
- **Creation_Agent**: The Strands agent deployed on AgentCore that parses raw prediction text into structured bundles with verification plans, dates, and verifiability scores
- **Verification_Agent**: The Strands agent deployed on AgentCore that researches whether predictions came true using Browser and Brave Search tools
- **Eval_DDB_Table**: The DynamoDB table `calledit-v4-eval` where prediction bundles are stored during eval runs
- **Reports_Table**: The DynamoDB table `calledit-v4-eval-reports` where eval report summaries and case results are stored for the dashboard
- **Verification_Pass**: A single execution of the verification agent across all eligible predictions in the eval table
- **Resolution_Rate**: The fraction of predictions that have been confirmed or refuted out of all predictions that have been verified at least once
- **Stale_Inconclusive**: A prediction whose verification date has passed but whose verdict remains inconclusive after verification, indicating a verification agent failure
- **V_Score**: The verifiability score (0.0–1.0) assigned by the creation agent's plan reviewer, predicting how likely the prediction is to be resolvable
- **Continuous_Report**: A report written to the Reports_Table after each verification pass, capturing the evolving state of all cases
- **Case_Status**: The lifecycle state of a case: `pending` (created, not yet verified), `inconclusive` (verified but unresolved), `resolved` (confirmed or refuted), or `error` (creation or verification failure)
- **Dashboard**: The React frontend at `frontend-v4/src/pages/EvalDashboard/` that displays eval reports and case results

## Requirements

### Requirement 1: One-Time Creation Phase

**User Story:** As an eval operator, I want to run the creation agent on all 70 golden dataset predictions once and persist the bundles, so that subsequent verification passes can re-verify without re-creating.

#### Acceptance Criteria

1. WHEN the `--continuous` flag is passed, THE Eval_Runner SHALL execute the creation agent on all cases in the golden dataset and store bundles in the Eval_DDB_Table with `--skip-cleanup` behavior
2. WHEN creation completes, THE Eval_Runner SHALL record each case's prediction_id, creation duration, and any creation errors in a local state file
3. IF a creation invocation fails for a case, THEN THE Eval_Runner SHALL log the error, mark the case as `error` status, and continue processing remaining cases
4. WHEN the `--continuous` flag is combined with `--verify-only`, THE Eval_Runner SHALL skip the creation phase and load existing bundles from the Eval_DDB_Table

### Requirement 2: Continuous Verification Pass

**User Story:** As an eval operator, I want to run the verification agent on all predictions (not just qualifying ones), so that non-deterministic future events can be evaluated as they resolve in the real world.

#### Acceptance Criteria

1. WHEN a verification pass executes in continuous mode, THE Eval_Runner SHALL invoke the Verification_Agent on all predictions that have a bundle in the Eval_DDB_Table, regardless of whether the case has a hardcoded expected outcome
2. WHEN the Verification_Agent returns a verdict of `confirmed` or `refuted`, THE Eval_Runner SHALL mark the case as `resolved` and record the verdict, confidence, evidence, and reasoning
3. WHEN the Verification_Agent returns a verdict of `inconclusive`, THE Eval_Runner SHALL mark the case as `inconclusive` and record the reasoning
4. IF the Verification_Agent invocation fails for a case, THEN THE Eval_Runner SHALL log the error, preserve the case's previous verdict if one exists, and continue processing remaining cases
5. THE Eval_Runner SHALL refresh the Cognito JWT token before it expires during long verification passes spanning more than 50 minutes

### Requirement 3: Recurring Re-Verification of Inconclusive Cases

**User Story:** As an eval operator, I want inconclusive predictions to be re-verified on subsequent passes, so that predictions resolve as real-world events happen.

#### Acceptance Criteria

1. WHEN a verification pass executes, THE Eval_Runner SHALL re-verify all cases with `inconclusive` status from previous passes
2. WHEN a previously inconclusive case receives a `confirmed` or `refuted` verdict, THE Eval_Runner SHALL update the case status to `resolved` and record the pass number on which resolution occurred
3. THE Eval_Runner SHALL skip re-verification of cases already in `resolved` status to avoid unnecessary Verification_Agent invocations
4. WHEN the `--reverify-resolved` flag is passed, THE Eval_Runner SHALL re-verify all cases including those already resolved

### Requirement 4: Per-Pass Evaluation and Reporting

**User Story:** As an eval operator, I want evaluators to run after each verification pass and produce a report, so that I can track how the system's performance evolves over time.

#### Acceptance Criteria

1. WHEN a verification pass completes, THE Eval_Runner SHALL run all creation evaluators on all 70 cases and all verification evaluators on resolved cases only
2. THE Eval_Runner SHALL compute calibration metrics using all cases that have been verified at least once
3. THE Eval_Runner SHALL write a Continuous_Report to the Reports_Table with agent type `continuous` and a unique timestamp for each pass
4. THE Continuous_Report SHALL include a `pass_number` field in run_metadata indicating which verification pass produced the report (1-indexed)
5. THE Continuous_Report SHALL include a `resolution_rate` field in calibration_scores representing the fraction of verified cases that have resolved

### Requirement 5: Resolution Rate and Stale Inconclusive Tracking

**User Story:** As an eval operator, I want to track how resolution rate improves over time and identify predictions that remain inconclusive after their verification date has passed, so that I can measure the verification agent's effectiveness on real-world events.

#### Acceptance Criteria

1. THE Eval_Runner SHALL compute the Resolution_Rate as the count of cases with `confirmed` or `refuted` verdicts divided by the total count of cases that have been verified at least once
2. THE Eval_Runner SHALL compute the Stale_Inconclusive rate as the count of cases whose verification date is in the past and whose verdict is `inconclusive`, divided by the total count of cases whose verification date is in the past
3. WHEN a case's verification date is in the future, THE Eval_Runner SHALL exclude that case from the Stale_Inconclusive calculation
4. THE Eval_Runner SHALL include both Resolution_Rate and Stale_Inconclusive rate in the Continuous_Report's calibration_scores

### Requirement 6: Calibration — V-Score Predicts Resolution Speed

**User Story:** As an eval operator, I want to measure whether high V-score predictions resolve faster than low V-score ones, so that I can validate the creation agent's scoring accuracy.

#### Acceptance Criteria

1. THE Eval_Runner SHALL compute the median pass number at which high-tier (V_Score >= 0.7) cases first resolved
2. THE Eval_Runner SHALL compute the median pass number at which moderate-tier (0.4 <= V_Score < 0.7) cases first resolved
3. THE Eval_Runner SHALL compute the median pass number at which low-tier (V_Score < 0.4) cases first resolved
4. THE Continuous_Report SHALL include a `resolution_speed_by_tier` field in calibration_scores containing the median resolution pass for each tier
5. WHEN fewer than 2 cases in a tier have resolved, THE Eval_Runner SHALL report the median as `null` for that tier

### Requirement 7: Continuous Run Orchestration

**User Story:** As an eval operator, I want a single CLI command that runs the full continuous loop (create once, then verify repeatedly on a schedule), so that I can start a continuous eval and walk away.

#### Acceptance Criteria

1. WHEN the `--continuous` flag is passed with `--interval <minutes>`, THE Eval_Runner SHALL execute the creation phase once, then repeat verification passes at the specified interval
2. WHEN the `--continuous` flag is passed without `--interval`, THE Eval_Runner SHALL default to a 15-minute interval between verification passes
3. WHEN the `--max-passes <N>` flag is passed, THE Eval_Runner SHALL stop after N verification passes and print a final summary
4. WHEN the `--max-passes` flag is not passed, THE Eval_Runner SHALL run indefinitely until interrupted with Ctrl+C
5. WHEN interrupted with Ctrl+C, THE Eval_Runner SHALL complete the current verification pass, write the final report, and exit gracefully
6. WHEN the `--continuous` flag is passed with `--once`, THE Eval_Runner SHALL execute a single verification pass (no creation) and exit, enabling on-demand re-verification

### Requirement 8: Continuous State Persistence

**User Story:** As an eval operator, I want the continuous eval state to persist between process restarts, so that I can stop and resume without losing progress.

#### Acceptance Criteria

1. THE Eval_Runner SHALL persist continuous eval state to a JSON file at `eval/continuous_state.json` after each verification pass
2. THE state file SHALL contain: the list of prediction_ids with their current Case_Status, the pass number, the timestamp of each pass, and the verdict history for each case
3. WHEN the `--continuous` flag is combined with `--resume`, THE Eval_Runner SHALL load state from the state file and continue from the last completed pass number
4. IF the state file does not exist when `--resume` is used, THEN THE Eval_Runner SHALL start fresh from pass 1

### Requirement 9: Dashboard — Continuous Eval Tab

**User Story:** As an eval operator, I want a dedicated dashboard tab for continuous eval runs that shows cases evolving over time, so that I can visually track resolution progress.

#### Acceptance Criteria

1. THE Dashboard SHALL include a "Continuous Eval" tab in the AGENT_TABS configuration with agent type `continuous`
2. WHEN the Continuous Eval tab is selected, THE Dashboard SHALL load reports from the Reports_Table with agent type `continuous`
3. THE Dashboard SHALL display a run selector dropdown listing all continuous eval passes, sorted by timestamp descending

### Requirement 10: Dashboard — Case Status Color Coding

**User Story:** As an eval operator, I want cases color-coded by their verification status, so that I can quickly see which predictions have resolved and which are problematic.

#### Acceptance Criteria

1. WHEN a case has a verdict of `confirmed` or `refuted`, THE Dashboard SHALL render the case row's verdict cell with green text (#22c55e)
2. WHEN a case has a verdict of `inconclusive` and the case's verification date is in the past, THE Dashboard SHALL render the case row's verdict cell with red text (#ef4444)
3. WHEN a case has not yet been verified or the case's verification date is in the future, THE Dashboard SHALL render the case row's verdict cell with grey text (#64748b)
4. WHEN a case has been successfully evaluated with all evaluators passing, THE Dashboard SHALL render the case row's ID cell with white text (#e2e8f0)
5. WHEN a case has a creation or verification error, THE Dashboard SHALL render the case row with a dark red background (#3b1111)

### Requirement 11: Dashboard — Resolution Rate Chart

**User Story:** As an eval operator, I want a chart showing resolution rate over time across verification passes, so that I can see the eval converging as real-world events happen.

#### Acceptance Criteria

1. WHEN multiple continuous eval reports exist, THE Dashboard SHALL render a line chart with pass number on the x-axis and resolution rate (0.0–1.0) on the y-axis
2. THE Dashboard SHALL plot a second line on the same chart showing the stale inconclusive rate over passes
3. WHEN fewer than 2 continuous eval reports exist, THE Dashboard SHALL display a message indicating insufficient data for the chart
4. THE Dashboard SHALL label each data point with the pass timestamp on hover

### Requirement 12: Dashboard — Resolution Speed by Tier Chart

**User Story:** As an eval operator, I want to visualize whether high V-score predictions resolve faster than low V-score ones, so that I can assess calibration quality at a glance.

#### Acceptance Criteria

1. WHEN a continuous eval report contains `resolution_speed_by_tier` data, THE Dashboard SHALL render a grouped bar chart showing median resolution pass for each V-score tier (high, moderate, low)
2. WHEN a tier has a `null` median (fewer than 2 resolved cases), THE Dashboard SHALL render that bar as empty with a "N/A" label
