# Next Agent Prompt — V4-8a Production Cutover

**Date:** March 24, 2026
**Previous session:** V4-5a integration tested, V4-5b implemented + scanner deployed, V4-8a fully specced (requirements + design + tasks)

---

## Session Goal

Execute the V4-8a spec: deploy both AgentCore agents, build new v4 frontend infrastructure, connect the React PWA to the v4 agents via presigned WebSocket URLs.

The spec is complete and approved. All 12 tasks are defined in `.kiro/specs/production-cutover/tasks.md`. Execute them in order.

## IMPORTANT — Pre-Execution Review

Before you start executing, read everything listed below. If you see ANY issues — tactical or strategic — flag them to the user immediately. Don't silently work around problems. Create a punch list in the project update doc (see Update 25 for the pattern).

## Read These Files FIRST

1. `.kiro/specs/production-cutover/requirements.md` — 11 requirements
2. `.kiro/specs/production-cutover/design.md` — full design with architecture diagrams, component interfaces, deployment order
3. `.kiro/specs/production-cutover/tasks.md` — 12 top-level tasks to execute
4. `docs/project-updates/28-project-update-v4-5-complete-next-steps.md` — session context, decisions 107-114
5. `docs/project-updates/v4-agentcore-architecture.md` — MANDATORY architecture reference
6. `.kiro/steering/agentcore-architecture.md` — MANDATORY architecture guardrails
7. `calleditv4/src/main.py` — creation agent entrypoint (async streaming handler)
8. `calleditv4-verification/src/main.py` — verification agent entrypoint (sync handler)
9. `infrastructure/verification-scanner/template.yaml` — scanner Lambda (needs agent ID update)
10. `infrastructure/verification-scanner/scanner.py` — scanner code (needs table name update)
11. `docs/project-updates/decision-log.md` — 114 decisions
12. `docs/project-updates/common-commands.md` — all current commands

## Key Decisions for This Session

- Decision 110: Presigned WebSocket URL — frontend calls Lambda to get presigned WSS URL, connects directly to AgentCore Runtime
- Decision 111: Fresh infrastructure — new CloudFront + S3 + HTTP API, v3 stays untouched
- Decision 112: S3 bucket in persistent resources template (rollback-safe)
- Decision 113: New `calledit-v4` DDB table — clean break from v3 key format, GSIs from day one
- Decision 114: DDB table + S3 bucket in same persistent resources template

## Deployment Order (from design doc)

1. Deploy `calledit-v4-persistent-resources` stack (S3 bucket + DDB table with GSIs)
2. `agentcore launch` both agents with `DYNAMODB_TABLE_NAME=calledit-v4` → capture runtime ARNs
3. Create Presigned URL Lambda + ListPredictions Lambda code
4. Deploy `calledit-v4-frontend` stack with runtime ARNs + Cognito params
5. Update Cognito callback URLs with new CloudFront domain
6. Update frontend React code for v4 (presigned WebSocket, v4 API endpoints)
7. Build and deploy frontend to S3 + invalidate CloudFront cache
8. Update scanner Lambda with `VERIFICATION_AGENT_ID` + `DYNAMODB_TABLE_NAME=calledit-v4`, enable schedule
9. Validate end-to-end

## Infrastructure Layout

```
infrastructure/
  v4-persistent-resources/
    template.yaml              # S3 bucket + DDB table calledit-v4 with 2 GSIs
  v4-frontend/
    template.yaml              # CloudFront + OAC + HTTP API + 2 Lambdas
    presigned_url/
      handler.py               # Cognito JWT → presigned WSS URL
      requirements.txt
    list_predictions/
      handler.py               # DDB GSI query for user's predictions
      requirements.txt
  verification-scanner/        # Existing (V4-5b) — update table name + agent ID
    template.yaml
    scanner.py
```

## DDB Table Design (calledit-v4)

- Primary key: `PK=PRED#{prediction_id}`, `SK=BUNDLE`
- GSI `user_id-created_at-index`: partition `user_id`, sort `created_at` (for ListPredictions)
- GSI `status-verification_date-index`: partition `status`, sort `verification_date` (for scanner)
- PAY_PER_REQUEST billing
- CloudFormation-managed (no setup scripts needed)

## Presigned URL Flow

1. Frontend calls `POST /presigned-url` with Cognito JWT
2. API Gateway validates JWT via Cognito authorizer
3. Lambda calls `AgentCoreRuntimeClient.generate_presigned_url(runtime_arn)`
4. Returns `{url: "wss://...", session_id: "uuid"}` to frontend
5. Frontend opens WebSocket directly to AgentCore Runtime
6. Agent streams SSE events back to frontend

## Import Gotchas (Carried Forward)

- `current_time`: `from strands_tools.current_time import current_time` (function, not module)
- `RequestContext`: `from bedrock_agentcore import RequestContext` (top-level, not `.context`)
- `AgentCoreRuntimeClient`: `from bedrock_agentcore.runtime import AgentCoreRuntimeClient`
- AWS region: NO hardcoded default — boto3 resolves from CLI config
- `agentcore launch` requires TTY — ask user to run and paste output
- TTY errors: stop immediately and ask the user to run the command

## Existing Cognito Info

The Cognito user pool is in the `calledit-backend` stack. Get the IDs:
```bash
aws cloudformation describe-stacks --stack-name calledit-backend --query "Stacks[0].Outputs[?contains(OutputKey, 'UserPool') || contains(OutputKey, 'CognitoUserPool')]" --output table
```

## Testing

- 148 creation agent tests in `calleditv4/tests/`
- 22 verification agent tests in `calleditv4-verification/tests/`
- 170 total tests passing
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Frontend testing is manual (load CloudFront URL, login, make prediction)
- `agentcore launch` and `agentcore invoke` require TTY

## CRITICAL — Project Documentation

After completing work:
- Update `docs/project-updates/28-project-update-v4-5-complete-next-steps.md` with execution results
- Or create `docs/project-updates/29-project-update-v4-8a-production-cutover.md`
- Update `docs/project-updates/decision-log.md` with any new decisions
- Update `docs/project-updates/project-summary.md` with new entries
- Update `docs/project-updates/common-commands.md` with v4 deployment commands

## Security Requirements

- S3 bucket: private, all public access blocked, AES256 encryption
- CloudFront: OAC (not OAI), HTTPS only, redirect HTTP
- No public S3 bucket policies — only CloudFront service principal
- Cognito JWT authorizer on all API routes
- No AWS credentials exposed to the browser
