# Requirements Document

## Introduction

The CalledIt eval framework's golden dataset (`eval/golden_dataset.json`) contains 55 base predictions, but only 10 (the `immediate` mode cases) are testable in the verification eval. The other 45 cases (`at_date`, `before_date`, `recurring`) have `expected_verification_outcome: null` because their verification dates are in the future. Worse, some "immediate" cases have time-dependent ground truth that goes stale — base-010 ("next full moon before April 1, 2026") was scored as a failure because the expected verdict expired when the date passed.

This feature introduces a generator script that produces a fresh golden dataset with time-anchored predictions each time it runs. Dynamic ground truth is computed at generation time so expected verdicts are always correct. The static golden dataset is preserved for timeless cases (calendar arithmetic, subjective predictions, etc.). The result: all four verification modes become testable in every eval run.

## Glossary

- **Generator**: The Python script (`eval/generate_dynamic_dataset.py`) that produces a fresh dynamic golden dataset file each time it runs. It computes ground truth at generation time using deterministic calculations and Brave Search API lookups.
- **Dynamic_Dataset**: The JSON file produced by the Generator (`eval/dynamic_golden_dataset.json`), containing time-anchored predictions with computed expected verdicts. Follows the same schema 4.0 format as the static Golden_Dataset.
- **Static_Dataset**: The existing `eval/golden_dataset.json` file, preserved for timeless cases where ground truth does not change over time.
- **Merged_Dataset**: The combined dataset produced by merging Static_Dataset (timeless cases) and Dynamic_Dataset (time-anchored cases) for use by the Eval_Runner. Cases are deduplicated by ID prefix (`static-*` vs `dyn-*`).
- **Ground_Truth_Source**: A categorization of how the Generator computes the expected verdict for a dynamic case. One of: `deterministic` (math, calendar, astronomical calculations), `brave_search` (live web lookup via Brave API), or `api_lookup` (structured API call).
- **Verification_Mode**: The timing semantics for verification — `immediate`, `at_date`, `before_date`, or `recurring`.
- **Eval_Runner**: The Python scripts (`eval/verification_eval.py`, `eval/creation_eval.py`, `eval/calibration_eval.py`) that run evaluators against golden dataset cases.
- **Prediction_Template**: A parameterized prediction definition in the Generator that produces a concrete prediction with computed ground truth when instantiated with current date/time context.
- **Staleness_Window**: The time period after which a dynamic prediction's ground truth may no longer be accurate. The Generator ensures all predictions have staleness windows longer than a typical eval run (~30 minutes).
- **Brave_API**: The Brave Search API used by the Generator to look up current facts for ground truth computation. Key available via `BRAVE_API_KEY` environment variable.

## Requirements

### Requirement 1: Generator Script Core

**User Story:** As a developer, I want a generator script that produces a fresh golden dataset with time-anchored predictions, so that every eval run uses current ground truth instead of stale static values.

#### Acceptance Criteria

1. THE Generator SHALL be a standalone Python script at `eval/generate_dynamic_dataset.py` executable via `/home/wsluser/projects/calledit/venv/bin/python eval/generate_dynamic_dataset.py`.
2. WHEN invoked, THE Generator SHALL produce a `eval/dynamic_golden_dataset.json` file in schema 4.0 format, compatible with the existing Eval_Runner's `load_dataset()` function.
3. THE Generator SHALL compute `expected_verification_outcome` for every prediction it produces — no prediction in the Dynamic_Dataset SHALL have a null expected verdict.
4. THE Generator SHALL record a `generated_at` ISO 8601 timestamp in the Dynamic_Dataset metadata section.
5. THE Generator SHALL record the `ground_truth_source` (deterministic, brave_search, or api_lookup) for each prediction in its `ground_truth` object.
6. THE Generator SHALL complete execution within 60 seconds under normal network conditions.
7. IF the Brave_API is unavailable or returns an error, THEN THE Generator SHALL skip brave_search-sourced predictions and log a warning, producing a dataset with only deterministic predictions.

### Requirement 2: Immediate Mode Dynamic Predictions

**User Story:** As a developer, I want the Generator to produce immediate-mode predictions about current facts with computed ground truth, so that the verification eval can score verdict accuracy without stale expected values.

#### Acceptance Criteria

1. THE Generator SHALL produce at least 3 immediate-mode predictions with non-null `expected_verification_outcome`.
2. THE Generator SHALL include deterministic immediate predictions where the answer is computable without external lookups (e.g., "Today is a weekday", day-of-week for the current date, current year arithmetic).
3. THE Generator SHALL include brave_search-sourced immediate predictions where the answer is looked up at generation time (e.g., "The current US President is [name]", "Python 3.13 has been released").
4. WHEN generating a deterministic immediate prediction, THE Generator SHALL compute the expected verdict using Python standard library functions (datetime, calendar, math) with no external dependencies.
5. WHEN generating a brave_search-sourced immediate prediction, THE Generator SHALL query the Brave_API, extract the factual answer, and set the expected verdict based on the extracted answer.
6. THE Generator SHALL include at least 1 immediate prediction expected to be `confirmed` and at least 1 expected to be `refuted`.

### Requirement 3: At-Date Mode Dynamic Predictions

**User Story:** As a developer, I want the Generator to produce at_date-mode predictions with verification dates in the very recent past, so that they are immediately verifiable and the verification eval can test at_date mode scoring.

#### Acceptance Criteria

1. THE Generator SHALL produce at least 3 at_date-mode predictions with non-null `expected_verification_outcome`.
2. THE Generator SHALL set `verification_date` for at_date predictions to a time in the recent past (within the last 24-72 hours), so the prediction is immediately verifiable by the Verification_Agent.
3. THE Generator SHALL include deterministic at_date predictions anchored to recent past dates (e.g., "The high temperature in [city] on [yesterday's date] exceeded 50°F" where the answer is looked up at generation time).
4. THE Generator SHALL include at_date predictions where the ground truth is computed via Brave_API lookup of historical data for the recent past date.
5. WHEN generating an at_date prediction, THE Generator SHALL verify that the `verification_date` is in the past relative to the generation timestamp.
6. THE Generator SHALL include at least 1 at_date prediction expected to be `confirmed` and at least 1 expected to be `refuted`.

### Requirement 4: Before-Date Mode Dynamic Predictions

**User Story:** As a developer, I want the Generator to produce before_date-mode predictions with deadlines that have already passed, so that the verification eval can test before_date mode scoring with known outcomes.

#### Acceptance Criteria

1. THE Generator SHALL produce at least 3 before_date-mode predictions with non-null `expected_verification_outcome`.
2. THE Generator SHALL set `verification_date` (the deadline) for before_date predictions to a date in the recent past (within the last 1-7 days), so the deadline has already passed and the outcome is final.
3. THE Generator SHALL include before_date predictions where the event DID occur before the deadline (expected verdict: `confirmed`) and predictions where the event did NOT occur before the deadline (expected verdict: `refuted`).
4. WHEN generating a before_date prediction with `ground_truth_source` equal to `deterministic`, THE Generator SHALL use events with publicly known dates that can be verified by calculation (e.g., "A full moon occurred before [recent past date]" computed via lunar cycle math).
5. WHEN generating a before_date prediction with `ground_truth_source` equal to `brave_search`, THE Generator SHALL look up whether the event occurred before the deadline using the Brave_API.
6. THE Generator SHALL include at least 1 before_date prediction expected to be `confirmed` and at least 1 expected to be `refuted`.

### Requirement 5: Recurring Mode Dynamic Predictions

**User Story:** As a developer, I want the Generator to produce recurring-mode predictions about current conditions that can be verified right now as a point-in-time snapshot, so that the verification eval can test recurring mode scoring.

#### Acceptance Criteria

1. THE Generator SHALL produce at least 3 recurring-mode predictions with non-null `expected_verification_outcome`.
2. THE Generator SHALL design recurring predictions as current-state checks where the answer is knowable at generation time (e.g., "The US national debt exceeds $35 trillion", "Bitcoin price is above $10,000").
3. WHEN generating a recurring prediction, THE Generator SHALL query the Brave_API for the current value and compute the expected verdict based on the queried value.
4. THE Generator SHALL set `recurring_interval` on each recurring prediction to indicate the expected check frequency.
5. THE Generator SHALL include the queried current value in the `ground_truth` object so the eval can audit the Generator's verdict computation.

### Requirement 6: Static Dataset Preservation and Timeless Case Identification

**User Story:** As a developer, I want the static golden dataset preserved for timeless cases, so that predictions with ground truth that never changes (calendar facts, subjective predictions) remain in a hand-curated file.

#### Acceptance Criteria

1. THE Static_Dataset (`eval/golden_dataset.json`) SHALL remain the source of truth for timeless predictions whose ground truth does not depend on when the eval runs.
2. THE Generator SHALL NOT modify the Static_Dataset file.
3. WHEN a prediction in the Static_Dataset has time-dependent ground truth (identified by a `time_sensitive: true` flag), THE Eval_Runner SHALL exclude that prediction from verification scoring unless a corresponding dynamic replacement exists in the Dynamic_Dataset.
4. THE Static_Dataset SHALL be updated to add a `time_sensitive: true` flag on predictions with ground truth that can go stale (e.g., base-010 full moon prediction).
5. THE Static_Dataset SHALL retain all existing predictions — no predictions SHALL be deleted.

### Requirement 7: Dataset Merging for Eval Runs

**User Story:** As a developer, I want the eval runner to merge static and dynamic datasets, so that a single eval run covers both timeless and time-anchored predictions.

#### Acceptance Criteria

1. THE Eval_Runner SHALL accept a `--dynamic-dataset` CLI argument specifying the path to the Dynamic_Dataset file.
2. WHEN both `--dataset` (static) and `--dynamic-dataset` are provided, THE Eval_Runner SHALL merge the two datasets, with dynamic cases taking precedence over static cases that share the same prediction intent (matched by a `replaces` field on dynamic cases).
3. WHEN only `--dataset` is provided (no `--dynamic-dataset`), THE Eval_Runner SHALL behave exactly as it does today — no breaking changes to existing eval workflows.
4. THE Eval_Runner SHALL include a `dataset_sources` field in the eval report metadata listing which dataset files were used.
5. THE merged dataset SHALL use ID prefixes to distinguish sources: static cases retain their existing IDs (e.g., `base-001`), dynamic cases use `dyn-` prefix (e.g., `dyn-imm-001`, `dyn-atd-001`, `dyn-bfd-001`, `dyn-rec-001`).

### Requirement 8: Dynamic Dataset Validation

**User Story:** As a developer, I want the dynamic dataset validated against the same schema rules as the static dataset, so that malformed generated predictions do not cause eval failures.

#### Acceptance Criteria

1. THE Generator SHALL validate the produced Dynamic_Dataset against schema 4.0 rules before writing the output file.
2. IF validation fails, THEN THE Generator SHALL exit with a non-zero exit code and print the validation errors.
3. THE existing `eval/validate_dataset.py` script SHALL accept the Dynamic_Dataset file path as an argument and validate it using the same rules applied to the Static_Dataset.
4. THE Generator SHALL validate that every prediction has a non-null `expected_verification_outcome`.
5. THE Generator SHALL validate that every prediction's `verification_mode` matches one of the four allowed values.

### Requirement 9: Ground Truth Auditability

**User Story:** As a developer, I want the Generator's ground truth computation to be auditable, so that when an eval scores a failure I can determine whether the agent or the Generator was wrong.

#### Acceptance Criteria

1. THE Generator SHALL record a `ground_truth_computation` object in each prediction's `ground_truth` section containing: the `source` (deterministic/brave_search/api_lookup), the `raw_data` (the input used for computation), the `computation_logic` (human-readable description of how the verdict was derived), and the `computed_at` timestamp.
2. WHEN `ground_truth_source` is `brave_search`, THE Generator SHALL record the Brave_API query string and the relevant snippet from the search results in `raw_data`.
3. WHEN `ground_truth_source` is `deterministic`, THE Generator SHALL record the computation inputs and formula in `raw_data` (e.g., `{"date": "2026-03-30", "day_of_week": "Monday", "formula": "calendar.weekday(2026, 3, 30)"}`).
4. THE eval report SHALL include the `ground_truth_computation` data for each case so that failures can be triaged without re-running the Generator.

### Requirement 10: Prediction Template Design Quality

**User Story:** As a developer, I want the Generator's prediction templates to produce high-quality eval cases that genuinely test the verification agent's capabilities, so that the eval measures real verification skill rather than trivial lookups.

#### Acceptance Criteria

1. THE Generator SHALL produce predictions across at least 3 difficulty levels: easy (deterministic facts), medium (single-source web lookups), and hard (multi-source reasoning or threshold comparisons).
2. THE Generator SHALL produce predictions across at least 4 domain categories (e.g., science, technology, finance, sports, politics, weather).
3. THE Generator SHALL produce at least 2 predictions per mode that require the Verification_Agent to use `brave_web_search` to verify (not just reasoning from training data).
4. THE Generator SHALL produce at least 2 predictions per mode where the expected verdict is `refuted`, to avoid a confirmation bias in the dataset.
5. THE Generator SHALL avoid predictions whose ground truth could change during a typical eval run (~30 minutes) — the Staleness_Window for every prediction SHALL exceed 2 hours.
6. THE Generator SHALL avoid predictions that require the Verification_Agent to access paywalled, login-gated, or rate-limited sources.
