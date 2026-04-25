# Next Agent Prompt — Golden Dataset v5 Cleanup

**Date:** April 24, 2026
**Previous session:** Dashboard bugfixes, verification agent BRAVE_API_KEY fix, CDK permissions stack, dataset analysis, spec creation. See Updates 41-42.

---

## Session Goal

Execute the golden dataset v5 cleanup spec. The requirements, design, and tasks are all complete — just execute the tasks in `.kiro/specs/golden-dataset-v5/tasks.md`.

## CRITICAL — Read These FIRST

1. `.kiro/specs/golden-dataset-v5/tasks.md` — Implementation tasks (execute these)
2. `.kiro/specs/golden-dataset-v5/design.md` — Full design with exact changes
3. `.kiro/specs/golden-dataset-v5/requirements.md` — 9 requirements, 35 acceptance criteria
4. `docs/project-updates/42-project-update-dataset-cleanup-and-agent-fixes.md` — Session context
5. `docs/project-updates/project-summary.md` — Current state

## What Was Already Done This Session (DO NOT REDO)

- Dashboard bugfix spec COMPLETE (`.kiro/specs/continuous-eval-dashboard-fixes/`) — all tasks executed, 134/134 tests
- Verification agent redeployed with BRAVE_API_KEY — resolution_rate jumped 0.25→0.50
- CDK permissions stack deployed (`infrastructure/agentcore-cdk/`) — replaces manual shell script
- Deploy helper scripts created (`calleditv4/deploy.sh`, `calleditv4-verification/deploy.sh`)
- Continuous eval Pass 3 completed: 6/12 smoke cases resolved
- Golden dataset v5 spec fully written (requirements + design + tasks)

## What Needs to Be Done Now

Execute the 6 tasks in `.kiro/specs/golden-dataset-v5/tasks.md`:

### Task 1: Remove duplicates + shorten dates + version bump
- Remove `base-046` and `base-052` from `eval/golden_dataset.json`
- Shorten `base-014` (Bitcoin → "above $90,000 next Friday") and `base-050` (SpaceX → "Starship test flight before May 2026")
- Bump `schema_version` and `dataset_version` to `"5.0"`
- Update metadata counts

### Task 2: Add 5 new recently-happened event predictions
- `base-056`: Hawks defeated Knicks 109-108 in Game 3 (sports, confirmed, smoke_test: true)
- `base-057`: S&P 500 closed above 7,100 on April 23 (finance, confirmed)
- `base-058`: Zohran Mamdani sworn in as NYC Mayor Jan 1, 2026 (politics, confirmed)
- `base-059`: NASA Artemis II launched April 1, 2026 (technology, confirmed)
- `base-060`: Hurricanes defeated Senators 2-1 in Game 3 (sports, confirmed)
- All: `verification_mode: "immediate"`, non-null outcome, complete `ground_truth`
- Optional: property tests for structural validity and metadata consistency

### Task 3: Checkpoint — validate dataset integrity

### Task 4: Remove `template_python_released` from dynamic generator
- File: `eval/generate_dynamic_dataset.py`
- Remove from `get_all_templates()` return list

### Task 5: Update test assertions
- `eval/tests/test_case_loader.py`:
  - static count: 55 → 58
  - merged count: 70 → 72
  - qualifying static: 7 → 11
  - qualifying merged: 22 → 25
  - smoke count: 12 → 13

### Task 6: Final checkpoint — run full test suite

## Key Files

| File | Purpose |
|------|---------|
| `eval/golden_dataset.json` | Main dataset — modify this |
| `eval/generate_dynamic_dataset.py` | Dynamic generator — remove dyn-imm-005 template |
| `eval/tests/test_case_loader.py` | Test assertions — update counts |
| `eval/case_loader.py` | Case loader — DO NOT MODIFY |
| `eval/dataset_merger.py` | Dataset merger — DO NOT MODIFY |

## After Dataset Changes — Run Full Continuous Eval

```bash
cd /home/wsluser/projects/calledit && source .env

# Delete old continuous state (smoke-only, 12 cases)
rm -f eval/continuous_state.json

# Run full continuous eval with new dataset
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --continuous --max-passes 1 --tier full \
    --description "Full baseline with dataset v5"
```

This creates all ~72 cases and runs one verification pass. Takes 60-90 minutes.

## Dataset Schema Reference

Each new prediction follows this structure:
```json
{
  "id": "base-0XX",
  "prediction_text": "...",
  "difficulty": "easy",
  "ground_truth": {
    "verifiability_reasoning": "...",
    "date_derivation": "Immediate — event already occurred",
    "verification_sources": ["..."],
    "objectivity_assessment": "objective",
    "verification_criteria": ["..."],
    "verification_steps": ["..."],
    "verification_timing": "Verifiable immediately",
    "expected_verification_criteria": ["..."],
    "expected_verification_method": "Web search for event results"
  },
  "dimension_tags": {
    "domain": "sports|finance|politics|technology",
    "stakes": "low",
    "time_horizon": "past",
    "persona": "sports_fan|investor|news_follower|tech_enthusiast"
  },
  "evaluation_rubric": "...",
  "is_boundary_case": false,
  "boundary_description": null,
  "verification_readiness": "immediate",
  "expected_verifiability_score_range": [0.8, 1.0],
  "expected_verification_outcome": "confirmed",
  "smoke_test": false,
  "verification_mode": "immediate"
}
```

## Important Context

- **Personal/subjective cases (base-027 through base-045)**: Keep ALL of them. They're sad-path baselines now and future memory integration test cases.
- **BRAVE_API_KEY**: Already deployed to verification agent. No action needed.
- **Dev server**: `cd frontend-v4 && npm run dev` — runs at http://localhost:5173/eval
- **All Python tests**: `/home/wsluser/projects/calledit/venv/bin/python -m pytest eval/tests/ -v`

## Decisions and Docs

- **Decision log:** at 158, next is 159
- **Project update:** at 42, next is 43
- After completing the dataset changes, create Update 43 and update project-summary.md
