# Project Update 33 — Verification Modes + TTY Fix + Dark Theme

**Date:** March 27, 2026
**Context:** Three distinct wins in one session: (1) unified dark theme + dashboard UX fixes, (2) resolved the long-standing TTY/command execution issue, (3) implemented all four verification modes (immediate, at_date, before_date, recurring) — resolving backlog item 0.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/verification-modes/` — Verification Modes spec (COMPLETE — all 12 tasks done)

### Prerequisite Reading
- `docs/project-updates/32-project-update-dark-theme-and-dashboard-ux.md` — Dark theme + dashboard fixes (same session, earlier)
- `docs/project-updates/31-project-update-v4-7a-eval-completion-and-dashboard-spec.md` — Dashboard + eval baseline context

---

## What Happened This Session

This was a packed session that started with UI polish, detoured into a long-standing infrastructure bug, and ended with a major feature implementation.

### Phase 1: Dark Theme + Dashboard UX (Update 32)

Fixed the eval dashboard table column alignment (nested `<tbody>` bug), unified the entire frontend on a dark slate theme, replaced gradient buttons with clean underline tabs, and added a collapsible metadata accordion. Deployed to production. See Update 32 for details.

### Phase 2: The TTY Fix

The `TTY=not a tty` and `Exit Code: -1` issues had plagued every agent session for 31+ updates. The user and agent investigated together:

1. `env | grep -i tty` revealed `TTY=not a tty` was an environment variable, not a runtime error
2. Research found Ernest Chiang's blog post documenting the exact same issue — Amazon Q CLI shell integration (`q init bash pre/post`) injects `PROMPT_COMMAND` hooks that conflict with Kiro's output capture
3. The fix: wrap both Amazon Q blocks in `~/.bashrc` with `if [[ "$TERM_PROGRAM" != "kiro" ]]` guards, plus `unset TTY` as a safety net
4. After Kiro restart: `Exit Code: 0`, full command output, clean results

This was a quality-of-life breakthrough. Every future agent session benefits from clean command execution.

### Phase 3: Prompt Version Pinning

The dashboard showed `DRAFT` for all prompt versions — making eval comparison impossible. Fixed by:
1. Adding `DEFAULT_PROMPT_VERSIONS` dict to `prompt_client.py` with numbered versions
2. Changing the version resolution from `"DRAFT"` fallback to the pinned defaults
3. Relaunching both agents to pick up the change
4. Smoke test confirmed: `prediction_parser: 2, verification_planner: 2, plan_reviewer: 3`

### Phase 4: Verification Modes (Backlog Item 0)

The big feature. The system previously only supported `immediate` mode — predictions verifiable right now with a single check. This left `at_date`, `before_date`, and `recurring` predictions sitting in `pending` forever.

The spec was built collaboratively:
- User pushed for the verification_planner (turn 2) to classify the mode, not the plan_reviewer — because the planner needs the mode to build mode-appropriate plan steps
- Plan_reviewer (turn 3) confirms the mode as a semi-deterministic consistency check
- User identified the need for `recurring_interval` and `max_snapshots` to prevent unbounded snapshot growth

Implementation (12 tasks, all complete):
1. Pydantic models: `verification_mode` on VerificationPlan + PlanReview, `recurring_interval` on VerificationPlan
2. Bundle builder: accepts mode, interval, max_snapshots
3. Mode resolution: `resolve_verification_mode()` — reviewer wins on disagreement
4. Prompts: verification_planner v2 (mode classification), plan_reviewer v3 (mode confirmation), verification_executor v2 (mode-specific verdict rules)
5. Verification agent: includes mode in user message
6. Scanner: mode-aware scheduling with `should_invoke()` + `handle_verification_result()` + recurring interval checks
7. Snapshot storage: `append_verification_snapshot()` with max_snapshots pruning
8. Golden dataset: expanded from 45 → 54 cases (9 new: 3 at_date, 3 before_date, 3 recurring)
9. Evaluators: 3 new modules (at_date_verdict_accuracy, before_date_verdict_appropriateness, recurring_evidence_freshness)
10. Eval runner: mode routing in `build_evaluator_list()`, per-mode aggregate breakdowns in `by_mode`
11. Creation eval runner: `verification_mode` extraction + per-mode aggregates

Smoke test confirmed: agent classifies base-002 as `immediate`, report includes `verification_mode` per case and `by_mode` aggregates.

## Decisions Made

### Decision 139: Verification Planner Classifies Mode, Reviewer Confirms

**Source:** This update — verification-modes spec discussion
**Date:** March 27, 2026

The verification_planner (turn 2) classifies `verification_mode` because it needs the mode to build mode-appropriate plan steps. The plan_reviewer (turn 3) independently confirms the mode as a consistency check. On disagreement, the reviewer wins (has more context from the full plan) and a warning is logged. Both the `VerificationPlan` and `PlanReview` Pydantic models include a `verification_mode` field.

### Decision 140: Recurring Interval and Max Snapshots

**Source:** This update — verification-modes design discussion
**Date:** March 27, 2026

Recurring predictions include `recurring_interval` (every_scan/daily/weekly, default daily) and `max_snapshots` (default 30). The scanner checks the last snapshot's `checked_at` against the interval before invoking. Oldest snapshots are pruned when the limit is exceeded. This prevents unbounded DDB item growth for recurring predictions.

## Files Created/Modified

### Created
- `.kiro/specs/verification-modes/` — requirements, design, tasks (all complete)
- `eval/evaluators/verification_at_date_verdict_accuracy.py`
- `eval/evaluators/verification_before_date_verdict_appropriateness.py`
- `eval/evaluators/verification_recurring_evidence_freshness.py`
- `docs/project-updates/33-project-update-verification-modes.md` — this update

### Modified
- `calleditv4/src/models.py` — added verification_mode + recurring_interval to VerificationPlan and PlanReview
- `calleditv4/src/bundle.py` — verification_mode, recurring_interval, max_snapshots in build_bundle() and format_ddb_update()
- `calleditv4/src/main.py` — resolve_verification_mode() + wired through all 4 handler routes
- `calleditv4/src/prompt_client.py` — DEFAULT_PROMPT_VERSIONS (planner→2, reviewer→3)
- `calleditv4-verification/src/main.py` — _build_user_message() includes mode
- `calleditv4-verification/src/prompt_client.py` — DEFAULT_PROMPT_VERSIONS (executor→2)
- `calleditv4-verification/src/bundle_loader.py` — append_verification_snapshot()
- `infrastructure/verification-scanner/scanner.py` — mode-aware scheduling
- `infrastructure/prompt-management/template.yaml` — planner v2, reviewer v3, executor v2
- `eval/golden_dataset.json` — 45→54 cases, verification_mode annotations, expected_mode_counts
- `eval/verification_eval.py` — mode routing, per-mode aggregates
- `eval/creation_eval.py` — verification_mode extraction, per-mode aggregates
- `calleditv4/tests/test_bundle.py` — updated REQUIRED_FIELDS for verification_mode

## What the Next Agent Should Do

### Priority 1: Run Full Eval Baselines with New Modes
Run smoke+judges on creation eval to get the first baseline with mode classification data. The dashboard will show `by_mode` breakdowns automatically.

### Priority 2: Iterate on Mode Classification Prompts
The planner v2 prompt is functional but may not classify edge cases correctly. Run the full creation eval and check which predictions get misclassified. Iterate on the prompt and track improvements in the dashboard.

### Priority 3: Verification Planner Self-Report Plans (Backlog Item 15)
Plan quality baseline is 0.57. The 5 personal/subjective cases average ~0.26. Teaching the planner to build self-report plans is the highest-impact prompt change.

### Priority 4: Tool Action Tracking (Backlog Item 16)
4/7 verification failures are Browser tool inability. Structured tracking would identify which tool to add or prompt to fix next.

### Key Files
- `.kiro/specs/verification-modes/tasks.md` — all 12 tasks complete
- `calleditv4/src/models.py` — VERIFICATION_MODES type alias
- `infrastructure/prompt-management/template.yaml` — planner v2, reviewer v3, executor v2
- `infrastructure/verification-scanner/scanner.py` — mode-aware scheduling
- `eval/golden_dataset.json` — 54 cases with verification_mode annotations
- `eval/verification_eval.py` — mode-aware eval runner
