# Project Update 38 — Strands Evals SDK Migration Spec

**Date:** April 1, 2026
**Context:** After fixing the Browser tool and running the first Browser baseline, we evaluated whether our custom eval framework was the right approach. It wasn't. Speccing the migration to the Strands Evals SDK.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/strands-evals-migration/` — Strands Evals SDK Migration spec (requirements complete, design + tasks pending)

### Prerequisite Reading
- `docs/project-updates/37-project-update-browser-tool-debugging.md` — Previous session context
- `docs/eval-framework-deep-dive.md` — Current eval framework documentation

---

## What Happened

### The Realization

After the Browser tool fix, we were updating the eval framework documentation and the README. The user asked a pointed question: "I thought we are using AgentCore evaluators for our LLM judges already?" We weren't. The LLM judges are hand-rolled Strands agents calling Bedrock models with rubric prompts and manual JSON parsing. The "three-layer eval architecture" from the original v4 design (Decision 89) was aspirational — only one layer was ever built, and it was custom code.

We activated the Strands and AgentCore Kiro powers and did a deep research session. What we found:

### The Strands Evals SDK — What It Actually Offers

The SDK provides a complete evaluation framework that maps almost exactly to what we built by hand:

```
┌─────────────────────────────────────────────────────────────┐
│                    Strands Evals SDK                         │
│                                                             │
│  Case ──────────── Our golden dataset predictions           │
│  Experiment ────── Our unified_eval.py orchestration        │
│  OutputEvaluator ─ Our hand-rolled LLM judges               │
│  Custom Evaluator  Our deterministic evaluators             │
│  EvaluationOutput  Our {score, pass, reason} dicts          │
│  ExperimentGen ─── Could supplement our golden dataset      │
│                                                             │
│  Built-in evaluators we're NOT using:                       │
│  • HelpfulnessEvaluator                                     │
│  • FaithfulnessEvaluator                                    │
│  • ToolSelectionEvaluator ← could track tool usage          │
│  • ToolParameterEvaluator                                   │
│  • TrajectoryEvaluator ← could eval 3-turn flow             │
│  • InteractionsEvaluator                                    │
│  • GoalSuccessRateEvaluator                                 │
│  • ExperimentGenerator ← auto-generate test cases           │
└─────────────────────────────────────────────────────────────┘
```

### What We Built vs What the SDK Provides

| What We Built | Lines of Code | SDK Equivalent | Lines with SDK |
|---------------|--------------|----------------|----------------|
| LLM judge (intent_preservation.py) | ~80 lines: rubric, Agent creation, JSON parsing, error handling | `OutputEvaluator(rubric=RUBRIC, model=MODEL)` | ~5 lines |
| LLM judge (plan_quality.py) | ~80 lines | `OutputEvaluator(rubric=RUBRIC, model=MODEL)` | ~5 lines |
| LLM judge (evidence_quality.py) | ~90 lines | `OutputEvaluator(rubric=RUBRIC, model=MODEL)` | ~5 lines |
| Deterministic evaluator (schema_validity.py) | ~30 lines | Custom `Evaluator` subclass | ~30 lines (same) |
| Eval orchestration (unified_eval.py) | ~700 lines | `Experiment.run_evaluations(task_fn)` | ~200 lines |
| Report format | Custom JSON dict | `EvaluationReport` | Standardized |
| Test case management | Manual JSON loading + filtering | `Case` objects + metadata | Structured |

The LLM judges are where the biggest win is. We hand-rolled JSON parsing, error handling, and scoring normalization that the SDK handles automatically. The orchestration is the second biggest win — `Experiment.run_evaluations()` replaces ~500 lines of manual evaluator looping.

### AgentCore Evaluations — Different Purpose

AgentCore Evaluations (now GA) is a managed service for production monitoring:
- **Online evaluation**: Samples live production traces, scores them continuously
- **On-demand evaluation**: Programmatic evaluation against traces for CI/CD
- **13 built-in evaluators**: General-purpose (helpfulness, faithfulness, tool selection)

This complements the Strands Evals SDK rather than replacing it. The SDK is for dev-time iteration ("is this prompt change better?"). AgentCore Evaluations is for production monitoring ("is the deployed agent degrading?"). We should use both, but the SDK migration comes first because it's where we spend 90% of our eval time.

### The Decision: Clean Break Migration

The user's position: "I cannot stand technical debt. Good evaluations are what gets you the job." No backlog item. No gradual migration. Clean break — delete the old code, adopt the SDK, rethink the evaluators and dashboard if it makes more sense with the new framework.

### The Spec

13 requirements covering the full migration:

1. **Golden dataset → Case objects** — static + dynamic merge, metadata for filtering
2. **6 deterministic creation evaluators** → SDK Evaluator subclasses
3. **5 deterministic verification evaluators** → SDK Evaluator subclasses
4. **3 mode-specific evaluators** → SDK Evaluator subclasses with metadata routing
5. **3 LLM judges** → OutputEvaluator with existing rubrics
6. **Task function** — chains creation → wait → verification for each Case
7. **Experiment construction** — tiered evaluator sets (smoke/smoke+judges/full)
8. **Calibration** — post-experiment analysis (cross-agent, not a standard evaluator)
9. **Report store** — adapted for SDK report format, DDB preserved
10. **Dashboard** — adapted for SDK report shape
11. **Old code deletion** — 19 evaluator files, 3 legacy runners, Streamlit dashboard
12. **Baseline comparison** — old vs new on same cases, verify equivalence
13. **CLI interface** — matching current flags

### What Changes for the User

**Before:** `python eval/unified_eval.py --dataset ... --tier full`
**After:** `python eval/run_eval.py --dataset ... --tier full`

Same CLI experience. Same report in DDB. Same dashboard. But under the hood: standardized evaluator interfaces, automatic JSON parsing for LLM judges, structured Case/Experiment management, and the ability to use SDK built-in evaluators (ToolSelectionEvaluator, TrajectoryEvaluator) without writing custom code.

### What We Gain Beyond Cleanup

The SDK opens doors we didn't have before:

1. **ToolSelectionEvaluator** — automatically evaluates whether the verification agent chose the right tool (Browser vs Brave vs Code Interpreter). This is backlog item 16 (tool action tracking) for free.
2. **TrajectoryEvaluator** — evaluates the creation agent's 3-turn flow as a trajectory. Did the parser → planner → reviewer sequence make sense?
3. **ExperimentGenerator** — auto-generate test cases from agent context descriptions. Could supplement the golden dataset with edge cases we haven't thought of.
4. **Async evaluation** — run evaluators in parallel for faster eval runs.
5. **Experiment serialization** — `Experiment.to_file()` / `from_file()` for reproducible runs.

## Files Created

- `.kiro/specs/strands-evals-migration/requirements.md` — 13 requirements
- `.kiro/specs/strands-evals-migration/.config.kiro` — Spec config
- `docs/project-updates/38-project-update-strands-evals-migration-spec.md` — This update

## What the Next Agent Should Do

### Continue the spec
Design document, then tasks. The requirements are at `.kiro/specs/strands-evals-migration/requirements.md`.

### Key research already done
- Strands Evals SDK docs fully read: OutputEvaluator, Custom Evaluator, Experiment, Case, ExperimentGenerator
- AgentCore Evaluations docs read: online eval, on-demand eval, 13 built-in evaluators
- Current eval code fully analyzed: 19 evaluator files, unified pipeline, report store, dashboard

### Install strands-evals if not already installed
```bash
/home/wsluser/projects/calledit/venv/bin/pip install strands-agents-evals
```

### Key constraints
- Clean break — delete old code, no backward compatibility
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Decision log at 150, next is 151
- Project update at 38, next is 39
