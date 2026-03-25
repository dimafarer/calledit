# Requirements Document

## Introduction

Reshape the existing v3 golden dataset (`eval/golden_dataset.json`) to be v4-native. The v3 dataset (45 base predictions + 23 fuzzy predictions, schema 3.0, dataset 3.1) was built around the old 4-agent serial graph with 3-category routing (auto_verifiable/automatable/human_only). V4 uses a single 3-turn creation agent with continuous verifiability scoring (0.0–1.0), AgentCore built-in tools (Browser + Code Interpreter), and structured Pydantic outputs (`ParsedClaim`, `VerificationPlan`, `PlanReview`). This reshape removes v3 technical debt, adds v4-native ground truth fields, flags a smoke test subset for fast iteration, updates evaluation rubric text to reference v4 concepts, and produces a validation script to enforce structural correctness. Per Decisions 122–126 from Project Update 30.

## Glossary

- **Reshape_Script**: The Python script that reads the v3 dataset, applies all field transformations, and writes the v4 dataset
- **Validation_Script**: The Python script that loads the reshaped v4 dataset and verifies structural correctness against all v4 schema rules
- **Base_Prediction**: One of the 45 primary prediction entries in the dataset, each with ground truth, dimension tags, and evaluation rubric
- **Fuzzy_Prediction**: One of the 23 variant prediction entries that test the clarification flow, linked to a base prediction via `base_prediction_id`
- **Verifiability_Score_Range**: A 2-element list `[low, high]` where both values are floats in [0.0, 1.0] and low ≤ high, representing the expected range of the v4 creation agent's verifiability score for a given prediction
- **Verification_Outcome**: One of four values — `"confirmed"`, `"refuted"`, `"inconclusive"`, or `null` — representing the expected result when the verification agent processes the prediction
- **Smoke_Test_Subset**: A subset of approximately 12 base predictions flagged with `"smoke_test": true` for fast iteration eval runs (per Decision 125)
- **V3_Dead_Fields**: The `expected_per_agent_outputs` and `tool_manifest_config` fields present in the v3 dataset that map to the dead 3-category system and MCP tool registry respectively
- **Evaluation_Rubric**: Free-text field on each prediction describing what the evaluator should look for; v3 rubrics reference "categorizer", "VB", and category names that must be updated to v4 concepts
- **Dataset_File**: The file `eval/golden_dataset.json` containing the complete golden dataset

## Requirements

### Requirement 1: Remove v3-Only Fields from Base Predictions

**User Story:** As an eval framework developer, I want all v3-specific fields removed from base predictions, so that the dataset contains no technical debt from the dead 3-category system.

#### Acceptance Criteria

1. WHEN the Reshape_Script processes a Base_Prediction, THE Reshape_Script SHALL remove the `expected_per_agent_outputs` field from that Base_Prediction
2. WHEN the Reshape_Script processes a Base_Prediction, THE Reshape_Script SHALL remove the `tool_manifest_config` field from that Base_Prediction
3. THE Validation_Script SHALL verify that no Base_Prediction in the reshaped Dataset_File contains an `expected_per_agent_outputs` field
4. THE Validation_Script SHALL verify that no Base_Prediction in the reshaped Dataset_File contains a `tool_manifest_config` field

### Requirement 2: Add Verifiability Score Range to Base Predictions

**User Story:** As an eval framework developer, I want each base prediction to have an expected verifiability score range, so that the creation agent's continuous scoring can be evaluated against ground truth.

#### Acceptance Criteria

1. WHEN the Reshape_Script processes a Base_Prediction, THE Reshape_Script SHALL add an `expected_verifiability_score_range` field containing a 2-element list of floats
2. THE Reshape_Script SHALL assign Verifiability_Score_Range values based on the prediction's ground truth characteristics: objective predictions with publicly accessible data sources receive ranges in [0.7, 1.0]; predictions with known data sources but no registered tool or temporal delays receive ranges in [0.4, 0.7]; subjective predictions or predictions requiring private physical observation receive ranges in [0.0, 0.4]
3. THE Validation_Script SHALL verify that every Base_Prediction contains an `expected_verifiability_score_range` field
4. THE Validation_Script SHALL verify that each `expected_verifiability_score_range` is a list of exactly 2 elements where both values are floats in the range [0.0, 1.0] and the first value is less than or equal to the second value

### Requirement 3: Add Expected Verification Outcome to Base Predictions

**User Story:** As an eval framework developer, I want each base prediction to have an expected verification outcome, so that cross-agent calibration (Spec V4-7a-4) can compare predicted outcomes against ground truth.

#### Acceptance Criteria

1. WHEN the Reshape_Script processes a Base_Prediction, THE Reshape_Script SHALL add an `expected_verification_outcome` field with a value of `"confirmed"`, `"refuted"`, `"inconclusive"`, or `null`
2. THE Reshape_Script SHALL assign `null` to predictions that cannot be verified at the current time (future events, missing tool access), `"confirmed"` to predictions with deterministic or currently verifiable positive outcomes, `"refuted"` to predictions with deterministic or currently verifiable negative outcomes, and `"inconclusive"` to predictions where the outcome depends on subjective interpretation or insufficient data
3. THE Validation_Script SHALL verify that every Base_Prediction contains an `expected_verification_outcome` field
4. THE Validation_Script SHALL verify that each `expected_verification_outcome` value is one of `"confirmed"`, `"refuted"`, `"inconclusive"`, or `null`

### Requirement 4: Add Smoke Test Flag to Base Predictions

**User Story:** As an eval framework developer, I want a subset of approximately 12 base predictions flagged for smoke testing, so that fast iteration eval runs can cover all domains with correct difficulty distribution per Decision 125.

#### Acceptance Criteria

1. WHEN the Reshape_Script processes a Base_Prediction, THE Reshape_Script SHALL add a `smoke_test` boolean field set to `true` for selected cases and `false` for all others
2. THE Reshape_Script SHALL select approximately 12 cases for the Smoke_Test_Subset with a distribution of 4 easy, 5 medium, and 3 hard predictions
3. THE Reshape_Script SHALL select Smoke_Test_Subset cases that collectively cover all 12 domains: weather, finance, sports, nature, tech, personal, entertainment, work, food, health, travel, and social
4. THE Reshape_Script SHALL include at least 1 boundary case (where `is_boundary_case` is `true`) in the Smoke_Test_Subset
5. THE Reshape_Script SHALL include at least 1 case with `verification_readiness` set to `"immediate"` in the Smoke_Test_Subset
6. THE Reshape_Script SHALL include at least 1 prediction with `objectivity_assessment` of `"subjective"` and at least 1 prediction with `objectivity_assessment` of `"objective"` in the Smoke_Test_Subset
7. THE Validation_Script SHALL verify that the total count of Base_Predictions with `smoke_test` set to `true` is between 10 and 14 inclusive
8. THE Validation_Script SHALL verify that the Smoke_Test_Subset contains exactly 4 easy, 5 medium, and 3 hard predictions
9. THE Validation_Script SHALL verify that the Smoke_Test_Subset covers all 12 domains
10. THE Validation_Script SHALL verify that the Smoke_Test_Subset contains at least 1 boundary case, at least 1 case with `verification_readiness` of `"immediate"`, at least 1 subjective prediction, and at least 1 objective prediction

### Requirement 5: Update Evaluation Rubric Text for v4 Concepts

**User Story:** As an eval framework developer, I want evaluation rubric text updated to reference v4 concepts instead of v3 concepts, so that rubrics accurately describe what the v4 evaluators should assess.

#### Acceptance Criteria

1. WHEN the Reshape_Script processes a Base_Prediction's `evaluation_rubric` field, THE Reshape_Script SHALL replace references to "Categorizer" or "categorizer" with references to the v4 creation agent's verifiability scoring
2. WHEN the Reshape_Script processes a Base_Prediction's `evaluation_rubric` field, THE Reshape_Script SHALL replace references to "VB" (verification bundle) with references to the v4 `VerificationPlan` output
3. WHEN the Reshape_Script processes a Base_Prediction's `evaluation_rubric` field, THE Reshape_Script SHALL replace references to category names (`auto_verifiable`, `automatable`, `human_only`) with descriptions using verifiability score ranges (high ≥0.7, moderate 0.4–0.7, low <0.4)
4. THE Validation_Script SHALL verify that no Base_Prediction's `evaluation_rubric` contains the exact strings `"auto_verifiable"`, `"automatable"`, or `"human_only"`

### Requirement 6: Update Schema and Dataset Versions

**User Story:** As an eval framework developer, I want the schema and dataset versions bumped to 4.0, so that tooling can distinguish v4 datasets from v3 datasets.

#### Acceptance Criteria

1. THE Reshape_Script SHALL set the top-level `schema_version` field to `"4.0"`
2. THE Reshape_Script SHALL set the top-level `dataset_version` field to `"4.0"`
3. THE Validation_Script SHALL verify that `schema_version` equals `"4.0"`
4. THE Validation_Script SHALL verify that `dataset_version` equals `"4.0"`

### Requirement 7: Preserve All v4-Relevant Fields on Base Predictions

**User Story:** As an eval framework developer, I want all fields that remain relevant for v4 preserved without modification, so that existing ground truth data is not lost during the reshape.

#### Acceptance Criteria

1. THE Reshape_Script SHALL preserve the following fields on every Base_Prediction without modification: `id`, `prediction_text`, `difficulty`, `dimension_tags`, `is_boundary_case`, `boundary_description`
2. THE Reshape_Script SHALL preserve the following `ground_truth` sub-fields on every Base_Prediction without modification: `verifiability_reasoning`, `date_derivation`, `verification_sources`, `objectivity_assessment`, `verification_criteria`, `verification_steps`, `verification_timing`, `expected_verification_criteria`, `expected_verification_method`
3. WHEN a Base_Prediction contains a `verification_readiness` field, THE Reshape_Script SHALL preserve that field without modification
4. THE Validation_Script SHALL verify that every Base_Prediction contains the fields `id`, `prediction_text`, `difficulty`, `ground_truth`, `dimension_tags`, `evaluation_rubric`, `is_boundary_case`, and `boundary_description`
5. THE Validation_Script SHALL verify that every Base_Prediction's `ground_truth` object contains the keys `verifiability_reasoning`, `date_derivation`, `verification_sources`, `objectivity_assessment`, `verification_criteria`, `verification_steps`, `verification_timing`, `expected_verification_criteria`, and `expected_verification_method`

### Requirement 8: Update Fuzzy Predictions for v4

**User Story:** As an eval framework developer, I want fuzzy predictions updated to remove v3 category references while preserving the clarification flow test structure, so that fuzzy predictions are v4-native.

#### Acceptance Criteria

1. THE Reshape_Script SHALL preserve all 23 Fuzzy_Predictions with their existing fields: `id`, `fuzzy_text`, `base_prediction_id`, `fuzziness_level`, `simulated_clarifications`, `expected_clarification_topics`, and `evaluation_rubric`
2. WHEN a Fuzzy_Prediction contains an `expected_post_clarification_outputs` field with category references, THE Reshape_Script SHALL replace that field with an `expected_post_clarification_verifiability` field containing the expected verifiability score tier (`"high"`, `"moderate"`, or `"low"`) that corresponds to the original category mapping: `auto_verifiable` maps to `"high"`, `automatable` maps to `"moderate"`, `human_only` maps to `"low"`
3. THE Validation_Script SHALL verify that every Fuzzy_Prediction's `base_prediction_id` references a valid Base_Prediction `id` in the dataset
4. THE Validation_Script SHALL verify that no Fuzzy_Prediction contains an `expected_post_clarification_outputs` field
5. THE Validation_Script SHALL verify that every Fuzzy_Prediction contains an `expected_post_clarification_verifiability` field with a value of `"high"`, `"moderate"`, or `"low"`

### Requirement 9: Update Metadata Counts

**User Story:** As an eval framework developer, I want the metadata section to accurately reflect the v4 dataset contents, so that tooling can validate dataset integrity.

#### Acceptance Criteria

1. THE Reshape_Script SHALL update the `metadata.expected_base_count` field to match the actual number of Base_Predictions in the reshaped dataset
2. THE Reshape_Script SHALL update the `metadata.expected_fuzzy_count` field to match the actual number of Fuzzy_Predictions in the reshaped dataset
3. THE Reshape_Script SHALL add a `metadata.expected_smoke_test_count` field set to the actual number of Base_Predictions with `smoke_test` set to `true`
4. THE Validation_Script SHALL verify that `metadata.expected_base_count` equals the actual count of Base_Predictions
5. THE Validation_Script SHALL verify that `metadata.expected_fuzzy_count` equals the actual count of Fuzzy_Predictions
6. THE Validation_Script SHALL verify that `metadata.expected_smoke_test_count` equals the actual count of Base_Predictions with `smoke_test` set to `true`

### Requirement 10: Validation Script Structural Checks

**User Story:** As an eval framework developer, I want a comprehensive validation script that catches any structural errors in the reshaped dataset, so that the dataset is guaranteed correct before downstream eval specs depend on it.

#### Acceptance Criteria

1. THE Validation_Script SHALL load the reshaped Dataset_File and exit with a non-zero status code if the file cannot be parsed as valid JSON
2. THE Validation_Script SHALL verify that every required field is present on every Base_Prediction and every Fuzzy_Prediction, reporting the specific prediction `id` and missing field name for each violation
3. THE Validation_Script SHALL verify that no V3_Dead_Fields (`expected_per_agent_outputs`, `tool_manifest_config`) remain on any Base_Prediction, reporting the specific prediction `id` for each violation
4. THE Validation_Script SHALL print a summary of all checks performed and their pass/fail status, with a final overall pass/fail result
5. THE Validation_Script SHALL exit with status code 0 when all checks pass and a non-zero status code when any check fails

### Requirement 11: Reshape Script Produces Valid Output

**User Story:** As an eval framework developer, I want the reshape script to produce a valid v4 dataset file in a single run, so that the transformation is repeatable and auditable.

#### Acceptance Criteria

1. THE Reshape_Script SHALL read the v3 Dataset_File from `eval/golden_dataset.json`
2. THE Reshape_Script SHALL write the reshaped v4 dataset to `eval/golden_dataset.json`, overwriting the v3 file
3. THE Reshape_Script SHALL produce valid JSON output with consistent 2-space indentation
4. THE Reshape_Script SHALL print a summary of transformations applied: count of fields removed, count of fields added, count of rubrics updated, and count of smoke test cases flagged
5. IF the Reshape_Script encounters a Base_Prediction with an unexpected structure, THEN THE Reshape_Script SHALL log a warning with the prediction `id` and continue processing remaining predictions
