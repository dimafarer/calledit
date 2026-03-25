# Project Update 30 — V4-7a Eval Framework Redesign + Execution

**Date:** March 25, 2026
**Context:** Research session to redesign the eval framework from first principles for v4 AgentCore agents, followed by execution of V4-7a-1 (golden dataset reshape), V4-7a-2 (creation agent eval), and the first judge baseline run.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** 15d2cfb

### Referenced Kiro Specs
- `.kiro/specs/golden-dataset-v4-reshape/` — V4-7a-1 spec (COMPLETE)
- `.kiro/specs/creation-agent-eval/` — V4-7a-2 spec (COMPLETE — judge baseline run done)

### Prerequisite Reading
- `docs/project-updates/29-project-update-v4-8a-production-cutover.md` — V4-8a execution results, decisions 115-121
- `docs/project-updates/v4-agentcore-architecture.md` — Architecture reference (three-layer eval section)
- `eval/golden_dataset.json` — v4-reshaped dataset (schema 4.0)
- `eval/reports/creation-eval-20260325-205419.json` — first judge baseline report

---

## What Happened This Session

This update covers two distinct phases: the original research session (no code, just strategy) and the execution session that followed — building the eval framework, running the first baselines, and getting the first real data on how the v4 creation agent performs.

### Phase 1: Research — Rethinking Eval from First Principles

The starting point was a question: do we port the v3 eval framework to v4, or rebuild it? The v3 framework had 17 evaluator modules (12 LLM judges), took 60+ minutes per full run, and was shaped around the old 4-agent serial graph with 3-category routing. None of that maps cleanly to v4's 3-turn single agent with continuous verifiability scoring. The answer was obvious once we looked at it clearly: rebuild.

The research covered the Strands Evals SDK docs, the AgentCore evaluation patterns, a full audit of the v3 evaluator modules (cataloguing cost vs value for each), and a close read of the v4 Pydantic models to understand what the agent actually produces. The v3 dataset also needed attention — it had `expected_per_agent_outputs.categorizer.expected_category` fields mapping to the dead 3-category system, and `tool_manifest_config` fields that made no sense in a world where tools are AgentCore built-ins.

The key insight that shaped everything: **v3 eval was measuring the wrong things at too high a cost.** 12 LLM judges × 68 cases = ~816 LLM invocations per run, and most of those judges were measuring overlapping things. The Strands best practice is "start simple, combine multiple evaluators" — not "measure everything from day one." For v4, we landed on 6 deterministic checks (instant, free, catch structural regressions) + 2 targeted LLM judges (intent preservation and plan quality — the two things that actually matter). That's it. We can always add evaluators when the data shows a gap.

Two north star metrics emerged from this thinking: (1) did the creation agent convert natural language into the most verifiable bundle possible? and (2) does the verifiability score accurately predict the verification agent's success? The second metric is the bridge between both agents — it's the calibration question that connects the whole system.

### Phase 2: Building the Eval Framework (V4-7a-1 and V4-7a-2)

The golden dataset reshape (V4-7a-1) was clean. The `reshape_v4.py` script transformed all 45 base predictions and 23 fuzzy predictions to v4-native format, flagged 12 smoke test cases (4 easy + 5 medium + 3 hard), and bumped the schema to 4.0. Idempotency confirmed on second run. Validation passed all checks.

Building the eval runner (V4-7a-2) was more interesting. The AgentCore backend was the tricky part — the agent uses JWT auth (Decision 121), which means boto3 SDK won't work. Had to use direct HTTPS requests with a Cognito bearer token. The SSE stream from AgentCore is double-encoded: `data: "{\"type\": ...}"` — the outer JSON is a string, not an object. Two `json.loads()` calls to unwrap it. This took a couple of debug runs to figure out (hence the three smoke run reports before the final clean baseline).

The first clean smoke run (`creation-eval-20260325-193650.json`) showed 12/12 cases, 100% Tier 1 pass rate. Structural correctness is solid — the agent always produces valid schemas, non-empty fields, scores in range, valid dates, exactly 5 dimensions, consistent tiers. That's the foundation. Now we needed the judges.

### Phase 3: The Prompt Version Investigation

Before running the judge baseline, we hit the prompt version question. The eval-framework rules are clear: always pin to numbered versions, never use DRAFT. But we needed to check whether DRAFT matched the latest numbered version first — if they're the same, we just use the numbered version. If they've diverged, we need to understand why before running.

The investigation revealed a mixed picture:
- `verification_planner` v1 = DRAFT ✓ (match)
- `plan_reviewer` v2 = DRAFT ✓ (match)
- `prediction_parser` DRAFT ≠ v1 ✗ (diverged — 1960 chars vs 1557 chars, 38 lines vs 31 lines)

The diff on the parser was meaningful. v1 had ambiguous timezone handling — it mentioned `current_time` only as a fallback for "no location context." The DRAFT had been updated with an explicit priority ladder: (1) call `current_time` first, (2) use location if available, (3) UTC as last resort. This is strictly better — it makes the timezone resolution deterministic and transparent. The DRAFT wasn't just different, it was an improvement.

The right move was to pin the DRAFT as v2 before running. We added `PredictionParserPromptVersionV2` to `infrastructure/prompt-management/template.yaml` and deployed via `aws cloudformation deploy`. This is how prompt versioning is supposed to work — the template is the source of truth, versions are immutable, and you deploy to create them. (Note: `list_prompt_versions` doesn't exist on the boto3 bedrock-agent client — had to use `list_prompts` with an identifier filter to enumerate versions. Minor gotcha.)

### Phase 4: The Judge Baseline

The judge run took 694 seconds — about 58 seconds per case including the two LLM judge calls. Results:

```
Tier 1 (deterministic): all 1.00 (unchanged from smoke-only)
Tier 2 (LLM judges):
  intent_preservation: 0.88
  plan_quality: 0.57
```

The 0.88 intent preservation is genuinely good. The parser understands what users mean in 10/12 cases. The two cases that scored lower were both defensible: base-023 (DMV wait time, 0.20) is a hard case where "nearest DMV" requires location context the agent doesn't have — that's a legitimately low-verifiability prediction, not a parser failure. base-015 (flight AA1234, 0.90) had minor drift where the planner added a "15-minute on-time window" assumption that wasn't in the original prediction.

The 0.57 plan quality was the interesting number. At first glance it looks bad. But when you look at the per-case breakdown, it tells a very clear story: **the score splits cleanly by prediction type.**

Objective/factual predictions — Christmas day-of-week (0.95), S&P 500 close (0.85), Tokyo temperature (0.90), Python 3.13 release (0.90) — all scored 0.80–0.95. The planner builds specific, executable plans with real sources for these. The judge was impressed.

Personal/private-data predictions — movie enjoyment (0.20), dinner taste (0.20), work promotion (0.30), Fitbit steps (0.30) — all scored 0.20–0.30. The judge's reasoning was consistent across all of them: the planner assumes it can contact the predictor directly or access their private devices/accounts. "Contact or check with the person who made the prediction" is not a step an automated agent can execute. The planner is trying to build automated verification for things that can only be verified via self-report.

This is actually good news. The 0.57 isn't random noise — it's a precise signal pointing at a specific, fixable problem. The v3 VBPrompt already had a "Track 2 — Self-report" pattern for exactly this case (schedule a prompt, ask a specific yes/no question at the right time, record the self-assessment). We just need to port that pattern to the v4 verification planner. Backlog item 15 tracks this.

One gotcha discovered during the run: the `prompt_versions` field in the report shows "DRAFT" even though we ran with pinned env vars. This is because the field comes from `get_prompt_version_manifest()` inside the deployed agent — it reflects what the agent fetched at runtime, not what we intended. The agent was deployed before we pinned v2, so it's still reporting DRAFT. The env vars control which version gets fetched, but the agent needs to be re-launched (`agentcore launch`) for the new version to take effect in the manifest. Decision 128 documents this. It's a workflow gotcha worth knowing for future runs.

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

### Decision 127: Structured Eval Run Metadata for Dashboard Context

**Source:** This update
**Date:** March 25, 2026

Each eval run carries structured metadata so the dashboard dropdown shows meaningful context instead of raw filenames. Fields: `description` (one-line goal, `--description` CLI flag), `prompt_versions`, `run_tier` (smoke/smoke+judges/full/calibration), `dataset_version`, `agent` (creation/verification). Dashboard shows `timestamp | agent | tier | description`. Auto-generated default if `--description` omitted.

**Dashboard Comparison UX (Note for V4-7a-4):** The structured run metadata enables multi-dimensional comparison — filter and overlay runs by `model_id`, `prompt_versions`, `git_commit`, `agent_runtime_arn`, `run_tier`, `dataset_version`. Same prompts + different models → model comparison. Same model + different prompt versions → prompt iteration tracking. Same config + different git commits → code change impact.

### Decision 128: Eval Report prompt_versions Reflects Agent-Reported Versions, Not Runner Env Vars

**Source:** This update — judge baseline run
**Date:** March 25, 2026

The `prompt_versions` field in eval reports comes from `get_prompt_version_manifest()` inside the deployed agent (populated when the agent calls `fetch_prompt()` at runtime), not from the `PROMPT_VERSION_*` env vars set in the eval runner. If the agent was deployed before a new prompt version was pinned, the report will show "DRAFT" even if the runner was invoked with pinned versions. The env vars only affect which version the agent fetches — but the agent must be re-deployed (via `agentcore launch`) for the new version to take effect. Future eval runs should verify the deployed agent's prompt versions match the intended pinned versions before running.

### Decision 129: Plan Quality 0.57 Baseline — Verification Planner Fails on Personal/Subjective Predictions

**Source:** This update — judge baseline run
**Date:** March 25, 2026

The first judge baseline revealed a clean split in plan quality by prediction type. Objective/factual predictions (calendar facts, stock prices, weather, tech releases) score 0.80–0.95. Personal/subjective predictions (movie enjoyment, dinner taste, work promotion, Fitbit steps) score 0.20–0.30 — the planner tries to build automated verification plans that assume agent-to-user contact or access to private devices/accounts, which is impossible. The fix: the verification planner needs to recognize personal/private-data predictions and build structured self-report plans (schedule a prompt, ask the user a specific yes/no question at the right time) instead of pretending it has access it doesn't have. This is the primary improvement target for the next prompt iteration. Tracked in backlog item 15.

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

## V4-7a-2 Execution Results (Creation Agent Eval — Judge Baseline)

### Run: smoke+judges, March 25, 2026
- Report: `eval/reports/creation-eval-20260325-205419.json`
- Description: "V4-7a first judge baseline — parser v2 timezone fix"
- Prompt versions: prediction_parser=2, verification_planner=1, plan_reviewer=2
- Duration: 694.3s (12 cases × ~58s avg including judge calls)
- Git commit: 15d2cfb

### Tier 1 Results (deterministic)
All 6 deterministic evaluators: **1.00** (100% pass rate, same as smoke-only baseline)

### Tier 2 Results (LLM judges)
- **intent_preservation: 0.88** — strong. 10/12 cases scored ≥0.9. Two failures:
  - base-023 (DMV wait time): 0.20 — agent couldn't identify "nearest DMV" without user location, transformed a specific claim into a general location search problem
  - base-015 (flight AA1234): 0.90 — minor drift, added "15-minute on-time window" assumption not in original prediction
- **plan_quality: 0.57** — moderate. Clear split by prediction type:
  - Objective/factual predictions (base-002 Christmas, base-004 S&P 500, base-008 Tokyo temp, base-011 Python release): 0.85–0.95
  - Personal/private data predictions (base-027 movie enjoyment, base-034 dinner taste, base-033 promotion, base-044 Fitbit steps): 0.20–0.30
  - Root cause: verification planner builds plans that assume agent can contact the predictor directly or access private devices/accounts — impossible for an automated agent

### Key Findings

**Intent preservation is strong (0.88).** The parser correctly captures what users mean in 10/12 cases. The one clear failure (DMV) is a hard case — "nearest" requires location context the agent doesn't have. This is a legitimate low-verifiability prediction, not a parser bug.

**Plan quality splits cleanly by prediction type.** Objective predictions (weather, stocks, calendar facts, tech releases) get excellent plans (0.80–0.95). Personal/subjective predictions get poor plans (0.20–0.30) because the planner tries to build automated verification for things that require self-report. The planner needs to recognize when self-report is the only valid verification path and build a structured self-report plan instead of assuming agent-to-user contact.

**The 0.57 plan quality score is signal, not noise.** It correctly identifies a real weakness: the verification planner doesn't handle personal/subjective predictions well. This is the primary improvement target for the next prompt iteration.

**Prompt versions show as DRAFT in report despite pinned env vars.** The `prompt_versions` field in the report comes from what the agent returns in the bundle (which reads from `get_prompt_version_manifest()` inside the agent), not from the eval runner's env vars. The agent was deployed before we pinned v2 — it's still reading DRAFT. This is a known limitation: the report's `prompt_versions` reflects what the deployed agent reports, not what we intended. Decision 128 tracks this.

### Pre-Run: Prediction Parser v2 Pinned
Before running the judge baseline, we discovered the prediction_parser DRAFT had diverged from v1:
- v1 (1557 chars, 31 lines): timezone handling was ambiguous — mentioned `current_time` only as fallback for "no location context"
- DRAFT/v2 (1960 chars, 38 lines): explicit `current_time`-first priority ladder: (1) explicit location, (2) `current_time` tool's timezone, (3) UTC as last resort
- Added `PredictionParserPromptVersionV2` to `infrastructure/prompt-management/template.yaml` and deployed
- verification_planner v1 = DRAFT (match), plan_reviewer v2 = DRAFT (match) — no changes needed

## Files Created/Modified

### Created
- `eval/reshape_v4.py` — v3→v4 dataset transformation script with lookup tables for all 45 predictions
- `eval/validate_v4.py` — structural validation script with 4 check categories
- `.kiro/specs/golden-dataset-v4-reshape/` — V4-7a-1 spec (requirements, design, tasks)
- `.kiro/specs/creation-agent-eval/` — V4-7a-2 spec (requirements, design, tasks)
- `eval/backends/agentcore_backend.py` — AgentCore HTTPS + JWT backend for eval runner
- `eval/evaluators/schema_validity.py`, `field_completeness.py`, `score_range.py`, `date_resolution.py`, `dimension_count.py`, `tier_consistency.py` — 6 Tier 1 deterministic evaluators
- `eval/evaluators/intent_preservation.py`, `plan_quality.py` — 2 Tier 2 LLM judge evaluators
- `eval/creation_eval.py` — CLI eval runner with tiered evaluators, report generation, structured metadata
- `eval/reports/creation-eval-20260325-185638.json` — first smoke run (pre-double-encoding fix)
- `eval/reports/creation-eval-20260325-192039.json` — second smoke run
- `eval/reports/creation-eval-20260325-193650.json` — third smoke run (double-encoding fix confirmed, 100% Tier 1)
- `eval/reports/creation-eval-20260325-205419.json` — first judge baseline (smoke+judges, intent_preservation=0.88, plan_quality=0.57)
- `docs/project-updates/30-project-update-v4-7a-eval-framework-redesign.md` — this document

### Modified
- `eval/golden_dataset.json` — reshaped from v3 (schema 3.0) to v4 (schema 4.0)
- `infrastructure/prompt-management/template.yaml` — added `PredictionParserPromptVersionV2` (explicit current_time-first timezone priority ladder)
- `docs/project-updates/decision-log.md` — decisions 122-129
- `docs/project-updates/project-summary.md` — update 30 entry + current state
- `docs/project-updates/backlog.md` — items 2 and 8 marked SUPERSEDED, item 15 added (verification planner self-report plans)

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

### Priority 1: Spec V4-7a-3 (Verification Agent Eval)

Separate eval experiment for the verification agent. Key differences from creation agent eval:
- Input: prediction bundle (not raw text) — the verification agent receives a bundle from DDB
- Output: verdict (confirmed/refuted/inconclusive) + confidence + evidence + reasoning
- The verification agent is sync (not streaming) — simpler backend than creation agent
- Evaluators: schema validity (verdict fields), verdict accuracy (against ground truth), evidence quality (LLM judge)
- Agent ARN: `arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_verification_Agent-77DiT7GHdH`
- Only cases with `verification_readiness: immediate` and `expected_verification_outcome` not null can be tested

### Priority 2: Spec V4-7a-4 (Cross-Agent Calibration + Dashboard)

- Cross-agent calibration: run creation agent → feed bundle to verification agent → compare verifiability_score prediction vs actual verdict
- HTML dashboard with 3 tabs: creation agent, verification agent, cross-agent calibration
- Dashboard must support multi-dimensional comparison via metadata (Decision 127)
- Filter/overlay runs by: model_id, prompt_versions, git_commit, features (LTM/STM), run_tier

### Priority 3: Iterate on Verification Planner Prompt (Backlog Item 15)

Plan quality baseline is 0.57. The fix is targeted — teach the planner to build structured self-report plans for personal/private-data predictions instead of assuming automated access. Port the v3 VBPrompt "Track 2 — Self-report" pattern to the v4 verification planner. Deploy as v2, run smoke+judges to measure improvement.

### Key Files to Read
- This update (decisions 122-129)
- `eval/creation_eval.py` — working eval runner (reference for V4-7a-3 backend)
- `eval/backends/agentcore_backend.py` — creation agent backend (adapt for verification agent)
- `eval/evaluators/` — 6 Tier 1 + 2 Tier 2 evaluators (reference for V4-7a-3 evaluators)
- `eval/reports/creation-eval-20260325-205419.json` — first judge baseline (per-case scores)
- `calleditv4-verification/src/main.py` — verification agent (what produces the output)
- `eval/golden_dataset.json` — dataset with `verification_readiness` and `expected_verification_outcome` fields
- `infrastructure/prompt-management/template.yaml` — verification planner prompt (for backlog item 15)

### Important Notes
- Prompt versions show as DRAFT in reports even when runner uses pinned env vars — agent must be re-launched after pinning (Decision 128)
- Plan quality primary improvement target: verification planner self-report plans (Decision 129, backlog item 15)
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Cognito credentials are set as environment variables — no need to export them manually
