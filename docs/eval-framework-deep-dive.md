# CalledIt Eval Framework — Deep Dive

> "Is it actually getting better, or does it just feel like it?"

The eval framework is the centerpiece of CalledIt. It measures whether two AI agents — one that understands human predictions, one that verifies them — are doing their jobs well. Every prompt change, tool swap, and architecture decision in this project was validated by running predictions through the eval pipeline and comparing numbers.

This document explains how it works, why it's designed this way, and what the numbers mean.

---

## The Three Questions

The eval framework answers three questions, each targeting a different agent:

1. **Did the creation agent understand the user's intent?** → Intent Preservation (IP)
2. **Did it build a plan the verification agent can execute?** → Plan Quality (PQ)
3. **Does the creation agent's confidence predict verification success?** → Calibration Accuracy (CA)

These aren't abstract metrics. IP tells you if "Lakers win tonight" got parsed as the right game on the right date. PQ tells you if the verification plan references tools the agent actually has. CA tells you if a 0.85 verifiability score means the verification agent will actually resolve the prediction — or if the creation agent is just guessing.

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │           Golden Dataset (70 predictions)    │
                    │  54 static (hand-curated, timeless)          │
                    │  16 dynamic (time-anchored, regenerated)     │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │         Dataset Audit & Filtering            │
                    │  Filter: only predictions with known         │
                    │  expected outcomes (22 of 70 qualify)        │
                    └──────────────────┬──────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────────────┐
                    │                  │                           │
                    ▼                  │                           │
        ┌───────────────────┐          │                           │
        │  PHASE 1: Create  │          │                           │
        │                   │          │                           │
        │  For each case:   │          │                           │
        │  prediction_text  │          │                           │
        │       ↓           │          │                           │
        │  Creation Agent   │          │                           │
        │  (JWT + HTTPS)    │          │                           │
        │       ↓           │          │                           │
        │  Prediction       │          │                           │
        │  Bundle → DDB     │          │                           │
        └────────┬──────────┘          │                           │
                 │                     │                           │
                 ▼                     │                           │
        ┌───────────────────┐          │                           │
        │  PHASE 2: Wait    │          │                           │
        │                   │          │                           │
        │  Compute wait     │          │                           │
        │  from bundle      │          │                           │
        │  verification     │          │                           │
        │  dates            │          │                           │
        │  (cap at 5 min)   │          │                           │
        └────────┬──────────┘          │                           │
                 │                     │                           │
                 ▼                     │                           │
        ┌───────────────────┐          │                           │
        │  PHASE 3: Verify  │          │                           │
        │                   │          │                           │
        │  For each case:   │          │                           │
        │  prediction_id    │          │                           │
        │       ↓           │          │                           │
        │  Verification     │          │                           │
        │  Agent (SigV4)    │          │                           │
        │       ↓           │          │                           │
        │  Verdict → DDB    │          │                           │
        └────────┬──────────┘          │                           │
                 │                     │                           │
                 ▼                     ▼                           │
        ┌─────────────────────────────────────────────┐           │
        │            PHASE 4: Evaluate                 │           │
        │                                              │           │
        │  ┌─────────────────┐  ┌──────────────────┐  │           │
        │  │ Creation Evals  │  │ Verification     │  │           │
        │  │                 │  │ Evals            │  │           │
        │  │ 6 Tier 1 (det.) │  │ 5 Tier 1 (det.) │  │           │
        │  │ 2 Tier 2 (LLM) │  │ 2 Tier 2 (LLM)  │  │           │
        │  └────────┬────────┘  └────────┬─────────┘  │           │
        │           │                    │             │           │
        │           └────────┬───────────┘             │           │
        │                    ▼                         │           │
        │           ┌────────────────┐                 │           │
        │           │  Calibration   │                 │           │
        │           │  Metrics       │                 │           │
        │           │                │                 │           │
        │           │  score vs      │                 │           │
        │           │  outcome       │                 │           │
        │           └────────────────┘                 │           │
        └──────────────────┬───────────────────────────┘           │
                           │                                       │
                           ▼                                       │
        ┌─────────────────────────────────────────────┐           │
        │          Unified Report (JSON + DDB)         │           │
        │                                              │           │
        │  creation_scores, verification_scores,       │           │
        │  calibration_scores, per_case_results        │           │
        └──────────────────┬───────────────────────────┘           │
                           │                                       │
                           ▼                                       │
        ┌─────────────────────────────────────────────┐           │
        │          React Dashboard (/eval)             │◄──────────┘
        │                                              │
        │  Scatter plots, score grids, case tables,    │
        │  phase timing, verdict distributions         │
        └─────────────────────────────────────────────┘
```

## What's Built vs What's Planned

The eval system is custom-built Python code. The LLM judges are Strands agents calling Bedrock models with evaluation rubric prompts. The deterministic evaluators are pure Python functions. The pipeline orchestrates everything: invoke agents, run evaluators, compute calibration, write reports.

We evaluated several AWS services for eval (Decisions 23-26, 43): Strands Evals SDK, AgentCore Evaluations, Bedrock Evaluations, Bedrock Guardrails, SageMaker Clarify. The custom approach won because it was simpler, more flexible, and gave us exactly the evaluators we needed without framework overhead.

**What's built and running:**
- Unified eval pipeline (`eval/unified_eval.py`) — creation → verification → evaluate → report
- 8 deterministic evaluators (structural correctness, instant, free)
- 4 LLM judges (Strands agents with Bedrock models, rubric-based scoring)
- Calibration metrics (cross-agent score-vs-outcome analysis)
- Golden dataset (54 static + 16 dynamic predictions)
- DDB report store + React dashboard
- ~75 minutes for 22 cases, ~$15-20 per full run

**What's not built (future work):**
- AgentCore Evaluations integration for span-level trace analysis on production traffic (infrastructure ready — observability enabled on both runtimes)
- Production-scale monitoring with automated quality alerts

## The Evaluators

### Creation Agent — Tier 1 (Deterministic)

These run on every eval, cost nothing, and catch structural regressions instantly:

| Evaluator | What It Checks | Failure Means |
|-----------|---------------|---------------|
| `schema_validity` | Bundle validates against Pydantic models (ParsedClaim, VerificationPlan, PlanReview) | Agent returned malformed output |
| `field_completeness` | All required fields are present and non-empty | Agent skipped a field |
| `score_range` | Verifiability score is between 0.0 and 1.0 | Score out of bounds |
| `date_resolution` | Verification date is a valid ISO datetime | Date parsing failed |
| `dimension_count` | At least 1 dimension assessment in the review | Reviewer didn't assess dimensions |
| `tier_consistency` | Score tier (high/medium/low) matches the numeric score | Tier label doesn't match score |

**Current baseline:** 1.00 (all pass, every run). These haven't failed since the Pydantic models were stabilized in V4-3a.

### Creation Agent — Tier 2 (LLM Judges)

These cost money (Bedrock model invocations) and take time, but measure reasoning quality that deterministic checks can't:

| Evaluator | Judge Model | What It Measures | Current Score |
|-----------|------------|-----------------|---------------|
| `intent_preservation` | Sonnet 4 | Does the bundle preserve the user's original prediction intent? Fidelity, temporal intent, scope, assumptions. | 0.87 |
| `plan_quality` | Sonnet 4 | Would this verification plan actually succeed? Source quality, criteria specificity, step executability. | 0.81 |

**Why Sonnet, not Opus?** Originally Opus 4.6 (Decision 27), but Sonnet 4 is sufficient for judging and much faster. Opus is reserved for the reflection architecture (backlog item 20).

**Rubric design:** Each judge has a detailed rubric with scoring bands (1.0 = perfect, 0.7-0.9 = minor drift, 0.4-0.6 = moderate, 0.0-0.3 = major). The rubric is injected as a prompt, not hardcoded logic. This means rubric improvements are prompt changes, testable through the same eval pipeline.

### Verification Agent — Tier 1 (Deterministic)

| Evaluator | What It Checks |
|-----------|---------------|
| `verification_schema_validity` | Verdict response validates against VerificationResult model |
| `verification_verdict_validity` | Verdict is one of: confirmed, refuted, inconclusive |
| `verification_confidence_range` | Confidence is between 0.0 and 1.0 |
| `verification_evidence_completeness` | At least 1 evidence item when verdict is confirmed/refuted |
| `verification_evidence_structure` | Each evidence item has source, finding, relevant_to_criteria |

### Verification Agent — Tier 2 (LLM Judges)

| Evaluator | What It Measures | Current Score |
|-----------|-----------------|---------------|
| `verification_verdict_accuracy` | Does the verdict match the golden dataset's expected outcome? | 0.94 |
| `verification_evidence_quality` | Quality of evidence gathered — source reliability, finding clarity, relevance to criteria | 0.73 |

### Verification Mode-Specific Evaluators

Different verification modes have different correctness criteria:

| Evaluator | Mode | What It Checks |
|-----------|------|---------------|
| `verification_at_date_verdict_accuracy` | at_date | Only valid after verification_date has passed |
| `verification_before_date_verdict_appropriateness` | before_date | Inconclusive before deadline is correct |
| `verification_recurring_evidence_freshness` | recurring | Evidence should be from the current check |

### Calibration Metrics

Calibration measures the bridge between the two agents — does the creation agent's verifiability score predict the verification agent's success?

| Metric | What It Measures | Current Score |
|--------|-----------------|---------------|
| `calibration_accuracy` | High score + resolved (confirmed OR refuted) = correct. High score + inconclusive = wrong. | 0.95 |
| `mean_absolute_error` | Average distance between predicted score and binary outcome | 0.16 |
| `high_score_confirmation_rate` | % of high-score predictions that get resolved | 0.95 |
| `low_score_failure_rate` | % of low-score predictions that fail to resolve | 0.00 |

**Key insight (Decision 148):** "High score" means "easy to verify," not "expected to be confirmed." A prediction scored 0.85 that gets correctly *refuted* is a calibration success — the agent predicted it would be easy to verify, and it was. Only inconclusive on a high-score prediction is a calibration failure.

## The Golden Dataset

The golden dataset is the ground truth that all eval runs are measured against.

### Static Dataset (`eval/golden_dataset.json`)

54 hand-curated predictions across 18 personas, schema version 4.0. Each prediction includes:

- `prediction_text` — the raw natural language prediction
- `ground_truth` — structured metadata: verifiability reasoning, date derivation, verification sources, objectivity assessment, verification criteria, verification steps
- `expected_verification_outcome` — confirmed, refuted, or null (not yet verifiable / uncertain)
- `verification_mode` — immediate, at_date, before_date, recurring
- `expected_verifiability_score_range` — [low, high] range the creation agent should produce
- `evaluation_rubric` — human-written guidance for the LLM judges
- `smoke_test` — boolean flag for the 12-case quick iteration subset

**Why 54 predictions but only 22 qualify?** Most predictions have `expected_verification_outcome: null` — they're in the dataset for creation agent testing (verifiability scoring, plan quality) but don't have a known ground truth verdict. Only predictions with a definitive expected outcome count toward verdict accuracy.

### Dynamic Dataset (`eval/dynamic_golden_dataset.json`)

16 time-anchored predictions regenerated before each eval run by `eval/generate_dynamic_dataset.py`:

- 9 deterministic (date calculations, math facts — no external API needed)
- 7 Brave Search-dependent (current events, live data — requires BRAVE_API_KEY)
- 4 verification modes covered (immediate, at_date, before_date, recurring)
- Each prediction has a computed `expected_verification_outcome` based on the generation-time data

**Why dynamic?** The static dataset went stale. A prediction about the next full moon had a hardcoded expected date that was correct when written but wrong two weeks later (base-010). The dynamic generator computes ground truth at generation time, so it's always current.

### Dataset Merger

`eval/dataset_merger.py` combines static + dynamic datasets via `--dynamic-dataset` CLI arg. Dynamic predictions with a `replaces` field override matching static predictions that have `time_sensitive: true`. Without `--dynamic-dataset`, runners behave exactly as before.

## The Unified Pipeline

`eval/unified_eval.py` is the single pipeline that mirrors production flow:

```
Dataset Audit → Creation Pass → Wait → Verification Pass → Evaluation → Report → Cleanup
```

### Phase 1: Creation Pass
For each qualifying prediction, invoke the creation agent via HTTPS with Cognito JWT auth. The agent runs the 3-turn flow (parse → plan → review) and saves a prediction bundle to the eval DDB table (`calledit-v4-eval`, not the production table).

### Phase 2: Wait
Compute the exact wait time from bundle verification dates. Immediate and recurring predictions proceed instantly. At_date and before_date predictions wait until their verification date (capped at 5 minutes for eval runs).

### Phase 3: Verification Pass
For each case, invoke the verification agent via HTTPS with SigV4 auth (same pattern as the production scanner Lambda). The agent loads the bundle from DDB, gathers evidence, and writes the verdict back.

### Phase 4: Evaluation
Run all evaluators against each case:
- 6 creation Tier 1 evaluators (instant, deterministic)
- 2 creation Tier 2 judges (LLM, ~10s each)
- 5 verification Tier 1 evaluators (instant, deterministic)
- 2 verification Tier 2 judges (LLM, ~10s each)
- Calibration metrics (deterministic, computed from scores + verdicts)

### Phase 5: Report
Write a unified JSON report with `creation_scores`, `verification_scores`, `calibration_scores`, and `per_case_results`. Also written to DDB (`calledit-v4-eval-reports` table) for the dashboard.

### Phase 6: Cleanup
Delete eval bundles from the eval DDB table to prevent accumulation.

## The Dashboard

The React dashboard at `/eval` reads reports from DDB and renders them with zero knowledge of evaluator internals. Adding a new evaluator or metric requires no frontend code changes — the dashboard renders whatever keys appear in the report.

### Unified Pipeline Tab (Default)
- **Calibration scatter plot** — "Can Our Agents Verify What They Promise?" X-axis: verifiability score, Y-axis: verification outcome. Green dots = calibration correct, red dots = calibration wrong.
- **Three-column score grid** — Creation (blue), Verification (purple), Calibration (amber)
- **Phase timing breakdown** — creation, wait, verification, evaluation durations
- **Per-case results table** — case ID, score, verdict, confidence, pass/fail indicator

### Creation Tab
- Per-evaluator scores with pass/fail indicators
- IP and PQ trend lines across runs

### Verification Tab
- Per-evaluator scores
- Verdict distribution (confirmed/refuted/inconclusive/error)
- Per-mode breakdowns (immediate, at_date, before_date, recurring)

### Calibration Tab
- Scatter plot with score-vs-outcome
- MAE, high_score_confirmation_rate, low_score_failure_rate

## Methodology: Isolated Single-Variable Testing

Every eval iteration changes exactly one thing (Decision 50):

- **Prompt change:** Update one prompt version in Bedrock Prompt Management, re-run eval, compare scores. The run metadata captures `prompt_versions: {"prediction_parser": "2", "verification_planner": "2", "plan_reviewer": "3"}` so you know exactly which prompts were used.
- **Tool change:** Switch `VERIFICATION_TOOLS` from `brave` to `browser`, re-run eval, compare. The run metadata captures the tool configuration.
- **Dataset change:** Add or modify golden dataset predictions, re-run eval, compare. The run metadata captures `dataset_sources`.

This methodology has been followed across 37 project updates. Every before/after comparison is documented with the exact variable that changed.

## Run Metadata

Every eval report includes structured metadata for multi-dimensional comparison:

```json
{
  "run_id": "unified-eval-20260401-015709",
  "timestamp": "2026-04-01T01:57:09Z",
  "description": "Browser tool fix baseline - VERIFICATION_TOOLS=browser",
  "tier": "full",
  "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
  "prompt_versions": {
    "prediction_parser": "2",
    "verification_planner": "2",
    "plan_reviewer": "3",
    "verification_executor": "2"
  },
  "dataset_sources": ["golden_dataset.json", "dynamic_golden_dataset.json"],
  "total_cases": 22,
  "excluded_cases": 48,
  "duration_seconds": 4521.3
}
```

This enables the dashboard to filter and overlay runs by any dimension: model, prompt versions, tool configuration, dataset version.

## Historical Baselines

| Date | Config | Cases | IP | PQ | VA | EQ | CA | Notes |
|------|--------|-------|----|----|----|----|----|-------|
| Mar 25 | Sonnet, smoke | 12 | — | — | — | — | — | First v4 baseline, 100% Tier 1 |
| Mar 26 | Sonnet, full | 7 | — | — | 0.43 | 0.46 | 0.50 | Browser failures (4/7) |
| Mar 30 | Sonnet+Brave | 7 | — | — | 0.86 | — | — | Brave Search added (Decision 145) |
| Mar 31 | Unified, Brave | 23 | 0.89 | 0.88 | 0.89 | 0.59 | 0.91 | First unified baseline |
| Apr 1 | Unified, Browser | 22 | 0.87 | 0.81 | 0.94 | 0.73 | 0.95 | Browser fix (Decision 149) |

The trend tells a story: verification accuracy went from 0.43 (Browser broken) → 0.86 (Brave workaround) → 0.89 (unified pipeline) → 0.94 (Browser fixed). Evidence quality jumped from 0.46 → 0.73 when Browser started working — the agent gets better evidence from a full browser than from search result snippets.

## Cost

| Run Type | Duration | Approx Cost | When to Use |
|----------|----------|-------------|-------------|
| Dry run | ~5s | $0 | Check case count, dataset filtering |
| Single case | ~2-5 min | ~$1 | Quick iteration on one prediction |
| Smoke (12 cases) | ~15 min | ~$5 | Fast feedback on prompt changes |
| Full (22 cases) | ~75 min | ~$15-20 | Milestone baselines, before/after comparisons |

## Commands

```bash
# Generate fresh dynamic dataset
source .env
python eval/generate_dynamic_dataset.py

# Dry run — list qualifying cases
python eval/unified_eval.py --dataset eval/golden_dataset.json \
  --dynamic-dataset eval/dynamic_golden_dataset.json --dry-run

# Single case
python eval/unified_eval.py --dataset eval/golden_dataset.json \
  --dynamic-dataset eval/dynamic_golden_dataset.json \
  --case base-002 --tier full --description "single case test"

# Full run
python eval/unified_eval.py --dataset eval/golden_dataset.json \
  --dynamic-dataset eval/dynamic_golden_dataset.json \
  --tier full --description "baseline run"
```

All commands use `/home/wsluser/projects/calledit/venv/bin/python`. See `docs/project-updates/common-commands.md` for the complete reference.
