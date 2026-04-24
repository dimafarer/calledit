# Continuous Eval Dashboard Fixes — Bugfix Design

## Overview

Three bugs in the Continuous Eval dashboard prevent correct visualization and tracking of verification results. Bug 1 is a frontend rendering issue where chart lines are invisible at Y-axis boundaries (0.0 and 1.0). Bug 2 is a backend data construction issue where inconclusive cases are excluded from the scatter plot because `_run_verification_pass()` only builds `verification_result` dicts for resolved cases. Bug 3 is a backend state management issue where pass numbering always resets to 1 because `run()` initializes `pass_num = 0` instead of reading from persisted state.

The fix approach is minimal and targeted: adjust the Y-axis domain and dot radius for Bug 1, widen the status filter from `"resolved"` to `("resolved", "inconclusive")` for Bug 2, and initialize `pass_num` from `self.state.pass_number` for Bug 3.

## Glossary

- **Bug_Condition (C)**: The set of inputs that trigger each bug — boundary Y-axis values for Bug 1, inconclusive case status for Bug 2, resumed state with pass_number > 0 for Bug 3
- **Property (P)**: The desired correct behavior — visible chart lines at boundaries, populated `actual_verdict` for inconclusive cases, sequential pass numbering across invocations
- **Preservation**: Existing behaviors that must remain unchanged — mid-range chart rendering, resolved case handling, fresh-state pass numbering, batched mode behavior
- **ResolutionRateChart**: React component in `frontend-v4/src/pages/EvalDashboard/components/ResolutionRateChart.tsx` that renders resolution rate and stale inconclusive rate as line charts over verification passes
- **CalibrationScatter**: React component in `frontend-v4/src/pages/EvalDashboard/components/CalibrationScatter.tsx` that renders verifiability score vs verification outcome as a scatter plot
- **ContinuousEvalRunner**: Python class in `eval/run_eval.py` that orchestrates the create-once, verify-repeatedly eval loop
- **CaseState**: Dataclass in `eval/continuous_state.py` tracking per-case lifecycle (status, verdict, confidence, evidence, etc.)
- **ContinuousState**: Dataclass in `eval/continuous_state.py` tracking top-level state including `pass_number` and all `CaseState` entries

## Bug Details

### Bug Condition

The three bugs manifest under distinct conditions:

**Bug 1** manifests when `resolution_rate` equals exactly 1.0 or `stale_inconclusive_rate` equals exactly 0.0. The Recharts `<YAxis domain={[0, 1]}>` clips the line to the axis boundary, making it invisible against the grid line. The dot radius of 4 is too small to be clearly visible at the boundary.

**Bug 2** manifests when a case has `cs.status = "inconclusive"` after verification. In `_run_verification_pass()`, the task output construction only builds a `vresult` dict when `cs.status == "resolved"`, so inconclusive cases get `verification_result: None`. Downstream, `extract_case_results()` sets `actual_verdict = vresult.get("verdict")` which yields `None`, and `CalibrationScatter` filters out cases where `actual_verdict` is null.

**Bug 3** manifests when the runner is invoked with `--resume` (or `--once --resume` or `--verify-only`). The `run()` method always initializes `pass_num = 0` at the top of the verification loop, then increments to 1 on the first iteration, regardless of `self.state.pass_number` which may be > 0 from previous invocations.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type {bug: 1|2|3, data: BugSpecificData}
  OUTPUT: boolean

  IF input.bug == 1:
    RETURN input.data.resolution_rate == 1.0
           OR input.data.stale_inconclusive_rate == 0.0

  IF input.bug == 2:
    RETURN input.data.case_status == "inconclusive"
           AND input.data.case_verdict == "inconclusive"

  IF input.bug == 3:
    RETURN input.data.state_pass_number > 0
           AND input.data.is_resumed == true
END FUNCTION
```

### Examples

- **Bug 1**: `resolution_rate=1.0` → green line at Y=1.0 is invisible (blends with top grid line). Expected: line visible with padding above it.
- **Bug 1**: `stale_inconclusive_rate=0.0` → red line at Y=0.0 is invisible (blends with bottom grid line). Expected: line visible with padding below it.
- **Bug 2**: Case `base-002` has `cs.verdict="inconclusive"`, `cs.status="inconclusive"` → `actual_verdict` is `None` → missing from scatter plot. Expected: appears at y=0.5 on scatter plot.
- **Bug 3**: First run completes pass 1, saves `state.pass_number=1`. Second run with `--once --resume` → `pass_num` starts at 0, increments to 1, report says "Pass 1" again. Expected: report says "Pass 2".

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Resolution rate and stale inconclusive rate lines at mid-range values (0.05–0.95) must continue to render clearly within the chart area
- Cases with `cs.status == "resolved"` and `cs.verdict` of `"confirmed"` or `"refuted"` must continue to have `verification_result` populated correctly in task outputs
- Cases with no verdict (`cs.verdict` is `None`, or status is `"pending"` or `"error"`) must continue to have `verification_result` set to `None`
- Fresh state (no `--resume`) must continue to start pass numbering from 1
- Batched (non-continuous) mode must continue to function identically with no changes to verification result construction or pass numbering
- Mouse interactions, tooltips, legends, and other chart interactivity must remain unchanged
- The `CalibrationScatter` component's filtering logic (requiring both `verifiability_score` and `actual_verdict`) must remain unchanged — the fix is in the backend data, not the frontend filter

**Scope:**
All inputs that do NOT involve Y-axis boundary values (Bug 1), inconclusive case status (Bug 2), or resumed state with pass_number > 0 (Bug 3) should be completely unaffected by these fixes.

## Hypothesized Root Cause

Based on the bug analysis and code review:

1. **Bug 1 — Y-Axis Domain Too Tight**: The `<YAxis domain={[0, 1]}>` in `ResolutionRateChart.tsx` (line 48) sets the visible range to exactly [0, 1]. When data points sit at these boundaries, the Recharts library renders them on the axis line itself, making them indistinguishable from the grid. The dot radius of 4 (line 52–53) is insufficient for boundary visibility.

2. **Bug 2 — Overly Restrictive Status Filter**: In `_run_verification_pass()` (around line 785 of `eval/run_eval.py`), the condition `if cs.verdict and cs.status == "resolved"` excludes inconclusive cases because their `cs.status` is `"inconclusive"`, not `"resolved"`. The `CaseState` dataclass correctly tracks inconclusive status and verdict, but the task output reconstruction doesn't include them.

3. **Bug 3 — Hardcoded Pass Counter Initialization**: In `ContinuousEvalRunner.run()` (line 617 of `eval/run_eval.py`), `pass_num = 0` is hardcoded at the start of the verification loop. When `--resume` loads a state with `pass_number > 0`, this value is ignored. The `self.state.pass_number` field is correctly persisted and loaded, but never used to initialize the loop counter.

## Correctness Properties

Property 1: Bug Condition — Chart Lines Visible at Y-Axis Boundaries

_For any_ `ResolutionRateChart` render where `resolution_rate` equals 1.0 or `stale_inconclusive_rate` equals 0.0, the chart SHALL display the corresponding line with visible padding (Y-axis domain extends beyond [0, 1]) and dots large enough to be clearly distinguishable from grid lines.

**Validates: Requirements 2.1, 2.2**

Property 2: Bug Condition — Inconclusive Cases in Task Outputs

_For any_ case where `cs.status == "inconclusive"` and `cs.verdict == "inconclusive"`, the `_run_verification_pass()` method SHALL construct a `verification_result` dict containing the verdict, confidence, evidence, and reasoning, so that `extract_case_results()` populates `actual_verdict` with `"inconclusive"`.

**Validates: Requirements 2.3, 2.4**

Property 3: Bug Condition — Sequential Pass Numbering on Resume

_For any_ continuous eval invocation with `--resume` where `self.state.pass_number` is N (N >= 1), the first verification pass SHALL be numbered N+1, and subsequent passes SHALL increment sequentially from there.

**Validates: Requirements 2.5**

Property 4: Preservation — Resolved Cases Unchanged

_For any_ case where `cs.status == "resolved"` and `cs.verdict` is `"confirmed"` or `"refuted"`, the fixed `_run_verification_pass()` SHALL produce the same `verification_result` dict as the original code, preserving all existing resolved case handling.

**Validates: Requirements 3.3, 3.4**

Property 5: Preservation — Fresh State Pass Numbering

_For any_ continuous eval invocation without `--resume` (fresh state with `pass_number == 0`), the first verification pass SHALL be numbered 1, identical to the original behavior.

**Validates: Requirements 3.5, 3.6**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `frontend-v4/src/pages/EvalDashboard/components/ResolutionRateChart.tsx`

**Change 1 — Y-Axis Domain Padding**:
- Change `<YAxis domain={[0, 1]} ...>` to `<YAxis domain={[-0.05, 1.05]} ...>`
- This adds 5% padding above and below the data range so lines at 0.0 and 1.0 are not clipped to the axis border

**Change 2 — Increase Dot Radius**:
- Change `dot={{ r: 4 }}` to `dot={{ r: 6 }}` on both `<Line>` elements
- Larger dots are visible even when the line itself overlaps with a grid line

---

**File**: `eval/run_eval.py`

**Function**: `ContinuousEvalRunner._run_verification_pass()`

**Change 3 — Widen Status Filter for vresult Construction**:
- Change `if cs.verdict and cs.status == "resolved":` to `if cs.verdict and cs.status in ("resolved", "inconclusive"):`
- This ensures inconclusive cases get a `verification_result` dict with their verdict, confidence, evidence, and reasoning
- `extract_case_results()` will then populate `actual_verdict` with `"inconclusive"` instead of `None`

---

**Function**: `ContinuousEvalRunner.run()`

**Change 4 — Initialize pass_num from State**:
- Change `pass_num = 0` to `pass_num = self.state.pass_number`
- When resuming, `self.state.pass_number` holds the last completed pass number (e.g., 1)
- The loop increments `pass_num` before use, so the next pass will be numbered correctly (e.g., 2)
- For fresh state, `self.state.pass_number` is 0, so behavior is identical to the original

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bugs on unfixed code, then verify the fixes work correctly and preserve existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE implementing the fixes. Confirm or refute the root cause analysis.

**Test Plan**: Write tests that exercise each bug condition on the unfixed code to observe failures.

**Test Cases**:
1. **Bug 1 — Boundary Rendering**: Render `ResolutionRateChart` with `resolution_rate=1.0` and `stale_inconclusive_rate=0.0`, inspect that Y-axis domain is `[0, 1]` (will confirm the clipping issue)
2. **Bug 2 — Inconclusive vresult**: Create a `CaseState` with `status="inconclusive"`, `verdict="inconclusive"`, run `_run_verification_pass()` logic, assert `verification_result` is `None` (will confirm on unfixed code)
3. **Bug 3 — Pass Numbering Reset**: Create a `ContinuousState` with `pass_number=3`, run the `run()` initialization logic, assert `pass_num` starts at 0 (will confirm on unfixed code)

**Expected Counterexamples**:
- Bug 2: `verification_result` is `None` for inconclusive cases because `cs.status == "resolved"` is `False`
- Bug 3: `pass_num` is always 0 regardless of `self.state.pass_number`

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed functions produce the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := fixedFunction(input)
  ASSERT expectedBehavior(result)
END FOR
```

**Bug 1**: For any `resolution_rate` in {0.0, 1.0} or `stale_inconclusive_rate` in {0.0, 1.0}, the Y-axis domain SHALL be `[-0.05, 1.05]` and dot radius SHALL be 6.

**Bug 2**: For any `CaseState` with `status="inconclusive"` and `verdict="inconclusive"`, the task output SHALL have `verification_result` containing `{"verdict": "inconclusive", ...}`.

**Bug 3**: For any `ContinuousState` with `pass_number=N` (N >= 0), the first pass SHALL be numbered `N+1`.

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed functions produce the same result as the original functions.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT originalFunction(input) = fixedFunction(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for resolved cases, mid-range chart values, and fresh-state pass numbering, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Resolved Case Preservation**: For any `CaseState` with `status="resolved"` and `verdict` in `("confirmed", "refuted")`, verify `verification_result` is constructed identically before and after the fix
2. **Pending/Error Case Preservation**: For any `CaseState` with `status` in `("pending", "error")` or `verdict=None`, verify `verification_result` remains `None` after the fix
3. **Fresh State Pass Numbering**: For `ContinuousState` with `pass_number=0`, verify the first pass is numbered 1 (same as original)
4. **Mid-Range Chart Values**: For `resolution_rate` and `stale_inconclusive_rate` between 0.05 and 0.95, verify chart rendering is unchanged

### Unit Tests

- Test `_run_verification_pass()` task output construction with inconclusive cases (Bug 2 fix check)
- Test `_run_verification_pass()` task output construction with resolved cases (Bug 2 preservation)
- Test `_run_verification_pass()` task output construction with pending/error cases (Bug 2 preservation)
- Test `run()` pass numbering with `state.pass_number=0` (Bug 3 fresh state)
- Test `run()` pass numbering with `state.pass_number=5` (Bug 3 resume)
- Test ResolutionRateChart Y-axis domain value (Bug 1)

### Property-Based Tests

- Generate random `CaseState` objects with `status` in `("resolved", "inconclusive", "pending", "error")` and random verdicts, verify the vresult construction logic produces correct output for each status
- Generate random `pass_number` values (0–100), verify the first pass is always `pass_number + 1`
- Generate random `resolution_rate` and `stale_inconclusive_rate` values in [0.0, 1.0], verify the Y-axis domain `[-0.05, 1.05]` always contains the data points with visible padding

### Integration Tests

- Run a continuous eval pass with a mix of resolved and inconclusive cases, verify the report contains `actual_verdict` for both
- Run two consecutive `--once --resume` invocations, verify pass numbers increment (1, 2)
- Load the Continuous Eval dashboard with boundary data, verify chart lines are visible
