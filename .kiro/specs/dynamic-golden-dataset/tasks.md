# Implementation Plan: Dynamic Golden Dataset

## Overview

Build a generator script that produces time-anchored predictions with computed ground truth, a dataset merger for combining static and dynamic datasets, and integrate both into the existing eval runners. All code is Python, tested with hypothesis property-based tests.

## Tasks

- [x] 1. Static dataset migration and core data models
  - [x] 1.1 Add `time_sensitive: true` flag to base-010 in `eval/golden_dataset.json`
    - Add `"time_sensitive": true` to the base-010 prediction object (full moon prediction)
    - Verify no other fields are changed and the file remains valid JSON
    - _Requirements: 6.4, 6.5_

  - [x] 1.2 Create `eval/dataset_merger.py` with `load_and_merge()` and `merge_datasets()`
    - Implement `load_and_merge(static_path, dynamic_path=None)` — returns static-only when dynamic_path is None
    - Implement `merge_datasets(static_path, dynamic_path)` — loads both, builds `replaces` index from dynamic predictions, filters static predictions with `time_sensitive: true` that have dynamic replacements, concatenates remaining static + all dynamic
    - Handle errors: dynamic file not found, invalid JSON, missing `base_predictions`
    - _Requirements: 7.1, 7.2, 7.3, 7.5_

  - [ ]* 1.3 Write property tests for dataset merger (Properties 11, 12, 13, 14)
    - **Property 11: Time-sensitive exclusion in merge** — For any static dataset with a `time_sensitive: true` prediction and a dynamic dataset with a matching `replaces` field, the merged result must exclude the static prediction.
    - **Validates: Requirements 6.3**
    - **Property 12: Merge precedence and deduplication** — For any static/dynamic pair where dynamic has `replaces` pointing to a static ID, merged dataset contains the dynamic prediction and excludes the replaced static; all other static predictions preserved.
    - **Validates: Requirements 7.2**
    - **Property 13: Backward compatibility** — For any static dataset, `load_and_merge(static_path, None)` returns a dataset identical to `load_dataset(static_path)`.
    - **Validates: Requirements 7.3**
    - **Property 14: ID prefix convention** — For any merged dataset, all dynamic-origin predictions have IDs starting with `dyn-`, all static-origin predictions retain their original IDs.
    - **Validates: Requirements 7.5**

- [x] 2. Checkpoint — Ensure merger tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Generator script — core framework and deterministic templates
  - [x] 3.1 Create `eval/generate_dynamic_dataset.py` with main entry point and template registry
    - Implement `main()` that instantiates templates, collects predictions, validates, and writes output
    - Implement `get_all_templates()` returning list of template callables
    - Implement `brave_search(query, count=5)` using the Brave Search API pattern from `calleditv4-verification/src/brave_search.py` (HTTP GET with `BRAVE_API_KEY` env var)
    - Implement `validate_dynamic_dataset(dataset)` checking schema 4.0 rules, non-null verdicts, valid enums, `generated_at` in metadata, `ground_truth_computation` in each prediction
    - Implement `write_dataset(dataset, path)` writing validated JSON
    - Template function signature: `template_name(now: datetime, brave_fn: Callable | None) -> dict | None`
    - If Brave API key is missing or API fails, set `brave_fn=None` and skip brave_search templates
    - Exit with code 1 on validation failure, print errors to stderr
    - _Requirements: 1.1, 1.2, 1.4, 1.6, 1.7, 8.1, 8.2_

  - [x] 3.2 Implement deterministic immediate-mode templates (>= 3 templates)
    - Template: weekday check ("Today is a weekday") — uses `calendar.weekday()`, verdict based on Mon-Fri
    - Template: current year parity ("The current year is even/odd") — uses `now.year % 2`
    - Template: current month has 31 days — uses `calendar.monthrange()`
    - Each template returns a full prediction dict with `ground_truth_computation` audit trail
    - ID convention: `dyn-imm-001`, `dyn-imm-002`, `dyn-imm-003`
    - At least 1 confirmed and 1 refuted across the set (design templates to guarantee this)
    - _Requirements: 2.1, 2.2, 2.4, 2.6, 9.1, 9.3_

  - [x] 3.3 Implement deterministic at_date-mode templates (>= 1 deterministic + brave templates in 4.2)
    - Template: day-of-week for yesterday ("Yesterday was a [day]") — uses `now - timedelta(days=1)` and `calendar.day_name`
    - Template: yesterday was a weekend day — deterministic check
    - Set `verification_date` to yesterday (within 24-72 hours of generation)
    - Verify `verification_date` is in the past relative to `generated_at`
    - _Requirements: 3.1, 3.2, 3.5, 3.6, 9.1, 9.3_

  - [x] 3.4 Implement deterministic before_date-mode templates (>= 1 deterministic + brave templates in 4.3)
    - Template: full moon occurred before [recent date] — lunar cycle math (replaces base-010 via `replaces: "base-010"`)
    - Template: solstice/equinox occurred before [date] — astronomical calculation
    - Set `verification_date` (deadline) to a date in the recent past (1-7 days)
    - _Requirements: 4.1, 4.2, 4.4, 4.6, 9.1, 9.3_

  - [ ]* 3.5 Write property tests for generator output (Properties 1, 2, 3, 8)
    - **Property 1: Generator output round-trip** — For any generator invocation, the produced JSON is loadable by `load_dataset()` and contains valid `base_predictions` array and `metadata` with `generated_at`.
    - **Validates: Requirements 1.2, 1.4**
    - **Property 2: Non-null verdict invariant** — For any prediction in a generated dataset, `expected_verification_outcome` is non-null and one of `confirmed`, `refuted`, `inconclusive`.
    - **Validates: Requirements 1.3, 8.4**
    - **Property 3: Valid enum fields** — For any prediction, `verification_mode` is one of the four allowed values; `ground_truth_source` is one of `deterministic`, `brave_search`, `api_lookup`; `difficulty` is one of `easy`, `medium`, `hard`.
    - **Validates: Requirements 1.5, 8.5**
    - **Property 8: Auditability completeness** — For any prediction, `ground_truth.ground_truth_computation` contains `source`, `raw_data`, `computation_logic`, `computed_at`. When `ground_truth_source` is `deterministic`, `raw_data` contains computation inputs.
    - **Validates: Requirements 9.1, 9.2, 9.3**

- [x] 4. Generator script — Brave Search templates and remaining modes
  - [x] 4.1 Implement brave_search immediate-mode templates
    - Template: "The current US President is [name]" — Brave search for current president, set verdict based on match
    - Template: "Python 3.13 has been released" — Brave search for Python latest version
    - Each template returns `None` when `brave_fn` is None (graceful degradation)
    - Record Brave query string and relevant snippet in `ground_truth_computation.raw_data`
    - _Requirements: 2.1, 2.3, 2.5, 9.1, 9.2_

  - [x] 4.2 Implement brave_search at_date-mode templates
    - Template: yesterday's weather or sports result — Brave search for historical data
    - At least 1 template producing `confirmed` and 1 producing `refuted`
    - _Requirements: 3.1, 3.3, 3.4, 3.6, 9.1, 9.2_

  - [x] 4.3 Implement brave_search before_date-mode templates
    - Template: specific event occurred before deadline — Brave search for event date
    - At least 1 template producing `confirmed` and 1 producing `refuted`
    - _Requirements: 4.1, 4.3, 4.5, 4.6, 9.1, 9.2_

  - [x] 4.4 Implement recurring-mode templates (all brave_search, >= 3)
    - Template: "US national debt exceeds $35 trillion" — Brave search for current value
    - Template: "Bitcoin price is above $10,000" — Brave search for current price
    - Template: website accessibility check or similar current-state check
    - Set `recurring_interval` on each prediction
    - Include queried current value in `ground_truth.ground_truth_computation.raw_data`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 9.1, 9.2_

  - [ ]* 4.5 Write property tests for Brave degradation and mode counts (Properties 4, 5, 9)
    - **Property 4: Graceful Brave API degradation** — When Brave API is mocked to fail, generator produces a valid dataset with only `deterministic` ground_truth_source predictions, no `brave_search` predictions.
    - **Validates: Requirements 1.7**
    - **Property 5: Minimum prediction count per mode** — With Brave API available, each mode has >= 3 predictions.
    - **Validates: Requirements 2.1, 3.1, 4.1, 5.1**
    - **Property 9: Recurring prediction completeness** — For any recurring prediction, `recurring_interval` is non-null string and `raw_data` contains the queried current value.
    - **Validates: Requirements 5.4, 5.5**

- [x] 5. Checkpoint — Ensure generator and property tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Prediction quality and diversity
  - [x] 6.1 Ensure difficulty and domain diversity across all templates
    - Verify predictions span at least 3 difficulty levels (easy, medium, hard)
    - Verify predictions span at least 4 domain categories in `dimension_tags.domain`
    - Ensure at least 2 predictions per mode require `brave_web_search` for verification
    - Ensure at least 2 predictions per mode have expected verdict `refuted`
    - Ensure all predictions have staleness windows > 2 hours
    - Avoid paywalled, login-gated, or rate-limited sources
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [ ]* 6.2 Write property tests for diversity (Properties 6, 7, 15)
    - **Property 6: Verdict distribution balance per mode** — Each of immediate, at_date, before_date modes has at least 1 `confirmed` and 1 `refuted` prediction.
    - **Validates: Requirements 2.6, 3.6, 4.6, 10.4**
    - **Property 7: Verification dates in valid temporal range** — at_date predictions have `verification_date` in the past within 72 hours; before_date predictions have deadline in the past within 7 days.
    - **Validates: Requirements 3.2, 3.5, 4.2**
    - **Property 15: Difficulty and domain diversity** — Generated dataset includes at least easy/medium/hard difficulties and >= 4 domain values.
    - **Validates: Requirements 10.1, 10.2**

- [x] 7. Eval runner integration
  - [x] 7.1 Add `--dynamic-dataset` CLI argument to all three eval runners
    - Add `--dynamic-dataset` optional argument to `verification_eval.py`, `creation_eval.py`, `calibration_eval.py`
    - Replace `load_dataset(args.dataset)` calls with `load_and_merge(args.dataset, args.dynamic_dataset)`
    - Import `load_and_merge` from `eval.dataset_merger`
    - When `--dynamic-dataset` is not provided, behavior is identical to today (backward compatible)
    - _Requirements: 7.1, 7.3_

  - [x] 7.2 Add `dataset_sources` to eval report metadata
    - Include `dataset_sources` field in each eval runner's report `run_metadata` listing the file paths used
    - When only static dataset is used, list just that path
    - When both are used, list both paths
    - _Requirements: 7.4, 9.4_

  - [ ]* 7.3 Write property test for report metadata (Property 16)
    - **Property 16: Report metadata includes dataset sources** — For any eval run using merged datasets, `run_metadata` contains `dataset_sources` listing all dataset file paths used.
    - **Validates: Requirements 7.4, 9.4**

- [x] 8. Validation extension
  - [x] 8.1 Extend `eval/validate_dataset.py` to support dynamic dataset validation
    - Accept dynamic dataset file path as argument
    - Relaxed coverage requirements for dynamic datasets (smaller, don't need 12+ per category)
    - Additional checks: `generated_at` in metadata, `ground_truth_computation` in each prediction, non-null `expected_verification_outcome` for all predictions
    - Same structural checks for prediction fields (valid enums, required fields)
    - _Requirements: 8.1, 8.3, 8.4, 8.5_

  - [ ]* 8.2 Write property test for static dataset immutability (Property 10)
    - **Property 10: Static dataset immutability** — For any generator invocation, `eval/golden_dataset.json` is byte-identical before and after generation.
    - **Validates: Requirements 6.2**

- [x] 9. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- All code is Python, using `/home/wsluser/projects/calledit/venv/bin/python`
- Property-based tests use `hypothesis` (already installed in venv)
- Test file: `eval/tests/test_dynamic_dataset.py`
- Each property test references a specific correctness property from the design document
- Brave Search pattern follows `calleditv4-verification/src/brave_search.py` (HTTP GET with `BRAVE_API_KEY`)
- Checkpoints ensure incremental validation between major phases
