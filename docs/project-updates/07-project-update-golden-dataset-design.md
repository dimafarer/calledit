# Project Update 07 — Golden Dataset V2 Design & Spec

**Date:** March 14, 2026 (planning complete, spec created, execution next)
**Context:** Designing and speccing a production-quality golden dataset v2 with ground truth metadata, DynamoDB reasoning capture, and cross-agent coherence testing
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/golden-dataset-v2/` — Spec 6: Golden Dataset V2 (9 requirements, 6 components, 11 properties)
- `.kiro/specs/prompt-eval-framework/` — Spec 5: Prompt Evaluation Framework (parent spec)

### Prerequisite Reading
- `docs/project-updates/06-project-update-eval-framework-execution.md` — Baseline results showing ReviewAgent as primary improvement target
- `eval/golden_dataset.json` — Current v1.0 dataset (15 base + 5 fuzzy) — will be archived

---

## Core Insight

People are prediction machines. We predict constantly — from life-changing ("I'll get the job") to fleeting ("traffic will be bad"). CalledIt lowers the bar to capturing these predictions. The golden dataset must represent this full spectrum.

## Key Design Decisions Made This Session

### Decision 31: Ground Truth Metadata Per Prediction
Instead of just storing `expected_category: "automatable"`, each prediction captures WHY it's that category through structured metadata:
- `verifiability_reasoning` — why this category
- `date_derivation` — how verification date is determined
- `verification_sources` — data sources needed
- `objectivity_assessment` — objective / subjective / mixed
- `verification_criteria` — measurable conditions
- `verification_steps` — ordered actions to verify

**Why this matters:** When verification categories evolve (see Decision 33), expected labels are re-derived from ground truth rather than manually re-tagging 50+ test cases.

### Decision 32: Clean Break from V1 (No Backward Compatibility)
The v2 dataset replaces v1 entirely. The v2 loader only supports `schema_version: "2.0"`. The v1 dataset is archived to `eval/golden_dataset_v1_archived.json`. V1 score history remains in git as historical record.

**Why not backward compatible:** The v1 dataset has 15+5 predictions. V2 has 40-50+20-30. Comparing scores across them is apples-to-oranges anyway. A clean break means simpler loader (one code path), stronger validation (ground truth required, not optional), and less maintenance.

### Decision 33: Future 4-Category System (Ground Truth Enables This)
Current categories: `auto_verifiable`, `automatable`, `human_only`

Proposed future categories:
- `current_agent_verifiable` — agent can do it now with registered tools
- `agent_verifiable_with_known_tool` — a known/existing API type could verify it
- `assumed_agent_verifiable_with_tool_build` — we'd need to build a custom tool
- `human_only` — subjective/personal, only a human can judge

The model's natural reasoning (observed in early testing) already aligns more with the 4-category system than the current 3-category system. Ground truth metadata makes this migration a re-derivation exercise, not a re-authoring exercise.

### Decision 34: DynamoDB for Eval Reasoning Capture
New table `calledit-eval-reasoning` stores full model reasoning traces during eval runs:
- Full text output from all 4 agents per test case
- Judge model reasoning, scores, model ID
- Token counts per agent and judge invocation
- Run metadata (manifest, dataset version, pass rate, duration)

Fire-and-forget pattern — DDB failures never block eval execution. TTL of 90 days. PAY_PER_REQUEST billing. The production Lambda stays frugal; the eval framework can justify any cost for insights.

### Decision 35: Lightweight Expected Outputs
Only `expected_category` is required per prediction. Parser, VB, and review expected outputs are optional rubric guidance for the LLM-as-judge. This makes maintaining 50+ predictions practical.

### Decision 36: Fuzziness Level 0 (Control Cases)
Added Level 0 — perfectly specified predictions used as controls where the ReviewAgent should find no clarification needed. Levels: 0 (control), 1 (missing one detail), 2 (missing multiple details), 3 (highly ambiguous).

### Decision 37: Cross-Agent Coherence as First-Class Concern
Parser date extraction, categorizer verifiability judgment, and VB methods/sources/criteria/steps should tell a consistent story. The ground truth metadata provides the reference narrative. At least 5 "coherence anchor" predictions have complete expected outputs for all 4 agents.

### Decision 38: Storage — Git Now, S3 Later
Keep in git with explicit `dataset_version` field. Move to private S3 bucket (with versioning, encryption, public access blocked) when dataset exceeds ~100 test cases.

## Methodology (Unchanged from Planning)

### Step 1: Persona Brainstorm (~100 raw candidates)
Generate predictions from 18 diverse human personas (parent, commuter, sports fan, investor, student, chef, traveler, manager, doctor/patient, gardener, gamer, pet owner, retiree, teenager, entrepreneur, teacher, artist, athlete).

### Step 2: Dimension Matrix Tagging (5 axes)
- **Domain:** weather, sports, finance, personal, health, tech, social, work, food, travel, entertainment, nature, politics
- **Stakes:** life-changing / significant / moderate / trivial
- **Time horizon:** minutes-to-hours / days / weeks-to-months / months-to-years
- **Expected category:** auto_verifiable / automatable / human_only
- **Fuzziness potential:** levels 0-3

### Step 3: Cross-Section Selection (~40-50 base predictions)
- At least 12 per category, 3 per stakes level, 3 per time horizon
- At least 8 domains, 12 personas
- At least 5 boundary/adversarial cases

### Step 4: Fuzziness Degradation (~20-30 fuzzy variants)
- Level 0: 3+ control cases (perfectly specified)
- Level 1: 5+ (missing one detail)
- Level 2: 5+ (missing multiple details)
- Level 3: 5+ (highly ambiguous)
- 5+ where clarification doesn't change category (human_only stays human_only)

### Step 5: Ground Truth + Rubrics
For each base prediction: full ground truth metadata (6 fields), dimension tags, difficulty, tool manifest config, evaluation rubric. Only `expected_category` required in expected outputs.

### Step 6: Versioning
- `schema_version: "2.0"` (JSON structure)
- `dataset_version: "2.0"` (content revision)
- Both tracked in eval reports and score history


## Persona Predictions (Reference)

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

## Spec Summary

### Requirements (9)
1. Ground truth metadata schema
2. Persona-driven prediction generation (40-50 base)
3. Fuzzy prediction variants with fuzziness levels 0-3 (20-30 fuzzy)
4. Lightweight expected outputs (only expected_category required)
5. Cross-agent coherence testability
6. DynamoDB eval reasoning store
7. Dataset schema evolution and versioning
8. Dataset maintenance process (validation script)
9. Dataset round-trip integrity

### Design Components (6)
1. V2 Schema — rewritten `golden_dataset.py` (v2-only, no backward compat)
2. Persona-Driven Dataset Content — 40-50 base + 20-30 fuzzy
3. Validation Script — `eval/validate_dataset.py`
4. DynamoDB Eval Reasoning Store — `calledit-eval-reasoning` table
5. Eval Runner V2 Integration — dataset_version tracking, DDB writes
6. Category Re-derivation Support — ground truth enables future 4-category migration

### Implementation Plan (10 tasks)
1. Rewrite v2 schema and loader (+ 6 property tests)
2. Checkpoint
3. Validation script (+ 1 property test)
4. DDB table in SAM template
5. EvalReasoningStore module (+ 2 property tests)
6. Checkpoint
7. Eval runner + score history v2 integration (+ 2 property tests)
8. Checkpoint
9. Archive v1, create v2 dataset content
10. Final checkpoint

## What the Next Agent Should Do

1. Follow the Content Creation Cycle below to build the v2 golden dataset (Task 9)
2. After dataset is built, run full eval with new v2 dataset to establish v2 baseline
3. Compare v2 baseline against v1 Run 3 results (qualitatively, not score-to-score)
4. Begin ReviewAgent prompt iteration using the richer eval data and DDB reasoning traces
5. Analyze cross-agent coherence using the ground truth anchors
6. Consider the 4-category migration once enough reasoning data is captured in DDB

---

## Content Creation Cycle — Golden Dataset V2

This section documents the deliberate, quality-focused process for creating the golden dataset content. The infrastructure (schema, loader, validation, DDB store, eval runner integration) is complete. What remains is the hardest part: crafting predictions that are genuinely useful for testing — not filler to hit a count target.

### Philosophy

Every prediction must earn its place. The dataset serves current testing (3-category system, 4-agent graph, clarification loop) and future testing (4-category system, new evaluators, prompt iteration, cross-agent coherence analysis). A prediction that only tests one thing is fine. A prediction that tests nothing interesting is waste.

The ground truth metadata is the soul of each prediction. If the `verifiability_reasoning` is vague, the prediction is vague. If the `verification_steps` are generic ("check the data"), the prediction won't catch a generic VB agent. The metadata should be precise enough that a human reading it says "yes, that's exactly why this prediction is in this category."

### Process: Batched Creation with Dual Review

We work in batches of ~10-12 predictions, organized by category. Each batch goes through a 5-step cycle:

**Step 1 — Draft.** The agent drafts predictions with full ground truth metadata, dimension tags, difficulty, tool manifest config, and evaluation rubric. Predictions are generated from the persona table, but the agent is free to invent new personas or combine them if it produces a more interesting test case.

**Step 2 — Agent Self-Review.** Before presenting to the human, the agent reviews its own work against these quality questions:
- Is the ground truth coherent? Do the sources support the criteria? Do the criteria align with the objectivity assessment?
- Would the categorizer actually struggle with this, or is it trivially obvious?
- Is the verifiability reasoning precise enough to re-derive labels under a 4-category system?
- Are the verification steps actionable and specific to this prediction (not boilerplate)?
- Does this prediction test something the existing v1 dataset doesn't?
- Is the evaluation rubric specific enough to guide the LLM-as-judge?
- For boundary cases: is the boundary condition clearly documented?

The agent flags any predictions it's uncertain about or where it sees potential weakness.

**Step 3 — Human Review.** The human reviews the batch, pushes back on weak predictions, suggests changes, and approves or rejects each prediction. The human brings domain knowledge the agent lacks — "people don't actually say it that way" or "this is too similar to base-015."

**Step 4 — Iterate.** Based on human feedback, the agent revises rejected predictions or replaces them. This may take multiple rounds for tricky cases.

**Step 5 — Commit Batch.** Approved predictions are added to the dataset JSON. The validation script is run to verify structural integrity and coverage progress.

### Batch Order

The batches are ordered to build coverage progressively:

| Batch | Focus | Count | Why This Order |
|---|---|---|---|
| 1 | auto_verifiable | ~12-14 | Easiest to get right — objective, tool-dependent. Establishes the "this is what good ground truth looks like" pattern. |
| 2 | automatable | ~12-14 | Builds on batch 1 — same objectivity but no tool available. Tests the "known tool vs hypothetical tool" distinction that matters for the 4-category future. |
| 3 | human_only | ~12-14 | Hardest to get right — subjective, personal, opinion-based. The ground truth must explain WHY no tool helps, not just "it's subjective." |
| 4 | Boundary cases | ~5-7 | Cross-category edge cases. These are the predictions that will break the categorizer. Each one should have a clear boundary_description explaining the trap. |
| 5 | Fuzzy variants (levels 0-1) | ~10-12 | Control cases (level 0) and light degradation (level 1). Tests whether the ReviewAgent correctly identifies what's missing. |
| 6 | Fuzzy variants (levels 2-3) | ~12-15 | Heavy degradation and slang/idioms. Tests the ReviewAgent's ability to ask the right clarification questions when the prediction is deeply ambiguous. |

### Quality Signals to Watch For

**Good predictions:**
- The categorizer could plausibly get it wrong (not trivially obvious)
- The ground truth tells a story you can follow
- The verification steps are specific enough that you could actually do them
- The evaluation rubric points the judge at something concrete

**Red flags:**
- Ground truth that says "this is [category] because it's [category]" (circular)
- Verification steps that are just "check the data" or "verify the outcome"
- Predictions that are too similar to each other (testing the same thing twice)
- Boundary cases where the boundary isn't actually interesting
- Fuzzy variants where the fuzziness is artificial (no human would say it that way)

### Coverage Tracking

After each batch, we check coverage against the requirements:
- Categories: ≥12 per category (auto_verifiable, automatable, human_only)
- Domains: ≥8 distinct domains
- Stakes: ≥3 per level (life-changing, significant, moderate, trivial)
- Time horizons: ≥3 per horizon (minutes-to-hours, days, weeks-to-months, months-to-years)
- Personas: ≥12 distinct personas
- Boundary cases: ≥5
- Fuzzy levels: ≥3 at level 0, ≥5 at levels 1/2/3
- Category-unchanged fuzzy: ≥5 where clarification doesn't change category

The validation script (`eval/validate_dataset.py`) checks all of this automatically.

---

## Files Created This Session

### New Files
- `.kiro/specs/golden-dataset-v2/.config.kiro` — Spec config
- `.kiro/specs/golden-dataset-v2/requirements.md` — 9 requirements
- `.kiro/specs/golden-dataset-v2/design.md` — 6 components, 11 correctness properties
- `.kiro/specs/golden-dataset-v2/tasks.md` — 10 tasks with 4 checkpoints
- `backend/calledit-backend/handlers/strands_make_call/golden_dataset.py` — Rewritten v2 schema, loader, serializer, filter
- `backend/calledit-backend/handlers/strands_make_call/eval_reasoning_store.py` — DDB reasoning store (fire-and-forget)
- `eval/validate_dataset.py` — Standalone validation script
- `tests/strands_make_call/test_golden_dataset_v2.py` — 53 tests for v2 schema/loader
- `tests/strands_make_call/test_validate_dataset.py` — 21 tests for validation script
- `tests/strands_make_call/test_eval_reasoning_store.py` — 15 tests for DDB store
- `tests/strands_make_call/test_score_history_v2.py` — 5 tests for dataset_version tracking

### Modified Files
- `docs/project-updates/07-project-update-golden-dataset-design.md` — Updated with session decisions + content creation cycle
- `backend/calledit-backend/template.yaml` — Added EvalReasoningTable DDB resource + CRUD policy
- `backend/calledit-backend/handlers/strands_make_call/eval_runner.py` — V2 field access, reasoning store integration, dataset_version in reports
- `backend/calledit-backend/handlers/strands_make_call/score_history.py` — dataset_version tracking, cross-version mismatch warnings
