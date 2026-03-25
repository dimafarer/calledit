# Next Agent Prompt — V4-5a Integration Testing + V4-5b Spec

**Date:** March 23, 2026
**Previous session:** V4-3b + V4-4 executed, V4-5a specced and implemented (code + 22 tests passing)

---

## Session Goal

Two things this session:

1. **Deploy and integration test V4-5a** (Verification Agent). The code is written, 22 pure function tests pass. You need to deploy the prompt, update the prompt ID, and run the agent against a real prediction in DDB.

2. **Spec V4-5b** (Verification Triggers). EventBridge scanner that finds due predictions and invokes the verification agent. This is the scheduling layer.

## IMPORTANT — Pre-Execution Review

Before you start executing, take the time to thoroughly review the codebase and all referenced files. Read everything listed below. If you see ANY issues — tactical or strategic — flag them to the user immediately. Don't silently work around problems. Create a punch list in the project update doc (see Update 25 for the pattern) and track issues as you resolve them.

## Read These Files FIRST

1. `docs/project-updates/27-project-update-v4-5-verification-agent-planning.md` — what just happened (V4-5a complete, decisions 104-106)
2. `docs/project-updates/26-project-update-v4-4-verifiability-scorer.md` — V4-4 context
3. `docs/project-updates/25-project-update-v4-3b-clarification-streaming.md` — V4-3b context (punch list pattern)
4. `docs/project-updates/v4-agentcore-architecture.md` — MANDATORY architecture reference
5. `.kiro/steering/agentcore-architecture.md` — MANDATORY architecture guardrails
6. `.kiro/specs/verification-agent-core/` — V4-5a spec (requirements, design, tasks)
7. `calleditv4-verification/src/main.py` — verification agent entrypoint
8. `calleditv4-verification/src/models.py` — VerificationResult, EvidenceItem
9. `calleditv4-verification/src/bundle_loader.py` — DDB load/update
10. `calleditv4-verification/src/prompt_client.py` — needs prompt ID update after deploy
11. `calleditv4/src/main.py` — creation agent (for reference — creates the bundles the verification agent consumes)
12. `calleditv4/src/bundle.py` — creation agent bundle module (DDB key format reference)
13. `infrastructure/prompt-management/template.yaml` — all prompts including new verification executor
14. `docs/project-updates/common-commands.md` — all current commands
15. `docs/project-updates/decision-log.md` — 106 decisions

## What V4-5a Delivers (Already Implemented)

A separate AgentCore project (`calleditv4-verification/`) that:
1. Receives `prediction_id` in payload
2. Loads prediction bundle from DDB
3. Validates status is "pending"
4. Fetches verification prompt from Prompt Management
5. Invokes Strands Agent with Browser + Code Interpreter + current_time
6. Produces structured verdict (confirmed/refuted/inconclusive) via VerificationResult model
7. Updates DDB with verdict, evidence, timestamp, status change
8. Returns JSON summary — synchronous, no streaming

## V4-5a Integration Testing Steps

### Step 1: Deploy the verification prompt
```bash
cd /home/wsluser/projects/calledit/infrastructure/prompt-management
aws cloudformation deploy --template-file template.yaml --stack-name calledit-prompts
```

### Step 2: Get the prompt ID from stack outputs
```bash
aws cloudformation describe-stacks --stack-name calledit-prompts \
  --query "Stacks[0].Outputs[?contains(OutputKey, 'VerificationExecutor')]" --output table
```

### Step 3: Update PROMPT_IDENTIFIERS in prompt_client.py
Replace `"PLACEHOLDER"` with the actual prompt ID in `calleditv4-verification/src/prompt_client.py`.

### Step 4: Start the verification agent dev server
```bash
cd /home/wsluser/projects/calledit/calleditv4-verification
source .venv/bin/activate  # or use the project's venv
agentcore dev
```

### Step 5: Test with a real prediction
Use a prediction_id from a bundle created by the creation agent (V4-3b integration tests created several). Check DDB for a prediction with `status: "pending"`:
```bash
agentcore invoke --dev '{"prediction_id": "pred-3f52a1b2-97b1-4c59-ac1c-f3cc26886156"}'
```

### Step 6: Verify DDB was updated
Check that the bundle now has `verdict`, `confidence`, `evidence`, `reasoning`, `verified_at`, and `status` changed from `pending` to `verified` or `inconclusive`.

## What V4-5b Should Cover

The verification trigger system:
1. EventBridge rule running every 15 minutes
2. DDB scan/query for predictions where `verification_date <= now` AND `status == "pending"`
3. For each due prediction, invoke the verification agent
4. Needs a DDB GSI on `status` + `verification_date` for efficient queries (backlog item 14)
5. The invocation mechanism: either `AgentCoreRuntimeClient` (for deployed agent) or direct `agentcore invoke` (for dev)

## Key Decisions

- Decision 86: Two separate AgentCore runtimes (creation + verification)
- Decision 96: NO MOCKS. Must prove value + get user approval before any mock.
- Decision 104: Split V4-5 into V4-5a (agent core) and V4-5b (triggers)
- Decision 105: Separate project directory per agent
- Decision 106: Minimal code duplication over shared packages
- 106 decisions total documented in `docs/project-updates/decision-log.md`

## Import Gotchas (Carried Forward)

- `current_time`: `from strands_tools.current_time import current_time` (function, not module)
- `RequestContext`: `from bedrock_agentcore import RequestContext` (top-level, not `.context`)
- AWS region: NO hardcoded default — boto3 resolves from CLI config
- `stream_async` with `structured_output_model`: works — `"data"` events for text, `"result"` event for structured output (Decision 102)
- `_make_event` needs `default=str` for Decimal serialization from DDB bundles
- Verification agent uses sync `agent()` with `structured_output_model`, NOT `stream_async` (it's batch, not streaming)

## Testing

- 148 creation agent tests in `calleditv4/tests/`
- 22 verification agent tests in `calleditv4-verification/tests/`
- 170 total tests passing
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Verification tests need full path: `/home/wsluser/projects/calledit/venv/bin/python -m pytest /home/wsluser/projects/calledit/calleditv4-verification/tests/test_verification.py -v`
- `agentcore dev` uses the project's `.venv/` — dependencies must be in `pyproject.toml`
- TTY errors in terminal: stop immediately and ask the user to run the command

## CRITICAL — Project Documentation

After completing work, update the living documentation:
- Update `docs/project-updates/27-project-update-v4-5-verification-agent-planning.md` with integration test results
- Create `docs/project-updates/28-project-update-v4-5b-verification-triggers.md` if V4-5b is specced/executed
- Update `docs/project-updates/decision-log.md` with any new decisions
- Update `docs/project-updates/project-summary.md` with new entries
- Update `docs/project-updates/backlog.md` — item 14 (DDB GSI) is directly relevant to V4-5b
- Update `docs/project-updates/common-commands.md` with verification agent commands

## AgentCore Steering

The AgentCore steering doc (`.kiro/steering/agentcore-architecture.md`) requires you to FLAG any deviation from AgentCore recommended patterns. Use your Kiro AgentCore power to search docs and validate approaches. The verification agent trigger via EventBridge is Deviation 2 in the steering doc — it's already documented and approved.
