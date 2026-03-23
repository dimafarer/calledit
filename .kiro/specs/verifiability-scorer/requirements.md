# Requirements Document — Spec V4-4: Verifiability Scorer (Simplified)

## Introduction

Extend the PlanReview structured output so the reviewer LLM produces score tier metadata, dimension-level assessments, and actionable guidance text directly — as part of its Turn 3 structured output. The previous V4-4 design was over-engineered: a separate `scorer.py` module with regex parsing of reasoning text, deterministic template-based guidance, and a legacy_category field. All of that is deleted.

The new approach: the reviewer agent already deeply understands the prediction (it produced the score and reasoning). We extend the `PlanReview` Pydantic model with 4 new fields (`score_tier`, `score_label`, `score_guidance`, `dimension_assessments`) and update the `calledit-plan-reviewer` prompt to instruct the LLM to populate them. The LLM generates the guidance and dimension assessments naturally as part of structured output — no post-processing, no regex, no templates.

The only deterministic code is a ~15-line pure function `score_to_tier(score: float) -> dict` that maps the numeric score to a tier name, color, and icon. This exists because colors/icons are display constants that shouldn't vary with LLM output. It lives in `models.py` or a small helper — not a whole module.

### What Changes
1. New `DimensionAssessment` Pydantic model in `models.py`
2. Extended `PlanReview` model with 4 new fields
3. Updated `calledit-plan-reviewer` prompt in CloudFormation
4. `score_to_tier()` pure function (~15 lines)
5. Threading new fields through bundle and stream events (they're already part of `PlanReview.model_dump()`)

### What Does NOT Change
- The scoring logic in the prompt (5 dimensions, 0.0-1.0 scale) — unchanged from V4-3a
- The `verifiability_score` and `verifiability_reasoning` fields — still present, still populated
- Frontend rendering (V4-7)
- Verification agent behavior (V4-5)

### Critical Constraints
- NO `legacy_category` field. Categories are dead. Clean break from v3.
- NO `scorer.py` module. The LLM does the heavy lifting via structured output.
- NO regex parsing of reasoning text. The LLM outputs structured dimension assessments directly.
- NO deterministic guidance templates. The LLM writes the guidance naturally.

## Glossary

- **PlanReview**: The Pydantic model for Turn 3 (plan-reviewer) structured output. Currently has `verifiability_score`, `verifiability_reasoning`, `reviewable_sections`. V4-4 extends it with `score_tier`, `score_label`, `score_guidance`, `dimension_assessments`
- **DimensionAssessment**: A new Pydantic model representing one dimension's evaluation. Fields: `dimension` (str), `assessment` (str: strong/moderate/weak), `explanation` (str)
- **score_to_tier**: A pure function that maps a numeric score to a dict with `tier`, `label`, `color`, `icon` — the only deterministic post-processing in V4-4
- **Creation_Agent**: The Strands Agent running the 3-turn creation flow (V4-3a/V4-3b)
- **Prediction_Bundle**: The structured JSON object persisted in DynamoDB
- **Stream_Event**: A JSON object yielded by the async streaming entrypoint (V4-3b)

## Requirements

### Requirement 1: Extend PlanReview Model

**User Story:** As a developer, I want the PlanReview structured output to include score tier metadata, dimension assessments, and guidance text, so that the reviewer LLM produces all score indicator data in a single structured output call with no post-processing.

#### Acceptance Criteria

1. THE PlanReview model SHALL include a `score_tier` field (str) constrained to one of `high`, `moderate`, `low`
2. THE PlanReview model SHALL include a `score_label` field (str) containing a human-readable label (e.g., "High Confidence", "Moderate Confidence", "Low Confidence")
3. THE PlanReview model SHALL include a `score_guidance` field (str) containing actionable guidance text the LLM generates based on its assessment of the prediction's verifiability
4. THE PlanReview model SHALL include a `dimension_assessments` field (List[DimensionAssessment]) containing exactly 5 entries, one per scoring dimension
5. THE DimensionAssessment model SHALL have three fields: `dimension` (str, one of: criteria_specificity, source_availability, temporal_clarity, outcome_objectivity, tool_coverage), `assessment` (str, one of: strong, moderate, weak), and `explanation` (str)
6. THE existing `verifiability_score`, `verifiability_reasoning`, and `reviewable_sections` fields SHALL remain unchanged

### Requirement 2: Deterministic Tier Mapping

**User Story:** As a frontend developer, I want a deterministic mapping from score to display color and icon, so that the visual treatment is consistent regardless of LLM variation in the tier/label fields.

#### Acceptance Criteria

1. WHEN the `verifiability_score` is greater than or equal to 0.7, THE `score_to_tier` function SHALL return tier `high`, label `High Confidence`, color `#166534`, and icon `🟢`
2. WHEN the `verifiability_score` is greater than or equal to 0.4 and less than 0.7, THE `score_to_tier` function SHALL return tier `moderate`, label `Moderate Confidence`, color `#854d0e`, and icon `🟡`
3. WHEN the `verifiability_score` is less than 0.4, THE `score_to_tier` function SHALL return tier `low`, label `Low Confidence`, color `#991b1b`, and icon `🔴`
4. THE `score_to_tier` function SHALL be a pure function taking a single float argument and returning a dict with keys `tier`, `label`, `color`, `icon`
5. THE `score_to_tier` function SHALL clamp scores outside [0.0, 1.0] to the nearest boundary before computing the tier

### Requirement 3: Update Plan-Reviewer Prompt

**User Story:** As a developer, I want the plan-reviewer prompt to instruct the LLM to produce the new structured fields, so that the extended PlanReview model is populated correctly via Strands structured output.

#### Acceptance Criteria

1. THE `calledit-plan-reviewer` prompt in CloudFormation SHALL instruct the reviewer to produce `score_tier`, `score_label`, `score_guidance`, and `dimension_assessments` as part of its structured output
2. THE prompt SHALL instruct the reviewer to assess each of the 5 dimensions (criteria_specificity, source_availability, temporal_clarity, outcome_objectivity, tool_coverage) with a strong/moderate/weak rating and a one-line explanation
3. THE prompt SHALL instruct the reviewer to generate actionable guidance text: encouragement for high-confidence predictions, specific improvement suggestions referencing weak dimensions for moderate/low-confidence predictions
4. THE prompt SHALL instruct the reviewer to set `score_tier` consistent with the numeric `verifiability_score` (high for >= 0.7, moderate for >= 0.4, low for < 0.4)
5. A new `AWS::Bedrock::PromptVersion` resource SHALL be added to the CloudFormation template for the updated prompt

### Requirement 4: Thread New Fields Through Bundle and Events

**User Story:** As a frontend developer, I want the new score fields available in stream events and the persisted bundle, so that I can render the verifiability indicator without additional API calls or client-side computation.

#### Acceptance Criteria

1. WHEN Turn 3 completes, THE `turn_complete` stream event output SHALL include the new PlanReview fields (`score_tier`, `score_label`, `score_guidance`, `dimension_assessments`) via `plan_review.model_dump()`
2. THE `flow_complete` stream event SHALL include the new fields in the Prediction_Bundle data
3. THE Prediction_Bundle saved to DynamoDB SHALL include the new fields as part of the existing `model_dump()` serialization
4. WHEN a clarification round completes, THE same field inclusion SHALL apply to the clarification round's Turn 3 `turn_complete` and `flow_complete` events
5. THE `score_to_tier` output (deterministic color/icon) SHALL be included in the `flow_complete` event as a `tier_display` field alongside the LLM-generated fields, so the frontend has both the LLM's natural language and the deterministic visual constants

### Requirement 5: No Legacy Category, No Scorer Module

**User Story:** As a developer, I want a clean break from the v3 category system and the over-engineered scorer module, so that the codebase stays simple and the LLM does the heavy lifting.

#### Acceptance Criteria

1. THE PlanReview model SHALL NOT include a `legacy_category` field or any mapping to v3 categories (`auto_verifiable`, `automatable`, `human_only`)
2. THERE SHALL NOT be a `calleditv4/src/scorer.py` module — all score-related code SHALL be either in the Pydantic model definitions or in a small helper function alongside the models
3. THERE SHALL NOT be any regex parsing of `verifiability_reasoning` text to extract dimension assessments — the LLM SHALL produce structured `dimension_assessments` directly
4. THERE SHALL NOT be any deterministic guidance text templates — the LLM SHALL generate `score_guidance` naturally based on its understanding of the prediction
