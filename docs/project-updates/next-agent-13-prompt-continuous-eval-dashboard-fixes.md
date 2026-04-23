# Next Agent Prompt — Continuous Eval Dashboard Fixes

**Date:** April 23, 2026
**Previous session:** Continuous verification eval full implementation + integration testing. See Update 40.

---

## Session Goal

Fix three dashboard rendering bugs in the Continuous Eval tab. The backend data is correct — these are frontend display issues.

## CRITICAL — Read These FIRST

1. `docs/project-updates/40-project-update-continuous-verification-eval-spec.md` — Full context
2. `docs/project-updates/project-summary.md` — Current state
3. `eval/continuous_state.json` — Current continuous state (if exists)

## Bug 1: Resolution Rate Chart — Lines Invisible at 1.0

**File:** `frontend-v4/src/pages/EvalDashboard/components/ResolutionRateChart.tsx`

**Problem:** When resolution_rate=1.0 and stale_inconclusive_rate=0.0, the green line sits at the top of the chart and the red line at the bottom — both blend with the chart border/grid lines and are invisible.

**Fix options:**
- Change Y-axis domain from `[0, 1]` to `[-0.05, 1.05]` so lines have padding
- Increase dot radius so data points are visible even at boundaries
- Add a subtle background fill under the lines

## Bug 2: Scatter Plot — Inconclusive Cases Not Appearing

**File:** `eval/run_eval.py` — `ContinuousEvalRunner._run_verification_pass()`

**Problem:** The CalibrationScatter chart filters cases that have both `verifiability_score` AND `actual_verdict`. Inconclusive cases from the continuous eval don't have `actual_verdict` populated in the case_results because the task_outputs construction only sets `verification_result` for resolved cases (status=resolved).

**Root cause in `_run_verification_pass()`:**
```python
# This only creates vresult for resolved cases
vresult = None
if cs.verdict and cs.status == "resolved":
    vresult = { "verdict": cs.verdict, ... }
```

Inconclusive cases have `cs.verdict = "inconclusive"` but `cs.status = "inconclusive"` (not "resolved"), so `vresult` stays `None`. Then `extract_case_results()` sets `actual_verdict = vresult.get("verdict")` which is `None`.

**Fix:** Include inconclusive cases in the vresult construction:
```python
vresult = None
if cs.verdict and cs.status in ("resolved", "inconclusive"):
    vresult = { "verdict": cs.verdict, "confidence": cs.confidence, ... }
```

## Bug 3: Pass Numbering — All Reports Labeled "Pass 1"

**Problem:** Each `--once --resume` run and each `--verify-only` run starts with a fresh state (pass_number=0) or loads state that was saved with pass_number=1. The pass_number doesn't increment across separate CLI invocations.

**Root cause:** When `--verify-only` is used without `--resume`, a fresh state is created with pass_number=0. When `--once --resume` is used, it loads state but the `run()` method always sets `self.state.pass_number = pass_num` where `pass_num` starts at 0 and increments to 1 in the loop.

**Fix:** When loading state via `--resume`, start `pass_num` from `self.state.pass_number` (the last completed pass) instead of 0. In `run()`:
```python
pass_num = self.state.pass_number  # Start from last completed pass
while True:
    pass_num += 1
    ...
```

## Additional Context

**How to test:** After fixes, run:
```bash
cd /home/wsluser/projects/calledit && source .env
# Reset DDB statuses
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python -c "
import boto3
ddb = boto3.resource('dynamodb', region_name='us-west-2')
table = ddb.Table('calledit-v4-eval')
resp = table.scan(FilterExpression='SK = :sk', ExpressionAttributeValues={':sk': 'BUNDLE'}, ProjectionExpression='PK, SK, #s', ExpressionAttributeNames={'#s': 'status'})
for item in resp.get('Items', []):
    if item.get('status') != 'pending':
        table.update_item(Key={'PK': item['PK'], 'SK': 'BUNDLE'}, UpdateExpression='SET #s = :p', ExpressionAttributeNames={'#s': 'status'}, ExpressionAttributeValues={':p': 'pending'})
print('Done')
"
# Delete old state
rm -f eval/continuous_state.json
# Run smoke test
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py --continuous --max-passes 1 --tier smoke --verify-only
```

Then check the Continuous Eval tab at http://localhost:5173/eval

**Dev server:** `cd frontend-v4 && npm run dev`

**All Python tests:** `/home/wsluser/projects/calledit/venv/bin/python -m pytest eval/tests/ -v` (expect 129 passed)

**Key files:**
- `eval/run_eval.py` — ContinuousEvalRunner class (bugs 2 and 3)
- `frontend-v4/src/pages/EvalDashboard/components/ResolutionRateChart.tsx` (bug 1)
- `frontend-v4/src/pages/EvalDashboard/components/CalibrationScatter.tsx` (scatter plot)
- `frontend-v4/src/pages/EvalDashboard/components/CaseTable.tsx` (case table with color coding)
- `frontend-v4/src/pages/EvalDashboard/components/ContinuousTab.tsx` (tab wrapper)
- `frontend-v4/src/pages/EvalDashboard/components/AgentTab.tsx` (score grids + scatter rendering)

**Decision log:** at 152, next is 153
**Project update:** at 40, next is 41
