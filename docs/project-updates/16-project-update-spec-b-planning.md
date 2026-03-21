# Project Update 16 — Spec B Planning & A2 Cleanup Completion

**Date:** March 21, 2026
**Context:** Completed Spec A2 cleanup (Prompt Management deploy, SAM env var bump, v3 version bump), then planned and split Spec B (verification execution agent) into three focused specs based on user feedback
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Committed — v3.0.0: A2 cleanup + Spec B planning (B1/B2/B3 split)

### Referenced Kiro Specs
- `.kiro/specs/mcp-tool-integration/` — Spec A2 (COMPLETE — fully deployed)
- `.kiro/specs/verification-execution-agent/` — Spec B1 (requirements complete, design next)
- `.kiro/specs/verification-triggers/` — Spec B2 (requirements complete, blocked on B1)
- `.kiro/specs/verification-eval-integration/` — Spec B3 (requirements complete, blocked on B1)
- `.kiro/specs/mcp-verification-foundation/` — SUPERSEDED (do not implement)

### Prerequisite Reading
- `docs/project-updates/15-project-update-mcp-tool-integration.md` — Spec A1+A2, MCP debugging
- `docs/project-updates/decision-log.md` — Decisions through 77

---

## What Happened This Session

### A2 Cleanup Completed
- Deployed Prompt Management stack: VB v3 + Review v4 with `{{tool_manifest}}` variable (user ran `aws cloudformation deploy`)
- Bumped SAM env vars: `PROMPT_VERSION_VB: "3"`, `PROMPT_VERSION_REVIEW: "4"`
- Redeployed backend with bumped versions (user ran `sam build && sam deploy`)
- Confirmed end-to-end: user made a prediction, logged call visible in DynamoDB
- Version bumped CHANGELOG.md to v3.0.0

### What the Prompt Changes Do
- **VB v3**: Now sees the real MCP tool list via `{{tool_manifest}}`. Instead of generic "check a weather service," it references `brave_web_search` by name with GPS coordinates and specific tool calls.
- **Review v4**: Validates tool choices against what's actually available. Flags if VB references a nonexistent tool. Asks why if a better tool exists but wasn't chosen.
- **Categorizer v2** (unchanged): Already had `{{tool_manifest}}` since v2. Routes predictions based on actual available tools.
- **Parser v1** (unchanged): Gets `tool_manifest` parameter for interface consistency but doesn't inject it into its prompt.

### Spec B Planning — Requirements Phase
Created initial 9-requirement spec for the verification execution agent. User provided three critical pieces of feedback:

1. **Verification timing** (Decision 76): Most `auto_verifiable` predictions can't be verified immediately. "Nice weather Saturday" is auto_verifiable (brave_web_search can check weather) but verifying on Wednesday only checks the forecast. The `verification_date` from the parser is the key signal — immediate verification only when the date has passed.

2. **Eval integration** (Decision 77): Don't build a second eval framework. Fold the VB-Executor comparison into the existing `eval_runner.py` with a `--verify` flag, new evaluators in `evaluators/`, and scores flowing into the existing dashboard.

3. **Spec size** (Decision 75): 9 requirements is too large for reliable execution. Split into B1 (agent), B2 (triggers/storage), B3 (eval integration).

### Spec B Split
- **Spec B1** (`verification-execution-agent`): 5 requirements — Verification Executor agent, data model, `run_verification()` entry point, MCP tool wiring, factory pattern. Self-contained, testable locally.
- **Spec B2** (`verification-triggers`): 3 requirements — DynamoDB result storage, immediate verification trigger (verification_date check), EventBridge scheduled scanner (every 15 minutes).
- **Spec B3** (`verification-eval-integration`): 4 requirements — `--verify` flag on eval runner, 4 new evaluators (ToolAlignment, CriteriaQuality, SourceAccuracy, StepFidelity), golden dataset `verification_readiness` field, dashboard page.

Dependency chain: B2 depends on B1. B3 depends on B1 but NOT B2.

## Decisions Made

- Decision 75: Split Spec B into three focused specs (B1, B2, B3)
- Decision 76: Two-mode verification trigger (immediate vs scheduled based on verification_date)
- Decision 77: Fold verification eval into existing framework, not a second one

## Files Created/Modified

### Created
- `.kiro/specs/verification-execution-agent/requirements.md` — B1 requirements (5 reqs)
- `.kiro/specs/verification-triggers/requirements.md` — B2 requirements (3 reqs)
- `.kiro/specs/verification-triggers/.config.kiro` — B2 config
- `.kiro/specs/verification-eval-integration/requirements.md` — B3 requirements (4 reqs)
- `.kiro/specs/verification-eval-integration/.config.kiro` — B3 config
- `docs/project-updates/16-project-update-spec-b-planning.md` — this file

### Modified
- `backend/calledit-backend/template.yaml` — bumped PROMPT_VERSION_VB to "3", PROMPT_VERSION_REVIEW to "4"
- `CHANGELOG.md` — added v3.0.0 entry
- `docs/project-updates/decision-log.md` — added Decisions 75-77
- `docs/project-updates/backlog.md` — updated item 7 status with B1/B2/B3 split

## What the Next Agent Should Do

### Immediate (Spec B1)
1. Proceed to design phase for Spec B1 (`verification-execution-agent`)
2. Key design decisions: agent prompt content, how `run_verification` builds the user prompt from the verification plan, JSON parsing strategy for Verification_Outcome
3. Reference existing agent factories (`verification_builder_agent.py`, `review_agent.py`) for the factory pattern
4. Reference `mcp_manager.py` for how to get MCP tools

### After B1 Design + Implementation
5. Design and implement Spec B2 (triggers + storage)
6. Design and implement Spec B3 (eval integration)

### Key Files
- `backend/calledit-backend/handlers/strands_make_call/mcp_manager.py` — MCP Manager (reuse for tool wiring)
- `backend/calledit-backend/handlers/strands_make_call/verification_builder_agent.py` — factory pattern reference
- `backend/calledit-backend/handlers/strands_make_call/prediction_graph.py` — graph wiring reference
- `backend/calledit-backend/handlers/strands_make_call/eval_runner.py` — eval runner to extend in B3
- `backend/calledit-backend/handlers/strands_make_call/evaluators/` — evaluator modules to extend in B3
- `eval/dashboard/` — Streamlit dashboard to extend in B3
- `eval/golden_dataset.json` — golden dataset to extend in B3

### Important Notes
- `.kiro/specs/mcp-verification-foundation/` is SUPERSEDED — do not implement from it
- Docker Lambda cold start is ~30s — AgentCore migration is the fix, not provisioned concurrency
- `sam build` needs `--no-cached` or `rm -rf .aws-sam` when Docker image code changes
- TTY errors in terminal: stop immediately and ask user to run the command
- All Python commands must use `/home/wsluser/projects/calledit/venv/bin/python`
