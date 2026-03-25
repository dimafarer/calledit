# Project Update 30 — V4-7a Eval Framework Redesign (Research & Strategy)

**Date:** March 25, 2026
**Context:** Research session to redesign the eval framework from first principles for v4 AgentCore agents. No code written — this is the strategic foundation for the eval specs that follow.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** cb4e1fa (V4-8a MVP — no new code in this session)

### Referenced Kiro Specs
- Specs to be created based on decisions in this update (see "What the Next Agent Should Do")

### Prerequisite Reading
- `docs/project-updates/29-project-update-v4-8a-production-cutover.md` — V4-8a execution results, decisions 115-121
- `docs/project-updates/v4-agentcore-architecture.md` — Architecture reference (three-layer eval section)
- `backend/calledit-backend/handlers/strands_make_call/eval_runner.py` — v3 eval runner (being replaced)
- `eval/golden_dataset.json` — v3 golden dataset (being reshaped)

---

## What Happened This Session

This was a research and strategy session — no code changes. The goal was to rethink evaluation from first principles for v4 rather than porting the v3 eval framework. The v3 framework had 17 evaluator modules (12 LLM judges), took 60+ minutes per full run, and was shaped around the old 4-agent serial graph with 3-category routing. None of that maps cleanly to v4's 3-turn single agent with continuous verifiability scoring.

### Research Conducted

1. **Strands Evals SDK documentation** — studied the full evaluator landscape, experiment management, and best practices from the official docs at strandsagents.com
2. **AgentCore evaluation patterns** — reviewed the three-layer eval architecture (Strands Evals → AgentCore Evaluations → Bedrock Evaluations)
3. **v3 eval framework audit** — catalogued all 17 evaluator modules, identified the cost/value ratio of each, mapped which ones are still relevant for v4
4. **v4 agent output analysis** — studied the `ParsedClaim`, `VerificationPlan`, and `PlanReview` Pydantic models to understand what v4 actually produces
5. **Golden dataset review** — examined the v3 dataset structure (45 base + 23 fuzzy, schema v3.1) and identified v3-specific fields that need reshaping

### Key Findings

**v3 eval was over-instrumented.** 17 evaluator modules with 12 LLM judge calls per prediction × 68 cases = ~816 LLM invocations per run. Most of the LLM judges were measuring overlapping things (ReasoningQuality × 3 agents, plus per-agent judges that covered the same ground). The Strands best practice is "start simple, combine multiple evaluators" — not "measure everything from day one."

**v3 dataset is v3-shaped.** The golden dataset has `expected_per_agent_outputs.categorizer.expected_category` mapping to the dead 3-category system (auto_verifiable/automatable/human_only). V4 uses a continuous verifiability score. The ground truth fields (verification_criteria, verification_method, verification_steps) are still valuable and map directly to v4's `VerificationPlan`, but the dataset needs reshaping to remove v3 debt and add v4-native ground truth.

**Two north star metrics emerged.** For the creation agent, what matters is: (1) did it convert natural language into the most verifiable JSON bundle possible? and (2) does the verifiability score accurately predict the verification agent's success? The second metric is the bridge between both agents — if the creation agent says 0.92 confidence but the verification agent fails, that's a calibration problem worth catching.

**Separate experiments, shared dashboard.** The creation agent and verification agent have fundamentally different jobs and should have separate eval experiments. But both should be accessible from the same dashboard, with a cross-agent calibration view that connects them.

## Decisions Made

### Decision 122: Tiered Evaluator Strategy for v4

**Source:** This update
**Date:** March 25, 2026

Replace the v3 "measure everything" approach with a tiered strategy:

**Tier 1 — Deterministic (every run, instant, free):**
- Schema validity (Pydantic model conformance for ParsedClaim, VerificationPlan, PlanReview)
- Field completeness (sources, criteria, steps all non-empty)
- Score range (verifiability_score between 0.0 and 1.0)
- Date resolution (valid ISO 8601 verification_date)
- Dimension count (exactly 5 dimension_assessments)
- Tier consistency (score_tier matches score value: ≥0.7=high, ≥0.4=moderate, <0.4=low)

**Tier 2 — LLM judge (on-demand, targeted):**
- Intent preservation (does the parsed claim + verification plan faithfully represent the user's original prediction?) — priority #1
- Plan quality (are criteria specific, sources real, steps executable?) — priority #2

**Tier 3 — Cross-agent calibration (milestone runs only):**
- Run creation agent, then verification agent on the same bundle
- Compare verifiability_score prediction vs actual verification outcome
- This is the metric that bridges both agents

**Rationale:** 6 deterministic + 2 LLM judges replaces 15 evaluators (12 LLM judges). Deterministic checks catch structural regressions instantly. LLM judges measure the things that actually matter. Cross-agent calibration is the ultimate quality signal but expensive (runs both agents), so milestone-only.

**Interview justification:** "We started with 17 evaluators in v3 and found that 12 LLM judges per prediction was measuring overlapping things at high cost. For v4 we followed the Strands best practice of starting simple — 6 fast deterministic checks for structural correctness, 2 targeted LLM judges for the metrics that actually matter (intent preservation and plan quality), and a cross-agent calibration metric for milestone runs. We can always add evaluators when the data shows a gap, but we can't un-waste the compute from running unnecessary judges."

### Decision 123: Separate Eval Experiments per Agent

**Source:** This update
**Date:** March 25, 2026

Creation agent and verification agent get separate eval experiments with separate test cases, evaluators, and scoring. Both accessible from the same HTML dashboard with a cross-agent calibration tab.

**Creation agent eval:**
- Input: prediction text → Output: prediction bundle (ParsedClaim + VerificationPlan + PlanReview)
- Measures: bundle quality (intent preservation, plan quality, score accuracy)
- Key question: "Did it convert natural language into the most verifiable bundle possible?"

**Verification agent eval:**
- Input: prediction bundle → Output: verdict (confirmed/refuted/inconclusive + confidence + evidence + reasoning)
- Measures: verdict accuracy, evidence quality
- Key question: "Given a well-formed bundle, did it produce the correct verdict?"

**Cross-agent calibration (connects both):**
- Run creation agent on prediction text, then verification agent on the resulting bundle
- Compare verifiability_score (creation agent's prediction of verification success) vs actual verification outcome
- Key question: "Does the creation agent accurately predict the verification agent's success?"

**Rationale:** The two agents have fundamentally different jobs, different input/output shapes, and different failure modes. Mixing them in one experiment would conflate creation quality with verification quality. The cross-agent calibration metric is the bridge.

### Decision 124: Golden Dataset Reshape for v4

**Source:** This update
**Date:** March 25, 2026

Reshape the golden dataset to be v4-native. No technical debt — the dataset should perfectly match what v4 agents produce and consume.

**Remove:**
- `expected_per_agent_outputs.categorizer.expected_category` (3-category system is dead in v4)
- `tool_manifest_config` (v4 uses AgentCore built-in tools, not MCP tool registry)
- Any v3-specific field references

**Add:**
- `expected_verifiability_score_range` (e.g., [0.8, 1.0] for easy predictions) — for score accuracy evaluation
- `expected_verification_outcome` (confirmed/refuted/inconclusive) — for cross-agent calibration
- `smoke_test` boolean flag — marks cases in the fast subset

**Keep:**
- `ground_truth.verification_criteria`, `verification_steps`, `verification_sources` — maps directly to v4's VerificationPlan
- `ground_truth.verifiability_reasoning`, `date_derivation`, `objectivity_assessment`
- `difficulty`, `dimension_tags`, `evaluation_rubric`
- `prediction_text`, `id`

**Rationale:** The v3 dataset was built around the 4-agent serial graph with category routing. V4 has a single agent with continuous scoring. Carrying v3 fields creates confusion about what's being measured. Clean break, same principle as Decision 113 (new DDB table, no v3 key format baggage).

### Decision 125: Smoke Test Subset Strategy

**Source:** This update
**Date:** March 25, 2026

Create a smoke test subset of ~12 cases for fast iteration: 4 easy + 5 medium + 3 hard, covering all domains (weather, finance, sports, nature, tech, personal). Flag these with `"smoke_test": true` in the dataset.

**Run tiers:**
- Smoke test (~12 cases, Tier 1 deterministic only): under 5 minutes, every iteration
- Smoke test + judges (~12 cases, Tier 1 + Tier 2): under 10 minutes, when testing prompt changes
- Full suite (all cases, Tier 1 + Tier 2): under 15 minutes, milestone runs
- Cross-agent calibration (subset with known verification outcomes): milestone-only, runs both agents

**Rationale:** v3 took 60+ minutes per full run because it ran 12 LLM judges on 68 cases. With 2 LLM judges instead of 12, even the full suite should be under 15 minutes. The smoke test subset enables rapid iteration without waiting for the full suite. The tiered approach means you always know what you're trading off — speed vs coverage.

### Decision 126: Creation Agent Priority Metrics

**Source:** This update
**Date:** March 25, 2026

The creation agent's evaluation priorities, in order:

1. **Intent preservation** — does the parsed claim + verification plan faithfully represent what the user meant? This is the foundation. If intent is lost, nothing else matters.
2. **Plan quality** — are the verification criteria specific and measurable? Are the sources real and accessible? Are the steps executable? A plan that preserves intent but can't be executed is useless.
3. **Score accuracy** — does the verifiability score (0.0-1.0) accurately predict how likely the verification agent is to succeed? This is the calibration metric that connects both agents.

**Rationale:** This ordering reflects the user's actual experience. A user submits "Lakers win tonight" and needs to trust that the system understood them (intent), built a plan that will actually work (plan quality), and gave them an honest confidence signal (score accuracy). Each layer depends on the one before it.

## V4-7a-1 Execution Results (Golden Dataset Reshape)

Spec executed successfully. Both scripts work, dataset is v4-native, validation passes all checks.

### Reshape Results
- 45 base predictions: v3 fields removed (`expected_per_agent_outputs`, `tool_manifest_config`), v4 fields added (`expected_verifiability_score_range`, `expected_verification_outcome`, `smoke_test`)
- 23 fuzzy predictions: `expected_post_clarification_outputs` replaced with `expected_post_clarification_verifiability` tier
- 45 evaluation rubrics updated (v3 terms → v4 concepts)
- 12 smoke test cases flagged (4 easy + 5 medium + 3 hard, all 12 domains)
- Schema version bumped to 4.0, dataset version bumped to 4.0
- Idempotency confirmed: second run shows 0 fields removed, 0 rubrics updated

### Validation Results
- Base predictions: PASS
- Fuzzy predictions: PASS
- Metadata & versions: PASS
- Smoke test constraints: PASS
- Result: ALL CHECKS PASSED

### V4-7a-2 Spec Created (Creation Agent Eval)
Requirements (14), design (17 correctness properties), and tasks (10 top-level) all complete. Ready for execution.

## Files Created/Modified

### Created
- `eval/reshape_v4.py` — v3→v4 dataset transformation script with lookup tables for all 45 predictions
- `eval/validate_v4.py` — structural validation script with 4 check categories
- `.kiro/specs/golden-dataset-v4-reshape/` — V4-7a-1 spec (requirements, design, tasks)
- `.kiro/specs/creation-agent-eval/` — V4-7a-2 spec (requirements, design, tasks)
- `docs/project-updates/30-project-update-v4-7a-eval-framework-redesign.md` — this document

### Modified
- `eval/golden_dataset.json` — reshaped from v3 (schema 3.0) to v4 (schema 4.0)
- `docs/project-updates/decision-log.md` — decisions 122-127
- `docs/project-updates/project-summary.md` — update 30 entry + current state
- `docs/project-updates/backlog.md` — items 2 and 8 marked SUPERSEDED

## Spec Plan (4 Specs)

The eval framework work is split into 4 specs, each with 90%+ confidence:

| Spec | Name | Confidence | Depends On | Scope |
|------|------|-----------|------------|-------|
| V4-7a-1 | Golden Dataset Reshape | 92% | None | Remove v3 fields, add v4 fields, flag smoke test subset |
| V4-7a-2 | Creation Agent Eval | 93% | V4-7a-1 | Tier 1 deterministic + Tier 2 LLM judges, Strands Evals SDK patterns, agentcore backend |
| V4-7a-3 | Verification Agent Eval | 95% | V4-7a-1 | Separate experiment, verdict accuracy evaluators |
| V4-7a-4 | Cross-Agent Calibration + Dashboard | 88% | V4-7a-2, V4-7a-3 | Calibration experiment (predicted vs actual), HTML dashboard with 3 tabs |

Specs 2 and 3 can run in parallel after Spec 1. Spec 4 depends on both.

## What the Next Agent Should Do

### Priority 1: Execute Spec V4-7a-2 (Creation Agent Eval)

The spec is fully created at `.kiro/specs/creation-agent-eval/` with requirements (14), design (17 properties), and tasks (10 top-level). Execute tasks in order:

1. Set up project structure (`eval/backends/`, `eval/evaluators/`, `eval/tests/`)
2. Implement AgentCore backend (`eval/backends/agentcore_backend.py`)
3. Implement 6 Tier 1 deterministic evaluators
4. Implement 2 Tier 2 LLM judge evaluators
5. Implement case loader and run tier filtering
6. Implement CLI runner and eval orchestration
7. Implement report generation
8. Wire everything together in `eval/creation_eval.py`

### Priority 2: Run Baseline Eval

After V4-7a-2 is built, run a smoke test against the deployed creation agent to establish the v4 baseline.

### Priority 3: Spec V4-7a-3 and V4-7a-4

After V4-7a-2 is executed and lessons learned are documented, create specs for:
- V4-7a-3: Verification Agent Eval (separate experiment)
- V4-7a-4: Cross-Agent Calibration + Dashboard

### Key Files to Read
- This update (decisions 122-126)
- `calleditv4/src/models.py` — v4 Pydantic models (what evaluators assess)
- `calleditv4/src/main.py` — creation agent (what produces the output)
- `calleditv4-verification/src/main.py` — verification agent
- `eval/golden_dataset.json` — current dataset (to be reshaped)
- `backend/calledit-backend/handlers/strands_make_call/eval_runner.py` — v3 eval runner (reference, not to be ported)

### Important Notes
- Start simple, expand with intention. The v3 mistake was measuring everything from day one.
- Every evaluator addition should be justified by data showing a gap, not by "it might be useful."
- The progress narrative (starting simple → adding evaluators based on data) should be visible in project updates.
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`


### Decision 127: Structured Eval Run Metadata for Dashboard Context

Each eval run carries structured metadata so the dashboard dropdown shows meaningful context instead of raw filenames. Fields: `description` (one-line goal, `--description` CLI flag), `prompt_versions`, `run_tier` (smoke/smoke+judges/full/calibration), `dataset_version`, `agent` (creation/verification). Dashboard shows `timestamp | agent | tier | description`. Auto-generated default if `--description` omitted. This will be implemented in Spec V4-7a-2 (Creation Agent Eval).


### Dashboard Comparison UX (Note for V4-7a-4)

The structured run metadata (Decision 127) enables multi-dimensional comparison in the dashboard. Users should be able to filter and superimpose runs across any metadata dimension:
- Same prompts, different models → model comparison
- Same model, different prompt versions → prompt iteration tracking
- Same config, different git commits → code change impact
- Any combination of the above

The metadata fields that serve as filter/group-by dimensions: `model_id`, `prompt_versions`, `git_commit`, `agent_runtime_arn`, `run_tier`, `dataset_version`. The dashboard loads all reports from `eval/reports/`, parses metadata, and provides filter controls for overlay comparison.
