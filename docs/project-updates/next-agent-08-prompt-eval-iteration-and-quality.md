# Next Agent Prompt — Eval Iteration + Verification Quality

**Date:** March 30, 2026
**Previous session:** Verification modes implemented (all 4 types), scanner fixed and live, dark theme deployed, TTY issue resolved, prompt versions pinned. Massive session — see Updates 32 and 33.

---

## Session Goal

The verification pipeline is now live and processing predictions every 15 minutes. But most verdicts are `inconclusive` due to Browser tool limitations. This session should focus on understanding the verification quality data, iterating on prompts to improve it, and running eval baselines to track progress. The user may also want to review the dashboard data and discuss next priorities.

## CRITICAL — Read the Project Updates FIRST

**Before doing anything else**, read these in order:
1. `docs/project-updates/33-project-update-verification-modes.md` — **THE MOST IMPORTANT FILE.** Covers verification modes implementation, scanner fix (3 issues: wrong API, wrong params, missing IAM), TTY fix, prompt pinning, and all decisions 137-142.
2. `docs/project-updates/32-project-update-dark-theme-and-dashboard-ux.md` — Dark theme, dashboard table fix, metadata accordion.
3. `docs/project-updates/project-summary.md` — Current state summary.
4. `docs/project-updates/backlog.md` — Items 15, 16 are top priorities.

## CRITICAL — Live Documentation Workflow

This project maintains a running narrative across 33+ project updates. After every milestone:
1. Update or create `docs/project-updates/NN-project-update-*.md` with execution results and narrative
2. Update `docs/project-updates/decision-log.md` (current highest: 142)
3. Update `docs/project-updates/project-summary.md`
4. Update `docs/project-updates/common-commands.md` with new commands
5. Update `docs/project-updates/backlog.md` if items are addressed or new ones identified

## What's Already Built and Deployed

### The App
- **Creation Agent** — AgentCore Runtime, WebSocket streaming, 3-turn prompt flow (parse → plan → review), verifiability scoring 0.0–1.0, verification_mode classification, multi-round clarification, DDB bundle save
- **Verification Agent** — AgentCore Runtime, sync handler, Browser + Code Interpreter tools, structured verdicts, mode-aware verdict logic, DDB evidence write
- **Scanner** — EventBridge every 15 min, queries GSI for pending predictions, mode-aware scheduling (immediate/at_date/before_date/recurring), SigV4 HTTPS to AgentCore Runtime, recurring interval + max_snapshots
- **Frontend** — React PWA at `https://d2fngmclz6psil.cloudfront.net`, Cognito auth, dark slate theme, underline tab navigation, prediction list with verification status display
- **Infrastructure** — 3 CloudFormation stacks, 5 Lambdas with SnapStart, CloudFront + private S3

### The Eval System
- **Creation Agent Eval** (`eval/creation_eval.py`) — 6 Tier 1 deterministic + 2 Tier 2 LLM judges. Baseline: IP=0.88, PQ=0.57, all T1=1.00. Now includes verification_mode extraction + per-mode aggregates.
- **Verification Agent Eval** (`eval/verification_eval.py`) — 5 Tier 1 + 2 Tier 2 + 3 mode-specific evaluators. Baseline: VA=0.43, EQ=0.46, all T1=1.00. Mode-aware routing + per-mode aggregates.
- **Calibration Runner** (`eval/calibration_eval.py`) — chains creation→verification. Baseline: CA=0.43 (7 cases)
- **DDB Report Store** (`eval/report_store.py`) — `calledit-v4-eval-reports` table
- **React Dashboard** — `/eval` route, 3 tabs, data-driven rendering, collapsible metadata, scatter plot with jitter
- **Golden Dataset** — 54 base + 23 fuzzy predictions, schema 4.0, 12 smoke test cases, 4 verification modes

### Current Baselines

**Creation Agent (12 smoke cases):**
- intent_preservation: 0.88 — strong
- plan_quality: 0.57 — splits by prediction type (objective 0.80-0.95, personal 0.20-0.30)
- All Tier 1: 1.00
- Prompt versions: prediction_parser=2, verification_planner=2, plan_reviewer=3

**Verification Agent (7 full cases):**
- verdict_accuracy: 0.43 — 3/7 correct. 4 failures are Browser tool inability.
- evidence_quality: 0.46
- All Tier 1: 1.00

**Calibration (7 full cases):**
- calibration_accuracy: 0.43
- All predictions scored high (0.85-0.92) but only 3/7 got confirmed verdicts

**Live Scanner Results:**
- 53 predictions processed, all received verdicts
- Most verdicts: inconclusive (Browser tool failures)
- Pipeline working end-to-end: scanner → AgentCore → verification agent → DDB update

## Areas the User May Want to Explore

### 1. Verification Quality — Why So Many Inconclusive?
The V4-7a-3 baseline and live scanner both show the same pattern: the Browser tool can't reach external sites (python.org, treasury.gov, wikipedia.org, sports sites). The agent correctly returns `inconclusive` when it can't gather evidence. This is a tool capability issue, not an agent reasoning issue.

Options:
- **Backlog item 16**: Tool action tracking — structured data on which tools fail and why
- **Prompt iteration**: Teach the verification executor to prefer Code Interpreter for calculations instead of Browser for sites that are known to fail
- **New tools**: Add domain-specific APIs (financial data, sports scores) via AgentCore Gateway

### 2. Verification Planner Self-Report Plans (Backlog Item 15)
Plan quality baseline is 0.57. The 5 personal/subjective cases average ~0.26. Teaching the planner to build self-report plans is the highest-impact prompt change. Target: PQ ≥ 0.75.

### 3. Dashboard Review
The dashboard now has per-mode aggregate breakdowns (`by_mode` in reports). Review the data across all three tabs and discuss what it reveals.

### 4. Run Fresh Baselines
With the new prompt versions (planner v2, reviewer v3, executor v2) and verification_mode classification, run fresh baselines to see how mode classification affects scores.

## Key Technical Details

**Verification Modes:** immediate (check now), at_date (wait for date), before_date (periodic until deadline), recurring (snapshot with interval). Planner classifies, reviewer confirms. Scanner handles mode-aware scheduling.

**Scanner:** EventBridge every 15 min → Lambda queries GSI → mode-aware `should_invoke()` → SigV4 HTTPS to AgentCore Runtime → `handle_verification_result()` (snapshots for recurring, status transitions for others).

**Auth:** Creation agent uses JWT (Cognito), verification agent uses SigV4 (batch agent). Scanner Lambda uses SigV4 with `requests` + `botocore.auth.SigV4Auth`.

**Prompt versions:** prediction_parser=2, verification_planner=2, plan_reviewer=3, verification_executor=2. All pinned in `DEFAULT_PROMPT_VERSIONS` dicts. Never DRAFT.

**TTY Fix:** Amazon Q CLI blocks in `~/.bashrc` wrapped with `if [[ "$TERM_PROGRAM" != "kiro" ]]` guard. Agent commands now return full output with Exit Code 0.

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
Predictions: calledit-v4
Eval Reports: calledit-v4-eval-reports
Eval Bundles (temp): calledit-v4-eval

# Cognito
COGNITO_USER_POOL_ID=us-west-2_GOEwUjJtv
COGNITO_CLIENT_ID=753gn25jle081ajqabpd4lbin9

# CloudFront
Distribution ID: E1V0EF85NP9DXQ
S3 Bucket: calledit-v4-persistent-resources-v4frontendbucket-tjqdqan1gbuy

# Scanner
Scanner Function: calledit-v4-scanner-VerificationScannerFunction-4KPOHquKmzrr
Scanner Stack: calledit-v4-scanner (NOT calledit-verification-scanner — that's v3)
```

## Import Gotchas (Carried Forward)

- `agentcore launch` and `agentcore invoke` require TTY — ask user to run and paste output
- AgentCore JWT auth (creation agent only): can't use boto3 SDK — must use HTTPS with bearer token
- AgentCore SigV4 auth (verification agent + scanner): use botocore SigV4Auth for request signing
- AgentCore SSE is double-encoded (creation agent): `data: "{\"type\": ...}"` — parse twice
- Verification agent handler returns summary only; full verdict read back from DDB
- `AutoPublishAlias: live` for SnapStart — NOT manual Version/Alias resources (Decision 135)
- DDB Decimal↔float conversion needed in all Lambda handlers and report_store.py
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Scanner deploys to `calledit-v4-scanner` stack (NOT `calledit-verification-scanner`)
- Scanner samconfig.toml updated — `sam build && sam deploy` now targets correct stack
- AgentCore execution role needs explicit DDB permissions via `aws iam put-role-policy`
- Frontend dev: `cd frontend-v4 && npm run dev` → `http://localhost:5173/eval`
- Frontend deploy: `npm run build && aws s3 sync dist/ s3://{bucket} --delete && aws cloudfront create-invalidation`

## Testing

- 148 creation agent tests in `calleditv4/tests/`
- 22 verification agent tests in `calleditv4-verification/tests/`
- Creation eval: 6 Tier 1 + 2 Tier 2 evaluators, 12 smoke / 54 full cases
- Verification eval: 5 Tier 1 + 2 Tier 2 + 3 mode-specific evaluators, 2 smoke / 7+ full cases
- Calibration eval: chains both agents, 2 smoke / 7 full cases
- React dashboard: TypeScript strict mode, Vitest configured
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
