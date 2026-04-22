# Implementation Plan: Strands Evals SDK Migration

## Overview

**Spec A: Eval Pipeline Migration.** Migrate CalledIt's custom eval framework (~1,200 lines) to the Strands Evals SDK. This spec covers the Python pipeline: case loader, evaluators, task function, calibration, CLI runner, report store write, baseline comparison, and old code deletion. Dashboard adaptation is in Spec B (`strands-evals-dashboard`).

Each task builds incrementally: install SDK → case loader → deterministic evaluators → mode-specific evaluators → LLM judges → task function → calibration → CLI runner → report store → baseline comparison → old code deletion → full baseline → documentation.

All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`. Property tests use `hypothesis`. Backends (`agentcore_backend.py`, `verification_backend.py`) are preserved unchanged.

## Tasks

- [x] 1. Install strands-agents-evals and set up module structure
  - [x] 1.1 Install `strands-agents-evals` into the venv and add to `requirements.txt`
    - Run `/home/wsluser/projects/calledit/venv/bin/pip install strands-agents-evals`
    - Add `strands-agents-evals>=0.1.0` to root `requirements.txt`
    - Verify import: `from strands_evals import Case, Experiment`
    - _Requirements: N/A (prerequisite)_

  - [x] 1.2 Create new module directory structure
    - Create `eval/evaluators/creation/__init__.py`
    - Create `eval/evaluators/verification/__init__.py`
    - Create `eval/case_loader.py` (empty placeholder)
    - Create `eval/task_function.py` (empty placeholder)
    - Create `eval/calibration.py` (empty placeholder)
    - Create `eval/run_eval.py` (empty placeholder)
    - Create `eval/tests/__init__.py` (already exists, verify)
    - _Requirements: N/A (prerequisite)_

- [x] 2. Implement case loader
  - [x] 2.1 Implement `case_loader.py` — golden dataset to Case objects
    - Implement `load_cases(static_path, dynamic_path, tier, case_id) -> list[Case]`
    - Use `dataset_merger.load_and_merge()` for static+dynamic merge
    - Map `prediction_text` → `Case.input`, `expected_verification_outcome` → `Case.expected_output`
    - Set `metadata.qualifying = (expected_verification_outcome is not None)`
    - Set `Case.name = prediction["id"]`
    - Filter by `--case <id>` or `--tier smoke` (smoke_test=True)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 2.2 Write property test for case construction (Property 1)
    - **Property 1: Case construction preserves prediction data**
    - Generate random prediction dicts with hypothesis strategies
    - Verify Case field mappings including None expected_output → qualifying=False
    - Verify case count equals merged prediction count
    - Tag: `# Feature: strands-evals-migration, Property 1: Case construction preserves prediction data`
    - File: `eval/tests/test_case_loader.py`
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**

  - [x] 2.3 Write property test for case filtering (Property 2)
    - **Property 2: Case filtering correctness**
    - Generate random Case lists and filter criteria
    - Verify subset relationship and filter correctness
    - Tag: `# Feature: strands-evals-migration, Property 2: Case filtering correctness`
    - File: `eval/tests/test_case_loader.py`
    - **Validates: Requirements 1.5, 1.6**

  - [x] 2.4 Write unit tests for case loader
    - Load actual `golden_dataset.json`, verify case count and field values for known predictions (e.g., base-001)
    - Test edge cases: missing fields, empty dataset, no qualifying cases after filter
    - File: `eval/tests/test_case_loader.py`
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6_

- [x] 3. Checkpoint — case loader
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement deterministic creation evaluators
  - [x] 4.1 Implement `eval/evaluators/creation/schema_validity.py`
    - `SchemaValidityEvaluator(Evaluator)` — validate bundle against Pydantic models
    - Return `EvaluationOutput(score=1.0, test_pass=True)` on success, `(0.0, False)` on failure
    - _Requirements: 2.1_

  - [x] 4.2 Implement `eval/evaluators/creation/field_completeness.py`
    - `FieldCompletenessEvaluator(Evaluator)` — check sources/criteria/steps non-empty
    - _Requirements: 2.2_

  - [x] 4.3 Implement `eval/evaluators/creation/score_range.py`
    - `ScoreRangeEvaluator(Evaluator)` — verify score in [0.0, 1.0]
    - _Requirements: 2.3_

  - [x] 4.4 Implement `eval/evaluators/creation/date_resolution.py`
    - `DateResolutionEvaluator(Evaluator)` — verify ISO 8601 date
    - _Requirements: 2.4_

  - [x] 4.5 Implement `eval/evaluators/creation/dimension_count.py`
    - `DimensionCountEvaluator(Evaluator)` — verify ≥1 dimension assessment
    - _Requirements: 2.5_

  - [x] 4.6 Implement `eval/evaluators/creation/tier_consistency.py`
    - `TierConsistencyEvaluator(Evaluator)` — verify tier label matches score thresholds
    - _Requirements: 2.6_

  - [x] 4.7 Implement `eval/evaluators/creation/__init__.py` with evaluator exports
    - Export all 6 creation evaluator classes
    - _Requirements: 2.1–2.6_

  - [x] 4.8 Write property test for deterministic creation evaluators (Property 3)
    - **Property 3: Deterministic creation evaluator equivalence**
    - Generate random creation bundles (valid and invalid) with hypothesis
    - For each evaluator, verify score matches the validation condition
    - Compare new SDK evaluator output against old evaluator function output for same input
    - Tag: `# Feature: strands-evals-migration, Property 3: Deterministic creation evaluator equivalence`
    - File: `eval/tests/test_creation_evaluators.py`
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

  - [x] 4.9 Write unit tests for creation evaluator edge cases
    - Test empty bundles, missing fields, None values, non-dict inputs
    - File: `eval/tests/test_creation_evaluators.py`
    - _Requirements: 2.1–2.6_

- [x] 5. Implement deterministic verification evaluators
  - [x] 5.1 Implement `eval/evaluators/verification/schema_validity.py`
    - `VerificationSchemaEvaluator(Evaluator)` — check verdict/confidence/evidence/reasoning types
    - _Requirements: 3.1_

  - [x] 5.2 Implement `eval/evaluators/verification/verdict_validity.py`
    - `VerdictValidityEvaluator(Evaluator)` — check verdict ∈ {confirmed, refuted, inconclusive}
    - _Requirements: 3.2_

  - [x] 5.3 Implement `eval/evaluators/verification/confidence_range.py`
    - `ConfidenceRangeEvaluator(Evaluator)` — verify confidence in [0.0, 1.0]
    - _Requirements: 3.3_

  - [x] 5.4 Implement `eval/evaluators/verification/evidence_completeness.py`
    - `EvidenceCompletenessEvaluator(Evaluator)` — verify ≥1 evidence item
    - _Requirements: 3.4_

  - [x] 5.5 Implement `eval/evaluators/verification/evidence_structure.py`
    - `EvidenceStructureEvaluator(Evaluator)` — verify source/finding/relevant_to_criteria per item
    - _Requirements: 3.5_

  - [x] 5.6 Implement `eval/evaluators/verification/__init__.py` with evaluator exports
    - Export all 5 verification evaluator classes
    - _Requirements: 3.1–3.5_

  - [x] 5.7 Write property test for deterministic verification evaluators (Property 4)
    - **Property 4: Deterministic verification evaluator equivalence**
    - Generate random verification result dicts with hypothesis
    - For each evaluator, verify score matches the validation condition
    - Compare new SDK evaluator output against old evaluator function output for same input
    - Tag: `# Feature: strands-evals-migration, Property 4: Deterministic verification evaluator equivalence`
    - File: `eval/tests/test_verification_evaluators.py`
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

  - [x] 5.8 Write unit tests for verification evaluator edge cases
    - Test empty results, missing fields, None values, wrong types
    - File: `eval/tests/test_verification_evaluators.py`
    - _Requirements: 3.1–3.5_

- [x] 6. Checkpoint — deterministic evaluators
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement mode-specific verification evaluators
  - [x] 7.1 Implement `eval/evaluators/verification/at_date_verdict.py`
    - `AtDateVerdictEvaluator(Evaluator)` — temporal logic for at_date mode
    - Return no-op `EvaluationOutput(score=1.0, reason="N/A — not at_date mode")` when mode doesn't match
    - _Requirements: 4.1, 4.4_

  - [x] 7.2 Implement `eval/evaluators/verification/before_date_verdict.py`
    - `BeforeDateVerdictEvaluator(Evaluator)` — deadline logic for before_date mode
    - Return no-op when mode doesn't match
    - _Requirements: 4.2, 4.4_

  - [x] 7.3 Implement `eval/evaluators/verification/recurring_freshness.py`
    - `RecurringFreshnessEvaluator(Evaluator)` — evidence source field coverage
    - Return no-op when mode doesn't match
    - _Requirements: 4.3, 4.4_

  - [x] 7.4 Update `eval/evaluators/verification/__init__.py` to export mode-specific evaluators
    - _Requirements: 4.1–4.4_

  - [x] 7.5 Write property test for mode-specific evaluator routing (Property 5)
    - **Property 5: Mode-specific evaluator routing and temporal logic**
    - Generate random Cases with different verification modes and temporal scenarios
    - Verify no-op for non-matching modes and correct scoring for matching modes
    - Tag: `# Feature: strands-evals-migration, Property 5: Mode-specific evaluator routing and temporal logic`
    - File: `eval/tests/test_mode_evaluators.py`
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

  - [x] 7.6 Write unit tests for mode-specific evaluator edge cases
    - Test boundary dates, missing metadata, None verification_date
    - File: `eval/tests/test_mode_evaluators.py`
    - _Requirements: 4.1–4.4_


- [x] 8. Implement LLM judge evaluators and verdict accuracy
  - [x] 8.1 Implement `eval/evaluators/creation/intent_preservation.py`
    - `OutputEvaluator` wrapper with existing intent preservation rubric
    - Judge model: `us.anthropic.claude-sonnet-4-20250514-v1:0`
    - `test_pass = score >= 0.5`
    - _Requirements: 5.1_

  - [x] 8.2 Implement `eval/evaluators/creation/plan_quality.py`
    - `OutputEvaluator` wrapper with existing plan quality rubric
    - Judge model: `us.anthropic.claude-sonnet-4-20250514-v1:0`
    - `test_pass = score >= 0.5`
    - _Requirements: 5.2_

  - [x] 8.3 Implement `eval/evaluators/verification/evidence_quality.py`
    - `OutputEvaluator` wrapper with existing evidence quality rubric
    - Judge model: `us.anthropic.claude-sonnet-4-20250514-v1:0`
    - `test_pass = score >= 0.5`
    - _Requirements: 5.3_

  - [x] 8.4 Implement `eval/evaluators/verification/verdict_accuracy.py`
    - `VerdictAccuracyEvaluator(Evaluator)` — deterministic exact match vs expected_output
    - Return empty list when expected_output is None
    - _Requirements: 5.4_

  - [x] 8.5 Update both `__init__.py` files to export LLM judge and verdict accuracy evaluators
    - _Requirements: 5.1–5.4_

  - [x] 8.6 Write property test for verdict accuracy (Property 6)
    - **Property 6: Verdict accuracy evaluator correctness**
    - Generate random (verdict, expected) pairs including None expected
    - Verify exact match logic and empty output for None expected
    - Tag: `# Feature: strands-evals-migration, Property 6: Verdict accuracy evaluator correctness`
    - File: `eval/tests/test_verdict_accuracy.py`
    - **Validates: Requirements 5.4**

  - [x] 8.7 Write unit tests for LLM judge evaluator configuration
    - Verify rubric text, model ID, and test_pass threshold are correctly configured
    - Do NOT invoke the LLM — test configuration only
    - File: `eval/tests/test_creation_evaluators.py`
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 9. Checkpoint — all evaluators
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement task function
  - [x] 10.1 Implement `eval/task_function.py` — two-agent pipeline callable
    - `TaskFunctionFactory.__init__(creation_backend, verification_backend, eval_table_name)`
    - `TaskFunctionFactory.__call__(case: Case) -> dict` — creation → wait → verification
    - Return partial results on failure (never raise)
    - Support `--resume` by checking eval DDB table for existing prediction IDs
    - Use existing `AgentCoreBackend` and `VerificationBackend` unchanged
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 10.2 Write property test for verification wait computation (Property 7)
    - **Property 7: Verification wait computation**
    - Generate random verification dates and current timestamps
    - Verify wait formula: `max(0, (vdate - now).total_seconds() + 30)` capped at 300s
    - Verify 0 wait for immediate/recurring modes and past dates
    - Tag: `# Feature: strands-evals-migration, Property 7: Verification wait computation`
    - File: `eval/tests/test_wait_computation.py`
    - **Validates: Requirements 6.2**

  - [x] 10.3 Write unit tests for task function error paths
    - Mock backend failures, verify error result shape
    - Verify partial results on creation failure (verification skipped)
    - Verify partial results on verification failure (creation bundle preserved)
    - File: `eval/tests/test_wait_computation.py`
    - _Requirements: 6.4, 6.5, 6.6_

- [x] 11. Implement calibration post-analysis
  - [x] 11.1 Implement `eval/calibration.py` — post-experiment analysis
    - `compute_calibration(case_results: list[dict]) -> dict`
    - Compute: calibration_accuracy, mean_absolute_error, high_score_confirmation_rate, low_score_failure_rate, verdict_distribution
    - Read verifiability_score from creation_bundle, verdict from verification_result
    - Port logic from existing `calibration_eval.compute_calibration_metrics()`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [x] 11.2 Write property test for calibration metrics (Property 8)
    - **Property 8: Calibration metrics correctness**
    - Generate random case result lists with scores and verdicts
    - Verify all 5 metrics are mathematically correct
    - Tag: `# Feature: strands-evals-migration, Property 8: Calibration metrics correctness`
    - File: `eval/tests/test_calibration.py`
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

  - [x] 11.3 Write unit tests for calibration edge cases
    - Test: all cases same verdict, zero qualifying cases, all errors, single case
    - File: `eval/tests/test_calibration.py`
    - _Requirements: 8.1–8.5_

- [x] 12. Implement experiment runner and CLI
  - [x] 12.1 Implement `eval/run_eval.py` — CLI entry point
    - `parse_args()` — same flags as current `unified_eval.py` plus `--local-backup`
    - `build_evaluators(tier)` — compose evaluator sets based on tier
    - `build_report(args, reports, calibration_scores)` — assemble report dict
    - `print_summary(report)` — stdout summary matching current format
    - `main()` — load cases → auth → build experiment → run → calibration → report → cleanup
    - DDB is primary store; local JSON only with `--local-backup`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 13.9, 13.10_

  - [x] 12.2 Write property test for report format (Property 9)
    - **Property 9: Report format completeness and aggregate correctness**
    - Generate random evaluator results
    - Verify report structure: run_metadata keys, creation_scores/verification_scores as mean aggregates, case_results count
    - Tag: `# Feature: strands-evals-migration, Property 9: Report format completeness and aggregate correctness`
    - File: `eval/tests/test_report.py`
    - **Validates: Requirements 9.2, 9.3, 9.4**

  - [x] 12.3 Write unit tests for CLI and tier composition
    - Verify all CLI flags are accepted and defaults are correct
    - Verify smoke/smoke+judges/full evaluator sets contain expected evaluators
    - File: `eval/tests/test_cli.py`
    - _Requirements: 7.1, 7.2, 7.3, 13.1–13.8_

- [x] 13. Checkpoint — core pipeline
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Adapt report store
  - [x] 14.1 Adapt `eval/report_store.py` for SDK report format
    - Update `write_report()` to accept new report shape (creation_scores, verification_scores, calibration_scores top-level keys)
    - Preserve `list_reports()` and `get_report()` read interfaces
    - Preserve PK=AGENT#unified, SK=timestamp schema
    - Preserve Float/Decimal conversion and item splitting logic
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 14.2 Write unit tests for report store adaptation
    - Verify DDB item shape with new report format
    - Verify split logic for large items
    - Verify `list_reports()` and `get_report()` still work
    - File: `eval/tests/test_report.py`
    - _Requirements: 9.1, 9.5, 9.6_

- [x] 15. Implement baseline comparison
  - [x] 15.1 Create baseline comparison script
    - Run old `unified_eval.py` on smoke subset (12 cases) — record scores
    - Run new SDK pipeline on same smoke subset — record scores
    - Produce comparison report: per-evaluator score differences
    - Tolerance: exact match for deterministic, ±0.05 for LLM judges
    - Report migration as validated when all within tolerance
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [x] 15.2 Write property test for baseline comparison logic (Property 10)
    - **Property 10: Baseline comparison validation logic**
    - Generate random score pairs
    - Verify tolerance logic (0.0 for deterministic, ±0.05 for LLM judges)
    - Verify validation decision
    - Tag: `# Feature: strands-evals-migration, Property 10: Baseline comparison validation logic`
    - File: `eval/tests/test_comparison.py`
    - **Validates: Requirements 12.3, 12.4**

- [x] 16. Checkpoint — baseline comparison
  - Ensure all tests pass, ask the user if questions arise.

- [x] 17. Delete old code
  - [x] 17.1 Delete old eval runner files
    - Delete: `eval/creation_eval.py`, `eval/verification_eval.py`, `eval/calibration_eval.py`, `eval/compare_runs.py`, `eval/analyze_v3_scores.py`, `eval/inject_v3_fields.py`, `eval/reshape_v4.py`, `eval/validate_v4.py`, `eval/debug_loader.py`, `eval/test_new_evaluators.py`, `eval/update_subjective_ground_truth.py`
    - Delete `eval/unified_eval.py`
    - _Requirements: 11.1_

  - [x] 17.2 Delete old evaluator files
    - Delete all 19 files in `eval/evaluators/` (the old flat evaluator implementations)
    - Preserve `eval/evaluators/creation/` and `eval/evaluators/verification/` (new SDK evaluators)
    - Clean up `eval/evaluators/__init__.py` to only export new SDK evaluator packages
    - _Requirements: 11.2_

  - [x] 17.3 Delete old Streamlit dashboard
    - Delete `eval/dashboard/` directory
    - _Requirements: 11.3_

  - [x] 17.4 Verify preserved files
    - Confirm retained: `eval/golden_dataset.json`, `eval/dynamic_golden_dataset.json`, `eval/generate_dynamic_dataset.py`, `eval/dataset_merger.py`, `eval/report_store.py`, `eval/backends/`, `eval/reports/`, `eval/validate_dataset.py`, `eval/score_history.json`
    - _Requirements: 11.4, 11.5_

- [x] 18. Full baseline run
  - [x] 18.1 Run full eval with new SDK pipeline
    - Execute: `/home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py --tier full --description "SDK migration baseline" --dynamic-dataset eval/dynamic_golden_dataset.json`
    - Verify report written to DDB
    - Record as new baseline
    - _Requirements: 7.3, 9.1_

- [x] 19. Documentation
  - [x] 19.1 Write decision log entry 151
    - Document the Strands Evals SDK migration decision
    - _Requirements: N/A (documentation)_

  - [x] 19.2 Write project update 39
    - Document the migration completion
    - _Requirements: N/A (documentation)_

  - [x] 19.3 Update eval deep dive doc
    - Update `docs/eval-framework-deep-dive.md` to reflect SDK-based architecture
    - _Requirements: N/A (documentation)_

- [x] 20. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass. Dashboard adaptation is tracked in Spec B (`strands-evals-dashboard`).

## Notes

- Property tests are REQUIRED (not optional) — eval correctness is critical
- Each property test is tagged: `# Feature: strands-evals-migration, Property N: <title>`
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Backends (agentcore_backend.py, verification_backend.py) are PRESERVED unchanged
- DDB is the primary report store. Local JSON only with `--local-backup` flag
- This is a CLEAN BREAK — old code is deleted, no backward compatibility
- `agentcore launch` and `agentcore invoke` require TTY — user runs those manually
- Checkpoints ensure incremental validation throughout the migration
