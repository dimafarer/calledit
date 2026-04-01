# CalledIt

> "Lakers win tonight." "It'll rain tomorrow." "Bitcoin hits 100k by Friday."
>
> People make predictions in natural language all the time. CalledIt is a platform that takes those fuzzy human predictions, figures out what you actually meant, builds a plan to verify them, and then autonomously checks whether you were right.

## What This Project Is

CalledIt is a prediction verification platform built on Amazon Bedrock AgentCore. Two AI agents collaborate through a shared DynamoDB prediction bundle: a creation agent that converts natural language into structured, machine-actionable verification plans, and a verification agent that runs autonomously at the right time, gathers real evidence from the web, and produces a verdict.

But the predictions are almost the least interesting part. The real story is what it took to get here.

## The Journey

This project has been rebuilt four times. Each architecture taught us something the previous one couldn't, and every lesson is documented in 37 project updates and 150 architectural decisions.

It started as a monolith — one agent doing everything. Parsing, categorization, planning, review, all in one prompt. Debugging was impossible. You couldn't tell if a bad verification plan was caused by bad parsing or bad planning because everything happened in one black box.

So we split it into a 4-agent Strands Graph. Parser → Categorizer → Verification Builder → Reviewer, each with its own prompt and responsibility. Clean separation of concerns. Except we discovered the "silo problem" — each agent re-interpreted the prediction from scratch instead of building on the previous agent's work. The categorizer would ignore the parser's date extraction. The reviewer would contradict the verification builder's plan.

We built an eval framework to measure this. 6 deterministic evaluators for structural correctness, 2 LLM judges (Opus 4.6) for reasoning quality. A golden dataset with 68 predictions across 18 personas, from "Christmas 2026 falls on a Friday" to "my Fitbit will show 10,000 steps today." We ran 16 eval iterations with isolated single-variable testing — change one prompt, measure the impact, repeat.

The eval data revealed something unexpected: the 4-agent serial graph and a single agent with multi-turn prompts scored within 1% of each other on every metric. The graph's clean architecture didn't translate to better output. The single agent maintained its own context naturally — no silo problem by design. Decision 94: single agent, multi-turn prompts.

Then we migrated to AgentCore. Zero technical debt rebuild. JWT auth for browser WebSocket streaming (no SigV4 presigned URLs, no streaming proxy Lambda). Built-in Browser and Code Interpreter tools. SnapStart on every Lambda. The verification agent runs every 15 minutes via EventBridge, picks up predictions that are due, gathers evidence, and writes verdicts back to DynamoDB.

Along the way we discovered that the Browser tool — which runs a full Chromium instance in a Firecracker microVM — was silently failing in the deployed runtime. "Unavailable due to access restrictions." No stack trace, no detailed error. Code Interpreter worked fine in the same container. We built a minimal PoC agent that tested each layer of the Browser lifecycle independently, and found the root cause in one invocation: the IAM policy used the account ID in the resource ARN, but the system browser `aws.browser.v1` is an AWS-owned resource with `aws` in the ARN instead. A one-line fix after weeks of mystery.

The eval framework caught things we never would have found manually. The creation agent's verifiability score was supposed to predict whether the verification agent could resolve a prediction — but the calibration runner showed it was wrong 50% of the time. High score didn't mean "easy to confirm." It meant "easy to verify" — which includes predictions that are easy to *refute*. A prediction scored 0.85 that gets correctly refuted is a calibration success, not a failure. Fixing that logic pushed calibration accuracy from 0.77 to 0.95.

The golden dataset itself went stale. A prediction about the next full moon had a hardcoded expected date that was correct when we wrote it but wrong two weeks later. We built a dynamic dataset generator — 16 time-anchored predictions regenerated before each eval run, with ground truth computed from deterministic calculations and live web searches.

Every one of these discoveries is documented. Every decision has a rationale. The project updates read like a development journal because that's what they are — written for future us and future agents picking up where we left off.

## Current State

The platform is live at `https://d2fngmclz6psil.cloudfront.net` with an eval dashboard at `/eval`.

**Latest unified baseline (22 cases, April 1, 2026):**

| Metric | Score | What It Measures |
|--------|-------|-----------------|
| Intent Preservation | 0.87 | Did the creation agent understand what the user meant? |
| Plan Quality | 0.81 | Would this verification plan actually work? |
| Verdict Accuracy | 0.94 | Did the verification agent get the right answer? |
| Evidence Quality | 0.73 | How good was the evidence gathered? |
| Calibration Accuracy | 0.95 | Does the confidence score predict verification success? |
| Tier 1 Pass Rate | 1.00 | Structural correctness (schema, fields, ranges) |

The verification agent correctly resolves 94% of predictions with known ground truth. The creation agent preserves user intent 87% of the time. The calibration score — the bridge metric between the two agents — sits at 0.95, meaning the creation agent's verifiability score reliably predicts whether the verification agent will succeed.

## Architecture

```
User → React PWA → Cognito JWT → AgentCore WebSocket → Creation Agent → DynamoDB
                                                                          ↑
EventBridge (15 min) → Scanner Lambda ──→ Verification Agent ─────────────┘

Eval Runners → Creation + Verification + Calibration → DDB Reports → Dashboard
```

Two AgentCore Runtime deployments:

- **Creation Agent** — user-facing, async streaming. 3-turn prompt flow (parse → plan → review). Scores verifiability 0.0–1.0 with per-dimension assessments. Supports multi-round clarification.
- **Verification Agent** — batch, autonomous. Gathers evidence using AgentCore Browser (Chromium in Firecracker microVM) + Code Interpreter (Python sandbox) + Brave Search. Produces structured verdicts with evidence chains.

Both agents use Claude Sonnet 4 via Bedrock and Bedrock Prompt Management for versioned, immutable prompts. The prediction bundle in DynamoDB is the contract between them. Tool selection is configurable via `VERIFICATION_TOOLS` env var — Browser, Brave Search, or both.

## The Eval Framework

This is the part we're most proud of. The eval system answers the question every AI project eventually faces: "is it actually getting better, or does it just feel like it?"

**Three layers:**
- **Strands Evals SDK** (inner loop) — local eval runners invoking deployed agents via HTTPS. 6 deterministic evaluators catch structural regressions instantly. 2 LLM judges (Opus 4.6) measure reasoning quality.
- **AgentCore Evaluations** (bridge) — deployed agent evaluation with span-level trace analysis. Production-like traffic patterns.
- **Bedrock Evaluations** (outer loop) — production quality monitoring at scale.

**Golden dataset:** 54 static predictions (hand-curated, timeless) + 16 dynamic predictions (time-anchored, regenerated before each run). Covers all 4 verification modes: immediate, at_date, before_date, recurring.

**Methodology:** Isolated single-variable testing. Every eval iteration changes exactly one thing — a prompt, a dataset, or a tool configuration — and measures the impact. 37 project updates document every iteration with before/after comparisons.

**The dashboard** at `/eval` visualizes everything: score trends, per-case breakdowns, calibration scatter plots ("Can Our Agents Verify What They Promise?"), phase timing, verdict distributions. It's data-driven — adding a new evaluator requires zero frontend code changes.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React PWA (TypeScript, Vite) via CloudFront + private S3 (OAC) |
| Agent Runtime | Amazon Bedrock AgentCore Runtime (two deployments) |
| Model | Claude Sonnet 4 via Amazon Bedrock |
| Tools | AgentCore Browser + Code Interpreter + Brave Search |
| Auth | Cognito User Pool with JWT (browser) + SigV4 (batch) |
| Storage | DynamoDB (predictions, eval reports, eval reasoning) |
| Prompts | Bedrock Prompt Management with immutable versions |
| Scheduling | EventBridge → Scanner Lambda → Verification Agent |
| Eval | Strands Evals SDK + Opus 4.6 judges + golden dataset (70 predictions) |
| Infrastructure | CloudFormation/SAM (3 stacks, 5 Lambdas with SnapStart) |
| Testing | 174 automated tests + Hypothesis property-based testing |

## Repository Structure

```
calleditv4/                          # Creation agent (AgentCore Runtime)
├── src/main.py                      # Streaming handler, 3-turn flow, clarification
├── src/models.py                    # Pydantic models (ParsedClaim, VerificationPlan, PlanReview)
├── src/prompt_client.py             # Bedrock Prompt Management client
└── tests/                           # 152 automated tests

calleditv4-verification/             # Verification agent (AgentCore Runtime)
├── src/main.py                      # Sync handler, evidence gathering, DDB verdict write
├── src/brave_search.py              # Brave Search API tool
└── tests/                           # 22 automated tests

eval/                                # Eval framework
├── unified_eval.py                  # Single pipeline: creation → verification → evaluate
├── golden_dataset.json              # 54 static predictions (schema 4.0)
├── generate_dynamic_dataset.py      # 16 time-anchored predictions, regenerated per run
├── evaluators/                      # Deterministic + LLM judge evaluators
└── reports/                         # JSON eval reports (also in DDB)

frontend-v4/                         # React PWA
├── src/pages/EvalDashboard/         # Eval dashboard (4 tabs, Recharts)
└── src/components/                  # Prediction UI, auth, navigation

infrastructure/
├── v4-persistent-resources/         # S3 + DDB tables (Retain policy)
├── v4-frontend/                     # CloudFront + HTTP API + 4 Lambdas (SnapStart)
├── verification-scanner/            # EventBridge scanner Lambda
├── prompt-management/               # Bedrock Prompt Management (CloudFormation)
└── agentcore-permissions/           # IAM permissions for AgentCore execution roles

docs/project-updates/                # 37 project updates + 150 decisions
├── project-summary.md               # Condensed current state
├── decision-log.md                  # Every architectural decision with rationale
├── backlog.md                       # 20 tracked items
└── NN-project-update-*.md           # Narrative development journal
```

## Key Decisions

150 decisions are documented in `docs/project-updates/decision-log.md`. A few that shaped the project:

- **Decision 3:** Split large specs into smaller ones. Confidence went from ~65% to ~90%.
- **Decision 44:** Verification criteria quality is the primary eval target, not categorization accuracy.
- **Decision 50:** Isolated single-variable testing as standard practice. Change one thing, measure the impact.
- **Decision 86:** Two agents, not one. Different prompts, memory needs, scaling profiles.
- **Decision 94:** Single agent with multi-turn prompts beats 4-agent serial graph. Validated by 16 eval runs.
- **Decision 148:** High verifiability score means "easy to verify," not "expected to be confirmed." Includes predictions designed to be refuted.
- **Decision 149:** Browser tool IAM fix — system browser uses AWS-owned resource ARN (`aws:browser/*`), not account-scoped.

## What's Next

The platform works. The eval system measures. Now the work shifts to using eval data to drive quality improvements:

- **Multi-model reflection architecture** — Haiku for instant parsing (~2s), Opus for reflective review. The creation agent produces a complete bundle immediately, then Opus reviews the assumptions and asks targeted clarification questions. Two models doing fundamentally different jobs in parallel, not the same job at different quality levels.
- **Quality-gated clarification** — questions are only asked when a wrong assumption would meaningfully change the verification plan. No generic "what timeframe?" when the answer is obvious from context.
- **Verification retry on inconclusive** — when the verification agent has the evidence but fumbles the reasoning, a targeted second pass with an explicit prompt could resolve it.

## Running Locally

```bash
# Dependencies
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Tests (174 total)
python -m pytest calleditv4/tests/ -v              # 152 creation agent tests
python -m pytest calleditv4-verification/tests/ -v  # 22 verification agent tests

# Creation agent dev server (requires TTY)
cd calleditv4 && agentcore dev

# Frontend (dashboard at http://localhost:5173/eval)
cd frontend-v4 && npm install && npm run dev

# Eval — unified pipeline (requires deployed agents + Cognito credentials)
source .env
python eval/generate_dynamic_dataset.py
python eval/unified_eval.py \
  --dataset eval/golden_dataset.json \
  --dynamic-dataset eval/dynamic_golden_dataset.json \
  --tier full --description "baseline run"
```

See `docs/project-updates/common-commands.md` for the full command reference.

## The Documentation

The `docs/project-updates/` directory is the soul of this project. 37 narrative updates written for future developers and future AI agents picking up where we left off. They capture not just what was built, but why — the hypotheses that were wrong, the debugging sessions that revealed unexpected root causes, the eval data that changed our assumptions.

Start with `docs/project-updates/project-summary.md` for the condensed version, or read the updates in order for the full story.

## Disclaimers

This is a demonstration and educational project exploring how AI agents handle imprecise natural language input. Not intended for production use. See [DISCLAIMER.md](DISCLAIMER.md) for full details.

## License

See [LICENSE](LICENSE) for details.
