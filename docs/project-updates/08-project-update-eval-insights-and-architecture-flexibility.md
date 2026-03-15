# Project Update 08 — Eval Suite Insights & Architecture Flexibility

**Date:** March 15, 2026
**Context:** Critical insights from reviewing the eval suite against the system's two core goals, plus architectural flexibility requirements for future testing
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/golden-dataset-v2/` — Spec 6: Golden Dataset V2 (COMPLETE — all 10 tasks executed)
- `.kiro/specs/prompt-eval-framework/` — Spec 5: Prompt Evaluation Framework

### Prerequisite Reading
- `docs/project-updates/05-project-update-eval-strategy.md` — Eval strategy decisions
- `docs/project-updates/06-project-update-eval-framework-execution.md` — Baseline results (v1 dataset)
- `docs/project-updates/07-project-update-golden-dataset-design.md` — Golden dataset v2 design + content creation cycle

---

## The Two System Goals

Every decision about the eval framework — what to test, how to score, what to display — should drive toward these two goals:

1. **Understand the full intent of the user's raw prediction.** The system must extract what the person actually means, not just what they literally said. "I bet the sun rises tomorrow" means "the sun will rise tomorrow" — the "I bet" is framing, not intent.

2. **Repackage the prediction with 100% intent preservation in a structure that enables an agent to verify it at the right time.** The output isn't just a category label — it's a complete verification plan: what to check, where to check it, what criteria to use, and when to check. The repackaging must preserve the user's original intent while making it machine-actionable.

These goals reframe how we evaluate every agent in the pipeline. The parser's job is intent extraction. The categorizer's job is determining the verification path. The VB's job is building the verification plan. The ReviewAgent's job is catching when intent would be lost or the verification plan has gaps.

## Insight 1: Agent Prompt Review Against the Two Goals

We reviewed all four agent prompts against the two goals. Key findings:

### Parser Prompt — Mostly Aligned, One Gap
The prompt says "Extract the user's EXACT prediction statement (no modifications)" — good for intent preservation. But it's too literal. The parser should extract the *intent* and resolve temporal references, not just echo text back. "I bet the sun rises tomorrow" should become "The sun will rise tomorrow" — the intent, not the framing.

**Status:** Not changing yet. Testing with boundary case base-040 ("I bet the sun rises tomorrow") will show whether the model already handles this despite the prompt's literal framing.

### Categorizer Prompt — Narrow human_only Definition
The human_only description says "Requires subjective judgment or information that cannot be obtained through any tool or stored context." But our golden dataset has predictions that are human_only because of *private data access* (promotion, exam results, marathon PR) or *physical observation requirements* (Tom's shirt, soufflé), not subjectivity.

**Status:** Planned prompt change for Run 3. Expanding human_only to: "Requires one or more of: (a) subjective judgment that no tool can assess, (b) direct physical observation of a specific person/place/event, or (c) private personal information not accessible through any API."

### VB Prompt — Missing Temporal Awareness (Weakest Link for Goal 2)
The VB prompt says "Create detailed verification plans" but doesn't address WHEN to verify. For human_only predictions, the VB should produce "schedule a reminder for the user at [time] to self-report." For automatable predictions, "when [tool] becomes available, execute these steps." The current prompt produces generic plans without temporal awareness.

**Status:** Not changing yet. Establishing baseline first, then iterating.

### ReviewAgent Prompt — Biggest Gap
The ReviewAgent focuses on "sections that could be improved with more user information" but doesn't frame this in terms of the two goals. It should ask: "Is there ambiguity in the user's intent that would cause the verification plan to verify the wrong thing?" Run 3 baseline (v1) showed judge scores of 0.3-0.55 for ReviewAgent — generic questions that don't target prediction-specific ambiguity.

**Status:** Not changing yet. This is the primary improvement target after the categorizer fix.

### CategoryMatch Evaluator — V2 Field Name Bug (Fixed)
The evaluator looked for `verifiable_category` in expected outputs but v2 uses `expected_category`. Fixed with a fallback: checks `expected_category` first, falls back to `verifiable_category`.

**Status:** Fixed in this session. Same fix applied to Convergence evaluator.

## Insight 2: Serial Graph Data Flow — The Silo Problem

The 4-agent graph is serial: Parser → Categorizer → VB → ReviewAgent. Strands Graph propagates data automatically — each agent receives the original prompt plus all upstream agents' outputs. But the agent prompts don't explicitly instruct agents to BUILD ON the previous agent's output.

The result: agents may be re-interpreting the original prediction from scratch rather than building on what the previous agent produced. The categorizer might ignore the parser's extracted date. The VB might ignore the categorizer's category reasoning. They're receiving the upstream data but not necessarily using it.

**Evidence from v2 baseline (Run 1):**
- 68% overall pass rate (46/68)
- auto_verifiable: 100% — model nails these
- automatable: 93% — one repeat offender (base-018 DR baseball, same as v1)
- human_only: 76% — misclassifications suggest the categorizer isn't considering the full context

**What the dashboard needs to show:** Not just each agent's output, but whether each agent's output is coherent with and builds upon the previous agent's output. The chain of reasoning: parser extracted X → categorizer used X to determine Y → VB used Y to build Z. When that chain breaks, we need to see it.

## Insight 3: Architecture Flexibility — Serial vs Swarm vs Single Agent

Three architecture variants should be testable through the same eval framework:

### Variant 1: Serial Graph (Current)
4 specialized agents, each sees previous output. Cheap (Sonnet 4), fast, but agents may work in silos.

### Variant 2: Agent Swarm
Agents collaborate iteratively on a shared output. Each agent works on its piece, then they go multiple rounds improving coherence as they see what each other produced through shared context. More expensive (multiple rounds), but potentially more coherent output.

### Variant 3: Single Agent
One powerful model (Opus 4.6) does everything in one shot with a comprehensive prompt. Most expensive per-call, but no inter-agent coherence problem — one model produces the entire structured output.

### Why This Matters for the Eval Framework
The eval framework is already mostly architecture-agnostic. The evaluators score the final output dict regardless of how it was produced. What we need:

1. **Execution backend abstraction** — `--backend serial|swarm|single` on the eval runner
2. **Architecture tag in eval reports** — so the dashboard can compare runs across architectures
3. **Model config in eval reports** — `{"parser": "sonnet-4", ...}` vs `{"agent": "opus-4.6"}`

The golden dataset doesn't change. The evaluators don't change. The ground truth doesn't change. Only the execution path changes. This is the power of separating the eval framework from the implementation.

**Portfolio angle:** Showing that you can evaluate the same task across fundamentally different AI architectures using a consistent eval framework is rare and valuable.


## Insight 4: Future Personal Context Changes Everything

A planned feature: collecting personal information from users' predictions and clarification answers over time. When built, the agent will have saved personal context (who is Tom? what's the user's commute route? what's their marathon PR?) available for both understanding intent and building verification plans.

This changes the eval framework in two ways:

1. **Category shifts** — Predictions currently classified as human_only (e.g., "I'll PR in the marathon") could shift to automatable or even auto_verifiable if the system knows the runner's previous PR and can check public race results.

2. **Verification plan quality** — The VB can produce much more specific plans when it knows personal context. "Schedule a reminder for Saturday evening" becomes "Check Boston Marathon results for [user_name], compare against their PR of 3:42:15."

The golden dataset's ground truth already notes what personal context would help for each human_only prediction. When the feature is built, we bump the dataset version, update expected categories where personal context changes them, and re-run the eval.

## V2 Baseline Results (Run 1 — Deterministic Only)

**Date:** March 15, 2026
**Dataset:** v2.0 (45 base + 23 fuzzy)
**Prompts:** All DRAFT (bundled constants, not Bedrock Prompt Management)
**Judge:** Disabled (deterministic evaluators only)
**DDB Reasoning Store:** Not deployed for this run

| Metric | Score |
|---|---|
| Overall pass rate | 68% (46/68) |
| auto_verifiable accuracy | 100% (13/13) |
| automatable accuracy | 93% (12/13) |
| human_only accuracy | 76% (10/13) |
| Parser JSON validity | 98% |
| Categorizer JSON validity | 100% |
| VB JSON validity | 100% |

**Key failures:**
- base-018 (DR baseball): categorizer said auto_verifiable, expected automatable. Repeat offender from v1 — categorizer gets over-confident when web_search has sports capabilities.
- Several human_only misclassifications — categorizer's narrow definition of human_only (subjective only) misses physical observation and private data cases.
- Fuzzy predictions: ClarificationQuality scores low (keyword matching is brittle), Convergence scores 0.0 on many cases (expected — most v2 predictions don't have full expected outputs for convergence comparison).

## Eval Run Plan

| Run | Prompts | Judge | Purpose |
|---|---|---|---|
| Run 1 (done) | DRAFT | No | V2 baseline — deterministic scores |
| Run 2 (done) | DRAFT | Yes (Opus 4.6) | Add reasoning quality layer + DDB traces |
| Run 3 (done) | Categorizer v2 | Yes | Measure effect of targeted prompt change |

## Run 2 Results (DRAFT + Judge)

**Date:** March 15, 2026
**Prompt versions:** parser:DRAFT, categorizer:DRAFT, vb:DRAFT, review:DRAFT

| Metric | Run 1 (det) | Run 2 (+ judge) | Delta |
|---|---|---|---|
| Overall pass rate | 68% | 51% | -17% |
| auto_verifiable | 100% | 100% | = |
| automatable | 93% | 100% | +7% |
| human_only | 76% | 82% | +6% |

**Key insight:** The judge drops overall pass rate from 68% → 51% by catching reasoning quality issues the deterministic evaluators miss. Same pattern as v1 Run 2 → Run 3. The gap between deterministic and judge scores is where the interesting work is.

## Run 3 Results (Categorizer v2 + Judge)

**Date:** March 15, 2026
**Prompt versions:** parser:DRAFT, categorizer:2, vb:DRAFT, review:DRAFT
**Change:** Expanded human_only definition to cover physical observation and private data

| Metric | Run 2 (DRAFT) | Run 3 (cat v2) | Delta |
|---|---|---|---|
| Overall pass rate | 51% | 38% | -13% |
| auto_verifiable | 100% | 100% | = |
| automatable | 100% | 71% | -29% |
| human_only | 82% | 88% | +6% |

**Key insight:** The human_only fix worked — 82% → 88%. The expanded definition correctly identifies physical observation and private data cases. But automatable regressed from 100% → 71%. The expanded human_only definition causes the categorizer to over-classify some automatable predictions as human_only — predictions involving personal context ("my flight", "my package") trigger the "private personal information" clause even though they're objectively verifiable with the right API.

**This is exactly the kind of tradeoff the dashboard needs to show:** a prompt change that improves one category but regresses another. The data tells the story.

### Decision 42: Categorizer Prompt Needs Nuance, Not Just Expansion
Simply expanding the human_only definition isn't enough. The categorizer needs to distinguish between "private data that no API can access" (human_only) and "personal data that a known API could access with authentication" (automatable). The 4-category system we discussed earlier would handle this naturally. For now, the prompt needs more precise language about what makes data truly inaccessible vs just not currently accessible.

After Run 3, we spec the eval dashboard with real data from all three runs.

## Decision Log

### Decision 39: Deploy DDB Table Before Judge Run
The judge run produces the most valuable DDB data (full reasoning traces). Running without the table loses that data permanently. Deployed `calledit-eval-reasoning` table via SAM before Run 2.

### Decision 40: Architecture Flexibility as Dashboard Requirement
The dashboard spec should include an "architecture" dimension so eval runs can be compared across serial graph, swarm, and single-agent backends. The eval report schema needs `architecture` and `model_config` fields.

### Decision 41: Eval Framework as Portfolio Centerpiece
The eval suite — golden dataset with ground truth, multi-tier evaluators, DDB reasoning capture, architecture-agnostic scoring, and a visual dashboard — is the transferable skill set. Even if the data shows a single Opus 4.6 agent outperforms the multi-agent graph, the eval framework that proved it is the valuable artifact.

## What the Next Agent Should Do

1. Wait for Run 2 (judge) to complete, analyze results
2. Apply categorizer human_only prompt fix, run Run 3
3. Spec the eval dashboard with data from all 3 runs
4. Dashboard spec should include: trend lines, per-agent drill-down, cross-agent coherence view, architecture comparison, DDB reasoning explorer
5. Consider the silo problem — how to make agents build on each other's output rather than re-interpreting from scratch

## Files Created/Modified This Session

### New Files
- `docs/project-updates/08-project-update-eval-insights-and-architecture-flexibility.md` — This document
- `backend/calledit-backend/handlers/strands_make_call/eval_reasoning_store.py` — DDB reasoning store
- `eval/validate_dataset.py` — Dataset validation script
- `eval/golden_dataset.json` — V2 dataset (45 base + 23 fuzzy)
- `eval/golden_dataset_v1_archived.json` — Archived v1 dataset
- Tests: test_golden_dataset_v2.py, test_validate_dataset.py, test_eval_reasoning_store.py, test_score_history_v2.py

### Modified Files
- `backend/calledit-backend/handlers/strands_make_call/golden_dataset.py` — Rewritten for v2 schema
- `backend/calledit-backend/handlers/strands_make_call/eval_runner.py` — V2 integration + DDB writes
- `backend/calledit-backend/handlers/strands_make_call/score_history.py` — dataset_version tracking
- `backend/calledit-backend/handlers/strands_make_call/evaluators/category_match.py` — V2 field name fix
- `backend/calledit-backend/handlers/strands_make_call/evaluators/convergence.py` — V2 field name fix
- `backend/calledit-backend/template.yaml` — Added EvalReasoningTable DDB resource
