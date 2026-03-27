# Requirements Document

## Introduction

Extend the CalledIt prediction verification system to support all four `verification_mode` types: `immediate` (already supported), `at_date`, `before_date`, and `recurring`. Currently only `immediate` mode predictions can be verified. The system must classify each prediction into the correct mode at creation time, pass mode context to the verification agent, schedule verification attempts according to mode-specific timing rules, and evaluate verification quality with mode-aware evaluators. The `immediate` path remains unchanged — new modes are additive.

## Glossary

- **Creation_Agent**: The AgentCore runtime (`calleditv4`) that parses user predictions through a 3-turn prompt flow (parse → plan → review) and writes prediction bundles to DynamoDB. It is a single Strands Agent running 3 sequential turns in a single conversation context — each turn sees all prior turns' outputs. On clarification, the human answers reviewer questions and the 3-turn flow repeats with enriched context (agent → agent → agent → human → repeat). Decision 94 validated this architecture over a multi-agent graph.
- **prediction_parser**: Turn 1 prompt (ID: `GESWTI1IAB`). Extracts the claim, resolves dates with timezone awareness. Produces a `ParsedClaim` structured output.
- **verification_planner**: Turn 2 prompt (ID: `ZTCOSG04KQ`). Builds the verification plan (sources, criteria, steps) and classifies the `verification_mode`. Produces a `VerificationPlan` structured output.
- **plan_reviewer**: Turn 3 prompt (ID: `6OOF6PHFRF`). Scores verifiability 0.0–1.0 across 5 dimensions, confirms the planner's `verification_mode` choice, and identifies assumptions for clarification questions. Produces a `PlanReview` structured output.
- **Verification_Agent**: The AgentCore runtime (`calleditv4-verification`) that loads a prediction bundle, gathers evidence using Browser and Code Interpreter tools, and produces a structured verdict (confirmed / refuted / inconclusive).
- **Scanner**: The EventBridge-triggered Lambda (`infrastructure/verification-scanner/scanner.py`) that queries the DynamoDB GSI for pending predictions and invokes the Verification_Agent for each one.
- **Prediction_Bundle**: The DynamoDB item (PK=`PRED#{id}`, SK=`BUNDLE`) containing parsed claim, verification plan, verifiability score, status, and verification results.
- **Verification_Mode**: An enum field on the Prediction_Bundle indicating the timing semantics for verification. One of: `immediate`, `at_date`, `before_date`, `recurring`.
- **Eval_Runner**: The Python script (`eval/verification_eval.py`) that runs verification evaluators against golden dataset cases or live DDB predictions and produces scored reports.
- **Evaluator**: A Python module in `eval/evaluators/` that scores one dimension of verification quality. Evaluators are either deterministic or LLM-judge-based.
- **Golden_Dataset**: The JSON file (`eval/golden_dataset.json`) containing test predictions with ground truth for evaluator scoring.
- **Dashboard**: The React eval dashboard (`frontend-v4/src/pages/EvalDashboard/`) that renders eval reports. It is data-driven and auto-renders new fields from report JSON.

## Requirements

### Requirement 1: Verification Mode Schema

**User Story:** As a developer, I want a `verification_mode` field on the prediction bundle, so that downstream components (Scanner, Verification_Agent, Eval_Runner) can branch on mode-specific logic.

#### Acceptance Criteria

1. THE Prediction_Bundle SHALL include a `verification_mode` field with allowed values `immediate`, `at_date`, `before_date`, or `recurring`.
2. WHEN a Prediction_Bundle is written to DynamoDB without a `verification_mode` value, THE Creation_Agent SHALL default `verification_mode` to `immediate`.
3. THE `build_bundle` function in `calleditv4/src/bundle.py` SHALL accept a `verification_mode` parameter and include it in the bundle dict.
4. THE `VerificationPlan` Pydantic model in `calleditv4/src/models.py` SHALL include a `verification_mode` field constrained to the four allowed values.
5. THE `PlanReview` Pydantic model in `calleditv4/src/models.py` SHALL include a `verification_mode` field constrained to the four allowed values (for the reviewer's confirmation).

### Requirement 2: Mode Classification by the Verification Planner

**User Story:** As a developer, I want the verification_planner (turn 2) to classify each prediction into the correct verification mode, so that the plan it builds matches the mode's timing semantics.

#### Acceptance Criteria

1. WHEN the verification_planner produces its structured output, IT SHALL set `verification_mode` to one of `immediate`, `at_date`, `before_date`, or `recurring` based on the prediction's temporal characteristics.
2. WHEN a prediction is verifiable right now with a single check and the answer is final (e.g., "Christmas 2026 falls on a Friday"), THE verification_planner SHALL classify `verification_mode` as `immediate`.
3. WHEN a prediction is only meaningful to check at a specific date and checking early gives the wrong answer (e.g., "S&P 500 will close higher today than yesterday"), THE verification_planner SHALL classify `verification_mode` as `at_date`.
4. WHEN a prediction can be confirmed as soon as the event occurs but can only be refuted after a deadline passes (e.g., "Python 3.14 will be released before December 2026"), THE verification_planner SHALL classify `verification_mode` as `before_date`.
5. WHEN a prediction describes a condition that is checked on a schedule and the verdict is a snapshot rather than a final answer (e.g., "The US national debt exceeds $35 trillion"), THE verification_planner SHALL classify `verification_mode` as `recurring`.
6. THE verification_planner SHALL build mode-appropriate plan steps (e.g., periodic check steps for `before_date`, snapshot semantics for `recurring`).
7. THE `calledit-verification-planner` prompt in Bedrock Prompt Management SHALL include instructions and examples for all four verification modes, deployed as a new numbered version.

### Requirement 2a: Mode Confirmation by the Plan Reviewer

**User Story:** As a developer, I want the plan_reviewer (turn 3) to confirm the verification_planner's mode classification as a semi-deterministic consistency check, so that mode misclassifications are caught before the bundle is saved.

#### Acceptance Criteria

1. WHEN the plan_reviewer produces its structured output, IT SHALL include a `verification_mode` field reflecting its own assessment of the correct mode.
2. THE Creation_Agent handler SHALL compare the verification_planner's `verification_mode` with the plan_reviewer's `verification_mode`.
3. WHEN both agree, THE Creation_Agent SHALL use the agreed mode in the saved Prediction_Bundle.
4. WHEN they disagree, THE Creation_Agent SHALL use the plan_reviewer's mode (the reviewer has more context from the full plan) and log a warning with both values.
5. THE `calledit-plan-reviewer` prompt in Bedrock Prompt Management SHALL include instructions to independently assess `verification_mode` and flag disagreement in its reasoning, deployed as a new numbered version.

### Requirement 3: Verification Mode in the Verification Agent Context

**User Story:** As a developer, I want the Verification_Agent to receive `verification_mode` in its reasoning context, so that it can adjust its evidence-gathering strategy and verdict logic per mode.

#### Acceptance Criteria

1. WHEN the Verification_Agent builds its user message from the Prediction_Bundle, THE Verification_Agent SHALL include the `verification_mode` value in the message.
2. WHILE `verification_mode` is `at_date` and the current time is before `verification_date`, THE Verification_Agent SHALL return `inconclusive` with reasoning that explains verification is premature.
3. WHILE `verification_mode` is `before_date` and the current time is before `verification_date`, THE Verification_Agent SHALL return `confirmed` only if evidence shows the event has already occurred, and `inconclusive` if the event has not yet occurred.
4. WHILE `verification_mode` is `before_date` and the current time is at or after `verification_date`, THE Verification_Agent SHALL return `refuted` if no evidence shows the event occurred before the deadline.
5. WHEN `verification_mode` is `recurring`, THE Verification_Agent SHALL treat the verdict as a point-in-time snapshot and include the check timestamp in its reasoning.
6. THE `calledit-verification-executor` prompt in Bedrock Prompt Management SHALL include mode-specific instructions, deployed as a new numbered version.

### Requirement 4: Mode-Aware Scanner Scheduling

**User Story:** As a developer, I want the Scanner to handle mode-specific scheduling, so that `at_date` predictions wait until the right time, `before_date` predictions are checked periodically, and `recurring` predictions are re-checked on schedule.

#### Acceptance Criteria

1. WHEN the Scanner retrieves a pending prediction with `verification_mode` equal to `immediate`, THE Scanner SHALL invoke the Verification_Agent immediately (current behavior, unchanged).
2. WHEN the Scanner retrieves a pending prediction with `verification_mode` equal to `at_date` and the current time is before `verification_date`, THE Scanner SHALL skip the prediction without invoking the Verification_Agent.
3. WHEN the Scanner retrieves a pending prediction with `verification_mode` equal to `at_date` and the current time is at or after `verification_date`, THE Scanner SHALL invoke the Verification_Agent.
4. WHEN the Scanner retrieves a pending prediction with `verification_mode` equal to `before_date` and the current time is before `verification_date`, THE Scanner SHALL invoke the Verification_Agent for a periodic check.
5. WHEN the Scanner retrieves a pending prediction with `verification_mode` equal to `before_date` and the Verification_Agent returns `confirmed`, THE Scanner SHALL treat the prediction as final (status transitions to `verified`).
6. WHEN the Scanner retrieves a prediction with `verification_mode` equal to `before_date`, the Verification_Agent returns `inconclusive`, and the current time is before `verification_date`, THE Scanner SHALL leave the prediction in `pending` status for the next scan cycle.
7. WHEN the Scanner retrieves a prediction with `verification_mode` equal to `recurring`, THE Scanner SHALL invoke the Verification_Agent and store the result as a snapshot without changing the prediction status from `pending`.
8. THE Scanner SHALL log the `verification_mode` for each prediction it processes.

### Requirement 5: Recurring Mode Snapshot Storage

**User Story:** As a developer, I want recurring verification results stored as timestamped snapshots with configurable interval and limits, so that the system maintains a bounded history of recurring checks rather than overwriting previous results or growing unbounded.

#### Acceptance Criteria

1. WHEN the Verification_Agent returns a result for a `recurring` prediction, THE Scanner SHALL append the result to a `verification_snapshots` list on the Prediction_Bundle rather than overwriting the top-level verdict fields.
2. THE each snapshot in `verification_snapshots` SHALL contain `verdict`, `confidence`, `evidence`, `reasoning`, and `checked_at` (ISO 8601 timestamp).
3. THE Prediction_Bundle for a `recurring` prediction SHALL retain `status` as `pending` after each snapshot is stored.
4. THE Prediction_Bundle for a `recurring` prediction SHALL include a `recurring_interval` field specifying the minimum time between checks (e.g., `"daily"`, `"weekly"`, `"every_scan"`). Default: `"daily"`.
5. THE Scanner SHALL skip a `recurring` prediction if the most recent snapshot's `checked_at` is more recent than the `recurring_interval` allows.
6. THE Prediction_Bundle for a `recurring` prediction SHALL include a `max_snapshots` field specifying the maximum number of snapshots to retain. Default: 30.
7. WHEN `verification_snapshots` exceeds `max_snapshots`, THE Scanner SHALL remove the oldest snapshot(s) to stay within the limit.
8. THE verification_planner SHALL set `recurring_interval` when classifying a prediction as `recurring`, based on how frequently the condition is likely to change.

### Requirement 6: Golden Dataset Verification Mode Annotations

**User Story:** As a developer, I want every golden dataset case annotated with `verification_mode`, so that the eval framework can route cases to the correct evaluator set.

#### Acceptance Criteria

1. THE Golden_Dataset SHALL include a `verification_mode` field on every base prediction entry.
2. WHEN a golden dataset case has `verification_readiness` equal to `immediate`, THE `verification_mode` field SHALL be set to `immediate`.
3. THE Golden_Dataset SHALL contain at least 3 cases with `verification_mode` equal to `at_date`.
4. THE Golden_Dataset SHALL contain at least 3 cases with `verification_mode` equal to `before_date`.
5. THE Golden_Dataset SHALL contain at least 3 cases with `verification_mode` equal to `recurring`.
6. THE Golden_Dataset `metadata` section SHALL include an `expected_mode_counts` object with counts per verification mode.

### Requirement 7: Mode-Aware Verification Evaluators

**User Story:** As a developer, I want mode-aware evaluators, so that the eval framework scores verification quality correctly for each mode's timing semantics.

#### Acceptance Criteria

1. THE Eval_Runner SHALL select the evaluator set based on the `verification_mode` of each test case.
2. WHEN `verification_mode` is `immediate`, THE Eval_Runner SHALL use the existing evaluator set (schema_validity, verdict_validity, confidence_range, evidence_completeness, evidence_structure, verdict_accuracy, evidence_quality) with no changes.
3. WHEN `verification_mode` is `at_date` and the simulated current time is before `verification_date`, THE `at_date_verdict_accuracy` Evaluator SHALL score `inconclusive` as the correct verdict (score 1.0).
4. WHEN `verification_mode` is `at_date` and the simulated current time is at or after `verification_date`, THE `at_date_verdict_accuracy` Evaluator SHALL score against the ground truth verdict using the same logic as the `immediate` verdict_accuracy Evaluator.
5. WHEN `verification_mode` is `before_date` and the simulated current time is before `verification_date`, THE `before_date_verdict_appropriateness` Evaluator SHALL score both `confirmed` and `inconclusive` as acceptable verdicts (score 1.0), and score `refuted` as incorrect (score 0.0).
6. WHEN `verification_mode` is `before_date` and the simulated current time is at or after `verification_date`, THE `before_date_verdict_appropriateness` Evaluator SHALL score against the ground truth verdict.
7. THE `recurring_evidence_freshness` Evaluator SHALL verify that evidence timestamps or source dates are from the current check period, not stale from a previous check.
8. THE existing `immediate` evaluators SHALL remain unchanged.

### Requirement 8: Eval Runner Mode Routing

**User Story:** As a developer, I want the eval runner to route each test case to the correct evaluator set based on `verification_mode`, so that mode-specific scoring is automatic.

#### Acceptance Criteria

1. THE Eval_Runner SHALL read `verification_mode` from each golden dataset case.
2. WHEN `verification_mode` is absent from a golden dataset case, THE Eval_Runner SHALL default to `immediate`.
3. THE `build_evaluator_list` function SHALL accept `verification_mode` as a parameter and return the evaluator set appropriate for that mode.
4. THE Eval_Runner SHALL include `verification_mode` in each per-case result in the eval report.
5. THE eval report `aggregates` section SHALL include per-mode score breakdowns.

### Requirement 9: Dashboard Mode Breakdown

**User Story:** As a developer, I want the eval dashboard to show verification quality broken down by mode, so that I can identify mode-specific quality issues.

#### Acceptance Criteria

1. WHEN an eval report contains per-case `verification_mode` fields, THE Dashboard SHALL render a mode breakdown section showing aggregate scores per mode.
2. THE Dashboard mode breakdown SHALL be data-driven, requiring no code changes beyond what the report JSON provides.
