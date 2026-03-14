# Implementation Plan: Golden Dataset V2

## Overview

Rewrite the golden dataset schema, loader, and serialization to v2 (ground truth metadata, dimension tags, fuzziness levels, dataset_version). Add a standalone validation script, a DynamoDB eval reasoning store, and integrate v2 into the eval runner and score history. Archive the v1 dataset and replace it with ~40-50 base + 20-30 fuzzy predictions. All property-based tests use Hypothesis.

## Tasks

- [-] 1. Rewrite V2 schema and loader (`golden_dataset.py`)
  - [-] 1.1 Define new dataclasses: `GroundTruthMetadata`, `DimensionTags`, `DatasetMetadata`, updated `BasePrediction`, `FuzzyPrediction`, `GoldenDataset` with v2 fields (`ground_truth`, `dimension_tags`, `is_boundary_case`, `boundary_description`, `fuzziness_level`, `dataset_version`, `metadata`)
    - Replace all v1 dataclasses — clean break, no backward compatibility
    - Update constants: `SUPPORTED_SCHEMA_VERSION = "2.0"`, add `VALID_OBJECTIVITY`, `VALID_STAKES`, `VALID_TIME_HORIZONS`, `VALID_FUZZINESS_LEVELS`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 3.2, 7.1_

  - [ ] 1.2 Rewrite `load_golden_dataset()` as v2-only loader
    - Reject `schema_version != "2.0"` with `ValueError` including both version strings
    - Validate all ground truth fields present and correctly typed for each base prediction
    - Validate `fuzziness_level` in {0,1,2,3} for each fuzzy prediction
    - Validate `expected_category` present in every base and fuzzy prediction
    - Validate fuzzy `base_prediction_id` references resolve
    - Validate count integrity against `metadata.expected_base_count` / `expected_fuzzy_count` if present
    - Validate `dataset_version` is present and non-empty
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 3.2, 4.1, 4.4, 7.1, 7.2, 9.3_

  - [ ] 1.3 Rewrite `dataset_to_dict()` for v2 serialization
    - Serialize all v2 fields including `ground_truth`, `dimension_tags`, `is_boundary_case`, `boundary_description`, `fuzziness_level`, `dataset_version`, `metadata`
    - _Requirements: 9.1_

  - [ ] 1.4 Update `filter_test_cases()` for v2 fields
    - Support filtering by `fuzziness_level` for fuzzy predictions
    - Use `expected_category` from new v2 expected outputs structure
    - _Requirements: 4.1_

  - [ ]* 1.5 Write property test: V2 base prediction ground truth completeness (Property 1)
    - **Property 1: V2 base prediction ground truth completeness**
    - Generate random v2 base predictions with valid/invalid ground truth fields, verify all six fields present and correctly typed
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 4.1, 4.4, 5.4**

  - [ ]* 1.6 Write property test: V2 fuzzy prediction structural validity (Property 2)
    - **Property 2: V2 fuzzy prediction structural validity**
    - Generate random v2 fuzzy predictions, verify `fuzziness_level` in {0,1,2,3}, required fields present, `base_prediction_id` references valid base, `expected_category` valid
    - **Validates: Requirements 3.2, 3.5, 3.7, 4.4**

  - [ ]* 1.7 Write property test: Unsupported schema version rejection (Property 5)
    - **Property 5: Unsupported schema version rejection**
    - Generate random version strings != "2.0", verify `load_golden_dataset()` raises `ValueError` containing both the bad version and "2.0"
    - **Validates: Requirements 7.2**

  - [ ]* 1.8 Write property test: Round-trip serialization (Property 8)
    - **Property 8: Round-trip serialization**
    - Generate random valid `GoldenDataset` objects, serialize via `dataset_to_dict()`, write to JSON, reload via `load_golden_dataset()`, verify equivalence
    - **Validates: Requirements 9.1**

  - [ ]* 1.9 Write property test: Count integrity check (Property 9)
    - **Property 9: Count integrity check**
    - Generate datasets with mismatched `metadata.expected_base_count` or `expected_fuzzy_count`, verify `ValueError` identifying the mismatch
    - **Validates: Requirements 9.3**

  - [ ]* 1.10 Write property test: Fuzzy variants with same base have distinct fuzziness levels (Property 11)
    - **Property 11: Fuzzy variants with same base have distinct fuzziness levels**
    - Generate sets of fuzzy predictions sharing `base_prediction_id`, verify each has a distinct `fuzziness_level`
    - **Validates: Requirements 3.7**

- [ ] 2. Checkpoint — V2 schema and loader
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Create validation script (`eval/validate_dataset.py`)
  - [ ] 3.1 Implement `validate_dataset()` returning list of error strings
    - Check structural constraints: required fields, types, valid enum values
    - Check referential integrity: fuzzy `base_prediction_id` references resolve
    - Check uniqueness: no duplicate IDs, no base/fuzzy ID namespace collisions
    - Check ground truth coherence: sources non-empty, criteria non-empty, steps non-empty, objectivity valid
    - Check coverage: at least 12 per category, 3 per stakes, 3 per time horizon, 8 domains, 12 personas, 5 boundary cases, fuzzy level distribution
    - Check count integrity: actual counts match metadata expected counts
    - Check `dataset_version` present and non-empty
    - Exit code 0 = valid, 1 = errors found; errors to stderr, summary to stdout
    - _Requirements: 8.1, 8.2, 8.4, 9.2, 9.3, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.3, 3.4_

  - [ ]* 3.2 Write property test: Validation script catches structural violations (Property 7)
    - **Property 7: Validation script catches structural violations**
    - Generate valid dataset JSON, inject exactly one structural violation (missing field, invalid enum, duplicate ID, dangling fuzzy reference, count mismatch), verify non-empty error list identifying the violation
    - **Validates: Requirements 8.1, 8.2, 8.4, 9.2**

- [ ] 4. Add DynamoDB EvalReasoningTable to SAM template
  - [ ] 4.1 Add `EvalReasoningTable` resource to `backend/calledit-backend/template.yaml`
    - Table name: `calledit-eval-reasoning`
    - Partition key: `eval_run_id` (S), Sort key: `record_key` (S)
    - BillingMode: PAY_PER_REQUEST
    - TTL on `ttl` attribute, PointInTimeRecovery enabled, SSE enabled
    - Add DynamoDB CRUD policy to `MakeCallStreamFunction` for the new table
    - _Requirements: 6.5_

- [ ] 5. Implement EvalReasoningStore (`eval_reasoning_store.py`)
  - [ ] 5.1 Create `backend/calledit-backend/handlers/strands_make_call/eval_reasoning_store.py`
    - `EvalReasoningStore` class with fire-and-forget `_put_item` (log warning on failure, never raise)
    - `write_run_metadata()`, `write_agent_outputs()`, `write_judge_reasoning()`, `write_token_counts()`
    - TTL set to 90 days from creation
    - `eval_run_id` generated as UUID per store instance
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 5.2 Write property test: Reasoning store fire-and-forget resilience (Property 3)
    - **Property 3: Reasoning store fire-and-forget resilience**
    - Generate random exceptions (ConnectionError, throttle, ValidationError), verify `EvalReasoningStore` logs warning and returns without raising
    - **Validates: Requirements 6.6**

  - [ ]* 5.3 Write property test: Reasoning store item completeness (Property 4)
    - **Property 4: Reasoning store item completeness**
    - Generate random agent outputs (4 non-empty strings), token counts (4 agents with input/output ints), judge reasoning (score float, reasoning string, model ID), verify DDB items contain all fields with correct types and future TTL
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

- [ ] 6. Checkpoint — DDB table and reasoning store
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Integrate V2 into eval runner and score history
  - [ ] 7.1 Update `eval_runner.py` for v2 schema
    - Add `dataset_version` and `schema_version` to evaluation report dict
    - Add `eval_run_id` to report (links to DDB reasoning store)
    - Create `EvalReasoningStore` instance per run, write agent outputs / judge reasoning / token counts as test cases execute
    - Handle fuzziness level 0 fuzzy predictions (still execute round 1, expect high ClarificationQuality score)
    - Update expected output field access for v2 structure (`expected_category` instead of nested `verifiable_category`)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6, 7.1, 7.3_

  - [ ] 7.2 Update `score_history.py` for dataset_version tracking
    - Include `dataset_version` in each score history entry
    - In `compare_latest()`, detect `dataset_version` mismatch between runs, add `dataset_version_mismatch: True` flag and warning message with both version strings
    - Compute per-test-case deltas only for IDs present in both runs when versions differ
    - _Requirements: 7.4_

  - [ ]* 7.3 Write property test: Dataset version propagation (Property 6)
    - **Property 6: Dataset version propagation**
    - Generate random version strings, trace through load → report → score history, verify `dataset_version` appears identically in all three
    - **Validates: Requirements 7.1, 7.3, 7.4**

  - [ ]* 7.4 Write property test: Score history cross-version warning (Property 10)
    - **Property 10: Score history cross-version warning**
    - Generate two consecutive score history entries with different `dataset_version` values, verify `compare_latest()` returns `dataset_version_mismatch: True` and warning containing both version strings
    - **Validates: Requirements 7.4**

- [ ] 8. Checkpoint — Eval runner and score history v2 integration
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Archive v1 dataset and create v2 golden dataset JSON
  - [ ] 9.1 Archive v1 dataset
    - Move `eval/golden_dataset.json` to `eval/golden_dataset_v1_archived.json`
    - _Requirements: 7.5_

  - [ ] 9.2 Create v2 `eval/golden_dataset.json` with 40-50 base predictions and 20-30 fuzzy predictions
    - Schema version "2.0", dataset version "2.0"
    - Include `metadata` with `expected_base_count` and `expected_fuzzy_count`
    - Persona-driven generation from 12+ personas across 8+ domains
    - All four stakes levels (3+ each), all four time horizons (3+ each)
    - At least 12 per category (auto_verifiable, automatable, human_only)
    - At least 5 boundary cases with `is_boundary_case: true` and `boundary_description`
    - Full `ground_truth` metadata on every base prediction (all 6 fields)
    - `dimension_tags` on every base prediction
    - Fuzzy predictions: 3+ at level 0, 5+ at levels 1/2/3, each referencing valid base ID
    - At least 5 fuzzy predictions where clarification doesn't change category
    - Multiple fuzzy variants of same base must have distinct fuzziness levels
    - Only `expected_category` required in expected outputs; other agent outputs optional rubric guidance
    - _Requirements: 1.1–1.7, 2.1–2.7, 3.1–3.7, 4.1–4.4, 5.1–5.4_

  - [ ] 9.3 Run validation script against the new v2 dataset to verify zero errors
    - _Requirements: 8.1_

- [ ] 10. Final checkpoint — Full integration
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis with `@settings(max_examples=100)`
- Unit tests validate specific examples and edge cases
- All Python commands must use the venv at `/home/wsluser/projects/calledit/venv`
- The v1 dataset is archived — no backward compatibility in the v2 loader
- DynamoDB reasoning store is fire-and-forget; eval never blocks on DDB failures
