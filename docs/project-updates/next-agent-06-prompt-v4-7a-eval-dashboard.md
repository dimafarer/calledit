# Next Agent Prompt — V4-7a Eval Framework (Dashboard + Completion)

**Date:** March 26, 2026
**Previous session:** V4-7a-3 verification agent eval built and first smoke baseline run. V4-7a-2 creation agent judge baseline complete. Both eval frameworks working end-to-end.

---

## Session Goal

Complete the V4-7a eval framework: finish V4-7a-3 remaining runs (smoke+judges, full tier), then spec and build V4-7a-4 (Cross-Agent Calibration + Dashboard).

## CRITICAL — Read the Project Update FIRST

**Before doing anything else**, read `docs/project-updates/30-project-update-v4-7a-eval-framework-redesign.md` in full. This is the living narrative of the project. It captures the color and context of every conversation, every design decision, every gotcha discovered during implementation. The specs capture what was built; the update captures *why* and *what we learned building it*. Future you needs both.

This is not optional. The previous agent skipped this file initially and had to be corrected. Read it first, understand the journey, then proceed.

## CRITICAL — Live Documentation Workflow

This project maintains a running narrative across 30+ project updates. After every milestone:
1. Update `docs/project-updates/30-project-update-*.md` with execution results and narrative
2. Update `docs/project-updates/decision-log.md` (current highest: 130)
3. Update `docs/project-updates/project-summary.md`
4. Update `docs/project-updates/common-commands.md` with new commands
5. Update `docs/project-updates/backlog.md` if items are addressed or new ones identified

The documentation is the project's interview story. Write it like you're explaining to a future version of yourself what happened and why.

## Read These Files FIRST (in this order)

1. `docs/project-updates/30-project-update-v4-7a-eval-framework-redesign.md` — **THE MOST IMPORTANT FILE.** Full session narrative with decisions 122-130, all execution results, the verification_mode discovery, the auth mismatch story, the DDB evidence readback fix. Read the whole thing.
2. `.kiro/steering/project-documentation.md` — MANDATORY documentation workflow
3. `.kiro/steering/agentcore-architecture.md` — MANDATORY architecture guardrails
4. `docs/project-updates/v4-agentcore-architecture.md` — Architecture reference
5. `.kiro/specs/verification-agent-eval/tasks.md` — V4-7a-3 task status (smoke baseline done, judges + full pending)
6. `eval/verification_eval.py` — Verification eval runner (working, tested)
7. `eval/backends/verification_backend.py` — SigV4 backend with DDB evidence readback
8. `eval/creation_eval.py` — Creation eval runner (working, tested)
9. `eval/backends/agentcore_backend.py` — JWT backend for creation agent
10. `eval/reports/verification-eval-20260326-013758.json` — First verification smoke baseline (100% Tier 1)
11. `eval/reports/creation-eval-20260325-205419.json` — First creation judge baseline (IP=0.88, PQ=0.57)
12. `docs/project-updates/decision-log.md` — 130 decisions
13. `docs/project-updates/common-commands.md` — All commands including both eval runners
14. `docs/project-updates/backlog.md` — Item 0 (verification_mode eval expansion) is the top priority after dashboard

## What's Already Done

### V4-7a-1: Golden Dataset Reshape (COMPLETE)
- Dataset reshaped to v4-native, schema 4.0, 12 smoke test cases, 7 verification-qualifying cases

### V4-7a-2: Creation Agent Eval (COMPLETE)
- `eval/creation_eval.py` — CLI runner with tiered evaluators
- `eval/backends/agentcore_backend.py` — HTTPS + JWT auth
- 6 Tier 1 deterministic evaluators (100% pass rate)
- 2 Tier 2 LLM judges: intent_preservation=0.88, plan_quality=0.57
- Plan quality splits by prediction type: objective 0.80-0.95, personal/subjective 0.20-0.30

### V4-7a-3: Verification Agent Eval (MOSTLY COMPLETE — needs judges + full run)
- `eval/verification_eval.py` — CLI runner with --source golden/ddb, eval table lifecycle
- `eval/backends/verification_backend.py` — SigV4 auth, DDB evidence readback
- 5 Tier 1 evaluators (100% pass rate on smoke)
- 2 Tier 2 evaluators implemented but not yet run (verdict_accuracy + evidence_quality)
- `calleditv4-verification/src/main.py` — table_name payload override added
- `infrastructure/agentcore-permissions/setup_eval_table_permissions.sh` — IAM setup script
- First smoke baseline: 2/2 cases, 100% Tier 1
  - base-002 (Christmas Friday): confirmed, confidence 1.0 ✓
  - base-011 (Python 3.13): inconclusive, confidence 0.3 ✗ (agent quality signal)

## What Needs to Happen Next

### Priority 1: Complete V4-7a-3 Remaining Runs
```bash
# Smoke + judges (adds verdict accuracy + evidence quality)
/home/wsluser/projects/calledit/venv/bin/python eval/verification_eval.py \
  --tier smoke+judges --description "V4-7a-3 first judge baseline"

# Full run (all 7 qualifying cases)
/home/wsluser/projects/calledit/venv/bin/python eval/verification_eval.py \
  --tier full --description "V4-7a-3 full baseline"
```
Document results in update 30. The base-011 inconclusive is worth investigating — check agent logs.

### Priority 2: Spec V4-7a-4 (Cross-Agent Calibration + Dashboard)
This is the capstone spec. Key components:
- **Cross-agent calibration**: run creation agent → feed bundle to verification agent → compare verifiability_score prediction vs actual verdict
- **HTML dashboard with 3 tabs**: creation agent, verification agent, cross-agent calibration
- **Multi-dimensional comparison**: filter/overlay runs by model_id, prompt_versions, git_commit, features (LTM/STM), run_tier (Decision 127)
- Dashboard loads all reports from `eval/reports/`, parses metadata, provides filter controls
- See "Dashboard Comparison UX" note in update 30 for the full vision

### Priority 3: Backlog Items (after dashboard)
- Backlog item 0: Extend eval to at_date/before_date/recurring verification modes
- Backlog item 15: Verification planner self-report plans for personal predictions

## Key Technical Details the Previous Agent Learned the Hard Way

**Auth is different per agent.** The creation agent uses JWT (Decision 121) for browser WebSocket connections. The verification agent uses SigV4 (AgentCore default) because it's a batch agent invoked by the scanner Lambda. Don't try to use JWT for the verification agent — you'll get a 403 "Authorization method mismatch."

**The verification agent handler returns a summary, not the full verdict.** It returns `{prediction_id, verdict, confidence, status}` but NOT `evidence` or `reasoning`. Those are written to DDB by `update_bundle_with_verdict()`. The eval backend reads them back from DDB after invocation. This is the right workaround until STM/LTM is integrated.

**AgentCore execution role needs manual IAM permissions.** The auto-created role doesn't include DynamoDB or Prompt Management access. Run `bash infrastructure/agentcore-permissions/setup_eval_table_permissions.sh` before the first verification eval run. This adds `dynamodb:GetItem/PutItem/UpdateItem/DeleteItem` on `calledit-v4-eval` and `bedrock:GetPrompt` on all prompts.

**Evaluators are scoped to verification_mode=immediate.** All 7 qualifying golden cases are `immediate` predictions with `confirmed` expected outcomes. The evaluators assume this mode. Other modes (at_date, before_date, recurring) need mode-aware evaluator variants — tracked in backlog item 0. The immediate evaluators are not wrong; they're correctly scoped (Decision 130).

**Prompt versions show as DRAFT in creation agent reports** even when runner uses pinned env vars. The report's `prompt_versions` reflects what the deployed agent reports, not what the runner intended. Agent must be re-launched for new versions to take effect (Decision 128).

**The eval table `calledit-v4-eval` is created automatically** by the eval runner if it doesn't exist. Bundles are written before the run and cleaned up after (even on errors). The table persists between runs — only the items are cleaned up.

## Spec Plan Status

| Spec | Name | Status |
|------|------|--------|
| V4-7a-1 | Golden Dataset Reshape | ✅ COMPLETE |
| V4-7a-2 | Creation Agent Eval | ✅ COMPLETE (IP=0.88, PQ=0.57) |
| V4-7a-3 | Verification Agent Eval | 🔄 IN PROGRESS (smoke 100% T1, judges pending) |
| V4-7a-4 | Cross-Agent Calibration + Dashboard | ⬜ NOT STARTED |

## Key Decisions (This Session)

- Decision 128: Eval report prompt_versions reflects agent-reported versions, not runner env vars
- Decision 129: Plan quality 0.57 baseline — verification planner fails on personal/subjective predictions
- Decision 130: Verification eval scoped to immediate mode — other modes additive (backlog item 0)

## Import Gotchas (Carried Forward)

- `current_time`: `from strands_tools.current_time import current_time` (function, not module)
- `RequestContext`: `from bedrock_agentcore import RequestContext` (top-level, not `.context`)
- AWS region: NO hardcoded default — boto3 resolves from CLI config
- `agentcore launch` and `agentcore invoke` require TTY — ask user to run and paste output
- TTY errors: stop immediately and ask the user to run the command
- AgentCore JWT auth (creation agent only): can't use boto3 SDK — must use HTTPS with bearer token
- AgentCore SigV4 auth (verification agent): use botocore SigV4Auth for request signing
- AgentCore SSE is double-encoded (creation agent): `data: "{\"type\": ...}"` — parse twice
- Verification agent response may be double-encoded: check `isinstance(outer, str)` before second parse

## Key Values

```
# Creation Agent
CREATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_Agent-AJiwpKBxRW

# Verification Agent
VERIFICATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_verification_Agent-77DiT7GHdH

# Eval Table
EVAL_TABLE_NAME=calledit-v4-eval

# Cognito (creation agent eval only)
COGNITO_USER_POOL_ID=us-west-2_GOEwUjJtv
COGNITO_CLIENT_ID=753gn25jle081ajqabpd4lbin9

# AgentCore Execution Role (for IAM permissions)
AGENTCORE_ROLE_NAME=AmazonBedrockAgentCoreSDKRuntime-us-west-2-37c792a758
```

## Testing

- 148 creation agent tests in `calleditv4/tests/`
- 22 verification agent tests in `calleditv4-verification/tests/`
- Creation eval: 6 Tier 1 + 2 Tier 2 evaluators, 12 smoke cases
- Verification eval: 5 Tier 1 + 2 Tier 2 evaluators, 7 qualifying cases (2 smoke)
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Creation eval requires `COGNITO_USERNAME` and `COGNITO_PASSWORD` env vars
- Verification eval uses SigV4 (no Cognito credentials needed)
