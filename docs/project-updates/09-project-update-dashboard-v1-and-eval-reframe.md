# Project Update 09 — Dashboard V1 Launch & Evaluation Reframe

**Date:** March 16, 2026
**Context:** Eval dashboard v1 is live. Walking through the data with the dashboard revealed a fundamental reframe of what the eval suite should measure.
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/eval-dashboard/` — Spec 7: Eval Dashboard (COMPLETE — all tasks executed)
- `.kiro/specs/verification-evaluators/` — Spec 8: Verification-Centric Evaluators (IN PROGRESS)

### Prerequisite Reading
- `docs/project-updates/08-project-update-eval-insights-and-architecture-flexibility.md` — Eval insights, architecture flexibility, Decisions 39-44
- `docs/eval-framework-comparison.md` — CalledIt custom eval vs Strands Evals SDK comparison

---

## Dashboard V1 — What We Built

Six-page Streamlit dashboard with DDB primary / local file fallback:

1. **Trends** — Overall pass rate and per-category accuracy over time with prompt version annotations
2. **Heatmap** — Per-test-case × per-evaluator score matrix, sorted worst-first, deterministic/judge grouped
3. **Prompt Correlation** — Side-by-side run comparison with category deltas and prompt version diffs
4. **Reasoning Explorer** — Drill into individual test cases: agent outputs, judge reasoning, token counts from DDB
5. **Coherence View** — Deterministic vs judge score agreement/disagreement analysis
6. **Fuzzy Convergence** — Round 1 vs round 2 scores for fuzzy predictions

### Data Sources
- DDB: 3 eval runs with `run_metadata`/`report_summary` + `agent_output` records (92 items total)
- Local: 4 report files in `backend/calledit-backend/handlers/strands_make_call/eval/reports/` + `score_history.json` in both project root and handler directory
- Data loader merges DDB and local sources, deduplicating by timestamp

### Bugs Fixed During Dashboard Build
- **DDB float serialization**: `Inexact` errors from boto3 when writing Python floats. Fixed with `_sanitize_for_ddb()` that recursively converts floats to rounded strings before write.
- **score_history.json missing eval_run_id**: Added `eval_run_id` to `append_score()` in `score_history.py` for future run correlation. Old entries default to empty string.
- **Data loader DDB-only mode**: Original loader only fell back to local when DDB was completely unavailable. Fixed to always merge DDB + local sources and always try local fallback for run detail when DDB has no `test_result` records.
- **Dual report directories**: Eval runner writes to `backend/calledit-backend/handlers/strands_make_call/eval/` (relative to its cwd), dashboard reads from project root `eval/`. Fixed data loader to search both paths.
- **Streamlit module path**: `app.py` now inserts project root into `sys.path` so imports work regardless of launch directory.

## The Reframe: Categorization Is Not the Goal

Walking through the dashboard data — particularly the Trends per-category chart and the Heatmap — surfaced a fundamental insight: we've been optimizing for the wrong metric.

### What We Were Measuring
- CategoryMatch: did the categorizer pick the right label? (auto_verifiable / automatable / human_only)
- JSONValidity: is the output valid JSON?
- ReasoningQuality: is the reasoning well-written? (judge)

### What Actually Matters
The system's two goals are:
1. Understand the full intent of the user's prediction
2. Repackage it with 100% intent preservation into a structure that enables verification at the right time

The category label is just a routing hint. The verification builder's output is what matters: verification criteria (the prediction transformed into checkable conditions) and verification method (a plan for proving true/false).

### The Categorizer Tradeoff That Triggered the Insight
The per-category chart showed the categorizer v2 prompt improving human_only (82% → 88%) while regressing automatable (100% → 71%). We spent significant effort trying to fix categorization boundaries. But the real question is: even when the category is "wrong," does the verification plan still work?

A prediction categorized as "automatable" when it should be "human_only" isn't a failure if the verification builder produces criteria that correctly capture the intent and a method that gracefully degrades to manual verification when automation isn't possible.

### Four Access Patterns Hiding in Three Categories
The conversation identified at least 4 distinct data access patterns:
1. **Publicly available data** (weather, sports, stocks) → auto_verifiable
2. **Personal data via authenticated API** (my flight, my package) → automatable with auth
3. **Third-party personal data** (John's calendar, Tom's email) → human_only unless access granted
4. **Physical observation / subjective** (shirt color, taste) → always human_only

The current 3-category system forces #2 and #3 into the same bucket. But per Decision 44, rather than adding more categories, we're shifting the eval focus to verification criteria quality.

### The Verification Builder as the Key Agent
The VB's job is now clearly defined:
- Transform the prediction into verification criteria (checkable true/false conditions)
- Produce the most automated verification method possible with available tools
- Gracefully degrade: if tools can't automate it, explain how to verify manually, or where to find/build the tool
- At verification time, the verification agent reads the criteria and method, then uses its own reasoning and currently-available tools (which may differ from what the VB assumed)

## New Evaluators Needed

### 1. Intent Preservation Evaluator
Does the verification criteria faithfully capture what the user meant?
- "I bet the Lakers win tonight" → criteria should be "Lakers win their game on [date]" not "user believes Lakers will win"
- The "I bet" is framing, not intent. The criteria must capture the intent.

### 2. Criteria-Method Alignment Evaluator
Given the verification criteria, does the verification method provide a realistic plan to determine true/false?
- If criteria is "Lakers win on March 15" → method should be "check ESPN/NBA API for game result"
- Not "ask the user if the Lakers won" (that's a fallback, not a primary method)

### Evaluator Priority Reframe
| Priority | Evaluator | What It Measures |
|---|---|---|
| PRIMARY | IntentPreservation | Does VB criteria capture the prediction's meaning? |
| PRIMARY | CriteriaMethodAlignment | Does the method enable proving true/false? |
| SECONDARY | JSONValidity | Is the output structurally valid? |
| TERTIARY | CategoryMatch | Did it pick the right routing label? |
| RECALIBRATE | ReasoningQuality | Judge should focus on verification executability, not essay quality |

## Strands Evals SDK Discovery

Discovered that `strands-agents-evals` is a standalone Python package — no AgentCore runtime required. Runs anywhere Python runs, including Lambda. Key capabilities:
- `OutputEvaluator` — LLM-as-judge with custom rubrics (replaces our hand-rolled judge)
- `TrajectoryEvaluator` — tool sequence analysis (addresses the silo problem)
- `Experiment` / `Case` — structured experiment management
- `ExperimentGenerator` — auto-generates test cases from context descriptions

Decision 43: integrate SDK after dashboard v1. Use SDK for evaluation primitives, keep custom code for persistence/versioning/visualization.

Full comparison in `docs/eval-framework-comparison.md`.

## Run 4 Results (Categorizer v2 + Judge, Post-Dashboard)

**Date:** March 15, 2026 (23:49:24Z)
**Prompt versions:** parser:1, categorizer:2, vb:1, review:1
**Dataset:** v2.0 (45 base + 23 fuzzy)

| Metric | Score |
|---|---|
| Overall pass rate | 35% (24/68) |
| auto_verifiable | 100% |
| automatable | 86% |
| human_only | 94% |
| Parser JSON validity | 93% |

This run used the updated eval_runner with DDB float sanitization fix. All record types (report_summary, test_result, agent_output) written successfully.

## Decision Log

### Decision 44: Verification Criteria Is the Primary Eval Target, Not Categorization
(Captured in doc 08 — see full text there)

### Decision 45: Two-Spec Approach for Eval Reframe
Spec 1 (verification-evaluators): Golden dataset v3 + new evaluators + Strands Evals SDK integration. Must come first — can't improve what you can't measure.
Spec 2 (vb-prompt-iteration): Iterate on VB prompt using new evaluators. Depends on Spec 1.

### Decision 46: Judge Rubric Recalibration
The current ReasoningQuality judge may be optimizing for essay quality rather than verification executability. The question "is the reasoning well-written?" should become "would this verification plan succeed at verifying the prediction?" This is a rubric change, not a code change — and maps naturally to Strands `OutputEvaluator` with a targeted rubric.

### Decision 47: Vague Predictions — Operationalize vs Acknowledge
Two types of vague predictions require different VB behavior:
1. **Operationalizable vague terms** ("nice weather", "taste good", "go well"): The VB should auto-fill reasonable measurable thresholds for round 1 (e.g., 60-80°F, sunny, low wind for "nice weather") and the ReviewAgent should ask clarification questions to validate those assumptions ("Do you consider 60°F a nice day? Is sunshine important to you?"). The golden dataset expected_verification_criteria should reflect the operationalized version, not "ask the user."
2. **Truly subjective / unobservable** ("feel happy", "enjoy the movie"): No external proxy exists. The VB should keep these human_only and the ReviewAgent should ask questions that might lead to a verifiable reformulation ("What would make you feel happy? Getting 8 hours of sleep?"). The golden dataset expected_verification_criteria should reflect the self-report approach.

The IntentPreservation evaluator rubric was updated to reward operationalization of vague terms rather than penalizing it. The golden dataset ground truth for operationalizable predictions (starting with base-042) was updated to expect measurable conditions.

## What the Next Agent Should Do

1. Execute `.kiro/specs/verification-evaluators/` — the verification-centric evaluators spec
2. After new evaluators are validated, start Spec 2: VB prompt iteration
3. Re-run eval with new evaluators to establish baseline under the new measurement framework

## Files Created/Modified This Session

### New Files
- `eval/dashboard/` — Complete dashboard (app.py, sidebar.py, data_loader.py, 6 page modules)
- `docs/eval-framework-comparison.md` — CalledIt vs Strands Evals SDK comparison
- `docs/project-updates/09-project-update-dashboard-v1-and-eval-reframe.md` — This document
- `eval/debug_loader.py` — Debug script for data loader testing

### Modified Files
- `requirements.txt` — Added streamlit, plotly
- `backend/calledit-backend/handlers/strands_make_call/eval_reasoning_store.py` — DDB float sanitization
- `backend/calledit-backend/handlers/strands_make_call/score_history.py` — eval_run_id in entries
- `docs/project-updates/08-project-update-eval-insights-and-architecture-flexibility.md` — Decisions 43-44, updated next steps
