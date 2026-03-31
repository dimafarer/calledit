# Project Update 36 — Dynamic Golden Dataset Execution

**Date:** March 31, 2026
**Context:** Executed the dynamic golden dataset spec (`.kiro/specs/dynamic-golden-dataset/`). Built the generator, merger, and integrated into all 3 eval runners. Smoke tests passed across all evaluators.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/dynamic-golden-dataset/` — Dynamic Golden Dataset spec (EXECUTED, all 9 tasks complete)

### Prerequisite Reading
- `docs/project-updates/35-project-update-dynamic-golden-dataset-spec.md` — Spec creation context

---

## What Happened

### Housekeeping

1. **Git credential audit** — Scanned recent commits for leaked Cognito credentials. All clean — only `os.environ.get()` references, no hardcoded values. `.env` properly gitignored.
2. **Bashrc cleanup** — Removed `force_deactivate()`, auto-deactivate block, and `reset_venv()` from `~/.bashrc`. These were causing `(venv) W` prompt bleed into Kiro's command output capture on new terminals.

### Dynamic Golden Dataset Spec Execution (9/9 tasks complete)

**Task 1: Static dataset migration + merger**
- Added `time_sensitive: true` to base-010 in `eval/golden_dataset.json`
- Built `eval/dataset_merger.py` with `load_and_merge()` and `merge_datasets()`
- Merger correctly excludes time-sensitive static predictions when dynamic replacements exist
- Backward compatible: `load_and_merge(static_path, None)` returns static-only

**Task 3: Generator core + deterministic templates**
- Built `eval/generate_dynamic_dataset.py` with 16 prediction templates
- 9 deterministic templates (no external deps): weekday check, year parity, month length, "is January", yesterday's day, yesterday weekend, full moon before date, equinox before date, summer solstice before date
- 7 Brave Search templates: US President, Python 3.13 release, yesterday's news, Python 3.12 release date, US national debt, Bitcoin price, Wikipedia accessibility
- Graceful degradation: without `BRAVE_API_KEY`, produces 9 deterministic-only predictions
- Full Brave run produces 16 predictions across all 4 modes

**Task 4: Brave Search templates**
- All templates tested against live Brave API
- Initial parsing issues (US President snippet matching, US debt snippet) fixed by searching across all result snippets instead of just the first
- Pragmatic approach per spec: tried queries, kept what parsed cleanly

**Tasks 6-8: Quality, eval runner integration, validation**
- 6 domains (science, politics, technology, current_events, nature, finance), 3 difficulties (easy, medium, hard)
- Each of immediate/at_date/before_date has ≥1 confirmed + ≥1 refuted verdict
- `--dynamic-dataset` CLI arg added to all 3 eval runners (creation, verification, calibration)
- `dataset_sources` field added to report metadata in all 3 runners
- `validate_dataset.py` extended with `validate_dynamic_dataset()` for dynamic-specific checks

### Smoke Test Results (single case: dyn-imm-001 "Today is a weekday")

| Eval Runner | Result | Key Scores |
|-------------|--------|------------|
| Creation | ✓ | IP=1.00, PQ=0.95, T1=1.00 |
| Verification | ✓ | VA=1.00, T1=1.00 |
| Calibration | ✓ | CA=1.00, score=0.95→confirmed |

All 3 runners correctly loaded the merged dataset (55 static - 1 replaced + 16 dynamic = 70 predictions), executed against the deployed AgentCore agents, and produced valid reports with `dataset_sources` metadata.

### Dataset Composition (with Brave API)

| Mode | Count | Confirmed | Refuted | Sources |
|------|-------|-----------|---------|---------|
| immediate | 6 | 5 | 1 | 4 deterministic, 2 brave |
| at_date | 3 | 2 | 1 | 2 deterministic, 1 brave |
| before_date | 4 | 3 | 1 | 3 deterministic, 1 brave |
| recurring | 3 | 3 | 0 | 3 brave |
| **Total** | **16** | **13** | **3** | **9 det, 7 brave** |

Merged dataset: 70 predictions (54 static + 16 dynamic, base-010 replaced by dyn-bfd-001).

## Files Created/Modified

### Created
- `eval/dataset_merger.py` — `load_and_merge()`, `merge_datasets()`, time-sensitive replacement logic
- `eval/generate_dynamic_dataset.py` — 16 templates, Brave Search integration, validation, CLI entry point
- `eval/dynamic_golden_dataset.json` — Generated output (gitignored, regenerated before each eval)
- `docs/project-updates/36-project-update-dynamic-golden-dataset-execution.md` — This update

### Modified
- `eval/golden_dataset.json` — Added `time_sensitive: true` to base-010
- `eval/creation_eval.py` — `--dynamic-dataset` arg, `load_and_merge()`, `dataset_sources` in metadata
- `eval/verification_eval.py` — Same changes
- `eval/calibration_eval.py` — Same changes
- `eval/validate_dataset.py` — Added `validate_dynamic_dataset()` function

## What the Next Agent Should Do

### Priority 1: Run Full Baselines with Merged Dataset
Run all 3 eval frameworks with `--dynamic-dataset eval/dynamic_golden_dataset.json`:
- Creation: `source .env && python eval/creation_eval.py --dataset eval/golden_dataset.json --dynamic-dataset eval/dynamic_golden_dataset.json --tier full --description "full baseline with dynamic dataset"`
- Verification: same pattern
- Calibration: same pattern

Compare against previous baselines (Update 34): Creation IP=0.79, Verification VA=0.71, Calibration CA=0.86.

### Priority 2: Debug AgentCore Browser Tool (Backlog Item 17)
Still open. Browser works via direct API but fails in deployed runtime.

### Priority 3: Verification Planner Self-Report Plans (Backlog Item 15)
Plan quality is 0.56-0.58. Personal/subjective cases average ~0.26.
