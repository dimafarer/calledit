# Next Agent Prompt — Browser Tool Debugging

**Date:** March 31, 2026
**Previous session:** Dynamic golden dataset execution, unified eval pipeline build, dashboard integration. See Update 36.

---

## Session Goal

Debug and fix the AgentCore Browser tool failure in the deployed runtime (backlog item 17). The Browser tool works via direct API calls from the local machine but fails silently inside the deployed AgentCore Runtime with "unavailable due to access restrictions."

## CRITICAL — Read the Project Updates FIRST

**Before doing anything else**, read these in order:
1. `docs/project-updates/36-project-update-dynamic-golden-dataset-execution.md` — Previous session context
2. `docs/project-updates/project-summary.md` — Current state summary
3. `docs/project-updates/backlog.md` — Item 17 (Browser debug) has full investigation history
4. `docs/project-updates/decision-log.md` — Decision 144 (Browser IAM), Decision 145 (Brave Search workaround)

## CRITICAL — Use Your Kiro Powers

You have Strands and AgentCore Kiro powers installed. **Activate and use them heavily:**
- `aws-agentcore` power — search docs for Browser tool configuration, runtime permissions, session management
- `strands` power — search docs for AgentCoreBrowser wrapper, tool configuration
- Do web searches if the Kiro powers don't have the answer
- Ask the user to run commands or paste output when you need TTY access

## CRITICAL — Live Documentation Workflow

This project maintains a running narrative across 36+ project updates. After every milestone:
1. Update or create `docs/project-updates/NN-project-update-*.md` with execution results and narrative
2. Update `docs/project-updates/decision-log.md` (current highest: 148)
3. Update `docs/project-updates/project-summary.md`
4. Update `docs/project-updates/backlog.md` if items are addressed or new ones identified

## Approach — Build a Minimal Browser PoC Agent First

**DO NOT start by debugging the full verification agent.** Instead:

1. **Create a minimal PoC agent** (`browser-poc/`) that does ONE thing: start a Browser session, navigate to a URL, return the page title. No LLM, no Brave Search, no Code Interpreter, no DDB. Just Browser.

2. **Test locally first** with `agentcore dev` — this runs on the local machine with your AWS credentials (Admin access). If Browser works locally but not deployed, the issue is in the runtime environment.

3. **Test deployed** with `agentcore launch` — if it fails here, compare the credential chain, env vars, and IAM permissions between local and deployed.

4. **Add logging** — the current verification agent swallows Browser errors silently. The PoC should log every step: session creation, navigation, response, errors with full stack traces.

5. **Iterate** — once the PoC works deployed, wire Browser back into the verification agent.

## What's Already Known

### Browser Works Via Direct API (Local Machine)
- Tested with AgentCore MCP power (Kiro's `aws-agentcore` power)
- Successfully navigated to `fiscaldata.treasury.gov` and got full page content
- Used local AWS credentials (Admin access)

### Browser Fails in Deployed Runtime
- Error: "unavailable due to access restrictions"
- No detailed error in CloudWatch or OTEL logs
- The Strands `AgentCoreBrowser` wrapper fails silently

### What's Been Tried
1. Added full Browser IAM permissions to execution role (Decision 144) — no change
2. Added explicit `region="us-west-2"` to `AgentCoreBrowser()` constructor — no change
3. Relaunched verification agent after both changes — no change
4. Code Interpreter works fine in the same runtime (same role, same container)

### Possible Root Causes to Investigate
1. The Strands `AgentCoreBrowser` wrapper may use a different credential path than Code Interpreter
2. The `playwright` dependency may not be available in the AgentCore Runtime container
3. Browser may require a WebSocket connection the runtime container's network doesn't support
4. There may be a service-level quota or enablement step for Browser in runtime context
5. The Browser tool may need different IAM actions than what we added

### Key Files
- `calleditv4-verification/src/main.py` — Verification agent with Browser tool initialization
- `infrastructure/agentcore-permissions/setup_agentcore_permissions.sh` — IAM permissions script
- `calleditv4-verification/.bedrock_agentcore.yaml` — Agent configuration

### Key Values
```
# Verification Agent
VERIFICATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_verification_Agent-77DiT7GHdH

# AgentCore Execution Role (verification agent)
ROLE_NAME=AmazonBedrockAgentCoreSDKRuntime-us-west-2-37c792a758

# CloudWatch Logs
/aws/bedrock-agentcore/runtimes/calleditv4_verification_Agent-77DiT7GHdH-DEFAULT
```

## What's Already Built and Deployed

### The App
- **Creation Agent** — AgentCore Runtime, WebSocket streaming, 3-turn prompt flow, DDB bundle save
- **Verification Agent** — AgentCore Runtime, Brave Search (working) + Browser (broken) + Code Interpreter (working)
- **Scanner** — EventBridge every 15 min, mode-aware scheduling
- **Frontend** — React PWA at `https://d2fngmclz6psil.cloudfront.net`, Cognito auth
- **Eval Dashboard** — `/eval` route, 4 tabs (Unified Pipeline, Creation, Verification, Calibration)

### The Eval System
- **Unified Eval Pipeline** (`eval/unified_eval.py`) — single pipeline: creation → verification → evaluate → report
- **First unified baseline**: IP=0.89, PQ=0.88, VA=0.89, CA=~0.91 (23 cases)
- **Dynamic Golden Dataset** — 16 templates (9 deterministic + 7 Brave), regenerated before each eval

### Current Baselines (March 31, 2026 — Unified Pipeline)

| Metric | Value | Notes |
|--------|-------|-------|
| Creation T1 | 1.00 | All 6 deterministic evaluators pass |
| Creation IP | 0.89 | Intent preservation |
| Creation PQ | 0.88 | Plan quality |
| Verification T1 | 1.00 | All 5 deterministic evaluators pass |
| Verification VA | 0.89 | 20/22 correct (1 creation error, 2 inconclusive) |
| Calibration CA | ~0.91 | After calibration logic fix (Decision 148) |

## Import Gotchas (Carried Forward)

- `agentcore launch` and `agentcore invoke` require TTY — ask user to run and paste output
- `agentcore launch --env KEY=VALUE` passes env vars to the runtime
- Both AgentCore execution roles need eval table DDB permissions (creation: `5a297cfdfd`, verification: `37c792a758`)
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Eval runs require `COGNITO_USERNAME`, `COGNITO_PASSWORD`, `BRAVE_API_KEY` env vars (in `.env`)
- `source .env` before any eval or agent commands
- The AgentCore Browser MCP power tools (start_browser_session, browser_navigate, etc.) work from the local machine — use them to test Browser API directly

## Testing

- 148 creation agent tests in `calleditv4/tests/`
- 22 verification agent tests in `calleditv4-verification/tests/`
- Unified eval: 23 qualifying cases, ~46 min full run
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
