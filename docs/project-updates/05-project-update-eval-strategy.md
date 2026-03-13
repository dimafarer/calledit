# Project Update 05 — Prompt Evaluation Strategy

**Date:** March 9, 2026 (discussion); execution deferred until after Spec 7
**Context:** Strategy for systematically improving agent prompts
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/prompt-eval-framework/` — Spec 5: Prompt Evaluation Framework
  - `requirements.md` — COMPLETE (8 requirements)
  - `design.md` — NOT YET CREATED
  - `tasks.md` — NOT YET CREATED

### Prerequisite Reading
- `docs/project-updates/04-project-update-category-simplification.md` — Must be executed first (categories must be finalized before building eval framework)

---

## The Problem

During testing, "Tomorrow will be a beautiful day" was correctly categorized as `human_verifiable_only` in round 1. After the user clarified "70+ degrees, sunny, New York," the categorizer should have upgraded the category — but it didn't. It clung to "beautiful is subjective" reasoning and ignored the clarification.

This revealed two issues:
1. The ReviewAgent over-assumed weather without confirming ("beautiful" could mean anything)
2. The categorizer under-utilized user clarifications

## Decision 13: Prompt Evaluation Strategy

**Primary: Golden Dataset + Automated Eval**
- Build ~25 test predictions with expected outcomes
- Run each prompt change against the full set, score automatically
- Catches regressions, provides objective "are we improving?" signal
- Confidence: 8/10

**Secondary: LLM-as-Judge** for nuanced reasoning quality (confidence: 6/10)

**Deferred: Strands Evals SDK** (unknown maturity, confidence: 5/10)

## Decision 14: Layered Test Pyramid for Predictions

**Layer 1 — Base Predictions (fully specified):**
Predictions that need zero clarification. Ground truth for the system.

Example: "Tomorrow the high temperature in Central Park, New York will reach at least 70°F"
→ Expected: `auto_verifiable` (with web search tool), no clarification needed

**Layer 2 — Fuzzy Predictions (degraded versions of base):**
Same predictions with information removed. Tests the clarification loop.

Example: "Tomorrow will be a beautiful day"
→ Expected round 1: `human_only`
→ After clarification: should converge to base prediction's category

## Decision 15: Clarification Improves Precision, Not Just Verifiability

Predictions that stay `human_only` still benefit from clarification. "Tom will wear that shirt" → ask "which Tom?", "which shirt?", "what day?" to maximize precision for the human verifier.

## Execution Order

1. ~~Execute Spec 6 (websocket-snapstart)~~ — DONE (see Update 03)
2. ~~Execute Spec 7 (category simplification + tool registry)~~ — DONE (see Update 04)
3. Then build eval framework (this spec) against the simplified 3-category system

**NOTE:** The Spec 5 requirements were written with the old 5-category system. The next agent MUST update the requirements to use the new 3-category names before creating the design:
- `agent_verifiable` → `auto_verifiable`
- `current_tool_verifiable` → `auto_verifiable`
- `strands_tool_verifiable` → `automatable` (unless tool is registered)
- `api_tool_verifiable` → `automatable` (unless tool is registered)
- `human_verifiable_only` → `human_only`

The golden dataset should use only 3 categories: `auto_verifiable`, `automatable`, `human_only`.

The `Verifiability_Category` glossary entry in the requirements needs updating from the old 5 values to the new 3.
