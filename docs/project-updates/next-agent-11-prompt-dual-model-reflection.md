# Next Agent Prompt — Dual-Model Reflection Architecture

**Date:** April 1, 2026
**Previous session:** Browser tool fix, configurable verification tools, eval validation with Browser. See Update 37.

---

## Session Goal

Build the dual-model reflection architecture for the creation agent (backlog item 20). Haiku for instant parsing, Opus for reflective review. Two models doing fundamentally different jobs in parallel — speed and completeness (Haiku) vs precision and intent preservation (Opus).

## CRITICAL — Read the Project Updates FIRST

**Before doing anything else**, read these in order:
1. `docs/project-updates/37-project-update-browser-tool-debugging.md` — Previous session context
2. `docs/project-updates/project-summary.md` — Current state summary
3. `docs/project-updates/backlog.md` — Item 20 (Dual-Model Reflection) has the full design vision
4. `docs/project-updates/decision-log.md` — Decisions 149-150 (Browser fix, VERIFICATION_TOOLS)

## CRITICAL — Use Your Kiro Powers

You have Strands and AgentCore Kiro powers installed. **Activate and use them:**
- `strands` power — search docs for multi-model agent patterns, per-turn model configuration, streaming
- `aws-agentcore` power — search docs for runtime configuration, model access
- Do web searches if the Kiro powers don't have the answer
- Ask the user to run commands or paste output when you need TTY access

## CRITICAL — Live Documentation Workflow

This project maintains a running narrative across 37+ project updates. After every milestone:
1. Update or create `docs/project-updates/NN-project-update-*.md` with execution results and narrative
2. Update `docs/project-updates/decision-log.md` (current highest: 150)
3. Update `docs/project-updates/project-summary.md`
4. Update `docs/project-updates/backlog.md` if items are addressed or new ones identified

## The Architecture — Read This Carefully

This is NOT "run the same prompts with a better model." This is two models with fundamentally different jobs:

### Pass 1: Haiku (Instant Draft)
- Runs the full 3-turn flow (parse → plan → review) with NO tools, NO external calls
- Uses only: prediction text, HTTP request metadata (user timezone from payload), server UTC time
- Makes enough assumptions to produce a complete, verifiable bundle
- Flags every assumption explicitly (e.g., "Assumed 'tonight' = April 1st Lakers vs Clippers game")
- Streams to the user immediately (~2-3 seconds)
- The user sees a complete bundle with flagged assumptions

### Pass 2: Opus (Reflective Review)
- Receives Haiku's complete output (not the raw prediction text)
- Does NOT redo the work — reviews it
- For each flagged assumption, evaluates: "Would a wrong assumption here change the verification outcome?"
- If the assumption is safe (only one reasonable interpretation), Opus leaves it alone
- If the assumption is risky (ambiguous date, multiple interpretations), Opus asks the user a specific question
- Each user answer triggers Opus to PATCH the affected bundle fields — not re-run the whole thing
- Multiple rounds until Opus is satisfied that intent_preservation, plan_quality, and schema_validity are high, or the user says "good enough"

### Clarification Quality Gate
- Questions are only asked if they reference a specific Haiku assumption
- A wrong assumption must significantly change the verification plan or verifiability score
- No generic questions ("what timeframe?") when the answer is obvious from context
- Questions are specific: "You said 'tonight' — I assumed the April 1st Lakers vs Clippers game. Is that right?"

### Key Principle
Haiku's job: speed and completeness (fill every field, make every assumption).
Opus's job: precision and intent preservation (challenge the assumptions that matter, leave the rest alone).

## What's Already Built

### The Creation Agent (`calleditv4/src/main.py`)
- 3-turn streaming flow: parse → plan → review
- `build_tools()` — configurable tool list via `VERIFICATION_TOOLS` env var
- `build_tool_manifest()` — human-readable tool descriptions for planner prompt
- `build_simple_prompt_system()` — backward-compat system prompt
- Clarification routing: user answers → re-run 3-turn flow with enriched context (this is what needs to change — re-run becomes Opus review + patch)
- Pydantic structured output: `ParsedClaim`, `VerificationPlan`, `PlanReview`
- 152 automated tests

### The Eval Framework
- Unified pipeline: `eval/unified_eval.py` — creation → verification → evaluate → report
- Golden dataset: 54 static + 16 dynamic predictions, 22 qualifying cases
- Current baseline (Browser, April 1): IP=0.87, PQ=0.81, VA=0.94, EQ=0.73, CA=0.95
- LLM judges: Opus 4.6 for intent_preservation and plan_quality
- `model_id` already captured in run metadata — add `model_config` for per-turn tracking

### Prompts (Bedrock Prompt Management)
- `calledit-prediction-parser` (v2) — extract claim, resolve dates
- `calledit-verification-planner` (v2) — build verification plan with `{{tool_manifest}}`
- `calledit-plan-reviewer` (v3) — score verifiability, identify assumptions, ask clarification questions

### Key Values
```
# Creation Agent
CREATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_Agent-AJiwpKBxRW
CREATION_ROLE_NAME=AmazonBedrockAgentCoreSDKRuntime-us-west-2-5a297cfdfd

# Verification Agent
VERIFICATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_verification_Agent-77DiT7GHdH
VERIFICATION_ROLE_NAME=AmazonBedrockAgentCoreSDKRuntime-us-west-2-37c792a758

# Models
SONNET_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
# Haiku and Opus model IDs — check Bedrock console for current availability
```

## Approach — Build This as a Spec

This is a feature, not a bugfix. Use the spec workflow:
1. Requirements — capture the dual-model architecture, assumption flagging, Opus review, quality-gated clarification, eval validation
2. Design — per-turn model configuration, Haiku prompt design (assumption-flagging), Opus review prompt design (assumption evaluation + targeted questions), bundle patching (not re-running), streaming UX (Haiku streams immediately, Opus questions arrive later)
3. Tasks — implement, test, deploy, eval

### Design Considerations

1. **Per-turn model selection**: The Strands Agent constructor takes a `model` parameter. You may need separate Agent instances for Haiku and Opus, or a way to switch models between turns. Check Strands docs for multi-model patterns.

2. **Assumption flagging in Haiku output**: The `ParsedClaim` and `VerificationPlan` Pydantic models need an `assumptions` field — a list of `{field: "verification_date", assumed_value: "2026-04-01", reasoning: "User said 'tonight', only one Lakers game scheduled"}`.

3. **Opus review prompt**: This is a NEW prompt, not a modification of the existing plan-reviewer. It receives the complete Haiku bundle + assumptions and evaluates each assumption's risk. It should be deployed via Bedrock Prompt Management.

4. **Bundle patching**: Opus should be able to update specific fields in the bundle (e.g., change `verification_date` from April 1 to April 3) without re-running the full 3-turn flow. This means the handler needs a "patch" code path alongside the existing "create" and "clarify" paths.

5. **Streaming UX**: The frontend currently shows turn-by-turn streaming events. The new flow would be: Haiku bundle streams immediately → user sees complete bundle → Opus questions arrive as a separate stream → user answers → Opus patches stream back. The frontend needs to handle this two-phase streaming.

6. **Eval comparison**: Run the same 22 qualifying cases with Haiku-only (pass 1 only) and Haiku+Opus (both passes). Compare IP and PQ scores. The eval framework already captures `model_id` — extend with `model_config: {"parse": "haiku", "plan": "haiku", "review": "haiku", "reflection": "opus"}`.

## What's Already Known About Model Availability

- **Haiku**: `us.anthropic.claude-3-5-haiku-20241022-v1:0` — check Bedrock console for access
- **Opus**: `us.anthropic.claude-opus-4-6-v1` — already used as eval judge (Decision 27)
- **Sonnet**: `us.anthropic.claude-sonnet-4-20250514-v1:0` — current production model

Verify model access in Bedrock console before starting implementation. Haiku may need to be enabled.

## Current Baselines (April 1, 2026 — Browser Baseline)

| Metric | Value | Notes |
|--------|-------|-------|
| Creation T1 | 1.00 | All 6 deterministic evaluators pass |
| Creation IP | 0.87 | Intent preservation |
| Creation PQ | 0.81 | Plan quality (dropped from 0.88 after Browser switch) |
| Verification T1 | 1.00 | All 5 deterministic evaluators pass |
| Verification VA | 0.94 | 19/22 correct (2 verification errors, 1 inconclusive) |
| Calibration CA | 0.95 | After calibration logic fix (Decision 148) |

## Import Gotchas (Carried Forward)

- `agentcore launch` and `agentcore invoke` require TTY — ask user to run and paste output
- `agentcore launch --env KEY=VALUE` passes env vars to the runtime
- `agentcore launch --env VERIFICATION_TOOLS=browser --env BRAVE_API_KEY=$BRAVE_API_KEY` for verification agent
- Both AgentCore execution roles have Browser + eval table DDB permissions
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Eval runs require `COGNITO_USERNAME`, `COGNITO_PASSWORD`, `BRAVE_API_KEY` env vars (in `.env`)
- `source .env` before any eval or agent commands
- Decision log is at 150, next decision is 151
- Project update is at 37, next is 38

## Testing

- 152 creation agent tests in `calleditv4/tests/`
- 22 verification agent tests in `calleditv4-verification/tests/`
- 12 browser PoC tests in `browser-poc/tests/`
- Unified eval: 22 qualifying cases, ~75 min full run (with Browser)
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
