# Implementation Plan: Golden Dataset V4 Reshape

## Overview

Two standalone Python scripts: `eval/reshape_v4.py` transforms the v3 golden dataset to v4-native format, `eval/validate_v4.py` verifies structural correctness. Tests in `eval/test_reshape_v4.py` use hypothesis for property-based testing and pytest for unit tests. All commands use `/home/wsluser/projects/calledit/venv/bin/python`.

## Tasks

- [x] 1. Implement the reshape script (`eval/reshape_v4.py`)
  - [x] 1.1 Create `eval/reshape_v4.py` with lookup tables and constants
    - Define `SCORE_RANGES` dict mapping all 45 base prediction ids to `[low, high]` score ranges per the design's Score Range Assignment Table (default ranges by v3 category, with overrides for base-013, base-006, base-042, base-043, base-044)
    - Define `VERIFICATION_OUTCOMES` dict mapping all 45 base prediction ids to `"confirmed"` / `"refuted"` / `"inconclusive"` / `None` per the design's Verification Outcome Assignment Logic
    - Define `SMOKE_TEST_IDS` set with the 12 selected ids from the design's Smoke Test Selection table
    - Define `CATEGORY_TO_TIER` dict: `{"auto_verifiable": "high", "automatable": "moderate", "human_only": "low"}`
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  - [x] 1.2 Implement `update_rubric(text: str) -> str`
    - Replace "Categorizer"/"categorizer" with v4 creation agent verifiability scoring references
    - Replace "VB" (standalone) with "VerificationPlan"
    - Replace "auto_verifiable", "automatable", "human_only" with verifiability score range descriptions (high ≥0.7, moderate 0.4–0.7, low <0.4)
    - _Requirements: 5.1, 5.2, 5.3_
  - [x] 1.3 Implement `transform_base_prediction(pred: dict) -> dict`
    - Remove `expected_per_agent_outputs` and `tool_manifest_config` if present (silent skip for idempotency)
    - Add `expected_verifiability_score_range` from `SCORE_RANGES` lookup
    - Add `expected_verification_outcome` from `VERIFICATION_OUTCOMES` lookup
    - Add `smoke_test` boolean from `SMOKE_TEST_IDS` membership
    - Call `update_rubric` on `evaluation_rubric`
    - Preserve all other fields unchanged
    - Log warning if prediction id not found in lookup tables
    - _Requirements: 1.1, 1.2, 2.1, 3.1, 4.1, 5.1, 5.2, 5.3, 7.1, 7.2, 7.3, 11.5_
  - [x] 1.4 Implement `transform_fuzzy_prediction(pred: dict) -> dict`
    - Extract category from `expected_post_clarification_outputs`, map via `CATEGORY_TO_TIER`, set as `expected_post_clarification_verifiability`
    - Remove `expected_post_clarification_outputs`
    - Handle idempotency: if `expected_post_clarification_verifiability` already exists and source field is gone, skip
    - Preserve all other fields unchanged
    - _Requirements: 8.1, 8.2_
  - [x] 1.5 Implement `reshape()` main function
    - Load `eval/golden_dataset.json`
    - Transform all base predictions via `transform_base_prediction`
    - Transform all fuzzy predictions via `transform_fuzzy_prediction`
    - Set `schema_version` and `dataset_version` to `"4.0"`
    - Update `metadata.expected_base_count`, `metadata.expected_fuzzy_count`, add `metadata.expected_smoke_test_count`
    - Write back to `eval/golden_dataset.json` with 2-space indentation and trailing newline
    - Print transformation summary (fields removed, fields added, rubrics updated, smoke test count)
    - _Requirements: 6.1, 6.2, 9.1, 9.2, 9.3, 11.1, 11.2, 11.3, 11.4_

- [x] 2. Implement the validation script (`eval/validate_v4.py`)
  - [x] 2.1 Create `eval/validate_v4.py` with `check_base_prediction(pred: dict) -> list[str]`
    - Check all required fields present: `id`, `prediction_text`, `difficulty`, `ground_truth`, `dimension_tags`, `evaluation_rubric`, `is_boundary_case`, `boundary_description`, `expected_verifiability_score_range`, `expected_verification_outcome`, `smoke_test`
    - Check `ground_truth` sub-fields present: `verifiability_reasoning`, `date_derivation`, `verification_sources`, `objectivity_assessment`, `verification_criteria`, `verification_steps`, `verification_timing`, `expected_verification_criteria`, `expected_verification_method`
    - Check no v3 dead fields (`expected_per_agent_outputs`, `tool_manifest_config`)
    - Validate `expected_verifiability_score_range` is 2-element list, both floats in [0.0, 1.0], first ≤ second
    - Validate `expected_verification_outcome` is one of `"confirmed"`, `"refuted"`, `"inconclusive"`, or `None`
    - Check `evaluation_rubric` contains no v3 terms: `"auto_verifiable"`, `"automatable"`, `"human_only"`
    - Return list of violation strings with prediction id and field name
    - _Requirements: 1.3, 1.4, 2.3, 2.4, 3.3, 3.4, 5.4, 7.4, 7.5, 10.2, 10.3_
  - [x] 2.2 Implement `check_fuzzy_prediction(pred: dict, valid_base_ids: set[str]) -> list[str]`
    - Check required fields: `id`, `fuzzy_text`, `base_prediction_id`, `fuzziness_level`, `simulated_clarifications`, `expected_clarification_topics`, `evaluation_rubric`, `expected_post_clarification_verifiability`
    - Check `base_prediction_id` references a valid base prediction id
    - Check no `expected_post_clarification_outputs` field present
    - Check `expected_post_clarification_verifiability` is one of `"high"`, `"moderate"`, `"low"`
    - _Requirements: 8.3, 8.4, 8.5, 10.2_
  - [x] 2.3 Implement `check_metadata(data: dict) -> list[str]` and `check_smoke_test_constraints(preds: list[dict]) -> list[str]`
    - `check_metadata`: verify `expected_base_count` == len(base_predictions), `expected_fuzzy_count` == len(fuzzy_predictions), `expected_smoke_test_count` == count of smoke_test=true
    - `check_smoke_test_constraints`: verify count 10–14, difficulty distribution 4 easy + 5 medium + 3 hard, all 12 domains covered, at least 1 boundary case, at least 1 immediate verification_readiness, at least 1 subjective, at least 1 objective
    - Verify `schema_version` == `"4.0"` and `dataset_version` == `"4.0"`
    - _Requirements: 4.7, 4.8, 4.9, 4.10, 6.3, 6.4, 9.4, 9.5, 9.6_
  - [x] 2.4 Implement `validate(path: str) -> list[str]` main function with CLI entry point
    - Load JSON (catch `JSONDecodeError`, exit non-zero)
    - Run all checks, accumulate violations
    - Print per-check pass/fail summary
    - Exit 0 if all pass, exit 1 if any fail
    - _Requirements: 10.1, 10.4, 10.5_

- [x] 3. Checkpoint — Reshape and validate scripts complete
  - Ensure both scripts run without errors. Run reshape then validate on the real dataset. Ask the user if questions arise.

- [ ] 4. Property-based tests (`eval/test_reshape_v4.py`)
  - [ ] 4.1 Set up test file with hypothesis imports and shared strategies
    - Create hypothesis strategies for generating random base prediction dicts (with v3 fields), random rubric strings containing v3 terms, random fuzzy prediction dicts with v3 category references
    - Import `transform_base_prediction`, `transform_fuzzy_prediction`, `update_rubric` from `eval.reshape_v4`
    - Import `check_base_prediction`, `check_fuzzy_prediction` from `eval.validate_v4`
    - _Requirements: (test infrastructure)_

  - [ ]* 4.2 Property 1: V3 field removal
    - **Property 1: V3 field removal**
    - For any base prediction dict containing `expected_per_agent_outputs` or `tool_manifest_config`, after `transform_base_prediction`, neither key should be present
    - **Validates: Requirements 1.1, 1.2**

  - [ ]* 4.3 Property 2: V4 field addition with valid structure
    - **Property 2: V4 field addition with valid structure**
    - After `transform_base_prediction`, result contains valid `expected_verifiability_score_range` (2-element list, floats in [0,1], first ≤ second), valid `expected_verification_outcome`, and `smoke_test` boolean
    - **Validates: Requirements 2.1, 3.1, 4.1**

  - [ ]* 4.4 Property 3: Preserved fields are unchanged
    - **Property 3: Preserved fields are unchanged**
    - After `transform_base_prediction`, fields `id`, `prediction_text`, `difficulty`, `dimension_tags`, `is_boundary_case`, `boundary_description`, and all `ground_truth` sub-fields are identical to input
    - **Validates: Requirements 7.1, 7.2, 7.3**

  - [ ]* 4.5 Property 4: Rubric text contains no v3 terms
    - **Property 4: Rubric text contains no v3 terms after transformation**
    - After `update_rubric`, output contains none of: `"auto_verifiable"`, `"automatable"`, `"human_only"`, `"Categorizer"`, `"categorizer"`, `" VB "`
    - **Validates: Requirements 5.1, 5.2, 5.3**

  - [ ]* 4.6 Property 5: Fuzzy prediction category-to-tier mapping
    - **Property 5: Fuzzy prediction category-to-tier mapping**
    - For any fuzzy prediction with `expected_post_clarification_outputs` containing a category, after `transform_fuzzy_prediction`, result has no `expected_post_clarification_outputs` and has correct `expected_post_clarification_verifiability` tier
    - **Validates: Requirements 8.2, 8.4, 8.5**

  - [ ]* 4.7 Property 6: Fuzzy prediction field preservation
    - **Property 6: Fuzzy prediction field preservation**
    - After `transform_fuzzy_prediction`, fields `id`, `fuzzy_text`, `base_prediction_id`, `fuzziness_level`, `simulated_clarifications`, `expected_clarification_topics`, `evaluation_rubric` are identical to input
    - **Validates: Requirements 8.1**

  - [ ]* 4.8 Property 8: Validator detects missing required fields
    - **Property 8: Validator detects missing required fields**
    - For any base prediction dict missing one or more required fields, `check_base_prediction` returns at least one violation mentioning the missing field name
    - **Validates: Requirements 2.3, 3.3, 7.4, 7.5, 10.2**

  - [ ]* 4.9 Property 9: Validator detects v3 dead fields
    - **Property 9: Validator detects v3 dead fields**
    - For any base prediction dict containing `expected_per_agent_outputs` or `tool_manifest_config`, `check_base_prediction` returns at least one violation mentioning that field
    - **Validates: Requirements 1.3, 1.4, 10.3**

  - [ ]* 4.10 Property 10: Validator accepts valid score ranges and rejects invalid ones
    - **Property 10: Validator accepts valid score ranges and rejects invalid ones**
    - Valid `[a, b]` with floats in [0,1] and a ≤ b accepted; invalid values (wrong length, out of range, a > b, non-numeric) rejected
    - **Validates: Requirements 2.4**

  - [ ]* 4.11 Property 12: Validator fuzzy prediction referential integrity
    - **Property 12: Validator fuzzy prediction referential integrity**
    - Fuzzy prediction with invalid `base_prediction_id` triggers violation; valid reference triggers no referential integrity violation
    - **Validates: Requirements 8.3**

  - [ ]* 4.12 Property 14: Lookup table validity
    - **Property 14: Lookup table validity**
    - All `SCORE_RANGES` entries are valid 2-element lists in [0,1] with first ≤ second; all `VERIFICATION_OUTCOMES` entries are valid values; both tables cover all 45 ids and have matching keys
    - **Validates: Requirements 2.2, 3.2**

- [ ] 5. Unit tests (`eval/test_reshape_v4.py`)
  - [ ]* 5.1 Write unit tests for smoke test constraints, versions, metadata, and idempotency
    - Test smoke test selection satisfies all constraints on real dataset (Req 4.2–4.6)
    - Test schema_version and dataset_version are "4.0" after reshape (Req 6.1, 6.2)
    - Test metadata counts match after reshape on real dataset (Property 7, Req 9.1–9.3)
    - Test reshape idempotency on real dataset — reshape twice, compare output (Property 13, Req 11.1, 11.2)
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.6, 6.1, 6.2, 9.1, 9.2, 9.3, 11.1, 11.2_

  - [ ]* 5.2 Write unit tests for validation script behavior
    - Test validator exits non-zero on invalid JSON file (Req 10.1)
    - Test validator prints summary with pass/fail per check (Req 10.4)
    - Test reshape script prints transformation summary with counts (Req 11.4)
    - Test reshape script logs warning for unexpected prediction structure (Req 11.5)
    - Test JSON output uses 2-space indentation (Req 11.3)
    - _Requirements: 10.1, 10.4, 11.3, 11.4, 11.5_

- [ ] 6. Checkpoint — Run all tests
  - Run `/home/wsluser/projects/calledit/venv/bin/python -m pytest eval/test_reshape_v4.py -v`
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Run reshape and validate to produce the final v4 dataset
  - [x] 7.1 Run the reshape script on the real dataset
    - Execute `/home/wsluser/projects/calledit/venv/bin/python eval/reshape_v4.py`
    - Verify transformation summary output looks correct
    - _Requirements: 11.1, 11.2, 11.4_
  - [x] 7.2 Run the validation script on the reshaped dataset
    - Execute `/home/wsluser/projects/calledit/venv/bin/python eval/validate_v4.py`
    - Verify all checks pass (exit code 0)
    - _Requirements: 10.4, 10.5_

- [x] 8. Final checkpoint — All tests pass, dataset is v4-native
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases against the real dataset
- No mocks policy (Decision 96) — tests use real data or hypothesis-generated inputs
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
