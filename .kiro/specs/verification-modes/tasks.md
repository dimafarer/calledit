# Implementation Plan: Verification Modes

## Overview

Extend the CalledIt prediction verification system to support four `verification_mode` types (`immediate`, `at_date`, `before_date`, `recurring`). Implementation follows the data flow: models → bundle → handler → prompts → verification agent → scanner → snapshots → golden dataset → evaluators → eval runner. The existing `immediate` path is unchanged — all changes are additive.

## Tasks

- [x] 1. Add verification_mode to Pydantic models and bundle builder
  - [x] 1.1 Add `verification_mode` field to `VerificationPlan` and `PlanReview` models in `calleditv4/src/models.py`
    - Import `Literal` and `Optional` from `typing`
    - Define `VERIFICATION_MODES = Literal["immediate", "at_date", "before_date", "recurring"]`
    - Add `verification_mode: VERIFICATION_MODES` with default `"immediate"` to `VerificationPlan`
    - Add `recurring_interval: Optional[str]` with default `None` to `VerificationPlan`
    - Add `verification_mode: VERIFICATION_MODES` with default `"immediate"` to `PlanReview`
    - _Requirements: 1.4, 1.5, 5.8_

  - [ ]* 1.2 Write property test for Pydantic verification_mode validation
    - **Property 1: Verification mode Pydantic validation**
    - Test in `calleditv4/tests/test_models.py`
    - For any string, constructing `VerificationPlan` or `PlanReview` with that string as `verification_mode` succeeds iff the string is one of the four valid values; invalid strings raise `ValidationError`
    - **Validates: Requirements 1.1, 1.4, 1.5**

  - [x] 1.3 Add `verification_mode`, `recurring_interval`, and `max_snapshots` parameters to `build_bundle()` in `calleditv4/src/bundle.py`
    - Add `verification_mode: str = "immediate"` parameter
    - Add `recurring_interval: Optional[str] = None` parameter
    - Add `max_snapshots: int = 30` parameter
    - Include all three in the bundle dict (only include `recurring_interval` and `max_snapshots` when `verification_mode == "recurring"`)
    - Also add `verification_mode` to `format_ddb_update()` so clarification rounds persist the resolved mode
    - _Requirements: 1.2, 1.3, 5.4, 5.6_

  - [ ]* 1.4 Write property test for bundle builder preserving verification_mode
    - **Property 2: Bundle builder preserves verification mode**
    - Test in `calleditv4/tests/test_bundle.py`
    - For any valid mode string and valid bundle inputs, `build_bundle()` produces a bundle where `bundle["verification_mode"]` equals the input mode; when no mode is provided, defaults to `"immediate"`
    - **Validates: Requirements 1.2, 1.3**

- [x] 2. Implement mode resolution and wire through creation handler
  - [x] 2.1 Add `resolve_verification_mode()` function in `calleditv4/src/main.py`
    - When planner and reviewer agree, return the agreed mode
    - When they disagree, return the reviewer's mode and log a warning with both values
    - _Requirements: 2a.2, 2a.3, 2a.4_

  - [ ]* 2.2 Write property test for mode resolution
    - **Property 3: Mode resolution — reviewer wins on disagreement**
    - Test in `calleditv4/tests/test_main.py`
    - For any two valid mode values, `resolve_verification_mode()` returns `reviewer_mode` when they disagree, and the agreed value when they agree
    - **Validates: Requirements 2a.2, 2a.3, 2a.4**

  - [x] 2.3 Wire mode resolution into the creation handler's 3-turn flow in `calleditv4/src/main.py`
    - After Turn 2 and Turn 3 complete, call `resolve_verification_mode(verification_plan.verification_mode, plan_review.verification_mode, prediction_id)`
    - Pass the resolved mode to `build_bundle()` (creation route)
    - Pass the resolved mode to `format_ddb_update()` (clarification route)
    - Include `verification_mode` in the `flow_complete` event data
    - _Requirements: 2a.2, 2a.3, 2a.4, 1.2_

- [x] 3. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Update prompts for mode classification
  - [x] 4.1 Add verification_planner v2 prompt in `infrastructure/prompt-management/template.yaml`
    - Add mode classification instructions with definitions and examples for all four modes to the `VerificationPlannerPrompt` variant text
    - Add `verification_mode` and `recurring_interval` to the expected JSON output schema in the prompt
    - Add a new `VerificationPlannerPromptVersionV2` resource (depends on v1)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 5.8_

  - [x] 4.2 Add plan_reviewer v3 prompt in `infrastructure/prompt-management/template.yaml`
    - Add instructions to independently assess `verification_mode` and flag disagreement in reasoning
    - Add `verification_mode` to the expected JSON output schema in the prompt
    - Add a new `PlanReviewerPromptVersionV3` resource (depends on v2)
    - _Requirements: 2a.1, 2a.5_

  - [x] 4.3 Add verification_executor v2 prompt in `infrastructure/prompt-management/template.yaml`
    - Add mode-specific verdict rules: `at_date` premature → `inconclusive`, `before_date` early confirm logic, `recurring` snapshot semantics
    - Add a new `VerificationExecutorPromptVersionV2` resource (depends on v1)
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 4.4 Update `DEFAULT_PROMPT_VERSIONS` in both prompt clients
    - In `calleditv4/src/prompt_client.py`: set `verification_planner` to `"2"`, `plan_reviewer` to `"3"`
    - In `calleditv4-verification/src/prompt_client.py`: set `verification_executor` to `"2"`
    - Note: user must deploy CloudFormation stack before these versions exist, then run `agentcore launch` to pick up changes
    - _Requirements: 2.7, 2a.5, 3.6_

- [x] 5. Update Verification Agent to include mode in context
  - [x] 5.1 Update `_build_user_message()` in `calleditv4-verification/src/main.py`
    - Add `VERIFICATION MODE: {verification_mode}` line to the user message between `VERIFICATION DATE` and `VERIFICATION PLAN`
    - Default to `"immediate"` via `.get("verification_mode", "immediate")`
    - _Requirements: 3.1_

  - [ ]* 5.2 Write property test for user message including mode
    - **Property 4: Verification agent user message includes mode**
    - Test in `calleditv4-verification/tests/test_main.py`
    - For any bundle containing a `verification_mode` value, `_build_user_message(bundle)` produces a string containing `"VERIFICATION MODE: {mode}"`
    - **Validates: Requirements 3.1**

- [x] 6. Implement Scanner mode-aware scheduling
  - [x] 6.1 Add `should_invoke()` function in `infrastructure/verification-scanner/scanner.py`
    - Define `RECURRING_INTERVAL_SECONDS` mapping (`every_scan`: 0, `daily`: 86400, `weekly`: 604800)
    - Add `_seconds_since(iso_a, iso_b)` helper for timestamp arithmetic
    - Implement mode-specific logic: `immediate` → always invoke, `at_date` → check `verification_date`, `before_date` → always invoke, `recurring` → check interval against last snapshot
    - Unknown modes default to immediate with a warning log
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.7, 5.5_

  - [x] 6.2 Add `handle_verification_result()` function in `infrastructure/verification-scanner/scanner.py`
    - For `recurring` mode: call `append_verification_snapshot()` (imported or inline), keep status `pending`
    - For `before_date` + `confirmed`: let default status transition happen (status → `verified`)
    - For `before_date` + `inconclusive` before deadline: leave as `pending`
    - Log `verification_mode` for each prediction processed
    - _Requirements: 4.5, 4.6, 4.7, 4.8_

  - [x] 6.3 Wire `should_invoke()` and `handle_verification_result()` into `lambda_handler()`
    - Replace the current "invoke everything" loop with mode-aware dispatch
    - Fetch full bundle item (not just GSI projection) to get `verification_mode`, `verification_snapshots`, `recurring_interval`
    - Call `should_invoke()` before invoking, skip with reason if False
    - Call `handle_verification_result()` after successful invocation
    - Add skip/invoke counts to the summary
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.7, 4.8_

  - [ ]* 6.4 Write property test for scanner scheduling correctness
    - **Property 5: Scanner scheduling correctness**
    - Test in `infrastructure/verification-scanner/tests/test_scanner.py`
    - For any prediction item with a valid `verification_mode` and any current timestamp, `should_invoke()` returns the correct (invoke, reason) tuple per mode rules
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.7, 5.5**

- [x] 7. Implement recurring snapshot storage
  - [x] 7.1 Add `append_verification_snapshot()` function in `calleditv4-verification/src/bundle_loader.py`
    - Accept `table`, `prediction_id`, `result`, `checked_at`, `max_snapshots` (default 30)
    - Build snapshot dict with `verdict`, `confidence`, `evidence`, `reasoning`, `checked_at`
    - Append to `verification_snapshots` list using DDB `list_append`
    - Prune oldest snapshots if list exceeds `max_snapshots`
    - Do NOT change status from `pending`
    - _Requirements: 5.1, 5.2, 5.3, 5.6, 5.7_

  - [ ]* 7.2 Write property test for snapshot append invariants
    - **Property 6: Recurring snapshot append invariants**
    - Test in `calleditv4-verification/tests/test_bundle_loader.py`
    - For any recurring prediction bundle and any result, appending a snapshot increases list length by 1 (before pruning), snapshot contains all required fields, status stays `pending`, and after pruning list length ≤ `max_snapshots`
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.6, 5.7**

- [x] 8. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Add golden dataset mode annotations and new test cases
  - [x] 9.1 Annotate existing golden dataset cases with `verification_mode` in `eval/golden_dataset.json`
    - Add `"verification_mode": "immediate"` to all existing `base_predictions` entries where `verification_readiness` is `"immediate"`
    - Add `expected_mode_counts` to the `metadata` section
    - _Requirements: 6.1, 6.2, 6.6_

  - [x] 9.2 Add 9 new golden dataset cases (3 per non-immediate mode) in `eval/golden_dataset.json`
    - 3 `at_date` cases (e.g., "S&P 500 will close higher today than yesterday", stock price at close, election result on election day)
    - 3 `before_date` cases (e.g., "Python 3.14 released before Dec 2026", "SpaceX lands on Mars before 2030", software release before deadline)
    - 3 `recurring` cases (e.g., "US national debt exceeds $35T", "Bitcoin above $100k", daily temperature check)
    - Each case needs `prediction_text`, `verification_mode`, `verification_readiness`, `expected_verification_outcome`, `ground_truth`, and appropriate metadata
    - Update `expected_base_count` and `expected_mode_counts` in metadata
    - _Requirements: 6.3, 6.4, 6.5, 6.6_

  - [ ]* 9.3 Write property test for golden dataset mode annotations
    - **Property 7: Golden dataset mode annotations**
    - Test in `eval/tests/test_golden_dataset.py`
    - For every entry in `base_predictions`, `verification_mode` exists and is one of the four valid values; for entries where `verification_readiness == "immediate"`, `verification_mode` must also be `"immediate"`
    - **Validates: Requirements 6.1, 6.2**

- [x] 10. Implement mode-aware evaluators
  - [x] 10.1 Create `eval/evaluators/verification_at_date_verdict_accuracy.py`
    - `evaluate(result, expected_verdict, verification_date, simulated_time)` function
    - Before `verification_date`: score `inconclusive` as 1.0, anything else as 0.0
    - At/after `verification_date`: exact match against expected verdict (1.0 match, 0.0 mismatch)
    - Follow the existing evaluator module pattern (return `{"score": float, "pass": bool, "reason": str}`)
    - _Requirements: 7.3, 7.4_

  - [ ]* 10.2 Write property test for at_date evaluator scoring
    - **Property 9: at_date evaluator scoring**
    - Test in `eval/tests/test_evaluators.py`
    - For any verdict and any time relationship to `verification_date`, the evaluator scores correctly per the before/after rules
    - **Validates: Requirements 7.3, 7.4**

  - [x] 10.3 Create `eval/evaluators/verification_before_date_verdict_appropriateness.py`
    - `evaluate(result, expected_verdict, verification_date, simulated_time)` function
    - Before `verification_date`: `confirmed` and `inconclusive` score 1.0, `refuted` scores 0.0
    - At/after `verification_date`: exact match against expected verdict
    - _Requirements: 7.5, 7.6_

  - [ ]* 10.4 Write property test for before_date evaluator scoring
    - **Property 10: before_date evaluator scoring**
    - Test in `eval/tests/test_evaluators.py`
    - For any verdict and any time relationship to `verification_date`, the evaluator scores correctly per the before/after rules
    - **Validates: Requirements 7.5, 7.6**

  - [x] 10.5 Create `eval/evaluators/verification_recurring_evidence_freshness.py`
    - `evaluate(result, prediction_text)` function (LLM-judge evaluator, Tier 2)
    - Verify that evidence timestamps or source dates are from the current check period, not stale
    - Follow the LLM-judge pattern from `verification_evidence_quality.py`
    - _Requirements: 7.7_

- [x] 11. Update eval runner with mode routing and per-mode aggregates
  - [x] 11.1 Update `build_evaluator_list()` in `eval/verification_eval.py` to accept `verification_mode`
    - Add `verification_mode: str = "immediate"` parameter
    - For `immediate`: return existing 7 evaluators (unchanged)
    - For `at_date`: replace `verdict_accuracy` with `at_date_verdict_accuracy`
    - For `before_date`: replace `verdict_accuracy` with `before_date_verdict_appropriateness`
    - For `recurring`: add `recurring_evidence_freshness`
    - Import the three new evaluator modules
    - _Requirements: 7.1, 7.2, 7.8, 8.3_

  - [ ]* 11.2 Write property test for evaluator routing by mode
    - **Property 8: Evaluator routing by mode**
    - Test in `eval/tests/test_verification_eval.py`
    - For any valid `verification_mode`, `build_evaluator_list(mode)` returns the correct evaluator set per mode
    - **Validates: Requirements 7.1, 7.2, 8.1, 8.3**

  - [x] 11.3 Update `run_eval()` and `load_golden_cases()` in `eval/verification_eval.py` for mode-aware routing
    - Read `verification_mode` from each golden dataset case (default to `"immediate"` if absent)
    - Call `build_evaluator_list()` per-case with the case's `verification_mode`
    - Include `verification_mode` in each per-case result dict
    - Pass `verification_date` and `simulated_time` to mode-specific evaluators that need them
    - _Requirements: 8.1, 8.2, 8.4_

  - [x] 11.4 Add per-mode aggregate breakdowns to `compute_aggregates()` in `eval/verification_eval.py`
    - Group results by `verification_mode`
    - Compute per-evaluator averages within each mode group
    - Add `by_mode` object to the `aggregate_scores` section of the report
    - _Requirements: 8.5_

  - [ ]* 11.5 Write property test for eval report mode metadata
    - **Property 11: Eval report includes mode metadata**
    - Test in `eval/tests/test_verification_eval.py`
    - For any eval report, each per-case result includes `verification_mode`, and `aggregate_scores` includes `by_mode` with breakdowns for each mode present
    - **Validates: Requirements 8.4, 8.5**

- [x] 12. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Requirement 9 (Dashboard Mode Breakdown) requires no code changes — the dashboard is data-driven and auto-renders new fields from the eval report JSON (Req 9.2)
- After deploying prompts (task 4), the user must run `aws cloudformation deploy` and then `agentcore launch` manually (requires TTY)
- All Python commands use the venv at `/home/wsluser/projects/calledit/venv/bin/python`
- Property tests use Hypothesis (already installed) with `@settings(max_examples=100)`
