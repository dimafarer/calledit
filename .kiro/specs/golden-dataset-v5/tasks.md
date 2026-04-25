# Implementation Plan: Golden Dataset v5.0 Cleanup

## Overview

Incremental cleanup of the CalledIt golden evaluation dataset from v4.0 to v5.0. Each task modifies data files (`eval/golden_dataset.json`, `eval/generate_dynamic_dataset.py`) and test assertions (`eval/tests/test_case_loader.py`), building on the previous step. Property-based tests validate structural invariants from the design document.

## Tasks

- [x] 1. Remove duplicate base predictions and bump version
  - [x] 1.1 Remove `base-046` and `base-052` from `eval/golden_dataset.json`
    - Delete the entire prediction object for `base-046` (duplicate of `base-004`, "The S&P 500 will close higher today than yesterday")
    - Delete the entire prediction object for `base-052` (duplicate of `base-009`, "The US national debt exceeds $35 trillion")
    - Verify `base-004` and `base-009` remain unchanged
    - Update `schema_version` from `"4.0"` to `"5.0"`
    - Update `dataset_version` from `"4.0"` to `"5.0"`
    - Update `metadata.expected_base_count` from 55 to 53
    - Update `metadata.expected_smoke_test_count` from 12 to 12 (neither removed case was smoke)
    - Update `metadata.expected_mode_counts.at_date` from 31 to 30 (base-046 was at_date)
    - Update `metadata.expected_mode_counts.recurring` from 3 to 2 (base-052 was recurring)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 6.1, 6.2, 7.1, 7.2, 7.3_

  - [x] 1.2 Shorten far-future predictions `base-014` and `base-050`
    - Update `base-014` prediction text from "Bitcoin will exceed $150,000 USD by December 31, 2026" to "Bitcoin will be trading above $90,000 USD next Friday"
    - Update `base-014` `ground_truth`, `evaluation_rubric`, and `dimension_tags.time_horizon` to `"days"`
    - Update `base-050` prediction text from "SpaceX will land a spacecraft on Mars before 2030" to "SpaceX will launch a Starship test flight before May 2026"
    - Update `base-050` `ground_truth`, `evaluation_rubric`, and `dimension_tags.time_horizon` to `"weeks-to-months"`
    - Both keep `verification_mode: "before_date"` and `expected_verification_outcome: null`
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 2. Add recently-happened event predictions
  - [x] 2.1 Add `base-056` through `base-060` to `eval/golden_dataset.json`
    - Add 5 new predictions after the last existing entry, following the schema from the design document
    - `base-056`: Atlanta Hawks defeated Knicks 109-108 in Game 3 (sports, confirmed, smoke_test: true)
    - `base-057`: S&P 500 closed above 7,100 on April 23, 2026 (finance, confirmed)
    - `base-058`: Zohran Mamdani sworn in as NYC Mayor Jan 1, 2026 (politics, confirmed)
    - `base-059`: NASA Artemis II launched April 1, 2026 (technology, confirmed)
    - `base-060`: Carolina Hurricanes defeated Senators 2-1 in Game 3 (sports, confirmed)
    - All new predictions: `verification_mode: "immediate"`, non-null `expected_verification_outcome`, complete `ground_truth` objects
    - Update `metadata.expected_base_count` from 53 to 58
    - Update `metadata.expected_smoke_test_count` from 12 to 13 (base-056 is smoke)
    - Update `metadata.expected_mode_counts.immediate` from 10 to 15
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 7.1, 7.2, 7.3, 9.2, 9.3_

  - [ ]* 2.2 Write property test for new prediction structural validity
    - **Property 1: New prediction structural validity**
    - Load `eval/golden_dataset.json`, filter predictions with id >= `base-056`
    - Assert each has non-null `expected_verification_outcome` ("confirmed" or "refuted")
    - Assert each has `verification_mode` == `"immediate"`
    - Assert each has non-empty `ground_truth.verification_sources`, `verification_criteria`, `verification_steps`, `expected_verification_method`
    - **Validates: Requirements 4.2, 4.3, 4.4**

  - [ ]* 2.3 Write property test for metadata-data consistency
    - **Property 2: Metadata-data consistency**
    - Load `eval/golden_dataset.json`
    - Assert `metadata.expected_base_count` == `len(base_predictions)`
    - Assert `metadata.expected_smoke_test_count` == count of predictions with `smoke_test: true`
    - Assert `metadata.expected_mode_counts` matches actual `verification_mode` distribution
    - **Validates: Requirements 7.1, 7.2, 7.3**

- [x] 3. Checkpoint - Validate dataset integrity
  - Ensure the golden dataset JSON is valid and parseable
  - Verify all 18 personal/subjective cases (base-027 through base-039, base-041 through base-045) are preserved unchanged
  - Verify `base-004` and `base-009` are present and unchanged
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Remove duplicate dynamic prediction
  - [x] 4.1 Remove `template_python_released` from `get_all_templates()` in `eval/generate_dynamic_dataset.py`
    - Remove the `template_python_released` entry from the list returned by `get_all_templates()`
    - The function definition can remain in the file (dead code)
    - This prevents `dyn-imm-005` from being generated
    - _Requirements: 2.1, 2.2, 2.3_

- [x] 5. Update test assertions
  - [x] 5.1 Update count assertions in `eval/tests/test_case_loader.py`
    - Change `test_load_static_dataset_count` assertion from `== 55` to `== 58`
    - Change `test_load_merged_dataset_count` assertion from `== 70` to `== 72`
    - Change `test_qualifying_count_static` assertion from `== 7` to `== 11`
    - Change `test_qualifying_count_merged` assertion from `== 22` to `== 25`
    - Change `test_smoke_filter_count` assertion from `== 12` to `== 13`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 5.2 Write additional validation tests
    - Assert `base-046` and `base-052` are absent from the dataset
    - Assert `schema_version` and `dataset_version` are `"5.0"`
    - Assert `base-014` and `base-050` have updated prediction text
    - Assert new predictions `base-056` through `base-060` exist with correct fields
    - Assert `template_python_released` is not in `get_all_templates()` return list
    - _Requirements: 1.1, 1.2, 3.1, 3.2, 4.5, 6.1, 6.2, 2.1_

- [x] 6. Final checkpoint - Run full test suite
  - Run `/home/wsluser/projects/calledit/venv/bin/python -m pytest eval/tests/ -v`
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The dataset schema is unchanged — only data values and counts are modified
- Property tests validate the two correctness properties from the design document
- Use venv at `/home/wsluser/projects/calledit/venv` for all Python commands
