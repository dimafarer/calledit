# Implementation Plan: Verifiability Scorer (V4-4)

## Overview

Extend Turn 3 structured output with score tier metadata, dimension assessments, and guidance text. The LLM does the heavy lifting; the only deterministic code is `score_to_tier()`. Four files change: models.py, template.yaml, main.py, and test_models.py.

## Tasks

- [x] 1. Add DimensionAssessment model, extend PlanReview, and add score_to_tier() in models.py
  - [x] 1.1 Add `DimensionAssessment` Pydantic model with `dimension`, `assessment`, `explanation` fields (all str with Field descriptions)
    - _Requirements: 1.5_
  - [x] 1.2 Add 4 new fields to `PlanReview`: `score_tier` (str), `score_label` (str), `score_guidance` (str), `dimension_assessments` (List[DimensionAssessment]) — all with Field descriptions
    - Existing fields (`verifiability_score`, `verifiability_reasoning`, `reviewable_sections`) remain unchanged
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6_
  - [x] 1.3 Add `score_to_tier(score: float) -> dict` pure function with clamping and 3-tier mapping (high >= 0.7, moderate >= 0.4, low < 0.4)
    - Returns dict with keys: `tier`, `label`, `color`, `icon`
    - Clamps input to [0.0, 1.0] before computing tier
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  - [x] 1.4 Update the `from models import` line in main.py to include `score_to_tier`
    - _Requirements: 4.5_

- [x] 2. Update plan-reviewer prompt and add PromptVersion in template.yaml
  - [x] 2.1 Extend the `calledit-plan-reviewer` prompt text with instructions for dimension assessments (5 dimensions, strong/moderate/weak ratings), score tier/label classification, and score guidance generation
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [x] 2.2 Add `PlanReviewerPromptVersionV2` resource (AWS::Bedrock::PromptVersion) with DependsOn PlanReviewerPromptVersion
    - _Requirements: 3.5_

- [x] 3. Thread new fields through main.py for both creation and clarification routes
  - [x] 3.1 Creation route: after `bundle = build_bundle(...)`, inject `score_tier`, `score_label`, `score_guidance`, `dimension_assessments` from `plan_review.model_dump()`, and `tier_display` from `score_to_tier()`
    - _Requirements: 4.1, 4.2, 4.3, 4.5_
  - [x] 3.2 Clarification route: add the same 5 fields to the `updated_bundle` dict, and add SET clauses + expression attribute values for the 4 new PlanReview fields in `format_ddb_update()` in bundle.py
    - _Requirements: 4.4, 4.5_

- [x] 4. Update tests in test_models.py
  - [x] 4.1 Update existing `TestPlanReviewStructure` and `TestFieldDescriptions` to cover the 4 new PlanReview fields and DimensionAssessment model
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 5.1, 5.2_
  - [ ]* 4.2 Write property test for DimensionAssessment and PlanReview model structure
    - **Property 1: DimensionAssessment and PlanReview model structure**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 4.1**
  - [ ]* 4.3 Write property test for tier boundary correctness
    - **Property 2: Tier boundary correctness**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
  - [ ]* 4.4 Write property test for score_to_tier determinism
    - **Property 3: score_to_tier determinism**
    - **Validates: Requirements 2.4**
  - [ ]* 4.5 Write property test for score_to_tier clamping
    - **Property 4: score_to_tier clamping**
    - **Validates: Requirements 2.5**
  - [x] 4.6 Add unit tests for score_to_tier boundary examples and edge cases
    - Boundary: `score_to_tier(0.0)`, `score_to_tier(0.4)`, `score_to_tier(0.7)`, `score_to_tier(1.0)`
    - Edge: `score_to_tier(-0.5)` → low, `score_to_tier(1.5)` → high
    - Verify no `legacy_category` in PlanReview schema
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 5.1, 5.2_

- [x] 5. Final checkpoint
  - Run all tests: `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/test_models.py calleditv4/tests/test_entrypoint.py -v`
  - Ensure all tests pass, ask the user if questions arise.
  - Deploy prompt: `aws cloudformation deploy --template-file template.yaml --stack-name calledit-prompts`
  - Integration test: `agentcore invoke --dev` with a sample prediction

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Property tests use Hypothesis with `@settings(max_examples=100)` per project convention
- No mocks (Decision 96) — all tested code is pure
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Integration testing is manual via `agentcore invoke --dev`
