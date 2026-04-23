# Next Agent Prompt — Continuous Verification Eval

**Date:** April 23, 2026
**Previous session:** Continuous verification eval — full implementation + integration testing complete. See Update 40.

---

## Session Goal

The continuous verification eval system is fully built and integration tested. Next steps: deploy the frontend to production, run a multi-case continuous eval, and expand the golden dataset.

The spec is at:
- `.kiro/specs/continuous-verification-eval/` — ALL TASKS COMPLETE, integration tested

## CRITICAL — Read These FIRST

1. `docs/project-updates/40-project-update-continuous-verification-eval-spec.md` — Full implementation + integration test results
2. `docs/project-updates/project-summary.md` — Current state
3. `docs/project-updates/common-commands.md` — Updated with SDK eval + continuous eval commands

## What's Already Built (Everything)

### Python Backend (all complete, 129/129 tests passing)
- `eval/continuous_state.py` — VerdictEntry, CaseState, ContinuousState dataclasses with save/load/eligibility/transitions
- `eval/continuous_metrics.py` — resolution rate, stale inconclusive rate, resolution speed by tier, continuous calibration
- `eval/run_eval.py` — ContinuousEvalRunner class + CLI flags (--continuous, --interval, --max-passes, --once, --reverify-resolved, --resume)
- `eval/tests/test_continuous_state.py` — P1-P3 property tests + unit tests
- `eval/tests/test_continuous_metrics.py` — P4-P6 property tests + unit tests
- `eval/tests/test_continuous_runner.py` — P7 property test + CLI flag tests

### React Dashboard (all complete, zero TypeScript diagnostics)
- `types.ts` — AgentType includes 'continuous', AGENT_TABS includes Continuous Eval, ContinuousCaseResult, ContinuousCalibrationScores
- `utils.ts` — getContinuousVerdictColor(), hasContinuousError()
- `CaseTable.tsx` — Continuous columns (Status, Verdict, V-Score, Pass#) with color coding
- `ResolutionRateChart.tsx` — Line chart (resolution rate + stale rate over passes)
- `ResolutionSpeedChart.tsx` — Bar chart (median resolution pass by V-score tier)
- `ContinuousTab.tsx` — Wraps AgentTab with charts
- `index.tsx` — Renders ContinuousTab for continuous tab

## What Needs to Be Done

### 1. Manual Integration Test (Task 12.2)
```bash
source .env
/home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py --continuous --max-passes 1 --tier smoke --case base-002
```
Verify: creation succeeds, verification returns verdict, report written to DDB, state saved to `eval/continuous_state.json`.

### 2. Dashboard Verification (Task 12.3)
Deploy frontend and verify the Continuous Eval tab loads, shows the report, renders case table with color coding.

### 3. Multi-Pass Test
```bash
/home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py --continuous --max-passes 3 --tier smoke
```
Verify: 3 passes execute, resolution rate changes between passes, state file accumulates verdict history.

### 4. Documentation
- Update decision-log.md if any new decisions arise
- Write project update 41 if significant findings from integration testing


## Key Values
```
# Creation Agent
CREATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_Agent-AJiwpKBxRW

# Verification Agent
VERIFICATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_verification_Agent-77DiT7GHdH

# Eval DDB Tables
EVAL_TABLE=calledit-v4-eval
EVAL_REPORTS_TABLE=calledit-v4-eval-reports
```

## Import Gotchas

- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Eval runs require `COGNITO_USERNAME`, `COGNITO_PASSWORD`, `BRAVE_API_KEY` env vars (in `.env`)
- `source .env` before any eval or agent commands
- `agentcore launch` and `agentcore invoke` require TTY — ask user to run and paste output
- Decision log is at 152, next decision is 153
- Project update is at 40, next is 41

## Testing

Run all eval tests:
```bash
/home/wsluser/projects/calledit/venv/bin/python -m pytest eval/tests/ -v
```

Expected: 129 passed
