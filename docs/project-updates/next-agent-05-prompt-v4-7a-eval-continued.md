# Next Agent Prompt — V4-7a Eval Framework (Continued)

**Date:** March 25, 2026
**Previous session:** V4-7a eval framework redesign — research, golden dataset reshape, creation agent eval runner built, first successful baseline (100% Tier 1 pass rate on 12 smoke cases)

---

## Session Goal

Continue building the v4 eval framework. Run the first LLM judge baseline (smoke+judges), then spec and build V4-7a-3 (Verification Agent Eval) and V4-7a-4 (Cross-Agent Calibration + Dashboard).

## CRITICAL — Live Documentation

This project maintains a running narrative across 30+ project updates. Every session must follow the documentation workflow in `.kiro/steering/project-documentation.md`. This is not optional — it's how the project maintains continuity across agent sessions.

**After every milestone (spec completion, successful eval run, deployment, significant decision):**
1. Update `docs/project-updates/30-project-update-v4-7a-eval-framework-redesign.md` with execution results
2. Or create `docs/project-updates/31-project-update-*.md` if the scope warrants a new update
3. Update `docs/project-updates/decision-log.md` with any new decisions (current highest: 127)
4. Update `docs/project-updates/project-summary.md` with new entries
5. Update `docs/project-updates/common-commands.md` with new commands
6. Update `docs/project-updates/backlog.md` if items are addressed or new ones identified

**The user cares deeply about this documentation.** It serves as the project narrative for interviews, portfolio review, and agent continuity. Every decision should be documented with rationale. Every eval run should be captured with results. The progress story (starting simple → expanding with intention based on data) should be visible in the updates.

## Read These Files FIRST

1. `docs/project-updates/30-project-update-v4-7a-eval-framework-redesign.md` — Current session context, decisions 122-127, spec plan, execution results so far
2. `docs/project-updates/v4-agentcore-architecture.md` — MANDATORY architecture reference
3. `.kiro/steering/agentcore-architecture.md` — MANDATORY architecture guardrails
4. `.kiro/steering/project-documentation.md` — MANDATORY documentation workflow
5. `.kiro/specs/creation-agent-eval/tasks.md` — V4-7a-2 task status (most required tasks complete)
6. `.kiro/specs/golden-dataset-v4-reshape/tasks.md` — V4-7a-1 task status (complete)
7. `eval/creation_eval.py` — The eval runner (working, tested)
8. `eval/backends/agentcore_backend.py` — AgentCore HTTPS + JWT backend
9. `eval/evaluators/` — 6 Tier 1 + 2 Tier 2 evaluators
10. `eval/golden_dataset.json` — V4-reshaped dataset (schema 4.0)
11. `eval/reports/creation-eval-20260325-193650.json` — First successful baseline report
12. `calleditv4/src/main.py` — Creation agent (async streaming + WebSocket handlers)
13. `calleditv4-verification/src/main.py` — Verification agent (sync handler)
14. `docs/project-updates/decision-log.md` — 127 decisions
15. `docs/project-updates/common-commands.md` — All current commands including v4 eval

## What's Already Done

### V4-7a-1: Golden Dataset Reshape (COMPLETE)
- `eval/reshape_v4.py` — transforms v3 dataset to v4 format (idempotent)
- `eval/validate_v4.py` — validates structural correctness (all checks pass)
- Dataset reshaped: 45 base + 23 fuzzy, schema 4.0, 12 smoke test cases flagged
- Removed: `expected_per_agent_outputs`, `tool_manifest_config` (v3 debt)
- Added: `expected_verifiability_score_range`, `expected_verification_outcome`, `smoke_test`

### V4-7a-2: Creation Agent Eval (MOSTLY COMPLETE — needs judge baseline)
- `eval/creation_eval.py` — CLI eval runner with tiered evaluators
- `eval/backends/agentcore_backend.py` — HTTPS + JWT auth (not boto3 SigV4)
- 6 Tier 1 deterministic evaluators in `eval/evaluators/` (all passing 100%)
- 2 Tier 2 LLM judge evaluators in `eval/evaluators/` (not yet run)
- Structured run metadata: description, prompt_versions, model_id, agent_runtime_arn, git_commit, run_tier, dataset_version, features dict (LTM/STM/tools)
- First baseline: 12/12 smoke cases, 100% Tier 1 pass rate

### Key Technical Details
- Agent is configured for JWT auth (Decision 121) — boto3 SDK won't work, must use HTTPS with bearer token
- AgentCore returns double-encoded SSE: `data: "{\"type\": ...}"` — parser does two `json.loads()` calls
- Cognito token obtained via `USER_PASSWORD_AUTH` flow (requires `COGNITO_USERNAME` and `COGNITO_PASSWORD` env vars)
- ~45 seconds per prediction (agent runs 3-turn flow with Browser + Code Interpreter)
- Prompt versions are DRAFT (not pinned to numbered versions yet)

## What Needs to Happen Next

### Priority 1: Run smoke+judges Baseline
Run the Tier 2 LLM judges on the smoke test subset to establish the intent preservation and plan quality baseline:
```bash
export COGNITO_USERNAME="<username>"
export COGNITO_PASSWORD="<password>"
/home/wsluser/projects/calledit/venv/bin/python eval/creation_eval.py --tier smoke+judges --description "V4-7a first judge baseline"
```
Document the results in the project update. This is the first data point for the two metrics that matter most (Decision 126).

### Priority 2: Spec V4-7a-3 (Verification Agent Eval)
Separate eval experiment for the verification agent. Key differences from creation agent eval:
- Input: prediction bundle (not raw text) — the verification agent receives a bundle from DDB
- Output: verdict (confirmed/refuted/inconclusive) + confidence + evidence + reasoning
- The verification agent is sync (not streaming) — simpler backend
- Evaluators: schema validity (verdict fields), verdict accuracy (against ground truth), evidence quality (LLM judge)
- The verification agent ARN: `arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_verification_Agent-77DiT7GHdH`
- Only cases with `verification_readiness: immediate` and `expected_verification_outcome` not null can be tested

### Priority 3: Spec V4-7a-4 (Cross-Agent Calibration + Dashboard)
- Cross-agent calibration: run creation agent → feed bundle to verification agent → compare verifiability_score prediction vs actual verdict
- HTML dashboard with 3 tabs: creation agent, verification agent, cross-agent calibration
- Dashboard must support multi-dimensional comparison via metadata (Decision 127 + dashboard comparison UX note in update 30)
- Filter/overlay runs by: model_id, prompt_versions, git_commit, features (LTM/STM), run_tier

### Priority 4: Document Everything
After each milestone, follow the documentation workflow. The narrative should show:
- "We started simple with 6 deterministic evaluators"
- "Tier 1 baseline showed 100% structural correctness"
- "Then we added LLM judges and found [specific insights]"
- "Then we built the verification agent eval and found [specific insights]"
- "Cross-agent calibration revealed [specific insights about score accuracy]"

This progression is the interview story.

## Spec Plan (from Update 30)

| Spec | Name | Confidence | Status |
|------|------|-----------|--------|
| V4-7a-1 | Golden Dataset Reshape | 92% | COMPLETE |
| V4-7a-2 | Creation Agent Eval | 93% | MOSTLY COMPLETE (needs judge baseline) |
| V4-7a-3 | Verification Agent Eval | 95% | NOT STARTED |
| V4-7a-4 | Cross-Agent Calibration + Dashboard | 88% | NOT STARTED |

## Key Decisions for This Session

- Decision 122: Tiered Evaluator Strategy (6 deterministic + 2 LLM judges)
- Decision 123: Separate Eval Experiments per Agent
- Decision 124: Golden Dataset Reshape for v4
- Decision 125: Smoke Test Subset Strategy (12 cases, 4E+5M+3H)
- Decision 126: Creation Agent Priority Metrics (intent → plan quality → score accuracy)
- Decision 127: Structured Eval Run Metadata (description, prompt_versions, model_id, git_commit, features, etc.)

## Import Gotchas (Carried Forward)

- `current_time`: `from strands_tools.current_time import current_time` (function, not module)
- `RequestContext`: `from bedrock_agentcore import RequestContext` (top-level, not `.context`)
- AWS region: NO hardcoded default — boto3 resolves from CLI config
- `agentcore launch` and `agentcore invoke` require TTY — ask user to run and paste output
- TTY errors: stop immediately and ask the user to run the command
- AgentCore JWT auth: can't use boto3 SDK for `invoke_agent_runtime` — must use HTTPS with bearer token
- AgentCore SSE is double-encoded: `data: "{\"type\": ...}"` — parse twice

## Testing

- 148 creation agent tests in `calleditv4/tests/`
- 22 verification agent tests in `calleditv4-verification/tests/`
- 170 total agent tests passing
- Eval framework: `eval/creation_eval.py` with 6 Tier 1 + 2 Tier 2 evaluators
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Eval requires `COGNITO_USERNAME` and `COGNITO_PASSWORD` env vars

## Key Values

```
# Creation Agent
CREATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_Agent-AJiwpKBxRW
CREATION_AGENT_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0

# Verification Agent
VERIFICATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_verification_Agent-77DiT7GHdH

# Cognito (from calledit-backend stack)
COGNITO_USER_POOL_ID=us-west-2_GOEwUjJtv
COGNITO_CLIENT_ID=753gn25jle081ajqabpd4lbin9

# Frontend
CLOUDFRONT_DOMAIN=d2fngmclz6psil.cloudfront.net

# DynamoDB
V4_TABLE_NAME=calledit-v4
```

## Security Requirements

- No AWS credentials in code or env files committed to git
- S3 buckets: private, all public access blocked, AES256 encryption
- Cognito JWT authorizer on all API routes
- No credentials in eval reports or commit messages
