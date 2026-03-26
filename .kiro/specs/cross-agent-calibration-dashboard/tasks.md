# Implementation Plan: Cross-Agent Calibration Dashboard

## Overview

Three components delivered incrementally: (1) DDB Report Store as the shared foundation, (2) backfill existing runners + historical reports, (3) Calibration Runner chaining creation→verification, (4) React Dashboard reading from DDB. Each task builds on the previous — no orphaned code.

## Tasks

- [ ] 1. Implement DDB Report Store (`eval/report_store.py`)
  - [ ] 1.1 Create `eval/report_store.py` with `_ensure_table_exists()`, `_float_to_decimal()`, `_decimal_to_float()`, and `write_report()`
    - Auto-create `calledit-v4-eval-reports` table (PAY_PER_REQUEST, PK=S, SK=S)
    - `write_report(agent_type, report)` writes with PK=`AGENT#{agent_type}`, SK=ISO timestamp from `run_metadata.timestamp`
    - Float→Decimal conversion on write, handle NaN/Inf by replacing with None
    - Handle >400KB items by splitting `case_results` to separate item with SK=`{timestamp}#CASES`
    - _Requirements: 11.1, 11.4, 11.5_

  - [ ] 1.2 Implement `list_reports()` and `get_report()`
    - `list_reports(agent_type)` queries PK, returns `run_metadata` + `aggregate_scores` only (ProjectionExpression excludes `case_results`), sorted by timestamp descending
    - `get_report(agent_type, timestamp)` fetches full report including `case_results`, reassembles split items if `#CASES` item exists
    - Decimal→float conversion on read
    - _Requirements: 11.2, 11.3, 11.5_

  - [ ] 1.3 Implement `backfill_from_files(directory)`
    - Read all `eval/reports/*.json` files, detect agent_type from filename pattern (`creation-eval-*`, `verification-eval-*`, `calibration-eval-*`) or `run_metadata.agent`
    - Idempotent: skip items that already exist via conditional put
    - Return `{"imported": N, "skipped": M, "errors": [...]}`
    - _Requirements: 12.4_

  - [ ]* 1.4 Write property test: Float↔Decimal round trip (Property 2)
    - **Property 2: Float↔Decimal round trip preserves values**
    - Generate nested dicts/lists with random floats, verify `_decimal_to_float(_float_to_decimal(obj))` preserves values within 1e-10
    - Use Hypothesis with `@settings(max_examples=100)`
    - Test file: `eval/tests/test_report_store.py`
    - **Validates: Requirements 11.5**

  - [ ]* 1.5 Write property test: list_reports excludes case_results (Property 3)
    - **Property 3: list_reports excludes case_results**
    - Generate reports, write them, verify `list_reports()` results never contain `case_results`
    - Test file: `eval/tests/test_report_store.py`
    - **Validates: Requirements 11.2**

  - [ ]* 1.6 Write property test: Backfill idempotency (Property 4)
    - **Property 4: Backfill idempotency**
    - Create temp directory with valid report JSON files, call `backfill_from_files()` twice, verify second call imports zero new items
    - Test file: `eval/tests/test_report_store.py`
    - **Validates: Requirements 12.4**

  - [ ]* 1.7 Write property test: Report write/read round trip (Property 1)
    - **Property 1: Report write/read round trip**
    - Generate valid eval reports, write via `write_report()`, read back via `get_report()`, verify equivalence within float precision
    - Test file: `eval/tests/test_report_store.py`
    - **Validates: Requirements 11.1, 11.3, 11.5**

- [ ] 2. Backfill existing eval runners to write to DDB
  - [ ] 2.1 Update `eval/creation_eval.py` to call `report_store.write_report("creation", report)` after `save_report()`
    - Fire-and-forget: catch all exceptions, log warning, never abort the eval run
    - Import `report_store` inside try/except to handle ImportError gracefully
    - _Requirements: 12.1, 12.3_

  - [ ] 2.2 Update `eval/verification_eval.py` to call `report_store.write_report("verification", report)` after `save_report()`
    - Same fire-and-forget pattern as creation runner
    - _Requirements: 12.2, 12.3_

- [ ] 3. Checkpoint — Verify report store and backfill
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Implement Calibration Runner (`eval/calibration_eval.py`)
  - [ ] 4.1 Create `eval/calibration_eval.py` with CLI, dataset loading, and dry-run
    - CLI: `--tier` (smoke/full), `--description`, `--dry-run`, `--case`
    - Load golden dataset, filter qualifying cases (expected_verification_outcome + verification_mode=immediate)
    - Smoke tier uses smoke_test subset, full uses all qualifying
    - Dry-run prints cases without invoking agents
    - Fail with clear error if Cognito or AWS credentials missing
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6_

  - [ ] 4.2 Implement `classify_score_tier()`, `is_calibration_correct()`, and `compute_calibration_metrics()`
    - Score tier: high (≥0.7), moderate (≥0.4), low (<0.4)
    - Calibration correct: high→confirmed, low→refuted/inconclusive, moderate→always correct
    - Metrics: calibration_accuracy, mean_absolute_error, high_score_confirmation_rate, low_score_failure_rate, verdict_distribution
    - _Requirements: 2.3, 2.4_

  - [ ] 4.3 Implement `run_calibration()` — creation→verification pipeline per case
    - Reuse AgentCoreBackend (JWT) and VerificationBackend (SigV4)
    - Per case: invoke creation backend → extract verifiability_score → write temp bundle to eval table → invoke verification backend → collect verdict + confidence
    - Record `creation_error` or `verification_error` per case on failure, continue to next case
    - Track creation_duration_seconds and verification_duration_seconds per case
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ] 4.4 Implement eval table lifecycle and report generation
    - Setup: write shaped bundles to `calledit-v4-eval` table (reuse pattern from verification_eval.py)
    - Cleanup: delete all temp items after run completes, regardless of individual case success/failure
    - Build calibration report with run_metadata (all 12 fields), aggregate_scores, case_results, bias_warning
    - Write to DDB via `report_store.write_report("calibration", report)` + save local JSON backup
    - Print summary table to stdout
    - _Requirements: 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 3.5_

  - [ ]* 4.5 Write property test: Score tier classification (Property 6)
    - **Property 6: Score tier classification consistency**
    - Generate random floats in [0.0, 1.0], verify tier boundaries are exhaustive and mutually exclusive
    - Test file: `eval/tests/test_calibration_eval.py`
    - **Validates: Requirements 2.3, 2.4**

  - [ ]* 4.6 Write property test: Calibration accuracy metric correctness (Property 7)
    - **Property 7: Calibration accuracy metric correctness**
    - Generate random case results with score_tiers and verdicts, verify calibration_accuracy = proportion where is_calibration_correct returns True, and MAE = avg |score - binary_outcome|
    - Test file: `eval/tests/test_calibration_eval.py`
    - **Validates: Requirements 2.3**

  - [ ]* 4.7 Write property test: Calibration report schema completeness (Property 5)
    - **Property 5: Calibration report schema completeness**
    - Generate random case results with varying scores/verdicts/errors, verify output report contains all required fields
    - Test file: `eval/tests/test_calibration_eval.py`
    - **Validates: Requirements 2.2, 2.3, 2.4**

  - [ ]* 4.8 Write property test: Tier case filtering (Property 14)
    - **Property 14: Tier case filtering**
    - Generate random case lists with smoke_test flags, verify smoke returns only smoke_test=True cases, full returns all qualifying, smoke ⊆ full
    - Test file: `eval/tests/test_calibration_eval.py`
    - **Validates: Requirements 3.1**

- [ ] 5. Checkpoint — Verify calibration runner
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Set up React Dashboard infrastructure
  - [ ] 6.1 Add dependencies and configure routing in `frontend-v4`
    - Add `react-router-dom`, `recharts`, `@aws-sdk/client-dynamodb`, `@aws-sdk/lib-dynamodb` to `frontend-v4/package.json`
    - Update `frontend-v4/src/App.tsx` to use BrowserRouter with Routes: `/` for existing AppContent, `/eval` for EvalDashboard
    - _Requirements: 4.1_

  - [ ] 6.2 Create DDB service module and TypeScript types
    - Create `frontend-v4/src/services/dynamodb.ts` — DDB DocumentClient singleton using Cognito credentials from existing AuthContext
    - Create `frontend-v4/src/pages/EvalDashboard/types.ts` — RunMetadata, ReportSummary, FullReport, CaseResult interfaces
    - _Requirements: 4.6_

  - [ ] 6.3 Create `useReportStore` hook
    - Create `frontend-v4/src/pages/EvalDashboard/hooks/useReportStore.ts`
    - `listReports(agentType)` — Query PK=`AGENT#{agentType}`, ProjectionExpression excludes case_results, sort descending
    - `getReport(agentType, timestamp)` — GetItem with PK+SK, reassemble split case_results if #CASES item exists
    - _Requirements: 4.3, 4.4, 4.5_

  - [ ] 6.4 Create utility functions
    - Create `frontend-v4/src/pages/EvalDashboard/utils.ts`
    - `getScoreColor(score)`: green ≥0.8, yellow ≥0.5, red <0.5
    - `truncateText(text, maxLen=60)`: truncate with "..." suffix
    - `formatRunLabel(metadata)`: "timestamp | agent | tier | description"
    - `verdictToNumeric(verdict)`: confirmed→1.0, inconclusive→0.5, refuted→0.0
    - `diffPromptVersions(a, b)`: returns set of changed keys
    - _Requirements: 5.1, 6.1, 6.2, 8.2_

- [ ] 7. Implement Dashboard shared components
  - [ ] 7.1 Create `EvalDashboard/index.tsx` with three tabs
    - Main page component with tab navigation: "Creation Agent", "Verification Agent", "Cross-Agent Calibration"
    - Each tab queries the correct PK via `useReportStore`
    - Display run metadata panel (description, prompt_versions, model_id, git_commit, run_tier, dataset_version, duration_seconds, case_count) when a run is selected
    - Data-driven: tabs render based on available agent types
    - _Requirements: 4.1, 4.2, 5.2_

  - [ ] 7.2 Create `RunSelector` component
    - Dropdown showing available runs formatted as `timestamp | agent | tier | description`
    - Sorted by timestamp descending (newest first)
    - Supports multi-select mode for comparison
    - Filter by `run_tier`
    - _Requirements: 5.1, 5.4, 9.1, 9.3_

  - [ ] 7.3 Create `AggregateScores` component
    - Renders all keys from `aggregate_scores` dynamically as color-coded bars
    - Green ≥0.8, yellow ≥0.5, red <0.5
    - Handles nested objects (e.g., verdict_distribution) gracefully
    - _Requirements: 6.1, 7.1, 8.1_

  - [ ] 7.4 Create `WarningBanner` component
    - Displays `ground_truth_limitation` and/or `bias_warning` from run metadata
    - Only renders when fields are non-empty strings
    - _Requirements: 5.3, 7.3, 8.4_

  - [ ] 7.5 Create `CaseTable` and `CaseDetail` components
    - `CaseTable`: data-driven columns derived from first case result's `scores` keys
    - Columns: case ID, input/prediction text (truncated to 60 chars), per-evaluator score with pass/fail indicator
    - Click row to expand inline `CaseDetail` panel; click again to collapse
    - `CaseDetail`: full input text, all evaluator scores with reason text, full error message for error cases
    - Error cases shown with distinct visual indicator
    - _Requirements: 6.2, 6.3, 7.2, 8.3, 8.5, 10.1, 10.2, 10.3_

- [ ] 8. Implement Dashboard tab-specific components
  - [ ] 8.1 Create `CalibrationScatter` component
    - Recharts scatter plot: verifiability_score (x-axis) vs verification outcome numeric (y-axis: 1.0/0.5/0.0)
    - Each case as a labeled point with hover tooltip
    - Exclude error cases from plot
    - _Requirements: 8.2_

  - [ ] 8.2 Create `TrendChart` component
    - Recharts line chart for multi-run comparison
    - Overlay aggregate scores across selected runs ordered by timestamp
    - User selects which metrics to plot from available keys
    - _Requirements: 9.2_

  - [ ] 8.3 Create `PromptVersionDiff` component
    - Highlights changed prompt versions between compared runs
    - Shows keys where values differ, including keys present in one but not the other
    - _Requirements: 9.4_

- [ ] 9. Checkpoint — Verify dashboard components
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Dashboard tests
  - [ ]* 10.1 Write property tests for dashboard utilities (Properties 9, 10, 11, 12, 13, 15, 16, 17)
    - **Property 9: Run selector format contains all components** — generate random metadata, verify formatted string contains timestamp, agent, tier, description
    - **Property 10: Run selector sorted by timestamp descending** — generate random timestamp lists, verify descending sort
    - **Property 11: Score color coding** — generate random scores in [0.0, 1.0], verify green ≥0.8, yellow ≥0.5, red <0.5
    - **Property 12: Text truncation preserves prefix** — generate random strings, verify length ≤63, prefix preserved, strings ≤60 unchanged
    - **Property 13: Verdict-to-numeric mapping** — verify confirmed→1.0, inconclusive→0.5, refuted→0.0
    - **Property 15: Run tier filtering** — generate random report lists, verify filter returns only matching run_tier
    - **Property 16: Prompt version diff correctness** — generate random version dict pairs, verify diff returns exactly the changed keys
    - **Property 17: Warning banner display** — generate random metadata, verify banner renders iff limitation/warning fields are non-empty
    - Test file: `frontend-v4/src/pages/EvalDashboard/__tests__/utils.test.ts`
    - **Validates: Requirements 5.1, 5.3, 5.4, 6.1, 6.2, 8.2, 9.3, 9.4**

  - [ ]* 10.2 Write property test: Tab-to-agent-type mapping (Property 8)
    - **Property 8: Tab-to-agent-type mapping**
    - Verify bijective mapping: "Creation Agent"→`AGENT#creation`, "Verification Agent"→`AGENT#verification`, "Cross-Agent Calibration"→`AGENT#calibration`
    - Test file: `frontend-v4/src/pages/EvalDashboard/__tests__/index.test.tsx`
    - **Validates: Requirements 4.3, 4.4, 4.5**

- [ ] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Python tests use Hypothesis with `@settings(max_examples=100)`
- React tests use Vitest (already configured in frontend-v4)
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Dependencies tracked in `requirements.txt` (Python) and `frontend-v4/package.json` (React)
