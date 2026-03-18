# Project Update 10 — Verification Builder Prompt Iteration Results, Per-Agent Evaluator Expansion & Architecture Vision

**Date:** March 17, 2026
**Context:** Verification Builder prompt v2 results, complete per-agent LLM judge strategy, pluggable backend abstraction, evaluation philosophy evolution
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/vb-prompt-iteration/` — Spec 9: VB Prompt Iteration (COMPLETE — all 3 runs done)
- `.kiro/specs/verification-evaluators/` — Spec 8: Verification-Centric Evaluators (COMPLETE)
- `.kiro/specs/eval-dashboard/` — Spec 7: Eval Dashboard (COMPLETE)
- `.kiro/specs/architecture-eval-expansion/` — Spec 10: Architecture Backend Abstraction + Per-Agent Evaluators (COMPLETE — all code tasks done, ready for full comparative runs)

### Prerequisite Reading
- `docs/project-updates/09-project-update-dashboard-v1-and-eval-reframe.md` — Dashboard v1, eval reframe, Decisions 44-47
- `docs/project-updates/decision-log.md` — All 55 decisions consolidated in one file

---

## The Two System Goals (Read This First)

Every evaluation decision in this project drives toward these two goals:

1. **Understand the full intent** of the user's raw prediction. "I bet the sun rises tomorrow" means "the sun will rise tomorrow" — the "I bet" is framing, not intent.
2. **Repackage with 100% intent preservation** in a structure that enables an agent to verify it at the right time. The output is a complete verification plan: what to check, where to check it, what criteria to use, and when to check.

The Verification Builder's output (verification criteria + verification method) is the primary eval target — it's what the verification agent will actually use when checking if a prediction came true. The category label is just a routing hint. Every other agent is evaluated by how well it sets up the Verification Builder to succeed.

---

## Verification Builder Prompt v2 Results — Isolated Single-Variable Testing

Three eval runs, each changing exactly one variable:

### Run 1: New Baseline (dataset v3.1, Verification Builder v1)
- IntentPreservation: 0.69 | CriteriaMethodAlignment: 0.67
- Establishes baseline with corrected ground truth for 7 subjective predictions

### Run 2: Verification Builder v2 (operationalization + specificity matching)
- IntentPreservation: **0.82** (+0.13) | CriteriaMethodAlignment: **0.74** (+0.07)
- IntentPreservation passed the 0.80 target
- Verification Builder now operationalizes vague terms into measurable conditions instead of hedging
- Specificity matching improved but CriteriaMethodAlignment still below 0.80

### Run 3: Review v2 (operationalization validation questions)
- Overall pass rate: **40%** (+4.4% from Run 2's 35%)
- IntentPreservation: **0.80** (held steady — Verification Builder v2 gains stable)
- CriteriaMethodAlignment: **0.73** (flat from Run 2's 0.74 — expected, Review prompt doesn't directly affect Verification Builder method quality)
- Per-category: auto_verifiable 100%, automatable 71%, human_only 94% (all unchanged)
- Changed prompt: review 1 → 2
- The +4.4% overall from just a Review prompt change suggests the review questions are now more targeted (operationalization validation), which helps the judge score the overall pipeline higher
- CriteriaMethodAlignment at 0.73 is the next target — the per-agent evaluators from Spec 10 will help identify exactly where method quality breaks down

### Key Insight: Isolated Testing Works
By changing one variable per run, we can attribute score changes precisely:
- Run 1→2 delta: purely from Verification Builder prompt changes (+0.13 IntentPreservation, +0.07 CriteriaMethodAlignment)
- Run 2→3 delta: purely from Review prompt changes (+4.4% overall pass rate, verification scores stable)
This is the correct methodology for prompt iteration — never change two things at once.

---

## Evaluation Philosophy Evolution — Three Phases

The eval framework has evolved through three distinct phases. Understanding this evolution is critical for the next agent.

### Phase 1: Categorization Focus (Spec 5)
The first eval framework focused on whether the categorizer picked the right label (auto_verifiable / automatable / human_only). CategoryMatch was the primary metric. Static/deterministic evaluators dominated.

### Phase 2: Verification Criteria Focus (Spec 8, Decision 44)
Walking through the dashboard data revealed that categorization is a minor metric. When the verification pipeline reviews a prediction in the future to decide if it's true or false, the category label is just a routing hint. The pipeline will look at the verification criteria and method, and work to verify that. IntentPreservation and CriteriaMethodAlignment became the primary metrics.

### Phase 3: Complete Per-Agent LLM Judge Coverage (Spec 10, this session)
The next insight: we had two good global evaluators (IntentPreservation, CriteriaMethodAlignment) scoring the Verification Builder's output, but we weren't evaluating whether each upstream agent was producing the right data for the next step. Static evaluators (CategoryMatch, JSONValidity, ClarificationQuality) catch structural regressions but don't answer the real question: "Is this agent contributing to the goal?"

Every agent now gets an LLM judge asking one question: "Is this agent's output contributing to the Verification Builder producing the best possible verification plan?"

---

## Per-Agent Evaluator Map (Complete After Spec 10)

| Agent | Evaluator | Type | Question It Answers |
|---|---|---|---|
| Parser | **IntentExtraction** | LLM Judge | Did it extract the factual claim, strip framing, resolve temporal refs — giving the Verification Builder clean intent to work with? |
| Categorizer | **CategorizationJustification** | LLM Judge | Given the parser output and available tools, does this routing decision set up the Verification Builder to build the most automated, actionable verification plan possible? |
| Verification Builder | IntentPreservation | LLM Judge | Does the Verification Builder's criteria faithfully capture the user's original intent as checkable conditions? (EXISTS — Spec 8) |
| Verification Builder | CriteriaMethodAlignment | LLM Judge | Does the Verification Builder's method provide a realistic plan to determine true/false? (EXISTS — Spec 8) |
| ReviewAgent | **ClarificationRelevance** | LLM Judge | Do the questions target the Verification Builder's specific operationalization assumptions rather than being generic? |
| Cross-Pipeline | **PipelineCoherence** | LLM Judge | Does each agent build on the previous agent's work, or are they re-interpreting from scratch (the silo problem)? |

**Bold** = new in Spec 10. Non-bold = already exist.

### What Existing Evaluators Become
- **CategoryMatch** (deterministic) → cheap regression check, no longer in primary pass rate
- **JSONValidity** (deterministic) → cheap regression check, still useful
- **ClarificationQuality** (keyword-based) → replaced by ClarificationRelevance as primary review eval
- **ReasoningQuality** (old generic LLM judge) → superseded by the targeted per-agent judges above
- **Convergence** (deterministic) → still useful for fuzzy prediction testing

---

## Architecture Backend Abstraction — Pluggable Design

### The Problem
The eval runner is hardcoded to `run_test_graph()` (serial 4-agent graph). We want to test different architectures with the same eval framework.

### The Design: Pluggable Backends
Instead of a hardcoded `--backend serial|swarm|single` enum, backends are pluggable modules in a `backends/` directory. Each module implements `run(prediction_text, tool_manifest) -> OutputContract` and `metadata() -> dict`. Adding a new architecture (2-agent, 5-agent, whatever) means dropping a new module — no changes to the eval runner.

### Flexible Output Contract
The output contract adapts to any number of agents:
- **Required:** `final_output` — the verification criteria and method (what evaluators actually score)
- **Optional:** `agent_outputs` — dict with whatever agent keys the backend produces. The serial backend has `parser`, `categorizer`, `verification_builder`, `review`. A single-agent backend has just `agent`. A 2-agent backend might have `parser_categorizer`, `vb_review`.
- **Required:** `metadata` — architecture name, model_config, execution_time, backend-specific data

Per-agent evaluators adapt: IntentExtraction only runs when `parser` key exists, CategorizationJustification only when `categorizer` exists, etc. PipelineCoherence evaluates whatever agents are present. IntentPreservation and CriteriaMethodAlignment always run against `final_output` regardless of architecture.

### Three Initial Backends
1. **Serial** (default) — wraps existing `run_test_graph()`, 4 agent keys
2. **Single** — one Opus 4.6 call, comprehensive prompt, 1 agent key
3. **Swarm** — collaborative multi-round, multiple agent keys + round count

### Why This Matters
The serial graph has the "silo problem" — agents may re-interpret from scratch rather than building on predecessors. A single agent with one context naturally sees all previous reasoning. The PipelineCoherence evaluator will quantify this difference. The eval framework proves or disproves architecture hypotheses with data.

---

## Decision Log

### Decision 48: Per-Agent Evaluators
Each agent should have at least one LLM judge evaluator asking "did this agent do its specific job in service of the two system goals?" All use Strands Evals SDK OutputEvaluator with targeted rubrics.

### Decision 49: Architecture Backend Abstraction
Pluggable backend system — each backend is a module in `backends/` implementing `run()` and `metadata()`. The eval runner discovers backends automatically. Adding a new architecture requires zero changes to the eval runner, evaluators, or dashboard.

### Decision 50: Isolated Single-Variable Testing as Standard Practice
Every eval iteration should change exactly one variable (prompt, dataset, or architecture) per run. This is now the standard methodology for all future prompt and architecture experiments.

### Decision 51: CategorizationJustification Evaluator — Verification-Builder-Centric Routing Assessment
The Categorizer's evaluation shifts from "did it pick the right label?" (CategoryMatch) to "did its routing decision enable the Verification Builder to produce the best possible verification plan?" The LLM judge sees parser output, categorizer output, tool manifest, AND Verification Builder output — assessing downstream impact. CategoryMatch remains as a cheap deterministic check but is no longer weighted in the primary pass rate.

### Decision 52: PipelineCoherence Evaluator — Quantifying the Silo Problem
A cross-agent LLM judge that sees all agent outputs together and scores whether each agent built on the previous agent's work. Adapts to any number of agents. Critical for architecture comparison — quantifies whether the single-agent backend produces more coherent output than the serial graph.

### Decision 53: Verification-Builder-Centric Composite Score
The eval report computes a "Verification-Builder-centric score" — a weighted composite where IntentPreservation and CriteriaMethodAlignment have the highest weight, and other evaluators are weighted by how directly they impact Verification Builder output quality. Replaces the old overall pass rate as the primary metric.

### Decision 54: Consolidated Decision Log
Created `docs/project-updates/decision-log.md` containing all decisions extracted from all project updates. Future agents can read this one file instead of scanning all project updates.

### Decision 55: Pluggable Backend with Flexible Output Contract
Backends are extensible — any architecture (2-agent, 5-agent, etc.) can be added by dropping a module in `backends/`. The output contract requires `final_output` (what evaluators score) and optional `agent_outputs` (whatever agents the backend has). Per-agent evaluators only run when their target agent key exists. This means the eval framework never needs to change when you experiment with new architectures.

---

## What the Next Agent Should Do

1. **Complete Run 3 results analysis** (Review v2) if not already done
2. **Generate design.md** for `.kiro/specs/architecture-eval-expansion/` from the requirements (11 requirements: pluggable backends, flexible output contract, 4 new evaluators, dashboard updates, eval runner integration)
3. **Generate tasks.md and execute.** Priority order:
   - New evaluators first (Reqs 6-9, 11) — can test immediately with existing serial backend
   - Backend abstraction (Reqs 1-5) — enables architecture comparison
   - Dashboard updates (Req 10) — visualize the comparison
4. **After implementation**, run comparative eval: serial vs single-agent with all 6 LLM judges
5. **Continue CriteriaMethodAlignment improvement** (currently 0.74, target 0.80)

### Key Context for the Next Agent

- The eval framework is the real learning artifact here — building a proper evaluation framework for multi-agent systems is what matters most
- The Verification Builder's output is what the verification agent will use at verification time — everything else serves the Verification Builder
- Static evaluators are cheap regression catches, LLM judges are the real signal
- The pluggable backend design means you can experiment with any architecture without touching the eval framework
- Read `docs/project-updates/decision-log.md` for the full decision history (Decisions 1-55)
- Read `docs/project-updates/09-project-update-dashboard-v1-and-eval-reframe.md` for the Phase 2 reframe context

### Key Files

- `.kiro/specs/architecture-eval-expansion/requirements.md` — Spec 10 requirements (start here)
- `backend/calledit-backend/handlers/strands_make_call/evaluators/` — Existing evaluators (7 files)
- `backend/calledit-backend/handlers/strands_make_call/eval_runner.py` — Eval runner CLI
- `backend/calledit-backend/handlers/strands_make_call/test_prediction_graph.py` — Standalone test graph (current serial backend)
- `eval/golden_dataset.json` — Golden dataset v3.1
- `eval/dashboard/` — Streamlit dashboard
- `infrastructure/prompt-management/template.yaml` — Bedrock Prompt Management stack

---

## Complete Eval Run History

This chart shows every eval run across the project, what changed in each, and the results. Use this to choose which runs are most interesting to re-run with the new per-agent judges and to run on the single backend for architecture comparison.

| # | Date | Dataset | Prompts (P/C/VB/R) | Judge | Architecture | Pass Rate | auto_v | auto_m | human | IP | CMA | What Changed | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Mar 15 16:50 | v2.0 | DRAFT/DRAFT/DRAFT/DRAFT | No | serial | 68% | 100% | 93% | 76% | — | — | V2 dataset baseline | First v2 run, deterministic only |
| 2 | Mar 15 18:07 | v2.0 | DRAFT/DRAFT/DRAFT/DRAFT | Yes | serial | 51% | 100% | 100% | 82% | — | — | Added Opus 4.6 judge | Judge drops pass rate by catching reasoning issues |
| 3 | Mar 15 19:26 | v2.0 | DRAFT/**2**/DRAFT/DRAFT | Yes | serial | 38% | 100% | **71%** | **88%** | — | — | Categorizer v2 (expanded human_only) | human_only ↑ but automatable regressed |
| 4 | Mar 15 23:49 | v2.0 | **1**/**2**/**1**/**1** | Yes | serial | 35% | 100% | 86% | 94% | — | — | Pinned all prompts to numbered versions | DDB float fix, proper version tracking |
| 5 | Mar 16 21:41 | **v3.0** | 1/2/1/1 | Yes | serial | 34% | 100% | 86% | 100% | — | — | Dataset v3 (verification criteria ground truth) | New evaluators: IntentPreservation, CriteriaMethodAlignment |
| 6 | Mar 16 23:50 | v3.0 | 1/**1**/1/1 | Yes | serial | 34% | 100% | 86% | 82% | — | — | Categorizer reverted to v1 | Testing categorizer v1 vs v2 effect |
| 7 | Mar 17 14:24 | **v3.1** | 1/2/1/1 | Yes | serial | 32% | 100% | 71% | 88% | 0.69 | 0.67 | Dataset v3.1 (7 subjective ground truth fixes) | New baseline for Verification Builder iteration |
| 8 | Mar 17 16:14 | v3.1 | 1/2/**2**/1 | Yes | serial | 35% | 100% | 71% | 94% | **0.82** | **0.74** | **Verification Builder v2** (operationalization) | IP passed 0.80 target! CMA improved but below 0.80 |
| 9 | Mar 17 19:24 | v3.1 | 1/2/2/**2** | Yes | serial | **40%** | 100% | 71% | 94% | 0.80 | 0.73 | **Review v2** (operationalization validation) | +4.4% from Review prompt alone |
| 10 | Mar 17 23:41 | v3.1 | 1/2/2/2 | Yes | serial | — | 100% | — | — | 0.90 | 0.70 | Spec 10 smoke test (1 prediction, all 6 judges) | First run with per-agent judges + VB-centric score |
| 11 | Mar 18 00:15 | v3.1 | 1/2/2/2 | No | serial | 100% | 100% | — | — | — | — | Serial backend smoke test (model_id wiring) | Validated model override threading |
| 12 | Mar 18 00:42 | v3.1 | 1/2/2/2 | No | **single** | 100% | 100% | — | — | — | — | **Single backend smoke test** (multi-prompt conversation) | First single-agent run, same prompts from Prompt Management |

**Legend:** P=Parser, C=Categorizer, VB=Verification Builder, R=Review, IP=IntentPreservation, CMA=CriteriaMethodAlignment. Bold = what changed from previous run.

### Recommended Re-Runs for Architecture Comparison

The most interesting runs to re-run with full per-agent judges on both serial and single backends:

1. **Run 9 config** (1/2/2/2 + judge) — current best prompts, full dataset. This is the apples-to-apples comparison: same prompts, same model, same dataset, different architecture.
2. **Run 7 config** (1/2/1/1 + judge) — pre-Verification Builder iteration baseline. Shows whether the single agent benefits more or less from prompt improvements than the serial graph.
3. **Run 3 config** (DRAFT/2/DRAFT/DRAFT + judge) — the categorizer v2 run that caused the automatable regression. Does the single agent handle the expanded human_only definition better than the serial graph?

### Decision 56: Single Backend Uses Same Prompts via Prompt Management
The single backend creates one agent that receives the same 4 prompts from Bedrock Prompt Management as sequential conversation turns. The agent maintains its own context across turns — no silo problem by design. This is a fairer comparison than a single mega-prompt because the only variable is context propagation (graph-managed vs natural conversation).

### Decision 57: Tools Should Be Architecture-Agnostic (Future)
Currently tools (web_search, parse_relative_date) are imported from agent-specific modules. They should live as MCP tools or A2A services so any backend architecture can use them without coupling to specific agent code. Future spec when the eval framework proves which architecture works best.

---

## Files Created/Modified This Session

### New Files
- `eval/update_subjective_ground_truth.py` — Script to update 7 subjective test case ground truth
- `eval/analyze_v3_scores.py` — Script to rank test cases by verification evaluator scores
- `.kiro/specs/vb-prompt-iteration/` — Spec 9: Verification Builder Prompt Iteration (requirements, design, tasks)
- `.kiro/specs/architecture-eval-expansion/` — Spec 10: Architecture Backend Abstraction + Per-Agent Evaluators (requirements, design, tasks — all code complete)
- `docs/project-updates/decision-log.md` — Consolidated decision log (Decisions 1-57, extracted from all project updates)
- `backend/calledit-backend/handlers/strands_make_call/backends/__init__.py` — OutputContract, discover_backends(), validate_output_contract()
- `backend/calledit-backend/handlers/strands_make_call/backends/serial.py` — Serial backend (wraps run_test_graph)
- `backend/calledit-backend/handlers/strands_make_call/backends/single.py` — Single-agent backend (4 prompt-managed steps in conversation)
- `backend/calledit-backend/handlers/strands_make_call/evaluators/intent_extraction.py` — Parser LLM judge
- `backend/calledit-backend/handlers/strands_make_call/evaluators/categorization_justification.py` — Categorizer LLM judge
- `backend/calledit-backend/handlers/strands_make_call/evaluators/clarification_relevance.py` — ReviewAgent LLM judge
- `backend/calledit-backend/handlers/strands_make_call/evaluators/pipeline_coherence.py` — Cross-agent coherence LLM judge

### Modified Files
- `eval/golden_dataset.json` — v3.1: updated ground truth for 7 subjective predictions
- `infrastructure/prompt-management/template.yaml` — Verification Builder v2 prompt + Review v2 prompt + version resources
- `backend/calledit-backend/handlers/strands_make_call/evaluators/intent_preservation.py` — Updated rubric to reward operationalization
- `backend/calledit-backend/handlers/strands_make_call/eval_runner.py` — Pluggable backend dispatch, --backend/--model/--list-backends CLI, per-agent judge integration, Verification-Builder-centric composite score, report schema updates
- `backend/calledit-backend/handlers/strands_make_call/parser_agent.py` — Added model_id parameter to create_parser_agent()
- `backend/calledit-backend/handlers/strands_make_call/categorizer_agent.py` — Added model_id parameter to create_categorizer_agent()
- `backend/calledit-backend/handlers/strands_make_call/verification_builder_agent.py` — Added model_id parameter to create_verification_builder_agent()
- `backend/calledit-backend/handlers/strands_make_call/review_agent.py` — Added model_id parameter to create_review_agent()
- `backend/calledit-backend/handlers/strands_make_call/test_prediction_graph.py` — Added model_id parameter to _create_test_graph() and run_test_graph()
- `eval/dashboard/sidebar.py` — Added architecture filter
- `eval/dashboard/pages/trends.py` — Added Verification-Builder-centric score chart, architecture in hover data
- `eval/dashboard/pages/prompt_correlation.py` — Added architecture comparison banner
- `eval/dashboard/pages/heatmap.py` — Updated judge evaluator detection for new evaluators
- `.gitignore` — Added handler eval reports path
- `docs/project-updates/10-project-update-vb-iteration-and-architecture-vision.md` — This document
