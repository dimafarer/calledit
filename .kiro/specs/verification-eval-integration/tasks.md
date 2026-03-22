# Implementation Plan: Verification Eval Integration (Spec B3)

## Overview

Extend the existing eval framework with a `--verify` mode and four new evaluators measuring plan-execution alignment. Implementation follows the dependency chain: golden dataset → evaluators → eval runner → report aggregation → DDB storage → dashboard. Property-based tests validate each component as it's built.

## Tasks

- [x] 1. Extend golden dataset with verification_readiness field
  - [x] 1.1 Add `verification_readiness` field to `BasePrediction` dataclass in `golden_dataset.py`
    - Add `verification_readiness: str = "future"` field to `BasePrediction`
    - Add `VALID_VERIFICATION_READINESS = {"immediate", "future"}` constant
    - Add validation in `_validate_base_prediction()` — parse with default `"future"`, reject invalid values
    - Add serialization in `_serialize_base()` — include `verification_readiness` in output dict
    - _Requirements: 3.1, 3.3, 3.4_

  - [x] 1.2 Update golden dataset JSON with verification_readiness on existing test cases
    - Add `"verification_readiness": "immediate"` to at least one base prediction (established fact, verifiable now)
    - Add `"verification_readiness": "future"` to at least one base prediction (future-dated prediction)
    - Leave some test cases without the field to test the default behavior
    - _Requirements: 3.2, 3.3_

  - [ ]* 1.3 Write property test for verification_readiness parsing (Property 7)
    - **Property 7: Verification readiness parsing and default**
    - **Validates: Requirements 3.1, 3.3**
    - Test file: `backend/calledit-backend/tests/test_verification_eval.py`
    - Use `hypothesis` `@given` with strategies generating base prediction dicts with/without `verification_readiness`
    - Assert parsed value is always one of `{"immediate", "future"}`
    - Assert absent field defaults to `"future"`

- [x] 2. Implement deterministic verification evaluators
  - [x] 2.1 Implement ToolAlignment evaluator in `evaluators/tool_alignment.py`
    - Follow `category_match.py` function signature pattern: returns `{"score": float, "evaluator": str, ...}`
    - Extract tool names from plan's `steps` field via keyword matching against known MCP tool names
    - Extract used tools from outcome's `tools_used` list
    - Score = Jaccard similarity: `|intersection| / |union|`, or `1.0` when both sets empty
    - Return `planned_tools`, `used_tools`, `overlap`, `plan_only`, `execution_only` in result dict
    - When score < 1.0, call `classify_delta()` for `delta_classification`; set `None` when score == 1.0
    - _Requirements: 2.1, 2.5, 2.6_

  - [x] 2.2 Implement SourceAccuracy evaluator in `evaluators/source_accuracy.py`
    - Follow `category_match.py` function signature pattern
    - Extract planned sources from plan's `source` field
    - Extract evidence sources from outcome's `evidence[].source` list
    - Score = proportion of planned sources that fuzzy-match (domain-level) at least one evidence source; `1.0` when planned sources empty
    - Return `planned_sources`, `evidence_sources`, `matched`, `unmatched_plan`, `unmatched_evidence`
    - When score < 1.0, call `classify_delta()` for `delta_classification`; set `None` when score == 1.0
    - _Requirements: 2.3, 2.5, 2.6_

  - [x] 2.3 Implement `classify_delta()` helper function
    - Place in a shared module or inline in each evaluator (design specifies lightweight LLM call)
    - Use direct Bedrock `converse` call (not Strands Evals SDK) for classification
    - Classify delta as one of: `plan_error`, `new_information`, `tool_drift`
    - On LLM failure, return `None` and log warning (never raise)
    - _Requirements: 2.5_

  - [ ]* 2.4 Write property test for ToolAlignment Jaccard calculation (Property 3)
    - **Property 3: ToolAlignment score equals Jaccard similarity**
    - **Validates: Requirements 2.1**
    - Use `hypothesis` `@given` with strategies generating random tool name sets
    - Assert score == `|intersection| / |union|` when union non-empty, `1.0` when both empty

  - [ ]* 2.5 Write property test for SourceAccuracy coverage calculation (Property 4)
    - **Property 4: SourceAccuracy score equals planned source coverage**
    - **Validates: Requirements 2.3**
    - Use `hypothesis` `@given` with strategies generating random source lists
    - Assert score == proportion of planned sources matched; `1.0` when planned empty

  - [ ]* 2.6 Write property test for delta classification invariant (Property 6)
    - **Property 6: Delta classification invariant**
    - **Validates: Requirements 2.5**
    - Use `hypothesis` `@given` generating evaluator results with varying scores
    - Assert `delta_classification` is present and valid when score < 1.0, `None` when score == 1.0

- [x] 3. Implement LLM judge verification evaluators
  - [x] 3.1 Implement CriteriaQuality evaluator in `evaluators/criteria_quality.py`
    - Follow `intent_preservation.py` pattern: Strands Evals SDK `OutputEvaluator`
    - Rubric evaluates: each criterion is specific/checkable, evidence maps to criteria, no criteria ignored
    - Return `{"score": float, "evaluator": "CriteriaQuality", "judge_reasoning": str, "judge_model": str}`
    - On error, return score 0.0 with error message in `judge_reasoning` (never raise)
    - _Requirements: 2.2, 2.6_

  - [x] 3.2 Implement StepFidelity evaluator in `evaluators/step_fidelity.py`
    - Follow `intent_preservation.py` pattern: Strands Evals SDK `OutputEvaluator`
    - Rubric evaluates: each step attempted, steps in order, no critical steps skipped
    - Include `delta_classification` in judge rubric output when score < 1.0
    - Return `{"score": float, "evaluator": "StepFidelity", "judge_reasoning": str, "judge_model": str, "delta_classification": str|None}`
    - On error, return score 0.0 with error message (never raise)
    - _Requirements: 2.4, 2.5, 2.6_

  - [ ]* 3.3 Write property test for LLM judge return structure (Property 5)
    - **Property 5: LLM judge evaluator return structure**
    - **Validates: Requirements 2.2, 2.4**
    - Use `hypothesis` `@given` generating various plan/outcome dicts (including error-inducing inputs)
    - Assert return dict always contains `score` (float in [0.0, 1.0]), `evaluator`, `judge_reasoning` (non-empty str), `judge_model` (non-empty str)

- [x] 4. Checkpoint — Ensure all evaluator tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Extend eval runner with --verify mode
  - [x] 5.1 Add `--verify` CLI flag and `use_verify` parameter to `run_on_demand_evaluation()`
    - Add `parser.add_argument("--verify", ...)` in `__main__` argparse block
    - Add `use_verify: bool = False` parameter to `run_on_demand_evaluation()`
    - Pass through from CLI args to function call
    - When `--verify` is not set, skip all verification execution and evaluators (no cost impact)
    - _Requirements: 1.1, 1.4, 1.5_

  - [x] 5.2 Implement `_evaluate_verification()` dispatch function in `eval_runner.py`
    - New function called after `_evaluate_base_prediction()` when `--verify` is active
    - Extract `verification_plan` from `pipeline_output["verification_method"]`
    - Call `run_verification()` from Spec B1 for `immediate` test cases
    - Apply ToolAlignment and SourceAccuracy (always); CriteriaQuality and StepFidelity (when `--judge`)
    - For `future`/unset cases: skip verification, add all 4 evaluators to `_skipped_evaluators` with reason `"future_dated"`
    - Store `verification_plan` and `verification_outcome` in test result dict
    - Handle verification execution failures: set evaluator scores to 0.0 with `"verification_failed"` note
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.6, 2.7_

  - [x] 5.3 Wire `_evaluate_verification()` into the main evaluation loop
    - In the `isinstance(tc, BasePrediction)` branch, after existing evaluators, call `_evaluate_verification()` when `use_verify=True`
    - Merge returned verification scores into the test result's `evaluator_scores` dict
    - Compose with existing filters (`--name`, `--category`, `--layer`, `--difficulty`)
    - _Requirements: 1.1, 1.5_

  - [ ]* 5.4 Write property test for verify-mode structural completeness (Property 1)
    - **Property 1: Verify-mode test result structural completeness**
    - **Validates: Requirements 1.1, 1.2, 2.6**
    - Generate test result dicts from `_evaluate_verification()` with `immediate` readiness
    - Assert presence of `verification_plan`, `verification_outcome`, and evaluator score keys

  - [ ]* 5.5 Write property test for future-dated skip behavior (Property 2)
    - **Property 2: Future-dated cases are skipped with reason**
    - **Validates: Requirements 1.3**
    - Generate test result dicts from `_evaluate_verification()` with `future`/unset readiness
    - Assert `_skipped_evaluators` contains all 4 verification evaluators with `"future_dated"` reason
    - Assert no `verification_outcome` key present

- [ ] 6. Extend report aggregation with verification alignment data
  - [x] 6.1 Extend `_aggregate_report()` in `eval_runner.py` with `verification_alignment_aggregates`
    - Add `verification_alignment_aggregates` section: mean/min/max for each of the 4 evaluator scores
    - Add `delta_classification_breakdown` counting `plan_error`, `new_information`, `tool_drift` across all results
    - Add `verification_count` and `skipped_count`
    - Set to `None` when `--verify` was not used (backward compat)
    - _Requirements: 4.1_

  - [ ]* 6.2 Write property test for verification alignment aggregation (Property 8)
    - **Property 8: Verification alignment aggregation correctness**
    - **Validates: Requirements 4.1**
    - Use `hypothesis` `@given` generating random lists of test results with verification scores
    - Assert mean/min/max are mathematically correct
    - Assert delta_classification_breakdown counts sum to total non-None classifications

- [x] 7. Extend DDB storage with verification outcome record type
  - [x] 7.1 Add `write_verification_outcome()` method to `EvalReasoningStore`
    - New method in `eval_reasoning_store.py` following existing fire-and-forget pattern
    - Record key: `verification_outcome#{test_case_id}`
    - Store `verification_plan`, `verification_outcome`, and `evaluator_scores`
    - All float values sanitized to strings via existing `_sanitize_for_ddb()`
    - _Requirements: 4.2_

  - [x] 7.2 Wire `write_verification_outcome()` into eval runner loop
    - After verification evaluators run, call `reasoning_store.write_verification_outcome()` if store available
    - _Requirements: 4.2_

  - [ ]* 7.3 Write property test for DDB verification record key format (Property 9)
    - **Property 9: DDB verification record key format**
    - **Validates: Requirements 4.2**
    - Use `hypothesis` `@given` generating random test case IDs
    - Assert record key matches `verification_outcome#{test_case_id}` pattern
    - Assert item contains required keys with floats sanitized to strings

- [x] 8. Checkpoint — Ensure all eval runner and storage tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Add Verification Alignment dashboard page and routing
  - [x] 9.1 Create `eval/dashboard/pages/verification_alignment.py`
    - Follow existing `render(run_detail, loader)` pattern
    - Four-dimension bar chart showing mean scores for each verification evaluator
    - Delta classification breakdown chart (plan_error vs new_information vs tool_drift)
    - Per-test-case table with expandable plan vs outcome comparison
    - Skipped test cases section showing future-dated cases
    - _Requirements: 4.3_

  - [x] 9.2 Update sidebar and app routing for Verification Alignment page
    - Add `"Verification Alignment"` to `st.radio` page list in `sidebar.py`
    - Import `verification_alignment` in `app.py`
    - Add `elif page == "Verification Alignment"` dispatch in `app.py` routing
    - _Requirements: 4.4_

- [x] 10. Confirm EVALUATOR_WEIGHTS exclusion
  - [x] 10.1 Assert the four new evaluator names are NOT in `EVALUATOR_WEIGHTS`
    - Verify `ToolAlignment`, `CriteriaQuality`, `SourceAccuracy`, `StepFidelity` are absent from `EVALUATOR_WEIGHTS` dict in `eval_runner.py`
    - Per Decision 62: scores reported but don't affect VB-centric composite until empirical calibration
    - _Requirements: 2.7_

- [x] 11. Integration test — end-to-end --verify run
  - [ ]* 11.1 Write integration test for single-case --verify execution
    - Test file: `backend/calledit-backend/tests/test_verification_eval.py`
    - Run `eval_runner.py --verify --judge --name <immediate_test_case> --dataset ../../../../eval/golden_dataset.json`
    - Assert test result contains `verification_plan`, `verification_outcome`, and all 4 evaluator scores
    - Assert report contains `verification_alignment_aggregates`
    - Uses real services (Decision 78: NO MOCKS), single case via `--name` filter for fast iteration
    - _Requirements: 1.1, 1.2, 1.5, 2.6, 4.1_

- [x] 12. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Checkpoints ensure incremental validation
- All tests use `/home/wsluser/projects/calledit/venv/bin/python` — no system Python
- Decision 78: NO MOCKS — all tests hit real services
- Decision 62: New evaluators NOT added to EVALUATOR_WEIGHTS until empirical calibration
- Decision 81: Eval runner calls `run_verification()` directly, bypassing production triggers
- Decision 83: 120s timeout for MCP cold start on verification execution
