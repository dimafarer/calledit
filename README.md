# CalledIt: Agentic Prediction Verification on Amazon Bedrock AgentCore

> Two AI agents collaborate to understand fuzzy human predictions and convert them into machine-verifiable determinations — then autonomously verify them. The real story is the eval system that measures how well they do it.

## The Problem

People make predictions in natural language: "Lakers win tonight", "it'll rain tomorrow in Seattle", "I bet the sun rises tomorrow." These range from precisely verifiable calendar facts to deeply subjective personal experiences. The challenge isn't just understanding what someone means — it's building a verification plan that an automated agent can actually execute, scoring how likely that plan is to succeed, and then executing it at the right time.

CalledIt is a platform for exploring this problem. Two specialized AI agents — a creation agent and a verification agent — collaborate through a shared DynamoDB prediction bundle. The creation agent converts fuzzy natural language into structured, machine-actionable verification plans. The verification agent runs autonomously at the right time, gathers real evidence, and produces a verdict.

But the more interesting question is: how do you know if the agents are doing a good job? That's where the eval system comes in.

## The Eval System

The eval framework is the centerpiece of this project. It answers three questions:

1. **Did the creation agent understand the user's intent?** (intent_preservation: 0.88 — strong)
2. **Did it build a plan that can actually be executed?** (plan_quality: 0.57 — splits cleanly by prediction type)
3. **Does the creation agent's confidence score predict the verification agent's success?** (calibration_accuracy: 0.50 — the bridge metric)

Three separate eval runners measure each agent independently, then a calibration runner chains them together to measure the handoff:

- `eval/creation_eval.py` — 6 deterministic evaluators + 2 LLM judges (Opus 4.6)
- `eval/verification_eval.py` — 5 deterministic evaluators + 2 Tier 2 evaluators
- `eval/calibration_eval.py` — chains creation → verification, compares predicted vs actual outcomes

All results are stored in DynamoDB (`calledit-v4-eval-reports`) and visualized in a React dashboard at `/eval`. The dashboard is data-driven — adding a new evaluator or agent type requires zero frontend code changes.

### What the Data Tells Us (So Far)

The first baselines revealed clear patterns:

- **Objective predictions** (calendar facts, stock prices, weather) get excellent plans (0.80–0.95 quality). The creation agent builds specific, executable verification steps with real sources.
- **Personal/subjective predictions** (movie enjoyment, dinner taste, Fitbit steps) get poor plans (0.20–0.30). The planner assumes it can contact the user or access private devices — impossible for an automated agent.
- **Browser tool failures** cause most verification inaccuracies (4/7 in the full baseline). The agent's reasoning is sound, but the tool can't reach external sites. This is a tool capability gap, not an agent quality issue.

These signals directly drive the next iteration: teach the verification planner to build self-report plans for personal predictions, and track tool action failures to prioritize which tool to add next.

## Architecture

```
Browser → Cognito JWT → AgentCore WebSocket → Creation Agent → DDB
                                                                ↑
EventBridge (15 min) → Scanner Lambda → Verification Agent ────┘
                                                                
Eval Runners → DDB Reports → React Dashboard (/eval)
```

Two AgentCore Runtime deployments with shared infrastructure:

- **Creation Agent** (`calleditv4/`) — user-facing, async streaming. Browser connects directly with Cognito JWT. 3-turn prompt flow: parse → plan → review. Scores verifiability 0.0–1.0 with per-dimension assessments.
- **Verification Agent** (`calleditv4-verification/`) — batch, sync. Triggered by EventBridge scanner every 15 minutes. Gathers evidence using AgentCore Browser + Code Interpreter, produces structured verdicts.

Both agents use Claude Sonnet 4 via Bedrock, AgentCore built-in tools, and Bedrock Prompt Management for versioned prompts. The prediction bundle in DynamoDB is the contract between them.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React PWA (TypeScript, Vite) via CloudFront + private S3 (OAC) |
| Agent Runtime | Amazon Bedrock AgentCore Runtime (two deployments) |
| Model | Claude Sonnet 4 via Amazon Bedrock |
| Tools | AgentCore Browser + Code Interpreter |
| Auth | Cognito User Pool with JWT authorization |
| API | API Gateway HTTP API with Cognito JWT authorizer + SnapStart |
| Storage | DynamoDB (`calledit-v4` predictions, `calledit-v4-eval-reports` eval data) |
| Prompts | Bedrock Prompt Management with immutable versions |
| Scheduling | EventBridge → Scanner Lambda → Verification Agent |
| Eval | 3 eval runners + golden dataset (45 base + 23 fuzzy) + React dashboard |
| Infrastructure | CloudFormation/SAM (3 stacks, 5 Lambdas with SnapStart) |

## Repository Structure

```
├── calleditv4/                      # Creation agent (AgentCore Runtime)
│   ├── src/main.py                  # Streaming handler + clarification flow
│   ├── src/models.py                # Pydantic models (ParsedClaim, VerificationPlan, PlanReview)
│   └── tests/                       # 148 automated tests
├── calleditv4-verification/         # Verification agent (AgentCore Runtime)
│   ├── src/main.py                  # Sync handler + DDB evidence readback
│   └── tests/                       # 22 automated tests
├── frontend-v4/                     # React PWA
│   ├── src/pages/EvalDashboard/     # Eval dashboard (3 tabs, Recharts)
│   ├── src/components/              # Prediction UI components
│   ├── src/contexts/AuthContext.tsx  # Cognito OAuth2 flow
│   └── server/eval-api.ts           # Vite dev proxy for local DDB access
├── eval/                            # Eval framework
│   ├── creation_eval.py             # Creation agent eval runner
│   ├── verification_eval.py         # Verification agent eval runner
│   ├── calibration_eval.py          # Cross-agent calibration runner
│   ├── report_store.py              # DDB report store (read/write/backfill)
│   ├── golden_dataset.json          # 45 base + 23 fuzzy predictions (schema 4.0)
│   ├── backends/                    # AgentCore backends (JWT + SigV4)
│   ├── evaluators/                  # Deterministic + LLM judge evaluators
│   └── reports/                     # Local JSON backup of eval reports
├── infrastructure/
│   ├── v4-persistent-resources/     # S3 bucket + DDB tables (Retain policy)
│   ├── v4-frontend/                 # CloudFront + HTTP API + 4 Lambdas (SnapStart)
│   ├── verification-scanner/        # EventBridge scanner Lambda (SnapStart)
│   └── prompt-management/           # Bedrock Prompt Management (CloudFormation)
└── docs/project-updates/            # 31 project updates + 136 decisions
```

## The Journey

This project evolved through four architectures, each teaching something the previous one couldn't:

| Phase | Architecture | Key Insight |
|-------|-------------|-------------|
| v1 | Monolith agent | A single agent doing parsing, categorization, planning, and review makes debugging impossible |
| v2 | 4-agent Strands Graph | Multi-agent doesn't automatically mean better — serial graph and single agent scored within 1% on 16 eval runs |
| v3 | MCP-powered Docker Lambda | Real tool execution works but 30s cold starts and MCP subprocess overhead validate the AgentCore migration |
| v4 | AgentCore Runtime | Zero technical debt — JWT auth, WebSocket streaming, built-in tools, SnapStart, DDB-backed eval |

31 project updates and 136 architectural decisions document the full journey in `docs/project-updates/`. The decision log (`docs/project-updates/decision-log.md`) captures every architectural choice with rationale — from "drop backward compatibility on the wire protocol" (Decision 1) to "AutoPublishAlias for SnapStart" (Decision 135).

## What's Next

The platform is built. The eval system is measuring. Now the work shifts to using the eval data to drive improvements:

- **Verification planner self-report plans** — the plan_quality score splits cleanly by prediction type. Personal/subjective predictions need structured self-report plans instead of assuming automated access. Target: plan_quality ≥ 0.75 (currently 0.57).
- **Tool action tracking** — 4/7 verification failures are Browser tool failures. Structured tracking of what the agent attempts, what succeeds, and what fails will identify which tool to add next.
- **Verification mode expansion** — the eval framework is scoped to `immediate` predictions. Adding `at_date`, `before_date`, and `recurring` modes with mode-aware evaluators.
- **Dashboard UX iteration** — multi-run comparison overlays, trend charts, prompt version diffs.

## Running Locally

```bash
# Python dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run all tests (170 total)
python -m pytest calleditv4/tests/ -v          # 148 creation agent tests
python -m pytest calleditv4-verification/tests/ -v  # 22 verification agent tests

# Start creation agent dev server (requires TTY)
cd calleditv4 && agentcore dev

# Start frontend dev server (dashboard at http://localhost:5173/eval)
cd frontend-v4 && npm install && npm run dev

# Run eval (creation agent smoke)
python eval/creation_eval.py --tier smoke --description "test run"

# Run eval (verification agent full)
python eval/verification_eval.py --tier full --description "full baseline"

# Run calibration (chains both agents)
export COGNITO_USERNAME="..." COGNITO_PASSWORD="..."
python eval/calibration_eval.py --tier smoke --description "calibration test"
```

See `docs/project-updates/common-commands.md` for full commands with actual parameter values.

## Deploying

```bash
# 1. Persistent resources (S3 + DDB tables)
aws cloudformation deploy --template-file infrastructure/v4-persistent-resources/template.yaml \
  --stack-name calledit-v4-persistent-resources

# 2. Launch agents (requires TTY)
cd calleditv4 && agentcore launch
cd calleditv4-verification && agentcore launch

# 3. Frontend stack (CloudFront + HTTP API + 4 Lambdas with SnapStart)
cd infrastructure/v4-frontend && sam build && sam deploy ...

# 4. Build and deploy frontend
cd frontend-v4 && npm run build
aws s3 sync dist/ s3://{bucket-name} --delete
aws cloudfront create-invalidation --distribution-id {dist-id} --paths "/*"

# 5. Scanner Lambda (SnapStart)
cd infrastructure/verification-scanner && sam build && sam deploy ...
```

## Disclaimers

This is a demonstration/educational project exploring how AI agents handle imprecise natural language input. Not intended for production use. See [DISCLAIMER.md](DISCLAIMER.md) for full details.

## License

See [LICENSE](LICENSE) for details.
