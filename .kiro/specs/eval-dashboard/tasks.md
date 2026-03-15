# Implementation Plan: Eval Dashboard

## Overview

Build a local Streamlit dashboard for exploring CalledIt eval results. Extend the eval runner to write `report_summary` and `test_result` records to DDB, implement a unified data loader (DDB primary, local fallback), and create 6 interactive pages: Trends, Heatmap, Prompt Correlation, Reasoning Explorer, Coherence View, and Fuzzy Convergence. All property-based tests use Hypothesis.

## Tasks

- [ ] 1. Extend EvalReasoningStore with new record types
  - [ ] 1.1 Add `write_report_summary()` and `write_test_result()` methods to `eval_reasoning_store.py`
    - `write_report_summary()` writes a `report_summary#SUMMARY` record with: timestamp, prompt_version_manifest, dataset_version, schema_version, architecture, model_config, per_agent_aggregates, per_category_accuracy, overall_pass_rate, total_tests, passed, failed, duration_s
    - `write_test_result(test_case_id, ...)` writes a `test_result#{test_case_id}` record with: test_case_id, layer, difficulty, expected_category, evaluator_scores, error, duration_s
    - Both use the existing fire-and-forget `_put_item` pattern with 90-day TTL
    - _Requirements: 9.1, 9.2_

  - [ ] 1.2 Update `write_run_metadata()` to write `report_summary#SUMMARY` instead of `run_metadata#SUMMARY`
    - Change the record_key from `run_metadata#SUMMARY` to `report_summary#SUMMARY`
    - Add the additional fields: architecture (default "serial"), model_config (default {}), per_agent_aggregates, per_category_accuracy, passed, failed
    - Old `run_metadata#SUMMARY` records expire via existing 90-day TTL
    - _Requirements: 9.1, 9.2_

  - [ ] 1.3 Update `eval_runner.py` to write `test_result` records during evaluation
    - After each test case is scored, call `reasoning_store.write_test_result()` with the per-test-case score dict
    - Pass the full report dict to an updated `write_report_summary()` call at the end of the run (replacing the existing `write_run_metadata()` call)
    - _Requirements: 9.1, 9.2_

- [ ] 2. Checkpoint — Eval runner DDB extension
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Install dependencies and set up dashboard project structure
  - [ ] 3.1 Add `streamlit` and `plotly` to root `requirements.txt` as dev dependencies
    - Add `streamlit>=1.30.0` and `plotly>=5.18.0` to `requirements.txt`
    - User should run: `/home/wsluser/projects/calledit/venv/bin/pip install -r requirements.txt`
    - _Requirements: 10.1_

  - [ ] 3.2 Create dashboard directory structure and entry point
    - Create `eval/dashboard/` directory with `__init__.py`
    - Create `eval/dashboard/app.py` — Streamlit entry point that loads data, renders sidebar, dispatches to selected page
    - Create `eval/dashboard/sidebar.py` — run selector, comparison selector, layer/category/dataset_version filters stored in `st.session_state`
    - Create `eval/dashboard/pages/` directory with `__init__.py`
    - _Requirements: 10.1, 8.1, 8.3_

- [ ] 4. Implement unified data loader (`eval/dashboard/data_loader.py`)
  - [ ] 4.1 Implement `EvalDataLoader` class with DDB-primary, local-fallback pattern
    - Constructor: initialize boto3 DDB client (catch import/connection errors gracefully), set local file paths
    - `is_ddb_available()`: returns True if DDB connection was established
    - `load_all_runs()`: query all `report_summary#SUMMARY` records from DDB; fallback to `score_history.json`; cache with `@st.cache_data`
    - `load_run_detail(eval_run_id)`: query all `test_result#{test_case_id}` records for a run; fallback to matching `eval/reports/eval-*.json` file
    - `load_agent_outputs(eval_run_id, test_case_id)`: query `agent_output#{test_case_id}` from DDB (no local fallback)
    - `load_judge_reasoning(eval_run_id, test_case_id)`: query `judge_reasoning#{test_case_id}#*` from DDB (no local fallback)
    - `load_token_counts(eval_run_id, test_case_id)`: query `token_counts#{test_case_id}` from DDB (no local fallback)
    - Handle optional fields: default `architecture` to "serial", `model_config` to {}, `dataset_version` to ""
    - Clamp score values outside [0, 1] to [0, 1] for display, log warning
    - Skip malformed local report files (invalid JSON or missing required fields), log warning
    - Show banner when DDB unavailable: "DDB unavailable — using local data. Reasoning traces not available."
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 6.1, 6.2, 6.4_

  - [ ] 4.2 Implement `compare_runs(run_a, run_b)` method on `EvalDataLoader`
    - Identify prompt keys where versions differ between two manifests
    - Compute category deltas (current minus previous for every category in either run)
    - Flag dataset_version mismatch
    - Return comparison dict with overall_pass_rate delta, category_deltas, changed_prompts, has_regression flag
    - _Requirements: 3.1, 3.2, 8.2_

  - [ ]* 4.3 Write property test: Trend data transformation preserves all run data
    - **Property 1: Trend data transformation preserves all run data**
    - **Validates: Requirements 1.1, 1.2, 1.3**

  - [ ]* 4.4 Write property test: Run comparison correctly identifies prompt changes and computes category deltas
    - **Property 5: Run comparison correctly identifies prompt changes and computes category deltas**
    - **Validates: Requirements 3.1, 3.2**

  - [ ]* 4.5 Write property test: Optional report fields default correctly when absent
    - **Property 8: Optional report fields default correctly when absent**
    - **Validates: Requirements 6.1, 6.2, 6.4**

  - [ ]* 4.6 Write property test: Filtering by architecture or dataset version returns only matching runs
    - **Property 9: Filtering by architecture or dataset version returns only matching runs**
    - **Validates: Requirements 6.3, 8.3**

  - [ ]* 4.7 Write property test: Dataset version mismatch detection
    - **Property 11: Dataset version mismatch detection**
    - **Validates: Requirements 8.2**

  - [ ]* 4.8 Write property test: Data loading preserves all fields from valid JSON
    - **Property 12: Data loading preserves all fields from valid JSON**
    - **Validates: Requirements 9.1, 9.2**

  - [ ]* 4.9 Write property test: Malformed reports are skipped without affecting valid reports
    - **Property 13: Malformed reports are skipped without affecting valid reports**
    - **Validates: Requirements 9.4**

- [ ] 5. Checkpoint — Data loader and property tests
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement Trends page (`eval/dashboard/pages/trends.py`)
  - [ ] 6.1 Implement `render(runs: list[dict])` function
    - Plotly line chart: overall pass rate over time (x=timestamp, y=pass_rate)
    - Plotly grouped bar chart: per-category accuracy over time
    - Prompt version annotations on the trend line (show which prompts changed between runs)
    - Hover tooltips showing prompt manifest, dataset version, total tests
    - Filter integration: respect sidebar layer/category/dataset_version filters
    - _Requirements: 1.1, 1.2, 1.3, 6.3_

- [ ] 7. Implement Heatmap page (`eval/dashboard/pages/heatmap.py`)
  - [ ] 7.1 Implement `render(run_detail: dict)` function
    - Plotly heatmap: rows = test cases, columns = evaluator names, cells = scores
    - Group columns: deterministic evaluators (left) vs judge evaluators (right)
    - Color scale: 0.0 (red) → 1.0 (green) with NaN as grey
    - Sort rows by ascending average evaluator score (worst first)
    - Click-to-drill: clicking a test case row navigates to Reasoning Explorer for that case
    - _Requirements: 2.1, 2.3, 2.5_

  - [ ]* 7.2 Write property test: Heatmap matrix dimensions match source data
    - **Property 2: Heatmap matrix dimensions match source data**
    - **Validates: Requirements 2.1**

  - [ ]* 7.3 Write property test: Evaluator column grouping separates deterministic from judge scores
    - **Property 3: Evaluator column grouping separates deterministic from judge scores**
    - **Validates: Requirements 2.3**

  - [ ]* 7.4 Write property test: Heatmap sort orders by ascending average score
    - **Property 4: Heatmap sort orders by ascending average score**
    - **Validates: Requirements 2.5**

- [ ] 8. Implement Prompt Correlation page (`eval/dashboard/pages/prompt_correlation.py`)
  - [ ] 8.1 Implement `render(run_a: dict, run_b: dict, runs: list[dict])` function
    - Side-by-side comparison of two selected runs using `compare_runs()`
    - Show prompt version diff (which prompts changed, from → to)
    - Show category delta table with color coding (green=improved, red=regressed, grey=unchanged)
    - Dataset version mismatch warning banner when versions differ
    - Overall pass rate delta with directional indicator
    - _Requirements: 3.1, 3.2, 8.2_

- [ ] 9. Implement Reasoning Explorer page (`eval/dashboard/pages/reasoning_explorer.py`)
  - [ ] 9.1 Implement `render(run_detail: dict, loader: EvalDataLoader)` function
    - Test case selector (dropdown or table with click)
    - For selected test case: show all evaluator scores in a summary table
    - Agent output viewer: display full text output from each agent in pipeline order (parser → categorizer → verification_builder → review)
    - Judge reasoning viewer: show judge reasoning text, score, and judge model for each judged agent
    - Token count display: show input/output tokens per agent
    - Graceful handling when DDB data unavailable (show scores from local report, message for missing reasoning)
    - _Requirements: 4.5, 5.3_

  - [ ]* 9.2 Write property test: Agent outputs are always ordered in pipeline sequence
    - **Property 6: Agent outputs are always ordered in pipeline sequence**
    - **Validates: Requirements 4.5**

  - [ ]* 9.3 Write property test: Agent output field extraction returns expected fields from valid JSON
    - **Property 7: Agent output field extraction returns expected fields from valid JSON**
    - **Validates: Requirements 5.3**

- [ ] 10. Implement Coherence View page (`eval/dashboard/pages/coherence.py`)
  - [ ] 10.1 Implement `render(run_detail: dict, loader: EvalDataLoader)` function
    - For each test case: show whether deterministic scores and judge scores agree
    - Highlight disagreements: cases where deterministic evaluators pass but judge scores are low (or vice versa)
    - Summary statistics: % agreement, most common disagreement patterns
    - Drill-down to reasoning for disagreement cases
    - _Requirements: 2.3, 5.3_

- [ ] 11. Implement Fuzzy Convergence page (`eval/dashboard/pages/fuzzy_convergence.py`)
  - [ ] 11.1 Implement `render(run_detail: dict)` function
    - Filter to fuzzy test cases only
    - Show round 1 scores (R1_ prefixed), round 2 scores (R2_ prefixed + Convergence), and clarification quality separately
    - Convergence visualization: bar chart comparing R1 vs R2 scores per test case
    - Highlight cases where clarification improved/degraded convergence
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 11.2 Write property test: Fuzzy score extraction correctly separates round 1 and round 2 scores
    - **Property 10: Fuzzy score extraction correctly separates round 1 and round 2 scores**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

- [ ] 12. Checkpoint — All pages implemented
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Wire everything together in app.py and sidebar.py
  - [ ] 13.1 Complete `app.py` page routing and data flow
    - Initialize `EvalDataLoader`, load all runs
    - Render sidebar, get selected run and filters
    - Page navigation: tabs or selectbox for 6 pages
    - Pass appropriate data to each page's `render()` function
    - Show DDB availability banner from `loader.is_ddb_available()`
    - Show empty state when no eval runs found
    - _Requirements: 8.1, 8.3, 9.3, 10.1_

  - [ ] 13.2 Complete `sidebar.py` run selection and filtering
    - Run selector dropdown populated from `load_all_runs()` (sorted by timestamp descending)
    - Comparison run selector (optional second run for Prompt Correlation page)
    - Layer filter (base/fuzzy/all)
    - Category filter (auto_verifiable/automatable/human_only/all)
    - Dataset version filter (populated from available versions)
    - Store selections in `st.session_state`
    - _Requirements: 8.1, 8.3, 6.3_

- [ ] 14. Final checkpoint — Full integration
  - Ensure all tests pass, ask the user if questions arise.
  - User should run: `cd /home/wsluser/projects/calledit && /home/wsluser/projects/calledit/venv/bin/python -m streamlit run eval/dashboard/app.py` to verify the dashboard launches.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis with `@settings(max_examples=100)`
- Test file: `tests/eval_dashboard/test_data_properties.py`
- All Python commands must use the venv at `/home/wsluser/projects/calledit/venv`
- DO NOT auto-run Python commands — provide the exact command for the user to run
- The old `run_metadata#SUMMARY` record type expires via 90-day TTL; no migration needed
- DDB is primary data source; local files are fallback only
