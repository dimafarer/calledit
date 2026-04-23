# Implementation Tasks

## Task 1: ContinuousState module — dataclasses and serialization
- [x] 1.1 Create `eval/continuous_state.py` with `VerdictEntry`, `CaseState`, and `ContinuousState` dataclasses matching the design schema
- [x] 1.2 Implement `ContinuousState.save(path)` — serialize to JSON with ISO timestamps and proper None handling
- [x] 1.3 Implement `ContinuousState.load(path)` — deserialize from JSON, handle missing file (return fresh), handle corrupt JSON (log warning, return fresh)
- [x] 1.4 Implement `ContinuousState.fresh(eval_table)` — create empty state with pass_number=0
- [x] 1.5 Implement `ContinuousState.get_eligible_for_verification(reverify_resolved)` — return cases with status pending/inconclusive (and resolved if flag is True), exclude error cases with no prediction_id
- [x] 1.6 Implement `ContinuousState.update_case_verdict(case_id, verdict, confidence, pass_number)` — transition status based on verdict (confirmed/refuted→resolved, inconclusive→inconclusive, None→preserve previous), append to verdict_history, set resolved_on_pass on first resolution
- [x] 1.7 Write property-based tests for P1 (state round-trip), P2 (case eligibility), P3 (state transitions) in `eval/tests/test_continuous_state.py`
- [x] 1.8 Write unit tests for edge cases: load from missing file, load from corrupt JSON, fresh state defaults, resume increments pass_number

> **Requirements covered:** 1.2, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 8.1, 8.2, 8.3, 8.4
> **Properties validated:** P1, P2, P3

## Task 2: ContinuousMetrics module — resolution rate, stale rate, resolution speed
- [x] 2.1 Create `eval/continuous_metrics.py` with `compute_resolution_rate(state)` — count resolved / count verified-at-least-once, return 0.0 when no cases verified
- [x] 2.2 Implement `compute_stale_inconclusive_rate(state, now)` — count (inconclusive AND verification_date < now) / count (verification_date < now), exclude future/null dates, return 0.0 when no past dates
- [x] 2.3 Implement `compute_resolution_speed_by_tier(state)` — median resolved_on_pass per V-score tier (high≥0.7, moderate 0.4–0.7, low<0.4), return null when tier has <2 resolved cases
- [x] 2.4 Implement `compute_continuous_calibration(state, task_outputs)` — combine base calibration fields with resolution_rate, stale_inconclusive_rate, and resolution_speed_by_tier
- [x] 2.5 Write property-based tests for P4 (resolution rate), P5 (stale inconclusive), P6 (resolution speed) in `eval/tests/test_continuous_metrics.py`
- [x] 2.6 Write unit tests for edge cases: 0 verified cases, all resolved, all future dates, exactly 1 resolved per tier (null), exactly 2 resolved (correct median)

> **Requirements covered:** 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5
> **Properties validated:** P4, P5, P6

## Task 3: CLI flag extensions — add continuous mode flags to parse_args
- [x] 3.1 Add `--continuous` (store_true), `--interval` (int, default 15), `--max-passes` (int, default None), `--once` (store_true), `--reverify-resolved` (store_true) to `parse_args()` in `eval/run_eval.py`
- [x] 3.2 Add flag interaction logic: `--continuous` implies `--skip-cleanup`; validate that `--once` requires `--continuous`; validate that `--interval` and `--max-passes` require `--continuous`
- [x] 3.3 Write unit tests for flag parsing and interaction rules in `eval/tests/test_continuous_runner.py`

> **Requirements covered:** 7.1, 7.2, 7.3, 7.6

## Task 4: ContinuousEvalRunner class — creation phase and verification pass
- [x] 4.1 Create `ContinuousEvalRunner` class in `eval/run_eval.py` with `__init__` accepting args, cases, backends, evaluators, and state
- [x] 4.2 Implement `_run_creation_phase()` — invoke creation backend on all cases, populate state with prediction_ids and statuses, handle per-case errors (mark as error, continue)
- [x] 4.3 Implement `_run_verification_pass()` — get eligible cases from state, invoke verification backend on each, update state with verdicts, handle per-case errors (preserve previous verdict, continue)
- [x] 4.4 Implement `_run_evaluation(task_outputs)` — run evaluators on all cases (creation evaluators on all, verification evaluators on resolved only), compute continuous calibration, build report dict
- [x] 4.5 Implement `_write_report(report)` — write Continuous_Report to DDB Reports_Table with agent type `continuous`, pass_number, resolution_rate, and resolution_speed_by_tier in calibration_scores
- [x] 4.6 Write property-based test for P7 (creation resilience) — random subset of creation failures, verify all cases have entries with correct statuses
- [x] 4.7 Write unit tests for creation phase error handling, verification pass eligibility filtering, and report schema correctness

> **Requirements covered:** 1.1, 1.3, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4, 4.5
> **Properties validated:** P7

## Task 5: Continuous loop orchestration — run(), SIGINT, sleep, resume
- [x] 5.1 Implement `run()` — main loop: create (if not verify-only) → verify → evaluate → report → save state → sleep → repeat; respect max-passes and once flags
- [x] 5.2 Implement SIGINT handler — set `_shutdown_requested` flag, complete current pass, write final report, save state, exit cleanly; force-exit on second SIGINT
- [x] 5.3 Implement token refresh logic — call `_maybe_refresh_token()` before each verification batch if >50 minutes elapsed since last refresh
- [x] 5.4 Wire `--continuous` path in `main()` — when `--continuous` is set, create ContinuousState (fresh or loaded via `--resume`), instantiate ContinuousEvalRunner, call `run()`
- [x] 5.5 Implement `--verify-only` in continuous mode — skip creation, load existing bundles from DDB, populate state with prediction_ids from loaded bundles
- [x] 5.6 Implement `--once` in continuous mode — single verification pass (no creation, no loop), write report, exit
- [x] 5.7 Write unit tests for loop control: max-passes stops correctly, once runs single pass, resume loads state and continues from last pass_number

> **Requirements covered:** 1.4, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 8.3, 8.4

## Task 6: Report schema extension — continuous-specific fields in case_results
- [x] 6.1 Extend `extract_case_results()` to include `status`, `resolved_on_pass`, `verification_date`, and `verdict_history` fields when building case results for continuous reports
- [x] 6.2 Extend `build_report()` to include `pass_number`, `total_passes`, and `interval_minutes` in run_metadata for continuous reports
- [x] 6.3 Update `report_store.py` `list_reports()` projection to include continuous-specific score keys (`resolution_rate`, `stale_inconclusive_rate`)
- [x] 6.4 Write unit tests verifying continuous report schema matches the design document

> **Requirements covered:** 4.3, 4.4, 4.5, 5.4

## Task 7: Dashboard — add Continuous Eval tab and TypeScript types
- [x] 7.1 Add `'continuous'` to the `AgentType` union in `frontend-v4/src/pages/EvalDashboard/types.ts`
- [x] 7.2 Add `{ key: 'continuous', label: 'Continuous Eval' }` to `AGENT_TABS` array
- [x] 7.3 Add `ContinuousCaseResult` interface extending `CaseResult` with `status`, `resolved_on_pass`, `verification_date`, and `verdict_history` fields
- [x] 7.4 Add `ContinuousCalibrationScores` interface with `resolution_rate`, `stale_inconclusive_rate`, and `resolution_speed_by_tier`
- [x] 7.5 Update `list_eval_reports` Lambda handler to accept `agent=continuous` query parameter

> **Requirements covered:** 9.1, 9.2, 9.3

## Task 8: Dashboard — case status color coding in CaseTable
- [x] 8.1 Add a `getVerdictColor(caseResult, agentType)` utility function in `utils.ts` that returns green (#22c55e) for resolved, red (#ef4444) for stale inconclusive (verdict=inconclusive AND verification_date in past), grey (#64748b) for pending/future
- [x] 8.2 Update `CaseTable.tsx` verdict cell rendering to use `getVerdictColor()` when `agentType === 'continuous'`
- [x] 8.3 Add dark red background (#3b1111) to case rows with creation or verification errors when `agentType === 'continuous'`

> **Requirements covered:** 10.1, 10.2, 10.3, 10.4, 10.5

## Task 9: Dashboard — ResolutionRateChart component
- [x] 9.1 Create `frontend-v4/src/pages/EvalDashboard/components/ResolutionRateChart.tsx` using recharts `LineChart` — x-axis: pass number, y-axis: rate (0.0–1.0), green line for resolution rate, red line for stale inconclusive rate
- [x] 9.2 Add tooltip showing pass timestamp and exact values on hover
- [x] 9.3 Show "Insufficient data for chart — need at least 2 continuous eval passes" message when fewer than 2 reports exist
- [x] 9.4 Wire the chart into the continuous tab — load all continuous reports, extract resolution_rate and stale_inconclusive_rate from each report's calibration_scores

> **Requirements covered:** 11.1, 11.2, 11.3, 11.4

## Task 10: Dashboard — ResolutionSpeedChart component
- [x] 10.1 Create `frontend-v4/src/pages/EvalDashboard/components/ResolutionSpeedChart.tsx` using recharts `BarChart` — grouped bars for high/moderate/low tiers, colored green/yellow/red
- [x] 10.2 Render null tiers as empty bars with "N/A" label
- [x] 10.3 Wire the chart into the continuous tab — extract `resolution_speed_by_tier` from the selected report's calibration_scores

> **Requirements covered:** 12.1, 12.2

## Task 11: Dashboard — ContinuousTab wrapper component
- [x] 11.1 Create `frontend-v4/src/pages/EvalDashboard/components/ContinuousTab.tsx` that wraps the existing `AgentTab` component and adds ResolutionRateChart and ResolutionSpeedChart above the case table
- [x] 11.2 Update `EvalDashboard/index.tsx` to render `ContinuousTab` when the continuous tab is selected, and the standard `AgentTab` for other tabs
- [x] 11.3 Verify the continuous tab loads reports with `agent=continuous` and displays the run selector, metadata accordion, score grids, and case table from the existing AgentTab

> **Requirements covered:** 9.1, 9.2, 9.3, 11.1, 12.1

## Task 12: Integration smoke test — end-to-end continuous eval
- [x] 12.1 Run all property-based and unit tests: `venv/bin/python -m pytest eval/tests/test_continuous_state.py eval/tests/test_continuous_metrics.py eval/tests/test_continuous_runner.py -v`
- [x] 12.2 Run a manual smoke test: `venv/bin/python eval/run_eval.py --continuous --max-passes 1 --tier smoke --case base-002` — verify creation, verification, report written to DDB, state saved to continuous_state.json
- [x] 12.3 Verify the dashboard loads the continuous report: check that the Continuous Eval tab appears, the report is listed in the run selector, case table renders with color coding
