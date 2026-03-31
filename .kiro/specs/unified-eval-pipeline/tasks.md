# Implementation Plan: Unified Eval Pipeline

## Overview

Implement `eval/unified_eval.py` as a single-file orchestrator that replaces the three separate eval runners. The pipeline chains: dataset audit → creation pass → verification timing → verification pass → evaluation → unified report → cleanup. All existing backends, evaluators, merger, and report store are reused without modification. Tasks are ordered for incremental testability: core pipeline first, then verification, evaluation, report, and finally dashboard integration.

## Tasks

- [x] 1. Scaffold `eval/unified_eval.py` with CLI, audit, and creation pass
  - [x] 1.1 Create `eval/unified_eval.py` with CLI argument parsing and `main()` entry point
    - Accept `--dataset`, `--dynamic-dataset`, `--tier` (smoke, smoke+judges, full), `--description`, `--output-dir`, `--dry-run`, `--case`, `--resume`, `--skip-cleanup`
    - Import `load_and_merge` from `eval.dataset_merger`
    - Implement `parse_args()` and `main()` skeleton that loads the merged dataset
    - _Requirements: 8.1_

  - [x] 1.2 Implement `audit_dataset()` function
    - Filter predictions where `expected_verification_outcome` is non-null into the included list
    - Collect prediction ids with null `expected_verification_outcome` into the excluded list
    - Log a warning for each excluded prediction id
    - Print included/excluded counts at the start of the run
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.3 Implement `--dry-run` mode
    - List all qualifying cases with prediction_id, difficulty, expected verdict, and verification mode
    - Do not invoke any agents or write to DDB
    - _Requirements: 8.2_

  - [x] 1.4 Implement `run_creation_pass()` function
    - Authenticate with Cognito via `get_cognito_token()` and create `AgentCoreBackend(bearer_token=token)`
    - Invoke creation agent for each qualifying prediction, capture bundle
    - Implement `shape_bundle()` to write each bundle to the Eval_Table with `PK=PRED#{prediction_id}`, `SK=BUNDLE`, `status=pending`, converting floats to `Decimal`
    - On per-prediction failure, record `creation_error` in case result, skip for subsequent phases, continue
    - Record creation pass duration
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 1.5 Implement Eval_Table lifecycle: `ensure_eval_table()` and `cleanup_eval_table()`
    - Create `calledit-v4-eval` table if it doesn't exist (PK=String HASH, SK=String RANGE, PAY_PER_REQUEST)
    - `cleanup_eval_table()` deletes all items written during the run, logs warnings on per-item failure
    - Respect `--skip-cleanup` flag
    - _Requirements: 7.1, 7.2, 7.4, 8.4_

  - [ ]* 1.6 Write property test: Dataset audit partitions correctly
    - **Property 1: Dataset audit partitions predictions correctly**
    - Use hypothesis to generate lists of prediction dicts with random null/non-null `expected_verification_outcome`
    - Assert: included list contains exactly non-null predictions, excluded list contains exactly null prediction ids, union equals all input ids, sets are disjoint
    - **Validates: Requirements 1.1, 1.2, 1.3**

  - [ ]* 1.7 Write property test: Bundle shaping produces valid DDB items
    - **Property 2: Bundle shaping produces valid DDB items**
    - Use hypothesis to generate random prediction_id strings and bundle dicts with nested floats
    - Assert: PK equals `PRED#{prediction_id}`, SK equals `BUNDLE`, status equals `pending`, all float values converted to Decimal
    - **Validates: Requirements 2.3**

- [x] 2. Checkpoint — Verify audit and creation pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Add verification timing and verification pass
  - [x] 3.1 Implement `compute_verification_wait()` function
    - Read `verification_date` (from `parsed_claim.verification_date`) from all bundles in the Eval_Table
    - Compute `max(0, latest_verification_date - now + 30s buffer)`
    - Log wait duration; sleep if positive, proceed immediately if zero/negative
    - Handle unparseable dates gracefully (log warning, proceed)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 3.2 Implement `run_verification_pass()` function
    - Iterate over prediction_ids that were successfully written during creation pass (skip cases with `creation_error`)
    - Invoke `VerificationBackend` with each `prediction_id` and `table_name=calledit-v4-eval`
    - Read full verdict (evidence, reasoning) back from Eval_Table
    - On per-prediction failure, record `verification_error`, continue
    - Record verification pass duration
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.3 Implement `--resume` flag support
    - Scan Eval_Table for existing items with `status=pending` or `status=verified`
    - Skip creation for prediction_ids already present
    - Proceed to verification/evaluation for already-created bundles
    - _Requirements: 7.3_

  - [x] 3.4 Implement `--case` single-case execution
    - Filter qualifying predictions to only the specified case id
    - Execute that single case through all phases
    - _Requirements: 8.3_

  - [ ]* 3.5 Write property test: Phase error isolation
    - **Property 3: Phase error isolation**
    - Use hypothesis to generate lists of case_result dicts with random error/success states
    - Assert: verification pass only processes cases without `creation_error` and with non-None `prediction_id`
    - **Validates: Requirements 2.4, 3.1, 3.4**

  - [ ]* 3.6 Write property test: Verification wait computation
    - **Property 4: Verification wait computation**
    - Use hypothesis to generate lists of ISO 8601 date strings and a random "now" datetime
    - Assert: result is non-negative; if all dates ≤ now, result is 0; otherwise result equals `max(0, max_date - now + 30)`
    - **Validates: Requirements 4.2**

- [x] 4. Checkpoint — Verify full creation→verification flow
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Add evaluation phase
  - [x] 5.1 Implement `build_creation_evaluators()` function
    - Always include 6 Tier 1 evaluators: schema_validity, field_completeness, score_range, date_resolution, dimension_count, tier_consistency
    - For `smoke+judges` or `full` tier, additionally include intent_preservation and plan_quality
    - _Requirements: 5.1, 5.2_

  - [x] 5.2 Implement `build_verification_evaluators()` function
    - Always include 5 Tier 1 evaluators: schema_validity, verdict_validity, confidence_range, evidence_completeness, evidence_structure
    - For `smoke+judges` or `full` tier with `golden` source, add mode-specific Tier 2 evaluators:
      - immediate/recurring: verdict_accuracy + evidence_quality (+ evidence_freshness for recurring)
      - at_date: at_date_verdict_accuracy + evidence_quality
      - before_date: verdict_appropriateness + evidence_quality
    - _Requirements: 5.3, 5.4, 5.5_

  - [x] 5.3 Implement `run_evaluation()` function
    - Run creation evaluators against each creation bundle
    - Run verification evaluators (mode-aware) against each verification result
    - Compute calibration metrics using `compute_calibration_metrics` from `calibration_eval.py` (reuse `classify_score_tier`, `is_calibration_correct`)
    - Compute per-evaluator averages, overall pass rates, and per-mode breakdowns for both creation and verification
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [ ]* 5.4 Write property test: Creation evaluator selection by tier
    - **Property 5: Creation evaluator selection by tier**
    - Assert: smoke → exactly 6 Tier 1; smoke+judges/full → 6 Tier 1 + 2 Tier 2
    - **Validates: Requirements 5.1, 5.2**

  - [ ]* 5.5 Write property test: Verification evaluator selection by tier and mode
    - **Property 6: Verification evaluator selection by tier and mode**
    - Assert: smoke → 5 Tier 1 only; smoke+judges/full → 5 Tier 1 + mode-specific Tier 2
    - **Validates: Requirements 5.3, 5.4, 5.5**

- [x] 6. Checkpoint — Verify evaluation phase
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Add unified report generation and report store integration
  - [x] 7.1 Implement `build_unified_report()` function
    - Assemble `run_metadata` with description, agent="unified", timestamp, duration_seconds, case_count, excluded_count, dataset_version, dataset_sources, run_tier, git_commit, prompt_versions, phase_durations, ground_truth_limitation
    - Assemble `creation_scores` with per-evaluator averages, overall_pass_rate, by_mode breakdowns
    - Assemble `verification_scores` with per-evaluator averages, overall_pass_rate, by_mode breakdowns
    - Assemble `calibration_scores` with calibration_accuracy, mean_absolute_error, high_score_confirmation_rate, low_score_failure_rate, verdict_distribution
    - Assemble `case_results` array with all per-case fields
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.8_

  - [x] 7.2 Implement `save_report()` and report store write
    - Save report as `unified-eval-{YYYYMMDD-HHMMSS}.json` in the output directory
    - Write to Report_Store with `agent_type=unified` using `write_report` from `eval.report_store`
    - _Requirements: 6.1, 6.7, 9.1_

  - [x] 7.3 Implement `print_summary()` for stdout output
    - Print creation metrics, verification metrics, calibration metrics, and per-case results
    - _Requirements: 8.5_

  - [ ]* 7.4 Write property test: Unified report structure completeness
    - **Property 7: Unified report structure completeness**
    - Use hypothesis to generate random case results, scores dicts, and metadata
    - Assert: report contains run_metadata with required keys, creation_scores with Tier 1 keys + overall_pass_rate, verification_scores with Tier 1 keys + overall_pass_rate, calibration_scores with all 5 required keys, case_results with correct length
    - **Validates: Requirements 6.2, 6.3, 6.4, 6.5, 6.6, 6.8**

- [x] 8. Checkpoint — Verify report generation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Wire all phases together in `main()`
  - [x] 9.1 Complete `main()` orchestration
    - Wire phases in order: audit → creation pass → verification timing → verification pass → evaluation → report → cleanup
    - Handle `--dry-run`, `--case`, `--resume`, `--skip-cleanup` flags
    - Ensure Cognito auth failure is fatal; per-case errors are non-fatal
    - Ensure cleanup runs even after errors (try/finally)
    - _Requirements: 2.1, 4.5, 7.2, 8.1, 8.2, 8.3, 8.4, 10.1, 10.2, 10.3_

  - [ ]* 9.2 Write property test: Resume skips existing prediction_ids
    - **Property 8: Resume skips existing prediction_ids**
    - Use hypothesis to generate random prediction lists and random existing id sets
    - Assert: creation invocations equal `len(qualifying) - len(qualifying ∩ existing)`
    - **Validates: Requirements 7.3**

- [x] 10. Checkpoint — Verify end-to-end pipeline
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Dashboard integration for unified reports
  - [ ] 11.1 Update `frontend-v4/src/pages/EvalDashboard/types.ts`
    - Add `'unified'` to the `AgentType` union type
    - Add a fourth entry to `AGENT_TABS` for unified reports
    - _Requirements: 9.2_

  - [ ] 11.2 Update `frontend-v4/src/pages/EvalDashboard/components/AgentTab.tsx` for unified tab
    - Render creation scores, verification scores, and calibration scores sections in a single view when `agentType=unified`
    - _Requirements: 9.2_

  - [ ] 11.3 Add calibration scatter plot component
    - Create or update `frontend-v4/src/pages/EvalDashboard/components/CalibrationScatter.tsx`
    - Plot verifiability_score (x-axis) vs binary verification outcome (y-axis, 1=confirmed, 0=refuted/inconclusive)
    - Render within the unified tab view
    - _Requirements: 9.3_

  - [ ] 11.4 Add score-vs-outcome correlation curves by tier
    - Render grouped curves for high, moderate, low Score_Tiers with case counts per tier
    - Display within the unified tab alongside the scatter plot
    - _Requirements: 9.4_

- [ ] 12. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- `eval/unified_eval.py` is the only new Python file; existing runners are not modified (Requirement 10.1, 10.2, 10.3)
- Test file: `eval/tests/test_unified_eval.py`
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Property-based tests use `hypothesis` with `@settings(max_examples=100)`
