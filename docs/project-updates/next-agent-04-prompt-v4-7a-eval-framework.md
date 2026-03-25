# Next Agent Prompt — V4-7a Eval Framework Update

**Date:** March 24, 2026
**Previous session:** V4-8a production cutover COMPLETE — both agents deployed to AgentCore, frontend-v4 live, full MVP working

---

## Session Goal

Adapt the eval framework to work with deployed v4 AgentCore agents. Run a baseline eval against the golden dataset. Establish v4 quality metrics so Memory integration (V4-6) can be measured with data.

The v3 eval framework runs against local agents via `agentcore dev` or the v3 Lambda pipeline. V4-7a updates it to invoke the deployed AgentCore agents via WebSocket or HTTP, using the same golden dataset and evaluators.

## IMPORTANT — Pre-Execution Review

Before you start executing, read everything listed below. If you see ANY issues — tactical or strategic — flag them to the user immediately. Don't silently work around problems.

## Read These Files FIRST

1. `docs/project-updates/29-project-update-v4-8a-production-cutover.md` — V4-8a execution results, decisions 115-121
2. `docs/project-updates/project-summary.md` — Current project state
3. `docs/project-updates/v4-agentcore-architecture.md` — MANDATORY architecture reference
4. `.kiro/steering/agentcore-architecture.md` — MANDATORY architecture guardrails
5. `calleditv4/src/main.py` — Creation agent with @app.websocket + @app.entrypoint handlers
6. `calleditv4-verification/src/main.py` — Verification agent (sync handler)
7. `backend/calledit-backend/handlers/strands_make_call/eval_runner.py` — Current v3 eval runner
8. `backend/calledit-backend/handlers/strands_make_call/backends/` — Pluggable backend system
9. `eval/golden_dataset.json` — Golden dataset (45 base + 23 fuzzy)
10. `docs/project-updates/decision-log.md` — 121 decisions
11. `docs/project-updates/common-commands.md` — All current commands

## Key Context

### What V4-8a Delivered
- Both agents deployed to AgentCore Runtime (us-west-2)
- Creation agent: `arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_Agent-AJiwpKBxRW`
- Verification agent: `arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_verification_Agent-77DiT7GHdH`
- JWT auth via Cognito (Decision 121) — browser uses `Sec-WebSocket-Protocol`, CLI uses SigV4
- DynamoDB table: `calledit-v4` with 2 GSIs
- Frontend-v4 at `https://d2fngmclz6psil.cloudfront.net`
- Scanner Lambda deployed as `calledit-v4-scanner` stack

### What the Eval Framework Currently Does (v3)
- `eval_runner.py` with pluggable backends (`serial`, `single`)
- Each backend creates a Strands Agent locally and runs the prediction through it
- 15 evaluators score the output
- Results saved to `eval/reports/` with prompt version manifest
- `--verify` flag runs the Verification Executor on immediate test cases
- `--judge` flag enables LLM-as-judge evaluators
- `--compare` flag compares against previous run

### What V4-7a Needs to Do
1. Create a new eval backend (`agentcore`) that invokes the deployed creation agent via HTTP (`InvokeAgentRuntime`) instead of creating a local agent
2. The backend sends the prediction text and receives the structured bundle back
3. Map the v4 bundle format to the eval framework's expected output format
4. Run baseline eval with all 15 evaluators against the golden dataset
5. Establish v4 quality metrics as the baseline for Memory integration comparison

### Architecture Considerations
- The eval runner should use `InvokeAgentRuntime` (HTTP), not WebSocket — eval doesn't need streaming
- The creation agent's `@app.entrypoint` handler returns the same structured output as the WebSocket handler
- `agentcore invoke` from CLI uses HTTP and works — the eval backend should do the same
- The verification agent can be invoked the same way for `--verify` mode
- Agent execution role already has Bedrock + DDB + Prompt Management permissions

### Three-Layer Eval Architecture (from architecture doc)
- **Layer 1 (this spec):** Strands Evals SDK — local eval runner invoking deployed agents
- **Layer 2 (future):** AgentCore Evaluations — span-level analysis on deployed agents
- **Layer 3 (future):** Bedrock Evaluations — production quality monitoring at scale

## Import Gotchas (Carried Forward)

- `current_time`: `from strands_tools.current_time import current_time` (function, not module)
- `RequestContext`: `from bedrock_agentcore import RequestContext` (top-level, not `.context`)
- `AgentCoreRuntimeClient`: `from bedrock_agentcore.runtime import AgentCoreRuntimeClient`
- AWS region: NO hardcoded default — boto3 resolves from CLI config
- `agentcore launch` and `agentcore invoke` require TTY — ask user to run and paste output
- TTY errors: stop immediately and ask the user to run the command

## Testing

- 148 creation agent tests in `calleditv4/tests/`
- 22 verification agent tests in `calleditv4-verification/tests/`
- 170 total tests passing
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Eval runs from `backend/calledit-backend/handlers/strands_make_call/`

## CRITICAL — Project Documentation

After completing work:
- Create `docs/project-updates/30-project-update-v4-7a-eval-framework.md`
- Update `docs/project-updates/decision-log.md` with any new decisions
- Update `docs/project-updates/project-summary.md` with new entries
- Update `docs/project-updates/common-commands.md` with v4 eval commands

## Security Requirements

- No AWS credentials in code or env files committed to git
- Agent execution role permissions are manual (inline policy on auto-created role)
- S3 buckets: private, all public access blocked, AES256 encryption
- Cognito JWT authorizer on all API routes
