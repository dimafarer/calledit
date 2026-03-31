# Next Agent Prompt — Dynamic Golden Dataset + Browser Debug

**Date:** March 30, 2026
**Previous session:** Massive session covering DDB cleanup, eval isolation, Brave Search tool, full baselines, and dynamic golden dataset spec. See Updates 34 and 35.

---

## Session Goal

Execute the dynamic golden dataset spec (`.kiro/specs/dynamic-golden-dataset/tasks.md`) to make all four verification modes testable in every eval run. After that, debug the AgentCore Browser tool failure in the deployed runtime (backlog item 17).

## CRITICAL — Read the Project Updates FIRST

**Before doing anything else**, read these in order:
1. `docs/project-updates/35-project-update-dynamic-golden-dataset-spec.md` — Dynamic golden dataset spec context
2. `docs/project-updates/34-project-update-ddb-cleanup-and-eval-isolation.md` — DDB cleanup, eval isolation, Brave Search, full baselines, Browser investigation
3. `docs/project-updates/project-summary.md` — Current state summary
4. `.kiro/specs/dynamic-golden-dataset/requirements.md` — 10 requirements (approved)
5. `.kiro/specs/dynamic-golden-dataset/design.md` — Generator architecture, 16 correctness properties (approved)
6. `.kiro/specs/dynamic-golden-dataset/tasks.md` — 9 tasks ready to execute
7. `docs/project-updates/backlog.md` — Item 17 (Browser debug) is top priority after spec execution

## CRITICAL — Live Documentation Workflow

This project maintains a running narrative across 35+ project updates. After every milestone:
1. Update or create `docs/project-updates/NN-project-update-*.md` with execution results and narrative
2. Update `docs/project-updates/decision-log.md` (current highest: 145)
3. Update `docs/project-updates/project-summary.md`
4. Update `docs/project-updates/common-commands.md` with new commands
5. Update `docs/project-updates/backlog.md` if items are addressed or new ones identified

## What's Already Built and Deployed

### The App
- **Creation Agent** — AgentCore Runtime, WebSocket streaming, 3-turn prompt flow (parse → plan → review), verifiability scoring 0.0–1.0, verification_mode classification, multi-round clarification, DDB bundle save, `table_name` payload override for eval isolation
- **Verification Agent** — AgentCore Runtime, sync handler, **Brave Search** (primary) + Browser (broken) + Code Interpreter tools, structured verdicts, mode-aware verdict logic, DDB evidence write
- **Scanner** — EventBridge every 15 min, queries GSI for pending predictions, mode-aware scheduling, SigV4 HTTPS to AgentCore Runtime
- **Frontend** — React PWA at `https://d2fngmclz6psil.cloudfront.net`, Cognito auth, dark slate theme
- **Infrastructure** — 3 CloudFormation stacks, 5 Lambdas with SnapStart, CloudFront + private S3

### The Eval System
- **Creation Agent Eval** (`eval/creation_eval.py`) — 6 Tier 1 + 2 Tier 2 LLM judges. Baseline: IP=0.79, PQ=0.56, all T1=1.00 (55 cases full run)
- **Verification Agent Eval** (`eval/verification_eval.py`) — 5 Tier 1 + 2 Tier 2 + 3 mode-specific. Baseline: VA=0.71 (0.86 adj), EQ=0.56, all T1=1.00 (7 cases full run)
- **Calibration Runner** (`eval/calibration_eval.py`) — chains creation→verification. Baseline: CA=0.86 (7 cases)
- **DDB Report Store** (`eval/report_store.py`) — `calledit-v4-eval-reports` table
- **React Dashboard** — `/eval` route, 3 tabs, data-driven rendering
- **Golden Dataset** — 55 base + 23 fuzzy predictions, schema 4.0, 12 smoke test cases
- **Eval Isolation** — Creation agent accepts `table_name` override, eval bundles go to `calledit-v4-eval`, cleaned up after

### Current Baselines (March 30, 2026)

| Metric | Value | Notes |
|--------|-------|-------|
| Creation IP | 0.79 (0.86 adj) | 5 judge JSON parse failures |
| Creation PQ | 0.56 (0.58 adj) | 2 judge failures |
| Verification VA | 0.71 (0.86 adj) | base-010 false failure, base-013 tool limitation |
| Verification EQ | 0.56 | |
| Calibration CA | 0.86 | 6/7 correct |

## Priority 1: Execute Dynamic Golden Dataset Spec

The spec is at `.kiro/specs/dynamic-golden-dataset/tasks.md` with 9 tasks:

1. Static dataset migration + dataset merger (`eval/dataset_merger.py`)
2. Checkpoint — merger tests pass
3. Generator core + deterministic templates (`eval/generate_dynamic_dataset.py`)
4. Brave Search templates — **approach experimentally**: try queries, keep what parses cleanly, swap what doesn't. Goal is 3 reliable templates per mode, not every domain.
5. Checkpoint — generator tests pass
6. Prediction quality and diversity
7. Eval runner integration (`--dynamic-dataset` flag on all 3 runners)
8. Validation extension
9. Final checkpoint

Key design decisions already made:
- 3 predictions per mode (12 dynamic total, ~67 merged)
- Two-file strategy: static stays for timeless cases, dynamic regenerated before each eval run
- Ground truth computed at generation time via deterministic calculations + Brave Search
- `--dynamic-dataset` CLI arg is optional, no breaking changes
- Dynamic IDs use `dyn-` prefix (e.g., `dyn-imm-001`, `dyn-atd-001`)

## Priority 2: Debug AgentCore Browser Tool (Backlog Item 17)

The Browser tool works via direct API calls (tested with AgentCore MCP power — successfully navigated to Treasury.gov) but fails inside the deployed AgentCore Runtime with "unavailable due to access restrictions." IAM permissions are correct. The Strands `AgentCoreBrowser` wrapper fails silently in the container.

What's been tried:
- Added full Browser IAM permissions to execution role
- Added explicit `region="us-west-2"` to `AgentCoreBrowser()` constructor
- Relaunched verification agent after both changes

What to investigate:
- Strands `AgentCoreBrowser` wrapper credential path in the runtime container
- `playwright` dependency availability in the AgentCore Runtime container
- WebSocket connectivity from the runtime container
- Service-level quota or enablement for Browser in runtime context

## Priority 3: Verification Planner Self-Report Plans (Backlog Item 15)

Plan quality is 0.56-0.58. Personal/subjective cases average ~0.26. Teaching the planner to build self-report plans is the highest-impact prompt change.

## Key Technical Details

**Verification Tools:** brave_web_search (primary, working), Browser (broken in runtime), Code Interpreter (working), current_time (working)

**Brave Search:** `calleditv4-verification/src/brave_search.py` — `@tool` function, HTTP GET to `api.search.brave.com`, key via `BRAVE_API_KEY` env var. Deployed with `agentcore launch --env BRAVE_API_KEY=...`

**Eval Isolation:** Creation agent accepts `table_name` in payload (Decision 143). Eval runner passes `calledit-v4-eval`. Post-eval cleanup deletes bundles.

**Prompt versions:** prediction_parser=2, verification_planner=2, plan_reviewer=3, verification_executor=3 (updated with Brave priority). All pinned in `DEFAULT_PROMPT_VERSIONS` dicts.

**AgentCore Permissions:** `infrastructure/agentcore-permissions/setup_agentcore_permissions.sh` — consolidated script for all custom IAM policies (DDB, Prompt Management, Browser). Safe to re-run.

## Key Values

```
# Production URLs
Frontend: https://d2fngmclz6psil.cloudfront.net
Dashboard: https://d2fngmclz6psil.cloudfront.net/eval
API: https://tlhoo9utzj.execute-api.us-west-2.amazonaws.com

# Creation Agent
CREATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_Agent-AJiwpKBxRW

# Verification Agent
VERIFICATION_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_verification_Agent-77DiT7GHdH

# DDB Tables
Predictions: calledit-v4 (5 real predictions, clean)
Eval Reports: calledit-v4-eval-reports
Eval Bundles (temp): calledit-v4-eval (cleaned after each run)

# Cognito
COGNITO_USER_POOL_ID=us-west-2_GOEwUjJtv
COGNITO_CLIENT_ID=753gn25jle081ajqabpd4lbin9
```

## Import Gotchas (Carried Forward)

- `agentcore launch` and `agentcore invoke` require TTY — ask user to run and paste output
- AgentCore Browser tool broken in deployed runtime — use Brave Search instead
- AgentCore execution role is auto-created by `agentcore launch` — custom permissions added via `setup_agentcore_permissions.sh`
- `agentcore launch --env KEY=VALUE` passes env vars to the runtime
- Eval isolation: creation agent accepts `table_name` override, eval runner passes `calledit-v4-eval`
- DDB Decimal↔float conversion needed in all Lambda handlers and report_store.py
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Eval runs require `COGNITO_USERNAME` and `COGNITO_PASSWORD` env vars
- LLM judges occasionally return empty responses (JSON parse error) — 7 failures in 55-case run

## Testing

- 148 creation agent tests in `calleditv4/tests/`
- 22 verification agent tests in `calleditv4-verification/tests/`
- Creation eval: 6 Tier 1 + 2 Tier 2 evaluators, 12 smoke / 55 full cases
- Verification eval: 5 Tier 1 + 2 Tier 2 + 3 mode-specific evaluators, 2 smoke / 7 full cases
- Calibration eval: chains both agents, 2 smoke / 7 full cases
- Dynamic dataset tests: `eval/tests/test_dynamic_dataset.py` (to be created)
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
