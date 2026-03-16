# Implementation Plan: Verification-Centric Evaluators

## Overview

Add verification-quality measurement to CalledIt's eval framework: extend the golden dataset to v3 with expected verification fields, build two new Strands Evals SDK-based evaluators (IntentPreservation, CriteriaMethodAlignment), recalibrate the VB judge rubric, wire everything through the eval runner, and update the dashboard to visualize the new scores.

## Tasks

- [x] 1. Golden Dataset V3 Schema Extension
  - [x] 1.1 Add v3 fields to `GroundTruthMetadata` dataclass and validation in `golden_dataset.py`
    - Add `expected_verification_criteria: List[str]` and `expected_verification_method: str` to `GroundTruthMetadata`
    - Update `_validate_ground_truth()` to require both fields on base predictions: `expected_verification_criteria` must be a non-empty list of strings, `expected_verification_method` must be a non-empty string
    - Raise `ValueError` with prediction ID and field name when validation fails
    - Update `SUPPORTED_SCHEMA_VERSION` to `"3.0"`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 1.2 Update serialization and dataset_to_dict in `golden_dataset.py`
    - Update `_serialize_base()` to include `expected_verification_criteria` and `expected_verification_method` in the serialized `ground_truth` dict
    - _Requirements: 1.7_

  - [x] 1.3 Update `eval/validate_dataset.py` to validate v3 fields
    - Add validation checks for `expected_verification_criteria` and `expected_verification_method` in the validation script
    - Report errors for any test case missing or having invalid v3 fields
    - _Requirements: 1.8_

  - [ ]* 1.4 Write property test: Ground truth v3 field validation round-trip
    - **Property 1: Ground truth v3 field validation round-trip**
    - Generate random valid ground_truth dicts with v3 fields → assert `_validate_ground_truth()` succeeds and fields are preserved
    - Generate invalid variants (missing, empty, wrong type) → assert `ValueError` raised with prediction ID
    - Test file: `backend/calledit-backend/tests/strands_make_call/test_verification_evaluators.py`
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5**

  - [ ]* 1.5 Write property test: Ground truth serialization round-trip
    - **Property 2: Ground truth serialization round-trip**
    - Generate random valid `BasePrediction` instances → serialize via `_serialize_base()` → validate via `_validate_ground_truth()` → assert v3 fields match
    - Test file: `backend/calledit-backend/tests/strands_make_call/test_verification_evaluators.py`
    - **Validates: Requirements 1.7**

- [x] 2. Golden Dataset V3 Content Population
  - [x] 2.1 Populate `expected_verification_criteria` and `expected_verification_method` for all 45 base predictions in `eval/golden_dataset.json`
    - Update `schema_version` and `dataset_version` to `"3.0"`
    - For each base prediction, add `expected_verification_criteria` (list of checkable true/false conditions capturing the factual claim without framing language) and `expected_verification_method` (concrete verification approach referencing specific data sources, tools, or observation methods)
    - Predictions with framing language: criteria must capture the underlying factual claim
    - Predictions referencing specific data sources: method must reference that source or equivalent
    - Predictions requiring human observation: method must describe the manual approach
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3. Checkpoint — Validate dataset loads cleanly
  - Ensure all tests pass, ask the user if questions arise.
  - Run `_validate_ground_truth()` on the updated dataset to confirm all 45 base predictions pass v3 validation

- [x] 4. Add Strands Evals SDK dependency
  - [x] 4.1 Add `strands-agents-evals` to root `requirements.txt`
    - Add `strands-agents-evals` as a development dependency in the root `requirements.txt`
    - Install via `/home/wsluser/projects/calledit/venv/bin/pip install -r requirements.txt`
    - _Requirements: 5.1_

- [x] 5. Implement IntentPreservation Evaluator
  - [x] 5.1 Create `evaluators/intent_preservation.py`
    - Implement `evaluate_intent_preservation(prediction_text, vb_criteria, expected_criteria, judge_model)` function
    - Instantiate Strands Evals SDK `OutputEvaluator` with rubric string, model ID, and `include_inputs=True`
    - Rubric: score semantic equivalence between VB criteria and expected criteria, penalize framing language retention
    - Map `EvaluationOutput.score` → `score`, `EvaluationOutput.reason` → `judge_reasoning`
    - Return `{"score": 0.0-1.0, "evaluator": "IntentPreservation", "judge_reasoning": str, "judge_model": str}`
    - On SDK failure: return `score=0.0` with error in `judge_reasoning`, never propagate exception
    - Use `DEFAULT_JUDGE_MODEL` (Opus 4.6) different from agent model (Sonnet 4)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 5.2, 5.4_

  - [ ]* 5.2 Write property test: Evaluator output structure invariant (IntentPreservation)
    - **Property 3: Evaluator output structure invariant**
    - Mock `OutputEvaluator` to return random `EvaluationOutput` values → assert return dict has keys `score` (float 0.0-1.0), `evaluator` ("IntentPreservation"), `judge_reasoning` (non-empty str), `judge_model` (non-empty str)
    - Test file: `backend/calledit-backend/tests/strands_make_call/test_verification_evaluators.py`
    - **Validates: Requirements 3.3, 3.6**

  - [ ]* 5.3 Write property test: Evaluator graceful degradation (IntentPreservation)
    - **Property 4: Evaluator graceful degradation on SDK failure**
    - Mock `OutputEvaluator` to raise various exception types → assert score is 0.0 and exception message in `judge_reasoning`
    - Test file: `backend/calledit-backend/tests/strands_make_call/test_verification_evaluators.py`
    - **Validates: Requirements 3.6**

- [x] 6. Implement CriteriaMethodAlignment Evaluator
  - [x] 6.1 Create `evaluators/criteria_method_alignment.py`
    - Implement `evaluate_criteria_method_alignment(vb_criteria, vb_method, expected_method, judge_model)` function
    - Instantiate Strands Evals SDK `OutputEvaluator` with rubric string, model ID, and `include_inputs=True`
    - Rubric: score whether method provides realistic, actionable plan to verify criteria; penalize "ask the user" as primary approach when public sources exist
    - Map `EvaluationOutput.score` → `score`, `EvaluationOutput.reason` → `judge_reasoning`
    - Return `{"score": 0.0-1.0, "evaluator": "CriteriaMethodAlignment", "judge_reasoning": str, "judge_model": str}`
    - On SDK failure: return `score=0.0` with error in `judge_reasoning`, never propagate exception
    - Use `DEFAULT_JUDGE_MODEL` (Opus 4.6) different from agent model (Sonnet 4)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.3, 5.4_

  - [ ]* 6.2 Write property test: Evaluator output structure invariant (CriteriaMethodAlignment)
    - **Property 3: Evaluator output structure invariant**
    - Mock `OutputEvaluator` to return random `EvaluationOutput` values → assert return dict has keys `score` (float 0.0-1.0), `evaluator` ("CriteriaMethodAlignment"), `judge_reasoning` (non-empty str), `judge_model` (non-empty str)
    - Test file: `backend/calledit-backend/tests/strands_make_call/test_verification_evaluators.py`
    - **Validates: Requirements 4.3, 4.6**

  - [ ]* 6.3 Write property test: Evaluator graceful degradation (CriteriaMethodAlignment)
    - **Property 4: Evaluator graceful degradation on SDK failure**
    - Mock `OutputEvaluator` to raise various exception types → assert score is 0.0 and exception message in `judge_reasoning`
    - Test file: `backend/calledit-backend/tests/strands_make_call/test_verification_evaluators.py`
    - **Validates: Requirements 4.6**

- [x] 7. Recalibrate ReasoningQuality VB Rubric
  - [x] 7.1 Update `verification_builder` rubric in `evaluators/reasoning_quality.py`
    - Replace the current `verification_builder` entry in `JUDGE_PROMPTS` with a rubric focused on whether the verification plan would succeed
    - New scoring anchors: 1.0 = specific data sources and timing; 0.7 = correct approach but vague sources; 0.4 = generic plan; 0.0 = plan would fail
    - Leave `categorizer` and `review` rubrics unchanged
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 5.5_

- [x] 8. Checkpoint — Evaluators ready
  - Ensure all tests pass, ask the user if questions arise.
  - Verify both new evaluator modules import cleanly and existing evaluators still work

- [-] 9. Eval Runner Integration
  - [x] 9.1 Update `_evaluate_base_prediction()` in `eval_runner.py` to invoke new evaluators
    - When `use_judge=True`, invoke `evaluate_intent_preservation()` with `prediction_text`, VB criteria from result, and `ground_truth.expected_verification_criteria`
    - When `use_judge=True`, invoke `evaluate_criteria_method_alignment()` with VB criteria from result, VB method from result, and `ground_truth.expected_verification_method`
    - Store results in `scores["IntentPreservation"]` and `scores["CriteriaMethodAlignment"]`
    - Write judge reasoning to DDB reasoning store for both evaluators (same pattern as existing ReasoningQuality writes)
    - _Requirements: 7.1, 7.2, 7.3, 7.5_

  - [x] 9.2 Update `_aggregate_report()` in `eval_runner.py` to compute verification quality averages
    - Compute average `IntentPreservation` and `CriteriaMethodAlignment` scores across all test cases
    - Include in report under `verification_quality_aggregates` with keys `intent_preservation_avg` and `criteria_method_alignment_avg`
    - _Requirements: 7.4, 7.6_

  - [x] 9.3 Update `print_report()` in `eval_runner.py` to display new scores
    - Display IntentPreservation and CriteriaMethodAlignment average scores in console output
    - _Requirements: 7.7_

  - [ ]* 9.4 Write property test: Eval runner includes verification evaluator scores
    - **Property 5: Eval runner includes verification evaluator scores when judge enabled**
    - Mock evaluator functions and pipeline → run `_evaluate_base_prediction()` with `use_judge=True` → assert both `IntentPreservation` and `CriteriaMethodAlignment` keys present in result
    - Test file: `backend/calledit-backend/tests/strands_make_call/test_verification_evaluators.py`
    - **Validates: Requirements 7.1, 7.2**

  - [ ]* 9.5 Write property test: Aggregate report computes verification quality averages
    - **Property 6: Aggregate report computes verification quality averages**
    - Generate random test result lists with IntentPreservation/CriteriaMethodAlignment scores → assert `verification_quality_aggregates` averages equal arithmetic mean
    - Test file: `backend/calledit-backend/tests/strands_make_call/test_verification_evaluators.py`
    - **Validates: Requirements 7.4, 7.6**

- [-] 10. Dashboard Updates
  - [x] 10.1 Update heatmap `_is_judge_evaluator()` in `eval/dashboard/pages/heatmap.py`
    - Update `_is_judge_evaluator()` to recognize `IntentPreservation` and `CriteriaMethodAlignment` as judge evaluators (right side of deterministic/judge separator)
    - The heatmap already dynamically discovers evaluator columns from `evaluator_scores` keys, so no matrix changes needed
    - _Requirements: 8.2_

  - [x] 10.2 Update trends page in `eval/dashboard/pages/trends.py`
    - Add IntentPreservation and CriteriaMethodAlignment average score trend lines sourced from `verification_quality_aggregates` in run summaries
    - Handle runs that predate the new evaluators (skip missing metrics gracefully)
    - _Requirements: 8.1_

  - [x] 10.3 Update reasoning explorer in `eval/dashboard/pages/reasoning_explorer.py`
    - Display IntentPreservation and CriteriaMethodAlignment judge reasoning when drilling into a test case
    - Source from DDB `judge_reasoning#<test_case_id>#IntentPreservation` and `judge_reasoning#<test_case_id>#CriteriaMethodAlignment` records
    - Show "No reasoning available" when records don't exist for older runs
    - _Requirements: 8.3_

  - [x] 10.4 Update data loader in `eval/dashboard/data_loader.py` for backward compatibility
    - Ensure `_normalize_test_result()` and `_normalize_run_summary()` handle runs with and without new evaluator scores without raising exceptions
    - Missing scores render as "N/A" in dashboard, not 0 or error
    - _Requirements: 8.4, 8.5_

  - [ ]* 10.5 Write property test: Heatmap discovers new evaluator columns
    - **Property 7: Heatmap discovers new evaluator columns**
    - Generate test case dicts with various `evaluator_scores` keys including IntentPreservation/CriteriaMethodAlignment → assert `_build_matrix()` includes them as columns on the judge side
    - Test file: `backend/calledit-backend/tests/strands_make_call/test_verification_evaluators.py`
    - **Validates: Requirements 8.2**

  - [ ]* 10.6 Write property test: Data loader handles missing evaluator scores
    - **Property 8: Data loader handles missing evaluator scores gracefully**
    - Generate run data with and without new evaluator keys → assert normalization never raises and preserves present scores without injecting zeros
    - Test file: `backend/calledit-backend/tests/strands_make_call/test_verification_evaluators.py`
    - **Validates: Requirements 8.5**

- [x] 11. Final checkpoint — Full integration
  - Ensure all tests pass, ask the user if questions arise.
  - Verify existing evaluators (`CategoryMatch`, `JSONValidity`, `ClarificationQuality`, `Convergence`, `ReasoningQuality` for categorizer/review) remain unchanged and functional

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- All Python commands must use the venv at `/home/wsluser/projects/calledit/venv`
- Existing deterministic evaluators and categorizer/review rubrics must remain untouched (Requirements 5.5, 5.6, 6.3, 6.4)
