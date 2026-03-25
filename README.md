# CalledIt: Agentic Prediction Verification on Amazon Bedrock AgentCore

> A prediction verification platform built with Amazon Bedrock AgentCore, demonstrating production-grade AI agent deployment with real-time WebSocket streaming, Cognito JWT authentication, and a three-layer eval architecture.

## What This Project Is

CalledIt is a prediction verification platform. You make a prediction ("Lakers win tonight", "it'll rain tomorrow", "Bitcoin hits $100k by Friday"), and two specialized AI agents collaborate to:

1. **Creation Agent** — parses your natural language into a structured claim, resolves dates with timezone awareness, builds a verification plan (sources, criteria, steps), scores verifiability on a continuous 0.0–1.0 scale, and asks clarification questions to improve the plan
2. **Verification Agent** — runs autonomously at the prediction's verification date, gathers real evidence using AgentCore Browser + Code Interpreter, and produces a structured verdict (confirmed/refuted/inconclusive)

The agents communicate through a shared DynamoDB prediction bundle — the creation agent writes it, the verification agent reads and updates it.

## Live Demo

The v4 frontend is deployed at the CloudFront URL in the stack outputs. Login via Cognito, make a prediction, watch the AI reason in real-time via WebSocket streaming, review the structured output, answer clarification questions, and check your prediction history.

## Architecture (v4)

```
Browser → Cognito JWT → AgentCore WebSocket → Creation Agent → DDB
                                                                ↑
EventBridge (15 min) → Scanner Lambda → Verification Agent ────┘
```

Two AgentCore Runtime deployments with shared infrastructure:

- **Creation Agent** (`calleditv4/`) — user-facing, async streaming via `@app.websocket`. Browser connects directly with Cognito JWT in `Sec-WebSocket-Protocol` header. 3-turn prompt flow: parse → plan → review. Token-by-token streaming to browser.
- **Verification Agent** (`calleditv4-verification/`) — batch, sync via `@app.entrypoint`. Triggered by EventBridge scanner every 15 minutes. Loads prediction bundle from DDB, gathers evidence, produces verdict.

### Key Design Decisions

- **JWT auth for browser WebSocket** (Decision 121) — browser connects directly to AgentCore Runtime, no proxy Lambda needed
- **Two agents, not one** (Decision 86) — different prompts, memory needs, scaling profiles
- **Verifiability strength score** (Decision 103) — continuous 0.0–1.0 replaces 3-category system
- **Single agent, multi-turn prompts** (Decision 94) — validated by 16 eval runs showing equivalent quality to 4-agent serial graph
- **Built-in tools first** (Decision 93) — AgentCore Browser + Code Interpreter, zero external API keys

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React PWA (TypeScript, Vite) via CloudFront + private S3 (OAC) |
| Agent Runtime | Amazon Bedrock AgentCore Runtime (two deployments) |
| Model | Claude Sonnet 4 via Amazon Bedrock |
| Tools | AgentCore Browser (Chromium in Firecracker microVM) + Code Interpreter |
| Auth | Cognito User Pool with JWT authorization |
| API | API Gateway HTTP API with Cognito JWT authorizer |
| Storage | DynamoDB (`calledit-v4` with 2 GSIs) |
| Prompts | Bedrock Prompt Management with immutable versions |
| Scheduling | EventBridge → Scanner Lambda → Verification Agent |
| Infrastructure | CloudFormation/SAM (3 stacks) |
| Eval | Strands Evals SDK + AgentCore Evaluations + Bedrock Evaluations |

## Repository Structure

```
├── calleditv4/                      # Creation agent (AgentCore Runtime)
│   ├── src/main.py                  # @app.entrypoint + @app.websocket handlers
│   ├── src/models.py                # Pydantic models (ParsedClaim, VerificationPlan, PlanReview)
│   ├── src/bundle.py                # DDB bundle operations
│   ├── src/prompt_client.py         # Bedrock Prompt Management client
│   └── tests/                       # 148 automated tests
├── calleditv4-verification/         # Verification agent (AgentCore Runtime)
│   ├── src/main.py                  # @app.entrypoint sync handler
│   └── tests/                       # 22 automated tests
├── frontend-v4/                     # React PWA (v4)
│   ├── src/services/agentCoreWebSocket.ts  # JWT WebSocket service
│   ├── src/components/PredictionInput.tsx   # Streaming + structured display
│   ├── src/components/ListPredictions.tsx   # User's prediction history
│   └── src/contexts/AuthContext.tsx         # Cognito OAuth2 flow
├── infrastructure/
│   ├── v4-persistent-resources/     # S3 bucket + DDB table (create-once)
│   ├── v4-frontend/                 # CloudFront + HTTP API + Lambdas
│   ├── verification-scanner/        # EventBridge scanner Lambda
│   └── prompt-management/           # Bedrock Prompt Management
├── backend/calledit-backend/        # v3 (archived, still running)
├── frontend/                        # v3 frontend (archived)
├── eval/                            # Eval framework
│   ├── golden_dataset.json          # 45 base + 23 fuzzy predictions
│   └── dashboard/                   # 8-page Streamlit dashboard
└── docs/project-updates/            # 29 project updates + 121 decisions
```

## The Eval Framework

15 evaluators across three layers:

- **Layer 1 (Strands Evals SDK):** Local development, prompt iteration, golden dataset with 68 test cases
- **Layer 2 (AgentCore Evaluations):** Deployed agent evaluation with span-level trace analysis
- **Layer 3 (Bedrock Evaluations):** Production quality monitoring, LLM-as-judge at scale

Evaluators: 6 LLM judges (IntentPreservation, CriteriaMethodAlignment, etc.) + 6 deterministic + 2 verification alignment + 1 delta classifier. 8-page Streamlit dashboard. 17+ eval runs with isolated single-variable testing.

## Project Evolution

| Phase | Architecture | Key Insight |
|-------|-------------|-------------|
| v1 | Monolith agent | Single agent doing multiple jobs makes debugging impossible |
| v2 | 4-agent Strands Graph | Multi-agent doesn't automatically mean better — serial graph and single agent scored within 1% |
| v3 | MCP-powered Docker Lambda | Real tool execution works but 30s cold starts validate AgentCore migration |
| v4 | AgentCore Runtime | Zero technical debt — JWT auth, WebSocket streaming, built-in tools, no cold starts |

29 project updates and 121 architectural decisions document the full journey in `docs/project-updates/`.


## Running Locally

```bash
# Install Python dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run creation agent tests (148 tests)
python -m pytest calleditv4/tests/ -v

# Run verification agent tests (22 tests)
python -m pytest calleditv4-verification/tests/ -v

# Start creation agent dev server (requires TTY)
cd calleditv4 && agentcore dev

# Start frontend dev server
cd frontend-v4 && npm install && npm run dev
```

## Deploying

```bash
# 1. Persistent resources (S3 + DDB)
aws cloudformation deploy --template-file infrastructure/v4-persistent-resources/template.yaml \
  --stack-name calledit-v4-persistent-resources

# 2. Launch agents (requires TTY)
cd calleditv4 && agentcore launch
cd calleditv4-verification && agentcore launch

# 3. Frontend stack (CloudFront + HTTP API + Lambdas)
cd infrastructure/v4-frontend && sam build && sam deploy \
  --stack-name calledit-v4-frontend --capabilities CAPABILITY_IAM --resolve-s3 \
  --parameter-overrides CognitoUserPoolId=... CognitoUserPoolClientId=... \
    CreationAgentRuntimeArn=... FrontendBucketName=... FrontendBucketArn=... \
    FrontendBucketDomainName=... DynamoDBTableArn=...

# 4. Build and deploy frontend
cd frontend-v4 && npm run build
aws s3 sync dist/ s3://{bucket-name} --delete
aws cloudfront create-invalidation --distribution-id {dist-id} --paths "/*"

# 5. Scanner Lambda
cd infrastructure/verification-scanner && sam build && sam deploy \
  --stack-name calledit-v4-scanner --capabilities CAPABILITY_IAM --resolve-s3 \
  --parameter-overrides DynamoDBTableName=calledit-v4 VerificationAgentId=...
```

See `docs/project-updates/common-commands.md` for full commands with actual parameter values.

## Disclaimers

This is a demonstration/educational project. Not intended for production use. See [DISCLAIMER.md](DISCLAIMER.md) for full details.

## License

See [LICENSE](LICENSE) for details.
