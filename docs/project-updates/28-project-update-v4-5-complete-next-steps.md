# Project Update 28 — V4-5 Complete, Deployment & Cutover Planning

**Date:** March 24, 2026
**Context:** V4-5a integration tested, V4-5b implemented. Planning the deployment sequence and frontend cutover.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/verification-agent-core/` — Spec V4-5a (COMPLETE + integration tested)
- `.kiro/specs/verification-triggers/` — Spec V4-5b (COMPLETE)

### Prerequisite Reading
- `docs/project-updates/27-project-update-v4-5-verification-agent-planning.md` — V4-5a/5b execution results
- `docs/project-updates/v4-agentcore-architecture.md` — Architecture reference

---

## What Happened This Session

### V4-5a Integration Testing
- Deployed verification executor prompt (ID: `ZQQNZIP6SK`)
- Test 1 (Lakers prediction): 408s, Browser context overflow, agent recovered with inconclusive verdict, DDB updated. Confirms Gateway + Brave Search needed for Phase 2.
- Test 2 ("test" prediction): 30s clean end-to-end. Verdict: inconclusive, confidence 0.95. Full pipeline validated.
- Pipeline components validated: DDB load, prompt fetch, agent invoke, structured output, DDB update, JSON return, never-raise error handling.

### V4-5b Implementation
- Promoted `verification_date` to top-level DDB attribute for GSI indexing
- Created GSI `status-verification_date-index` on `calledit-db` (ACTIVE, 0 items — sparse, existing items lack top-level field)
- Scanner Lambda at `infrastructure/verification-scanner/` with dual invocation mode
- SAM template, setup script, requirements.txt
- 148 creation agent tests + 22 verification agent tests = 170 total, all passing

### Revised Deployment Sequence (Decisions 107-110)

The user defined a clear 4-phase deployment sequence, reordering the original v4 spec plan:

**Phase 1: Deploy agents with `agentcore launch`**
- Launch both creation and verification agents to AgentCore Runtime
- Enable the verification scanner Lambda (with schedule disabled initially)
- Validate both agents work in deployed mode

**Phase 2: Frontend cutover**
- Connect the React PWA (S3 + CloudFront) directly to the AgentCore agents
- This IS the production cutover — downtime is acceptable
- Tear down v3 API Gateway + Lambda backend

**Phase 3: Eval framework update**
- Adapt the eval framework and dashboard to work with deployed v4 agents
- Run a baseline eval against the golden dataset
- Establish v4 quality metrics

**Phase 4: Memory integration + retest**
- Add AgentCore Memory (STM + LTM) to the creation agent
- Retest with eval framework to measure improvement

---

## Frontend Connectivity Analysis

### Current Architecture (v3)
```
React PWA → CloudFront → API Gateway (WebSocket + REST) → Lambda → Strands Agent
```

### Option A: Keep API Gateway as Proxy
```
React PWA → CloudFront → API Gateway → Lambda (thin proxy) → AgentCore Runtime API
```

Pros:
- Familiar pattern, existing Cognito auth integration works
- WebSocket support for streaming (API Gateway WebSocket API already exists)
- CORS handled by API Gateway
- Rate limiting, throttling, API keys all built in

Cons:
- Extra hop (Lambda proxy adds latency)
- Maintaining a Lambda just to forward requests
- Two scaling systems (API Gateway + AgentCore)
- v3 technical debt carried forward

### Option B: Direct from Frontend to AgentCore Runtime API
```
React PWA → CloudFront → AgentCore Runtime API (via AWS SDK / SigV4)
```

Pros:
- Simplest architecture — no proxy layer
- AgentCore handles scaling, no Lambda to maintain
- Lower latency (one fewer hop)

Cons:
- AgentCore Runtime API requires IAM SigV4 signing — browser can't do this directly
- Need Cognito Identity Pool to get temporary AWS credentials for the browser
- No WebSocket — AgentCore Runtime uses HTTP POST with streaming response
- CORS configuration needed on AgentCore side (if supported)
- The creation agent uses async yield (streaming) — need to verify AgentCore Runtime API supports streaming responses to browser clients

### Option C: Thin Lambda Proxy (Recommended)
```
React PWA → CloudFront → Lambda Function URL (or API Gateway HTTP API) → AgentCore Runtime API
```

Pros:
- Lambda handles SigV4 signing to AgentCore (browser doesn't need AWS credentials)
- Lambda Function URL is simpler than API Gateway (no WebSocket API needed)
- Cognito auth at the Lambda level (validate JWT, extract user_id)
- Can transform between frontend WebSocket events and AgentCore HTTP streaming
- Clean separation: frontend speaks HTTP/WebSocket, Lambda speaks AgentCore API
- Minimal code — just auth validation + request forwarding

Cons:
- Still a proxy hop (but Lambda Function URLs have very low latency)
- Need to handle streaming: Lambda receives AgentCore streaming response, forwards to client

### Recommendation: Option C (Thin Lambda Proxy)

The key blocker for Option B is SigV4 signing — browsers can't sign AWS API requests without temporary credentials, and getting those requires Cognito Identity Pool federation which adds complexity. Option C keeps auth simple (Cognito JWT validation in Lambda) and lets the Lambda handle the AgentCore API interaction.

The proxy Lambda is ~50 lines: validate Cognito JWT → extract user_id → call AgentCore Runtime API with SigV4 → stream response back to client. This replaces the entire v3 Lambda backend (MakeCallStreamFunction, ConnectFunction, DisconnectFunction, etc.).

AgentCore Identity is another option — it provides workload identity tokens and OAuth2 flows — but it's designed for agent-to-service auth (Gateway tools), not frontend-to-agent auth. Cognito remains the right choice for user authentication.

---

## Decisions Made

- **Decision 107:** Deploy agents first, cutover second. Launch both AgentCore runtimes before connecting the frontend. Validates agents work in deployed mode before users hit them.

- **Decision 108:** Frontend cutover is a hard switch, not a gradual migration. Downtime is acceptable. The v3 backend gets torn down after the v4 frontend is connected and validated.

- **Decision 109:** Eval framework update before Memory integration. Establish a v4 baseline with the eval framework so Memory's impact can be measured with data, not intuition.

- **Decision 110:** Presigned WebSocket URL for frontend-to-agent connectivity. AgentCore Runtime natively supports WebSocket via `generate_presigned_url()`. Frontend calls a small Lambda (Cognito JWT → presigned WSS URL), then connects directly to AgentCore — no streaming proxy needed. Replaces the earlier "thin Lambda proxy" plan.

- **Decision 111:** Fresh infrastructure instances for v4. New CloudFront + S3 + API Gateway HTTP API, not in-place updates to the v3 stack. v3 stays running until v4 is validated. Shared resources (DDB, Cognito, Prompt Management) reused.

- **Decision 112:** S3 bucket in separate CloudFormation template. Non-empty buckets can't be rolled back by CloudFormation. Separate template: create once, never touch, reference from main stack.

- **Decision 113:** Separate v4 DynamoDB table `calledit-v4`. Clean break from v3 key format (`PK=USER:{id}` → `PK=PRED#{id}`). CloudFormation-managed with GSIs from day one: `user_id` + `created_at` for listing, `status` + `verification_date` for scanner. No scanning, no v3 baggage.

- **Decision 114:** v4 DDB table in same persistent resources template as S3 bucket. Both are create-once-never-delete resources. Template at `infrastructure/v4-persistent-resources/template.yaml`.

## What the Next Agent Should Do

### Phase 1: Agent Deployment
1. `agentcore launch` for creation agent (`calleditv4/`)
2. `agentcore launch` for verification agent (`calleditv4-verification/`)
3. Deploy scanner Lambda with schedule disabled
4. Validate both agents via `agentcore invoke` (not `--dev`)
5. Enable scanner schedule after verification agent is confirmed working

### Phase 2: Frontend Cutover
1. Build thin Lambda proxy (Cognito JWT → AgentCore Runtime API)
2. Deploy proxy Lambda with Function URL
3. Update React PWA to call proxy Lambda instead of v3 API Gateway
4. Deploy updated frontend to S3 + CloudFront
5. Tear down v3 backend (API Gateway, Lambda functions, Docker image)

### Phase 3: Eval Framework
1. Adapt eval runner to invoke deployed v4 agents (not local `agentcore dev`)
2. Run baseline eval against golden dataset
3. Update dashboard for v4 metrics

### Phase 4: Memory Integration
1. Create AgentCore Memory resource (STM + 3 LTM strategies)
2. Wire into creation agent
3. Optionally wire into verification agent (enrichment)
4. Retest with eval framework, compare against Phase 3 baseline

### Key Files
- `calleditv4/` — Creation agent (ready for `agentcore launch`)
- `calleditv4-verification/` — Verification agent (ready for `agentcore launch`)
- `infrastructure/verification-scanner/` — Scanner Lambda (ready for deploy)
- `infrastructure/prompt-management/template.yaml` — All prompts deployed
- `.kiro/steering/agentcore-architecture.md` — Architecture guardrails
