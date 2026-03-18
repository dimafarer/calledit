# Implementation Plan: Comparative Eval Dashboard

## Overview

Build dashboard visualizations for architecture comparison on top of the existing Streamlit eval dashboard. The data loader gets extended first (foundation), then dashboard pages are implemented, then sidebar/routing wires everything together, and finally property-based and unit tests validate correctness. Comparative eval runs are optional tasks run manually in parallel.

## Tasks

- [x] 1. Extend Data Loader — per-agent aggregates, Verification-Builder-centric score, and execution time
  - [x] 1.1 Add `vb_centric_score` and `per_agent_aggregates` to `_normalize_run_summary` in `eval/dashboard/data_loader.py`
    - Read `vb_centric_score` from raw summary, default to `None` when missing
    - Read `per_agent_aggregates` from raw summary, default to `{}` when missing
    - Ensure backward compatibility with older runs that lack these fields
    - _Requirements: 1.1, 1.2, 1.4_

  - [x] 1.2 Add `execution_time_ms` to `_normalize_test_result` in `eval/dashboard/data_loader.py`
    - Read `execution_time_ms` from raw test result, default to `0` when missing
    - _Requirements: 1.3_

  - [x] 1.3 Extend `compare_runs` in `eval/dashboard/data_loader.py` with `vb_centric_delta` and `per_agent_deltas`
    - Add `vb_centric_delta` dict with `current`, `previous`, `delta` keys
    - Add `per_agent_deltas` dict with per-evaluator delta for each evaluator present in both runs' `per_agent_aggregates`
    - _Requirements: 10.1, 10.2_

- [x] 2. Checkpoint — Verify data loader extensions
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Architecture Comparison Page
  - [x] 3.1 Create `eval/dashboard/pages/architecture_comparison.py` with `render` function
    - Signature: `render(run_a_detail, run_b_detail, run_a_summary, run_b_summary)`
    - Same-architecture guard: display notice when both runs have the same `architecture` value, suggest Prompt Correlation page
    - Verification-Builder-centric score section: two `st.metric` columns with delta indicator
    - Per-evaluator score comparison: grouped bar chart (Plotly) with evaluators on x-axis grouped by `EVALUATOR_GROUPS` taxonomy (final-output, per-agent, cross-pipeline, deterministic) with visual separators
    - Per-agent evaluator scores: show only evaluators present in each run's `per_agent_aggregates`, display "N/A" for missing evaluators
    - PipelineCoherence callout: dedicated section explaining the silo problem
    - Per-category accuracy: grouped bar chart with categories on x-axis
    - Execution time comparison: total and per-test-case average for both runs
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_

- [x] 4. Trends Page — Per-Agent Judge Score Traces
  - [x] 4.1 Add per-agent judge score chart to `eval/dashboard/pages/trends.py`
    - Add "Final-Output Evaluators" section with IntentPreservation and CriteriaMethodAlignment traces (refactor from existing "Verification Quality" chart)
    - Add "Per-Agent & Cross-Pipeline Evaluators" section with IntentExtraction, CategorizationJustification, ClarificationRelevance, PipelineCoherence traces
    - Data source: `per_agent_aggregates` for per-agent evaluators, `verification_quality_aggregates` for final-output evaluators
    - Use `connectgaps=True` so runs lacking per-agent data show gaps instead of zero
    - Skip the per-agent chart entirely if no run has `per_agent_aggregates` data
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 4.2 Add architecture filtering to Trends page
    - Accept architecture filter from sidebar selections
    - Filter `sorted_runs` to only runs matching the selected architecture before rendering all charts
    - When filter is "all", show all runs
    - _Requirements: 6.3_

- [x] 5. Heatmap Enhancements — Architecture and Evaluator Grouping
  - [x] 5.1 Add evaluator group column ordering and labels to `eval/dashboard/pages/heatmap.py`
    - Reorder columns by group: final-output → per-agent → cross-pipeline → deterministic
    - Add group label annotations above each column group
    - Add vertical separators between all 4 groups (extend existing det/judge separator)
    - _Requirements: 4.1, 4.4_

  - [x] 5.2 Add architecture label and side-by-side heatmap mode
    - Display architecture label in page header from `run_detail`
    - Change `render` signature to accept optional `comparison_detail` parameter
    - When comparison run is selected and architectures differ, render two side-by-side heatmaps with matching test case row order
    - _Requirements: 4.2, 4.3_

- [x] 6. Coherence View — Multi-Judge Agreement Analysis
  - [x] 6.1 Update judge classification in `eval/dashboard/pages/coherence.py`
    - Replace `"ReasoningQuality" in name` check with a set of all 6 LLM judge names: `{"IntentPreservation", "CriteriaMethodAlignment", "IntentExtraction", "CategorizationJustification", "ClarificationRelevance", "PipelineCoherence"}`
    - Keep backward compatibility with `ReasoningQuality` (legacy)
    - _Requirements: 5.1_

  - [x] 6.2 Add per-judge agreement breakdown and judge-vs-judge correlation
    - Per-judge agreement: for each LLM judge, compute agreement rate with deterministic evaluators (pass/fail threshold at 0.5), display as table
    - Judge-vs-judge correlation: for each pair of LLM judges, compute how often they agree on the same test cases, display as correlation matrix
    - Skip judge-vs-judge section if fewer than 2 judges have data
    - _Requirements: 5.2, 5.3_

  - [x] 6.3 Include per-agent judges in chain-of-reasoning inspection
    - When run has per-agent evaluator data, include per-agent judge scores and reasoning alongside existing agent output fields in the chain-of-reasoning expander
    - _Requirements: 5.4_

- [x] 7. Prompt Correlation — Architecture-Aware Comparison
  - [x] 7.1 Add Verification-Builder-centric score delta and per-agent evaluator deltas to `eval/dashboard/pages/prompt_correlation.py`
    - Display `vb_centric_score` for both runs with delta indicator above existing overall pass rate delta
    - Display per-agent evaluator score deltas (IntentExtraction, CategorizationJustification, ClarificationRelevance, PipelineCoherence) when both runs have `per_agent_aggregates`
    - _Requirements: 10.1, 10.2_

  - [x] 7.2 Add architecture-aware effect grouping
    - When comparing runs across architectures, group delta display into "Architecture Effect" (evaluators present in only one run's `per_agent_aggregates`) and "Prompt Effect" (evaluators present in both runs but prompt versions differ)
    - Use `architecture` and `prompt_version_manifest` fields to distinguish
    - _Requirements: 10.3_

- [x] 8. Sidebar and Routing Updates
  - [x] 8.1 Add "Architecture Comparison" to sidebar page navigation in `eval/dashboard/sidebar.py`
    - Add "Architecture Comparison" to the page radio options list
    - _Requirements: 6.1_

  - [x] 8.2 Update `eval/dashboard/app.py` routing for Architecture Comparison and enhanced pages
    - Add routing for "Architecture Comparison" page, passing both run details and run summaries
    - Pass comparison run detail to Heatmap when in side-by-side mode
    - Apply architecture filter to Trends page runs (filter `filtered_runs` by architecture before passing to `trends.render`)
    - Apply architecture filter to Heatmap page
    - _Requirements: 6.2, 6.3, 6.4_

- [x] 9. Checkpoint — Verify all dashboard pages render correctly
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Property-based tests
  - [ ]* 10.1 Write property test for run summary normalization (Property 1)
    - **Property 1: Run summary normalization preserves new fields**
    - Generate random run summary dicts with/without `per_agent_aggregates` and `vb_centric_score`
    - Verify normalization preserves values when present, defaults to `{}` and `None` when absent
    - Test file: `tests/dashboard/test_dashboard_properties.py`
    - **Validates: Requirements 1.1, 1.2, 1.4**

  - [ ]* 10.2 Write property test for test result normalization (Property 2)
    - **Property 2: Test result normalization preserves execution_time_ms**
    - Generate random test result dicts with/without `execution_time_ms`
    - Verify normalization preserves value when present, defaults to `0` when absent
    - Test file: `tests/dashboard/test_dashboard_properties.py`
    - **Validates: Requirements 1.3**

  - [ ]* 10.3 Write property test for evaluator group classification (Property 3)
    - **Property 3: Evaluator group classification**
    - Generate random evaluator name strings including the 10 known names and arbitrary strings
    - Verify each name is classified into exactly one group: final_output, per_agent, cross_pipeline, deterministic, or unknown
    - Verify the 6 LLM judge names are non-deterministic and the 4 deterministic names are deterministic
    - Test file: `tests/dashboard/test_dashboard_properties.py`
    - **Validates: Requirements 2.2, 4.1, 5.1**

  - [ ]* 10.4 Write property test for per-agent evaluator presence filtering (Property 4)
    - **Property 4: Per-agent evaluator presence filtering**
    - Generate two random `per_agent_aggregates` dicts
    - Verify the set of evaluators displayed for each run equals exactly the keys present in that run's aggregates
    - Test file: `tests/dashboard/test_dashboard_properties.py`
    - **Validates: Requirements 2.4**

  - [ ]* 10.5 Write property test for per-agent judge score extraction (Property 5)
    - **Property 5: Per-agent judge score extraction from run summaries**
    - Generate lists of run summaries with random per-agent data
    - Verify extraction produces `None` for missing evaluators, not `0`
    - Test file: `tests/dashboard/test_dashboard_properties.py`
    - **Validates: Requirements 3.1, 3.2**

  - [ ]* 10.6 Write property test for heatmap row order consistency (Property 6)
    - **Property 6: Heatmap row order consistency**
    - Generate two lists of test cases with overlapping IDs
    - Verify row ordering is consistent across both heatmaps
    - Test file: `tests/dashboard/test_dashboard_properties.py`
    - **Validates: Requirements 4.3**

  - [ ]* 10.7 Write property test for per-judge agreement rate (Property 7)
    - **Property 7: Per-judge agreement rate computation**
    - Generate test cases with random deterministic and judge scores
    - Verify agreement rate is in [0.0, 1.0] and matches expected fraction
    - Test file: `tests/dashboard/test_dashboard_properties.py`
    - **Validates: Requirements 5.2**

  - [ ]* 10.8 Write property test for judge-vs-judge correlation symmetry (Property 8)
    - **Property 8: Judge-vs-judge correlation symmetry**
    - Generate test cases with multiple judge scores
    - Verify pairwise correlation is symmetric (A→B == B→A) and in [0.0, 1.0]
    - Test file: `tests/dashboard/test_dashboard_properties.py`
    - **Validates: Requirements 5.3**

  - [ ]* 10.9 Write property test for architecture filtering (Property 9)
    - **Property 9: Architecture filtering**
    - Generate lists of runs with random architecture values and a filter string
    - Verify filtering returns only matching runs, "all" returns all, result is subset of input
    - Test file: `tests/dashboard/test_dashboard_properties.py`
    - **Validates: Requirements 6.3, 6.4**

  - [ ]* 10.10 Write property test for compare_runs delta correctness (Property 11)
    - **Property 11: Compare runs delta correctness**
    - Generate two run summaries with random `vb_centric_score` and `per_agent_aggregates`
    - Verify `vb_centric_delta.delta == current - previous` within floating point tolerance
    - Verify per-agent deltas equal `current_avg - previous_avg`
    - Test file: `tests/dashboard/test_dashboard_properties.py`
    - **Validates: Requirements 10.1, 10.2**

  - [ ]* 10.11 Write property test for architecture-vs-prompt effect classification (Property 12)
    - **Property 12: Architecture-vs-prompt effect classification**
    - Generate two run summaries with different architectures and prompt manifests
    - Verify evaluator deltas are labeled "Architecture Effect" when evaluator exists in only one run, "Prompt Effect" when both runs have it but prompts differ
    - Test file: `tests/dashboard/test_dashboard_properties.py`
    - **Validates: Requirements 10.3**

- [ ] 11. Unit tests
  - [ ]* 11.1 Write unit tests for dashboard components
    - Coherence View judge classification: verify each of the 6 known judge names is classified correctly, verify `ReasoningQuality` (legacy) is still recognized, verify deterministic evaluators are not classified as judges
    - Sidebar page list: verify "Architecture Comparison" appears in page navigation options
    - Same-architecture detection: verify two runs with `architecture: "serial"` trigger the notice, verify `"serial"` vs `"single"` does not
    - Empty data edge cases: verify Architecture Comparison page handles empty `per_agent_aggregates`, empty `per_category_accuracy`, and `None` `vb_centric_score` without errors
    - Backward compatibility: verify a pre-Spec-10 run summary (no `per_agent_aggregates`, no `vb_centric_score`, no `execution_time_ms`) normalizes without errors
    - Test file: `tests/dashboard/test_dashboard_unit.py`
    - _Requirements: 1.4, 2.4, 2.8, 5.1, 6.1_

- [ ] 12. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ]* 13. Comparative eval runs (manual, run in parallel)
  - [ ]* 13.1 Run 9 config — serial backend (current best prompts)
    - `cd /home/wsluser/projects/calledit/backend/calledit-backend/handlers/strands_make_call`
    - `PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=2 PROMPT_VERSION_REVIEW=2 /home/wsluser/projects/calledit/venv/bin/python eval_runner.py --dataset ../../../../eval/golden_dataset.json --backend serial --judge`
    - _Requirements: 7.1, 7.3, 7.4_

  - [ ]* 13.2 Run 9 config — single backend (current best prompts)
    - `PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=2 PROMPT_VERSION_REVIEW=2 /home/wsluser/projects/calledit/venv/bin/python eval_runner.py --dataset ../../../../eval/golden_dataset.json --backend single --judge`
    - _Requirements: 7.2, 7.3, 7.4_

  - [ ]* 13.3 Run 7 config — serial backend (pre-Verification-Builder iteration baseline)
    - `PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=1 PROMPT_VERSION_REVIEW=1 /home/wsluser/projects/calledit/venv/bin/python eval_runner.py --dataset ../../../../eval/golden_dataset.json --backend serial --judge`
    - _Requirements: 8.1, 8.3, 8.4_

  - [ ]* 13.4 Run 7 config — single backend (pre-Verification-Builder iteration baseline)
    - `PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=1 PROMPT_VERSION_REVIEW=1 /home/wsluser/projects/calledit/venv/bin/python eval_runner.py --dataset ../../../../eval/golden_dataset.json --backend single --judge`
    - _Requirements: 8.2, 8.3, 8.4_

  - [ ]* 13.5 Run 3 config — single backend only (categorizer v2)
    - `PROMPT_VERSION_CATEGORIZER=2 /home/wsluser/projects/calledit/venv/bin/python eval_runner.py --dataset ../../../../eval/golden_dataset.json --backend single --judge`
    - _Requirements: 9.1, 9.2, 9.3_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Data loader extensions (task 1) are the foundation — all dashboard pages depend on them
- Dashboard pages (tasks 3-7) can be built in parallel once the data loader is done
- Sidebar/routing (task 8) wires everything together after pages exist
- Property tests and unit tests (tasks 10-11) validate correctness properties from the design
- Comparative eval runs (task 13) are manual operations the user runs in parallel — they produce the data the dashboard visualizes
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
