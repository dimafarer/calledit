# Project Update 07 — Golden Dataset Design for Comprehensive Prediction Coverage

**Date:** March 14, 2026 (planning); execution deferred to next session
**Context:** Designing a production-quality golden dataset that represents the full spectrum of human prediction behavior
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/prompt-eval-framework/` — Spec 5: Prompt Evaluation Framework (golden dataset is Requirement 4)

### Prerequisite Reading
- `docs/project-updates/06-project-update-eval-framework-execution.md` — Baseline results showing ReviewAgent as primary improvement target
- `eval/golden_dataset.json` — Current v1.0 dataset (15 base + 5 fuzzy)

---

## Core Insight

People are prediction machines. We predict constantly — from life-changing ("I'll get the job") to fleeting ("traffic will be bad"). CalledIt lowers the bar to capturing these predictions. The golden dataset must represent this full spectrum.

## Methodology

### Step 1: Persona Brainstorm (~100 raw candidates)
Generate predictions from diverse human personas:
- Parent, commuter, sports fan, investor, student, chef, traveler
- Manager, doctor/patient, gardener, gamer, pet owner
- Retiree, teenager, entrepreneur, teacher, artist, athlete
- Each persona: 5-8 predictions spanning stakes and time horizons

### Step 2: Dimension Matrix Tagging
Classify each prediction along 5 dimensions:
- **Domain:** weather, sports, finance, personal, health, tech, social, work, food, travel, entertainment, nature, politics
- **Stakes:** life-changing / significant / moderate / trivial
- **Time horizon:** minutes / hours / days / weeks / months / years
- **Expected category:** auto_verifiable / automatable / human_only
- **Fuzziness potential:** how many levels of degradation are natural

### Step 3: Cross-Section Selection (~40-50 base predictions)
Select predictions that cover the matrix well:
- At least 3 per expected category
- At least 2 per domain
- Mix of stakes levels
- Mix of time horizons
- Prioritize predictions that are interesting edge cases for the categorizer

### Step 4: Fuzziness Degradation (~20-30 fuzzy variants)
For selected base predictions, create fuzzy variants:
- Level 1: Missing one detail (location, time, threshold)
- Level 2: Missing multiple details (vague subject + vague criteria)
- Level 3: Highly ambiguous (slang, idioms, implicit context)
Each fuzzy variant needs: expected clarification topics, simulated answers, expected post-clarification outputs

### Step 5: Expected Outputs & Rubrics
For each test case:
- Expected per-agent outputs (parser, categorizer, VB, review)
- Evaluation rubric for the LLM-as-judge (what should the reasoning reference?)
- Difficulty annotation (easy/medium/hard)
- Tool manifest config (which tools should be visible)

### Step 6: Dataset Versioning
- Bump `schema_version` to "2.0" for the comprehensive dataset
- Record dataset version in eval reports alongside prompt version manifest
- Consider: git tag for dataset versions, or a `dataset_version` field in score_history

## Persona Predictions (To Generate)

| Persona | Example Predictions | Typical Category | Typical Fuzziness |
|---|---|---|---|
| Parent | "Kid sleeps through the night" | human_only | Level 2-3 |
| Commuter | "7:15 train delayed" | automatable | Level 1-2 |
| Sports fan | "Yankees win tonight" | automatable | Level 1 |
| Investor | "Tesla hits $400 by June" | automatable | Level 1 |
| Student | "Get an A on midterm" | human_only | Level 2 |
| Chef | "Soufflé won't fall" | human_only | Level 3 |
| Traveler | "Flight on time" | automatable | Level 1 |
| Manager | "Ship feature by sprint end" | human_only | Level 2 |
| Doctor/patient | "Cold gone by Monday" | human_only | Level 2 |
| Gardener | "Tomatoes ripen by August" | automatable | Level 2 |
| Gamer | "Beat this level tonight" | human_only | Level 3 |
| Pet owner | "Dog destroys toy in an hour" | human_only | Level 2 |
| Retiree | "Market recovers this quarter" | automatable | Level 1 |
| Teenager | "She'll text back within an hour" | human_only | Level 3 |
| Entrepreneur | "We'll close the funding round by Q2" | human_only | Level 2 |
| Teacher | "80% of students pass the final" | human_only | Level 1 |
| Artist | "This painting sells at the gallery show" | human_only | Level 2 |
| Athlete | "I'll PR in the marathon Saturday" | human_only | Level 2 |

## Storage & Versioning Decision (TBD)

Options:
1. **Git (current)** — simple, versioned with code. Add explicit `dataset_version` field.
2. **S3 with versioning** — separate from code, version history built in, supports large datasets.
3. **DynamoDB** — queryable but overkill for a JSON document.

Recommendation: Keep in git with explicit `dataset_version` field for now. Move to S3 when dataset exceeds ~100 test cases or when multiple people contribute.

## Next Steps

1. Generate the full persona brainstorm (Step 1)
2. Tag on dimension matrix (Step 2)
3. Select cross-section (Step 3)
4. Create fuzzy variants (Step 4)
5. Write expected outputs and rubrics (Step 5)
6. Update golden_dataset.json schema to v2.0
7. Run full eval with new dataset
8. Compare against baseline (Run 3 with judge)
