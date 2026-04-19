# Next Agent Prompt — Strands Evals SDK Migration

**Date:** April 1, 2026
**Previous session:** Browser tool fix, configurable verification tools, eval baseline with Browser, eval framework deep dive, migration decision. See Updates 37-38.

---

## Session Goal

Complete the design doc for Spec A (if not done), then execute Spec A — the Strands Evals SDK pipeline migration. This is the Python-only work: case loader, evaluators, task function, calibration, CLI runner, report store write, baseline comparison, and old code deletion.

Spec B (dashboard adaptation) comes after Spec A is validated. The specs are at:
- `.kiro/specs/strands-evals-migration/` — Spec A (pipeline, requirements + design + tasks complete)
- `.kiro/specs/strands-evals-dashboard/` — Spec B (dashboard, requirements only — design + tasks after Spec A)

## CRITICAL — Read the Project Updates FIRST

**Before doing anything else**, read these in order:
1. `docs/project-updates/38-project-update-strands-evals-migration-spec.md` — Migration context and rationale
2. `docs/project-updates/37-project-update-browser-tool-debugging.md` — Previous session (Browser fix)
3. `docs/project-updates/project-summary.md` — Current state summary
4. `docs/eval-framework-deep-dive.md` — Current eval framework documentation (what's being replaced)
5. `.kiro/specs/strands-evals-migration/requirements.md` — The 13 requirements

## CRITICAL — Use Your Kiro Powers

You have Strands and AgentCore Kiro powers installed. **Use them heavily for SDK documentation:**
- `strands` power — search docs for Evals SDK: OutputEvaluator, Custom Evaluator, Experiment, Case, ExperimentGenerator, TrajectoryEvaluator, ToolSelectionEvaluator
- `aws-agentcore` power — search docs for AgentCore Evaluations (future integration)
- Do web searches for strands-agents-evals package details if needed

## CRITICAL — Live Documentation Workflow

This project maintains a running narrative across 38+ project updates. After every milestone:
1. Update or create `docs/project-updates/NN-project-update-*.md` with execution results and narrative
2. Update `docs/project-updates/decision-log.md` (current highest: 150)
3. Update `docs/project-updates/project-summary.md`
4. Update `docs/project-updates/backlog.md` if items are addressed or new ones identified

## CRITICAL — This Is a Clean Break

**No backward compatibility.** Delete old eval code. The user hates technical debt. If something can be done better with the SDK, do it the SDK way. Rethink evaluators, report format, and dashboard if it makes more sense.

## What the Strands Evals SDK Provides

### Core Concepts
```
Case(input, expected_output, metadata, session_id)
    ↓
Experiment(cases=[...], evaluators=[...])
    ↓
experiment.run_evaluations(task_function)
    ↓
EvaluationReport → EvaluationOutput(score, test_pass, reason, label)
```

### Built-in Evaluators (8)
1. OutputEvaluator — LLM judge with custom rubric (replaces our hand-rolled judges)
2. HelpfulnessEvaluator — user-perspective helpfulness
3. FaithfulnessEvaluator — grounded in conversation history
4. ToolSelectionEvaluator — tool choice accuracy (could replace backlog item 16)
5. ToolParameterEvaluator — tool parameter accuracy
6. TrajectoryEvaluator — action sequence evaluation (could eval 3-turn flow)
7. InteractionsEvaluator — multi-agent interaction quality
8. GoalSuccessRateEvaluator — end-to-end task completion

### Custom Evaluators
Extend `Evaluator` base class with `evaluate(evaluation_case) -> list[EvaluationOutput]`

### ExperimentGenerator
Auto-generate test cases from context descriptions. Could supplement golden dataset.

## What's Being Replaced

### Current Eval Code (to be deleted)
```
eval/
├── unified_eval.py          # ~700 lines → Experiment.run_evaluations()
├── creation_eval.py         # Legacy runner (already superseded)
├── verification_eval.py     # Legacy runner (already superseded)
├── calibration_eval.py      # Calibration logic → post-experiment analysis
├── compare_runs.py          # Delete
├── analyze_v3_scores.py     # Delete
├── inject_v3_fields.py      # Delete
├── reshape_v4.py            # Delete
├── validate_v4.py           # Delete
├── debug_loader.py          # Delete
├── test_new_evaluators.py   # Delete
├── update_subjective_ground_truth.py  # Delete
├── evaluators/              # 19 files → SDK evaluator classes
│   ├── schema_validity.py   # → Custom Evaluator subclass
│   ├── intent_preservation.py  # → OutputEvaluator(rubric=...)
│   ├── plan_quality.py      # → OutputEvaluator(rubric=...)
│   └── ... (16 more)
└── dashboard/               # Old Streamlit dashboard (already superseded by React)
```

### What's Preserved
```
eval/
├── golden_dataset.json      # Static predictions (loaded as Cases)
├── dynamic_golden_dataset.json  # Dynamic predictions
├── generate_dynamic_dataset.py  # Dataset generator
├── dataset_merger.py        # Static + dynamic merge
├── validate_dataset.py      # Dataset validation
├── report_store.py          # DDB read/write (adapted for SDK format)
├── score_history.json       # Historical scores
├── backends/                # AgentCore backends (JWT + SigV4)
└── reports/                 # Historical report files
```

## Current Baselines (April 1, 2026)

| Metric | Value | Notes |
|--------|-------|-------|
| Creation T1 | 1.00 | All 6 deterministic evaluators pass |
| Creation IP | 0.87 | Intent preservation |
| Creation PQ | 0.81 | Plan quality |
| Verification T1 | 1.00 | All 5 deterministic evaluators pass |
| Verification VA | 0.94 | Verdict accuracy |
| Verification EQ | 0.73 | Evidence quality |
| Calibration CA | 0.95 | Calibration accuracy |

These baselines should be reproduced (within ±0.05 for LLM judges) by the new SDK pipeline.

## Key Values
```
# Creation Agent
CREATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_Agent-AJiwpKBxRW

# Verification Agent
VERIFICATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_verification_Agent-77DiT7GHdH

# Models
SONNET_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0

# Eval DDB Tables
EVAL_TABLE=calledit-v4-eval
EVAL_REPORTS_TABLE=calledit-v4-eval-reports
```

## Import Gotchas (Carried Forward)

- `agentcore launch` and `agentcore invoke` require TTY — ask user to run and paste output
- Both agents currently deployed with `VERIFICATION_TOOLS=browser` and `BRAVE_API_KEY`
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Eval runs require `COGNITO_USERNAME`, `COGNITO_PASSWORD`, `BRAVE_API_KEY` env vars (in `.env`)
- `source .env` before any eval or agent commands
- Install strands-evals: `/home/wsluser/projects/calledit/venv/bin/pip install strands-agents-evals`
- Decision log is at 150, next decision is 151
- Project update is at 38, next is 39

## Testing

- 152 creation agent tests in `calleditv4/tests/`
- 22 verification agent tests in `calleditv4-verification/tests/`
- 12 browser PoC tests in `browser-poc/tests/`
- Unified eval: 22 qualifying cases, ~75 min full run (with Browser)
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`

## Approach

1. **Execute Spec A** — the Strands Evals SDK pipeline migration (20 tasks)
2. **Validate equivalence** — baseline comparison on existing 22 cases (old vs new pipeline)
3. **Delete old code** — clean break
4. **Expand golden dataset** (backlog item 21) — add 10-15 qualifying sports/weather/finance predictions with known historical outcomes. Current dataset is skewed toward calendar math; Brave Search domains are underrepresented.
5. **New expanded baseline** — run full eval on expanded dataset
6. **Execute Spec B** — dashboard adaptation for SDK report format
7. **Document** — decisions, project update, eval deep dive update

### Known Issues to Address
- **Verification agent date anchoring**: The Yankees prediction was correctly parsed as "April 13, 2026 game" but the verification agent searched for "2025 World Series" instead. The verification executor prompt needs to be more explicit about using the exact date from the verification plan in search queries. Consider fixing this during or after the SDK migration.
- **VERIFICATION_TOOLS=both is now deployed** on the verification agent. Brave Search works for sports scores (Knicks: Thunder 111, Knicks 100 — correct). Browser gets blocked by ESPN/MLB.com bot detection. The `both` mode lets the agent fall back to Brave when Browser fails.
