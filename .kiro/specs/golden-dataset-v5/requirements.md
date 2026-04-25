# Requirements Document

## Introduction

Clean up the CalledIt golden evaluation dataset from schema version 4.0 to 5.0. The dataset drives continuous evaluation of the prediction creation and verification agents. This cleanup removes redundant test cases, shortens unreachable far-future deadlines, adds recently-happened events with known outcomes, and bumps the schema version. The goal is a tighter, higher-signal dataset for the full continuous eval run.

## Glossary

- **Golden_Dataset**: The static JSON file (`eval/golden_dataset.json`) containing base predictions and fuzzy predictions used by the eval framework.
- **Base_Prediction**: A single prediction entry in the `base_predictions` array, identified by a unique `id` field (e.g., `base-001`).
- **Dynamic_Dataset**: The generated JSON file (`eval/dynamic_golden_dataset.json`) containing time-anchored predictions produced by `eval/generate_dynamic_dataset.py`.
- **Dynamic_Generator**: The Python module `eval/generate_dynamic_dataset.py` that produces the Dynamic_Dataset from template functions.
- **Smoke_Test_Flag**: The boolean `smoke_test` field on a Base_Prediction that marks it for inclusion in the fast "smoke" evaluation tier.
- **Expected_Verification_Outcome**: The `expected_verification_outcome` field on a Base_Prediction, set to `"confirmed"`, `"refuted"`, or `null` (unknown/future).
- **Verification_Mode**: The `verification_mode` field indicating when a prediction can be checked: `"immediate"`, `"at_date"`, `"before_date"`, or `"recurring"`.
- **Schema_Version**: The `schema_version` and `dataset_version` fields at the root of the Golden_Dataset JSON.
- **Metadata_Block**: The `metadata` object in the Golden_Dataset containing expected counts and mode distributions.
- **Case_Loader**: The Python module `eval/case_loader.py` that converts Golden_Dataset predictions into Strands Evals SDK Case objects.
- **Dataset_Merger**: The Python module `eval/dataset_merger.py` that merges the static Golden_Dataset with the Dynamic_Dataset.
- **Test_Suite**: The pytest test files under `eval/tests/` that validate dataset structure and case loading.

## Requirements

### Requirement 1: Remove Duplicate Base Predictions

**User Story:** As an eval framework maintainer, I want duplicate predictions removed from the Golden_Dataset, so that each test case is unique and evaluation metrics are not inflated by redundant cases.

#### Acceptance Criteria

1. WHEN the Golden_Dataset is loaded, THE Golden_Dataset SHALL NOT contain Base_Prediction `base-046` (duplicate of `base-004`, both "The S&P 500 will close higher today than yesterday").
2. WHEN the Golden_Dataset is loaded, THE Golden_Dataset SHALL NOT contain Base_Prediction `base-052` (duplicate of `base-009`, both "The US national debt exceeds $35 trillion").
3. THE Golden_Dataset SHALL retain Base_Prediction `base-004` with its existing Smoke_Test_Flag value of `true`.
4. THE Golden_Dataset SHALL retain Base_Prediction `base-009` with its existing fields unchanged.

### Requirement 2: Remove Duplicate Dynamic Prediction

**User Story:** As an eval framework maintainer, I want the duplicate dynamic prediction removed from the Dynamic_Generator, so that the merged dataset does not contain redundant cases.

#### Acceptance Criteria

1. THE Dynamic_Generator SHALL NOT include the `template_python_released` template function in the `get_all_templates()` return list.
2. WHEN the Dynamic_Dataset is generated, THE Dynamic_Generator SHALL NOT produce a prediction with id `dyn-imm-005`.
3. THE Golden_Dataset SHALL retain Base_Prediction `base-011` ("Python 3.13 has been officially released") as the canonical version of this test case.

### Requirement 3: Shorten Far-Future Prediction Deadlines

**User Story:** As an eval framework maintainer, I want far-future prediction deadlines shortened to near-term dates, so that the verification agent can attempt resolution during the eval run window.

#### Acceptance Criteria

1. THE Golden_Dataset SHALL replace the prediction text of `base-014` from "Bitcoin will exceed $150,000 USD by December 31, 2026" to a near-term Bitcoin price prediction with a deadline approximately one week from the dataset creation date (e.g., "Bitcoin will be trading above $90,000 USD next Friday").
2. THE Golden_Dataset SHALL replace the prediction text of `base-050` from "SpaceX will land a spacecraft on Mars before 2030" to a near-term SpaceX prediction with a deadline within the current month (e.g., "SpaceX will launch a Starship test flight this month").
3. WHEN `base-014` is updated, THE Golden_Dataset SHALL update the `ground_truth`, `evaluation_rubric`, and `dimension_tags` fields to match the new prediction text.
4. WHEN `base-050` is updated, THE Golden_Dataset SHALL update the `ground_truth`, `evaluation_rubric`, and `dimension_tags` fields to match the new prediction text.

### Requirement 4: Add Recently-Happened Event Predictions

**User Story:** As an eval framework maintainer, I want predictions about recently-happened real-world events added to the Golden_Dataset, so that the verification agent's ability to find and confirm historical facts via web search is tested.

#### Acceptance Criteria

1. THE Golden_Dataset SHALL contain at least 5 new Base_Predictions covering recently-happened events across at least 4 of these domains: sports, finance, politics, weather, technology.
2. WHEN a recently-happened event prediction is added, THE Base_Prediction SHALL have its Expected_Verification_Outcome set to either `"confirmed"` or `"refuted"` (never `null`).
3. WHEN a recently-happened event prediction is added, THE Base_Prediction SHALL have its Verification_Mode set to `"immediate"` (the event has already occurred and can be verified now).
4. WHEN a recently-happened event prediction is added, THE Base_Prediction SHALL include a complete `ground_truth` object with `verification_sources`, `verification_criteria`, `verification_steps`, and `expected_verification_method` fields.
5. THE Golden_Dataset SHALL assign sequential ids to new predictions starting from `base-056` (continuing after the last existing id `base-055`).

### Requirement 5: Preserve Personal and Subjective Cases

**User Story:** As an eval framework maintainer, I want all personal and subjective prediction cases preserved in the Golden_Dataset, so that they serve as sad-path baselines now and memory integration test cases in the future.

#### Acceptance Criteria

1. THE Golden_Dataset SHALL retain all of the following Base_Predictions unchanged: `base-027`, `base-028`, `base-029`, `base-030`, `base-031`, `base-032`, `base-033`, `base-034`, `base-035`, `base-036`, `base-037`, `base-038`, `base-039`, `base-041`, `base-042`, `base-043`, `base-044`, `base-045`.
2. THE Golden_Dataset SHALL retain the Smoke_Test_Flag values for `base-027`, `base-033`, `base-034`, and `base-044` unchanged.

### Requirement 6: Bump Schema and Dataset Version

**User Story:** As an eval framework maintainer, I want the schema and dataset versions bumped to 5.0, so that the version number reflects the structural changes made in this cleanup.

#### Acceptance Criteria

1. THE Golden_Dataset SHALL have its `schema_version` field set to `"5.0"`.
2. THE Golden_Dataset SHALL have its `dataset_version` field set to `"5.0"`.

### Requirement 7: Update Metadata Block

**User Story:** As an eval framework maintainer, I want the Metadata_Block updated to reflect the new prediction counts, so that dataset validation checks pass.

#### Acceptance Criteria

1. WHEN duplicate predictions are removed and new predictions are added, THE Metadata_Block SHALL update `expected_base_count` to match the actual number of Base_Predictions in the `base_predictions` array.
2. WHEN duplicate predictions are removed, THE Metadata_Block SHALL update `expected_smoke_test_count` to match the actual number of Base_Predictions with `smoke_test: true`.
3. WHEN predictions are added or removed, THE Metadata_Block SHALL update `expected_mode_counts` to match the actual distribution of Verification_Mode values across all Base_Predictions.
4. THE Metadata_Block SHALL leave `expected_fuzzy_count` unchanged at 23 (fuzzy predictions are not modified in this cleanup).

### Requirement 8: Update Test Assertions

**User Story:** As an eval framework maintainer, I want all test assertions updated to match the new dataset counts, so that the Test_Suite passes after the cleanup.

#### Acceptance Criteria

1. WHEN the static dataset count changes, THE Test_Suite SHALL update the `test_load_static_dataset_count` assertion to match the new Base_Prediction count.
2. WHEN the dynamic dataset loses `dyn-imm-005`, THE Test_Suite SHALL update the `test_load_merged_dataset_count` assertion to reflect the new merged count (static count minus replacements plus new dynamic count of 15).
3. WHEN new predictions with Expected_Verification_Outcome are added, THE Test_Suite SHALL update the `test_qualifying_count_static` assertion to match the new count of qualifying cases.
4. WHEN the merged qualifying count changes, THE Test_Suite SHALL update the `test_qualifying_count_merged` assertion to match the new merged qualifying count.
5. WHEN the smoke test count changes due to removed predictions, THE Test_Suite SHALL update the `test_smoke_filter_count` assertion to match the new smoke test count.

### Requirement 9: Maintain Smoke Test Coverage

**User Story:** As an eval framework maintainer, I want smoke test coverage maintained after removing duplicates, so that the fast evaluation tier still covers key verification modes and domains.

#### Acceptance Criteria

1. IF a removed Base_Prediction had `smoke_test: true`, THEN THE Golden_Dataset SHALL verify that the remaining smoke test cases still cover the same Verification_Mode that the removed case covered.
2. THE Golden_Dataset SHALL have at least 10 Base_Predictions with `smoke_test: true` after all changes.
3. WHEN new recently-happened event predictions are added, THE Golden_Dataset SHALL consider marking at least one as `smoke_test: true` to improve smoke tier coverage of the `"immediate"` Verification_Mode with known outcomes.
