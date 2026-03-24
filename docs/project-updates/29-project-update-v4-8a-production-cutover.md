# Project Update 29 — V4-8a Production Cutover (In Progress)

**Date:** March 24, 2026
**Context:** Executing the V4-8a spec — deploying agents, building v4 frontend infrastructure, connecting React PWA to AgentCore.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/production-cutover/` — V4-8a spec (requirements, design, tasks)

### Prerequisite Reading
- `docs/project-updates/28-project-update-v4-5-complete-next-steps.md` — Decisions 107-114
- `docs/project-updates/v4-agentcore-architecture.md` — Architecture reference

---

## What Happened This Session

### Decisions Made During Execution

- **Decision 115:** No separate `v4-persistent-resources` directory needed for scanner or prompt management — `infrastructure/verification-scanner/` is already v4-only (v3 scanner is in `backend/`), and `infrastructure/prompt-management/` is shared v3+v4. The persistent resources template (`infrastructure/v4-persistent-resources/template.yaml`) contains only the S3 bucket and DDB table.

- **Decision 116:** Reuse existing Cognito User Pool from `calledit-backend` stack. Creating a new one would mean new user accounts. V4 references it by parameter (User Pool ID + Client ID). At v3 teardown, Cognito resources will be extracted to `infrastructure/cognito/template.yaml` via CloudFormation resource import.

- **Decision 117:** New `frontend-v4/` directory for the React PWA. Copy good parts from v3 `frontend/` (Cognito auth, component structure, styling), rewrite the technical debt (v3 WebSocket proxy, REST API integration). V3 `frontend/` stays untouched until v4 is validated, then gets archived.

- **Decision 118:** `AWS_DEFAULT_REGION` fix for AgentCore Runtime. Both agent entrypoints now set `AWS_DEFAULT_REGION` from `AWS_REGION` env var (or default `us-west-2`) at import time. AgentCore Runtime doesn't inherit AWS CLI config, so boto3 calls without explicit region fail. This was discovered during first `agentcore invoke` — creation agent hit `"You must specify a region."` on DDB access.

### Infrastructure Deployed

#### 1. Persistent Resources Stack (`calledit-v4-persistent-resources`)

Template: `infrastructure/v4-persistent-resources/template.yaml`

Resources created:
- **S3 Bucket:** `calledit-v4-persistent-resources-v4frontendbucket-tjqdqan1gbuy`
  - Private, all public access blocked, AES256 encryption
  - `DeletionPolicy: Retain` (rollback-safe)
- **DynamoDB Table:** `calledit-v4`
  - Key: `PK` (String) + `SK` (String), format `PK=PRED#{id}`, `SK=BUNDLE`
  - GSI `user_id-created_at-index`: partition `user_id`, sort `created_at`
  - GSI `status-verification_date-index`: partition `status`, sort `verification_date`
  - PAY_PER_REQUEST billing
  - `DeletionPolicy: Retain`

Stack outputs:
| Output | Value |
|--------|-------|
| V4FrontendBucketName | `calledit-v4-persistent-resources-v4frontendbucket-tjqdqan1gbuy` |
| V4FrontendBucketArn | `arn:aws:s3:::calledit-v4-persistent-resources-v4frontendbucket-tjqdqan1gbuy` |
| V4FrontendBucketRegionalDomainName | `calledit-v4-persistent-resources-v4frontendbucket-tjqdqan1gbuy.s3.us-west-2.amazonaws.com` |
| V4PredictionsTableName | `calledit-v4` |
| V4PredictionsTableArn | `arn:aws:dynamodb:us-west-2:894249332178:table/calledit-v4` |

#### 2. AgentCore Agent Deployments

Both agents deployed via `agentcore launch` with the region fix applied:

| Agent | ARN | Status |
|-------|-----|--------|
| Creation Agent | `arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_Agent-AJiwpKBxRW` | Deployed |
| Verification Agent | `arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_verification_Agent-77DiT7GHdH` | Deployed |

Validation results:
- Creation agent: `flow_started` event received, then region error (fixed, redeployed, confirmed working)
- Verification agent: Correctly returned `"Missing 'prediction_id' in payload"` when sent a creation payload — expected behavior

#### 3. V4 Frontend Stack (`calledit-v4-frontend`) — DEPLOYED

Template: `infrastructure/v4-frontend/template.yaml` (SAM template)

Stack outputs:
| Output | Value |
|--------|-------|
| CloudFrontDomainName | `d3iu89wz08eik9.cloudfront.net` |
| CloudFrontDistributionId | `E2OOP71HBN61T1` |
| HttpApiUrl | `https://ocvtlajdog.execute-api.us-west-2.amazonaws.com` |

Resources defined:
- **CloudFront OAC** — Origin Access Control (SigV4, always sign, S3 origin type)
- **CloudFront Distribution** — HTTPS redirect, `index.html` default root, 403/404 → `/index.html` for SPA routing
- **S3 Bucket Policy** — `s3:GetObject` for `cloudfront.amazonaws.com` only, conditioned on distribution ARN
- **HTTP API** — API Gateway HTTP API with Cognito JWT authorizer
- **Presigned URL Lambda** — Python 3.12, calls `AgentCoreRuntimeClient.generate_presigned_url()`
- **ListPredictions Lambda** — Python 3.12, queries `calledit-v4` GSI for user's predictions
- **Routes** — `POST /presigned-url` and `GET /predictions`, both JWT-protected
- **CORS** — CloudFront domain + `http://localhost:5173`

### Code Changes

#### Agent Entrypoints — Region Fix
- `calleditv4/src/main.py`: Added `AWS_DEFAULT_REGION` env var setup at import time
- `calleditv4-verification/src/main.py`: Same region fix
- Both agents: Changed `DYNAMODB_TABLE_NAME` default from `calledit-db` to `calledit-v4`
- `calleditv4/tests/test_entrypoint.py`: Updated test assertion for new default table name (14 tests passing)

#### New Lambda Handlers
- `infrastructure/v4-frontend/presigned_url/handler.py`: Extracts `sub` from JWT claims, calls `generate_presigned_url()`, returns `{url, session_id}`
- `infrastructure/v4-frontend/presigned_url/requirements.txt`: `bedrock-agentcore`
- `infrastructure/v4-frontend/list_predictions/handler.py`: Queries `user_id-created_at-index` GSI, returns formatted predictions with `DecimalEncoder`
- `infrastructure/v4-frontend/list_predictions/requirements.txt`: `boto3`

#### .gitignore Update
- Added broader env file patterns: `.env.*`, `*.env`, `frontend-v4/.env*`, `infrastructure/**/.env*`

### Issues Encountered

1. **Region error on first creation agent invoke:** `"You must specify a region."` — boto3 in AgentCore Runtime doesn't inherit AWS CLI config. Fixed by setting `AWS_DEFAULT_REGION` from `AWS_REGION` env var at import time. Required agent redeploy.

2. **cfn-lint false positive on IdentitySource:** Validator flagged `IdentitySource` as needing array type. CloudFormation docs confirm it's `Array of String` — fixed by using YAML list syntax.

3. **Scanner template overwrote frontend stack:** The scanner `sam deploy` accidentally used `--stack-name calledit-v4-frontend` instead of `calledit-v4-scanner`. CloudFormation replaced the entire frontend stack (CloudFront, HTTP API, Lambdas) with the scanner Lambda. Fixed by redeploying scanner under `calledit-v4-scanner` and redeploying frontend under `calledit-v4-frontend`. CloudFront domain changed from `d3iu89wz08eik9.cloudfront.net` to `d2fngmclz6psil.cloudfront.net`. Required Cognito callback URL update and frontend rebuild.

4. **AgentCoreRuntimeClient requires region argument:** The presigned URL Lambda's `AgentCoreRuntimeClient()` constructor requires an explicit region parameter. Fixed by passing `os.environ.get("AWS_REGION", "us-west-2")`.

5. **Wrong IAM permission for presigned URL:** Template used `bedrock:InvokeAgent` — the correct permission for AgentCore Runtime is `bedrock-agentcore:InvokeAgentRuntime` (and `bedrock-agentcore:InvokeAgentRuntimeWithWebSocketStream` for WebSocket).

6. **CRITICAL — WebSocket 424 Failed Dependency (RESOLVED):** The presigned URL generates correctly and the frontend receives it, but the WebSocket connection to AgentCore Runtime fails with HTTP 424. Root cause: the creation agent only has `@app.entrypoint` (HTTP streaming handler) but does NOT have `@app.websocket` handler. AgentCore Runtime requires a separate `@app.websocket` decorator for WebSocket connections — it's a different protocol contract than HTTP streaming. Fixed by adding `@app.websocket` handler (Decision 119).

7. **SigV4 presigned URL rejected from browser (RESOLVED by pivot to JWT):** Even after adding the WebSocket handler, SigV4 presigned URLs fail from browsers — no response headers returned. Works from Python CLI. Root cause: browsers send an `Origin` header that AgentCore rejects on SigV4-signed WebSocket connections. Pivoted to JWT bearer token auth via `Sec-WebSocket-Protocol` header (Decision 121). Browser connects directly with Cognito access token — no presigned URL Lambda needed.

8. **Request header allowlist wildcard rejected:** `X-Amzn-Bedrock-AgentCore-Runtime-Custom-*` wildcard not allowed — regex requires actual alphanumeric characters. Fixed by removing the wildcard, keeping only `Authorization`.

9. **Agent execution role missing permissions:** AgentCore auto-created execution role lacks `bedrock:GetPrompt`, `bedrock:InvokeModel`, and `dynamodb:*` permissions. Fixed by adding inline policy via CLI. This is a manual step — AgentCore doesn't auto-configure these.

### End-to-End Flow Validated

Browser → Cognito login → JWT in `Sec-WebSocket-Protocol` → AgentCore WebSocket → creation agent → 3-turn streaming (parse → plan → review) → events streamed to browser in real-time. Prediction ID generated, agent reasoning visible in UI. DDB save pending verification of permissions.

Known issue: streaming comes in large chunks (per-turn batches) instead of token-by-token. Root cause: WebSocket handler proxies through HTTP handler's generator which batches text events. Fix: refactor WebSocket handler to call `stream_async()` directly.

### What's Next (Remaining Polish)

- **Streaming granularity:** Refactor WebSocket handler to call `stream_async()` directly instead of proxying through HTTP handler — enables token-by-token streaming like v3 Lambda had
- **Frontend display:** Render structured output (parsed claim, verification plan, score indicator) from `turn_complete` and `flow_complete` events, not just raw text
- **Verification agent role:** Add same IAM inline policy to verification agent execution role
- **Presigned URL Lambda cleanup:** Can be removed from the frontend stack (JWT auth replaced it for WebSocket)
- **IAM permission scoping:** Scope wildcard `bedrock-agentcore:InvokeAgentRuntimeWithWebSocketStream` back to specific resource ARN

### Decision 119: Add @app.websocket handler to creation agent

AgentCore Runtime has two separate protocol contracts:
- `@app.entrypoint` — HTTP streaming, used by `agentcore invoke` and `InvokeAgentRuntime` API
- `@app.websocket` — WebSocket bidirectional streaming, used by `generate_presigned_url()` and browser connections

The creation agent currently only has `@app.entrypoint`. The presigned URL flow (Decision 110) requires `@app.websocket`. Both can coexist in the same agent — the agent supports both HTTP and WebSocket simultaneously.

The WebSocket handler contract (from AgentCore docs):
```python
@app.websocket
async def websocket_handler(websocket, context):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        # Process and send responses
        await websocket.send_json({"result": "..."})
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()
```

The fix:
1. Add `@app.websocket` handler to `calleditv4/src/main.py` that reuses the existing creation flow logic
2. The WebSocket handler receives the prediction payload via `websocket.receive_json()`
3. Instead of yielding SSE events, it sends JSON events via `websocket.send_json()`
4. The existing `@app.entrypoint` handler stays for CLI/API compatibility
5. Update IAM permission from `InvokeAgentRuntime` to `InvokeAgentRuntimeWithWebSocketStream`
6. Redeploy agent via `agentcore launch`

### Decision 120: Presigned URL Lambda IAM permission

The correct IAM permission for WebSocket connections is `bedrock-agentcore:InvokeAgentRuntimeWithWebSocketStream`, not `bedrock:InvokeAgent` or `bedrock-agentcore:InvokeAgentRuntime`. Currently using wildcard `*` resource for debugging — will scope back down after WebSocket is working.

### Key Values for Next Steps

```
# Creation Agent
CREATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_Agent-AJiwpKBxRW

# Verification Agent
VERIFICATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_verification_Agent-77DiT7GHdH

# Persistent Resources
V4_BUCKET_NAME=calledit-v4-persistent-resources-v4frontendbucket-tjqdqan1gbuy
V4_BUCKET_DOMAIN=calledit-v4-persistent-resources-v4frontendbucket-tjqdqan1gbuy.s3.us-west-2.amazonaws.com
V4_TABLE_NAME=calledit-v4

# Frontend Stack (current — after scanner overwrite recovery)
CLOUDFRONT_DOMAIN=d2fngmclz6psil.cloudfront.net
CLOUDFRONT_DISTRIBUTION_ID=E1V0EF85NP9DXQ
HTTP_API_URL=https://tlhoo9utzj.execute-api.us-west-2.amazonaws.com

# Cognito (from calledit-backend stack)
COGNITO_USER_POOL_ID=us-west-2_GOEwUjJtv
COGNITO_CLIENT_ID=753gn25jle081ajqabpd4lbin9
COGNITO_DOMAIN_PREFIX=calledit-backend-894249332178-domain

# Scanner Stack
SCANNER_STACK_NAME=calledit-v4-scanner
```

### CloudFormation Stacks Deployed

| Stack Name | Template | Status |
|------------|----------|--------|
| `calledit-v4-persistent-resources` | `infrastructure/v4-persistent-resources/template.yaml` | DEPLOYED |
| `calledit-v4-frontend` | `infrastructure/v4-frontend/template.yaml` | DEPLOYED (needs IAM fix) |
| `calledit-v4-scanner` | `infrastructure/verification-scanner/template.yaml` | DEPLOYED |
