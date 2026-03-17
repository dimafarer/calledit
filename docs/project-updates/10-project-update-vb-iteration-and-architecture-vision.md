# Project Update 10 — VB Prompt Iteration Results & Architecture Vision

**Date:** March 17, 2026
**Context:** VB prompt v2 results, per-agent evaluator strategy, architecture backend abstraction plan
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/vb-prompt-iteration/` — Spec 9: VB Prompt Iteration (IN PROGRESS — Runs 1-2 complete, Run 3 running)
- `.kiro/specs/verification-evaluators/` — Spec 8: Verification-Centric Evaluators (COMPLETE)
- `.kiro/specs/eval-dashboard/` — Spec 7: Eval Dashboard (COMPLETE)

### Prerequisite Reading
- `docs/project-updates/09-project-update-dashboard-v1-and-eval-reframe.md` — Dashboard v1, eval reframe, Decisions 44-47

---

## VB Prompt v2 Results — Isolated Single-Variable Testing

Three eval runs, each changing exactly one variable:

### Run 1: New Baseline (dataset v3.1, VB v1)
- IntentPreservation: 0.69 | CriteriaMethodAlignment: 0.67
- Establishes baseline with corrected ground truth for 7 subjective predictions

### Run 2: VB v2 (operationalization + specificity matching)
- IntentPreservation: **0.82** (+0.13) | CriteriaMethodAlignment: **0.74** (+0.07)
- IntentPreservation passed the 0.80 target
- VB now operationalizes vague terms into measurable conditions instead of hedging
- Specificity matching improved but CriteriaMethodAlignment still below 0.80

### Run 3: Review v2 (operationalization validation questions)
- Running at time of writing

### Key Insight: Isolated Testing Works
By changing one variable per run, we can attribute score changes precisely:
- Run 1→2 delta: purely from VB prompt changes
- Run 2→3 delta: purely from Review prompt changes
This is the correct methodology for prompt iteration — never change two things at once.

## Per-Agent Evaluator Strategy

Dashboard analysis revealed that we're evaluating structural correctness (JSON validity) and category accuracy, but not whether each agent does its specific job in service of the two system goals.

### Current Evaluators vs What's Needed

| Agent | Current Evaluators | What's Missing |
|---|---|---|
| Parser | JSONValidity | IntentExtraction — did it extract the factual claim and resolve temporal references? |
| Categorizer | CategoryMatch, ReasoningQuality | Adequate (category is tertiary per Decision 44) |
| VB | IntentPreservation, CriteriaMethodAlignment | In good shape after Spec 8 |
| ReviewAgent | ClarificationQuality (keyword, brittle), ReasoningQuality | ClarificationRelevance — do the questions target the VB's assumptions? |

### Priority Order for New Evaluators
1. ClarificationRelevance (ReviewAgent) — measures whether the review loop is useful
2. IntentExtraction (Parser) — parser errors cascade through the whole pipeline
3. Both use Strands Evals SDK OutputEvaluator with targeted rubrics

## Architecture Backend Abstraction

### The Problem
The eval runner is hardcoded to `run_test_graph()` (serial 4-agent graph). We want to test three architectures with the same eval framework:

1. **Serial Graph** (current) — 4 specialized agents in sequence via Strands Graph
2. **Swarm** — agents collaborate iteratively on shared context, multiple rounds
3. **Single Agent** — one powerful model (Opus 4.6) with a comprehensive prompt covering all four steps in one context

### The Insight
The evaluators, golden dataset, DDB persistence, dashboard, and scoring are already architecture-agnostic. They score the output dict regardless of how it was produced. The only coupling is `eval_runner.py` → `run_test_graph()`.

### The Fix
A backend abstraction: `run_backend(prediction_text, tool_manifest, backend="serial")` that returns the same output dict shape regardless of architecture. The eval runner gets a `--backend serial|swarm|single` flag. The report records the architecture tag. The dashboard already has architecture filtering.

### Why Single Agent Might Win
The serial graph has the "silo problem" — agents may re-interpret from scratch rather than building on predecessors. A single agent with one context naturally sees all previous reasoning. The prediction pipeline has never overflowed context even with multiple rounds, so context size isn't a constraint. The eval framework would prove or disprove this with data.

## Decision Log

### Decision 48: Per-Agent Evaluators
Each agent should have at least one evaluator that asks "did this agent do its specific job in service of the two system goals?" Priority: ClarificationRelevance (ReviewAgent), then IntentExtraction (Parser). Both use Strands Evals SDK OutputEvaluator.

### Decision 49: Architecture Backend Abstraction
Add a `--backend serial|swarm|single` flag to the eval runner. Each backend implements the same output contract. The eval framework scores all architectures identically. This enables data-driven architecture comparison.

### Decision 50: Isolated Single-Variable Testing as Standard Practice
Every eval iteration should change exactly one variable (prompt, dataset, or architecture) per run. This is now the standard methodology for all future prompt and architecture experiments.

## What the Next Agent Should Do

1. Complete Run 3 results analysis (Review v2)
2. Spec: Architecture Backend Abstraction + Per-Agent Evaluators
   - Backend abstraction (serial/swarm/single)
   - IntentExtraction evaluator (Parser)
   - ClarificationRelevance evaluator (ReviewAgent)
3. Implement single-agent backend and run comparative eval
4. Continue CriteriaMethodAlignment improvement (currently 0.74, target 0.80)

## Files Created/Modified This Session

### New Files
- `eval/update_subjective_ground_truth.py` — Script to update 7 subjective test case ground truth
- `eval/analyze_v3_scores.py` — Script to rank test cases by verification evaluator scores
- `.kiro/specs/vb-prompt-iteration/` — Spec 9: VB Prompt Iteration (requirements, design, tasks)
- `docs/project-updates/10-project-update-vb-iteration-and-architecture-vision.md` — This document

### Modified Files
- `eval/golden_dataset.json` — v3.1: updated ground truth for 7 subjective predictions
- `infrastructure/prompt-management/template.yaml` — VB v2 prompt + Review v2 prompt + version resources
- `backend/calledit-backend/handlers/strands_make_call/evaluators/intent_preservation.py` — Updated rubric to reward operationalization
- `.gitignore` — Added handler eval reports path
