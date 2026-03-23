# Project Update 26 — V4-4 Verifiability Scorer Spec Complete

**Date:** March 23, 2026
**Context:** Wrote the V4-4 spec (Verifiability Scorer). Spec went through one design iteration — the first version was over-engineered, the second is tight. Ready to execute.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/verifiability-scorer/` — Spec V4-4 (COMPLETE)

### Prerequisite Reading
- `docs/project-updates/25-project-update-v4-3b-clarification-streaming.md` — V4-3b (clarification & streaming)

---

## What Happened This Session

### First Design: Over-Engineered

The initial V4-4 design built a whole `scorer.py` module with regex parsing of the `verifiability_reasoning` text, deterministic guidance templates, a `legacy_category` field for v3 backward compat, and 13 correctness properties. This was overkill — the reviewer LLM already deeply understands the prediction. It produced the score and reasoning. It should just output the tier, dimension breakdown, and guidance directly as structured output.

### Second Design: LLM Does the Heavy Lifting

Rewrote the spec from scratch. The simplified approach:

1. Extend `PlanReview` Pydantic model with 4 new fields (`score_tier`, `score_label`, `score_guidance`, `dimension_assessments`)
2. New `DimensionAssessment` Pydantic model (dimension, assessment, explanation)
3. Update the `calledit-plan-reviewer` prompt to instruct the LLM to produce the new fields
4. A ~15-line `score_to_tier()` pure function for deterministic color/icon mapping
5. Thread new fields through bundle and stream events

No `scorer.py` module. No regex parsing. No deterministic guidance templates. No `legacy_category` — clean break from v3 categories (Decision 103).

### Why No Legacy Category

The user explicitly rejected backward compatibility with v3 categories. The v3 system used `auto_verifiable`/`automatable`/`human_only` — v4 replaces this entirely with a continuous score + tier system. No transition period, no technical debt. The v3 frontend will need updating when it connects to v4 (that's V4-7's job).

## Decisions Made

- **Decision 103:** No legacy category mapping. Clean break from v3's 3-category system. The `PlanReview` model has no `legacy_category` field. The v3 frontend's `getVerifiabilityDisplay()` and `CATEGORY_CONFIG` are not supported by v4. Frontend update is V4-7's scope.

## Spec Summary

### Requirements (5)
1. Extend PlanReview model with score_tier, score_label, score_guidance, dimension_assessments
2. Deterministic score_to_tier() pure function for color/icon mapping
3. Update plan-reviewer prompt in CloudFormation
4. Thread new fields through bundle and stream events
5. Anti-requirements: no legacy_category, no scorer.py, no regex, no templates

### Design
- 4 files change: models.py, template.yaml, main.py, bundle.py (minor)
- New fields injected into bundle dict after build_bundle() returns (no signature changes)
- 4 correctness properties (model structure, tier boundaries, determinism, clamping)

### Tasks (5 top-level)
1. Models: DimensionAssessment + PlanReview extension + score_to_tier()
2. Prompt: Update plan-reviewer + new PromptVersion
3. Main.py: Thread fields through creation and clarification routes
4. Tests: Update existing + optional property tests
5. Final checkpoint: run tests, deploy prompt, integration test

## Files Created

- `.kiro/specs/verifiability-scorer/requirements.md` — 5 requirements
- `.kiro/specs/verifiability-scorer/design.md` — Simplified design
- `.kiro/specs/verifiability-scorer/tasks.md` — 5 top-level tasks
- `docs/project-updates/26-project-update-v4-4-verifiability-scorer.md` — This file

## What the Next Agent Should Do

Execute the V4-4 spec tasks. Read these files first:
1. `.kiro/specs/verifiability-scorer/tasks.md` — task list
2. `.kiro/specs/verifiability-scorer/design.md` — design with exact code
3. `.kiro/specs/verifiability-scorer/requirements.md` — 5 requirements
4. `calleditv4/src/models.py` — current PlanReview model to extend
5. `calleditv4/src/main.py` — current async streaming entrypoint
6. `infrastructure/prompt-management/template.yaml` — current prompts


## Execution Results

### Implementation
All 5 tasks completed:
1. Models: `DimensionAssessment` model, extended `PlanReview` with 4 new fields, `score_to_tier()` function
2. Prompt: Updated `calledit-plan-reviewer` with dimension assessment and guidance instructions, added `PlanReviewerPromptVersionV2`
3. Main.py: Threaded new fields through creation and clarification routes, `tier_display` from `score_to_tier()`
4. Bundle.py: Updated `format_ddb_update()` with 5 new optional params for clarification DDB persistence
5. Tests: Updated all PlanReview constructions, added 12 new tests (10 score_to_tier + 1 structure + 1 descriptions)

### Test Results
148 tests passing (136 V4-3b + 12 new V4-4). No regressions.

### Integration Test
Strands `structured_output_model` populated all new fields correctly even before deploying the prompt update — the LLM saw the new fields in the Pydantic tool schema and filled them in. The prompt update (not yet deployed) will improve guidance quality but isn't required for functionality.

Key output from integration test:
- `score_tier: "high"`, `score_label: "High Confidence"` — LLM-generated, consistent with 0.78 score
- `score_guidance` — natural, contextual guidance text
- `dimension_assessments` — all 5 dimensions with strong ratings and specific explanations
- `tier_display` — deterministic `{"tier": "high", "color": "#166534", "icon": "🟢"}`

### AgentCore Deviation Flag: None

## Files Created/Modified

### Created
- `docs/project-updates/26-project-update-v4-4-verifiability-scorer.md` — This file

### Modified
- `calleditv4/src/models.py` — `DimensionAssessment` model, extended `PlanReview`, `score_to_tier()`
- `calleditv4/src/main.py` — V4-4 field injection in creation and clarification routes
- `calleditv4/src/bundle.py` — `format_ddb_update()` gains 5 new optional params
- `calleditv4/tests/test_models.py` — Updated for new fields, 12 new tests
- `infrastructure/prompt-management/template.yaml` — Updated plan-reviewer prompt + V2 version
- `docs/project-updates/decision-log.md` — Decision 103
- `docs/project-updates/project-summary.md` — Update 26 entry

## What the Next Agent Should Do

1. Deploy the prompt update: `aws cloudformation deploy --template-file template.yaml --stack-name calledit-prompts`
2. V4-5 (Verification Agent) — the second AgentCore runtime
3. Pin prompt versions after prompt iteration
