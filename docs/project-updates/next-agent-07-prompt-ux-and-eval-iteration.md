# Next Agent Prompt — V4 UX Flow + Eval Dashboard Iteration

**Date:** March 26, 2026
**Previous session:** V4-7a eval framework complete. Calibration runner built and baselined. React eval dashboard deployed to production. SnapStart on all 5 v4 Lambdas. DDB report store resolves months of local-file technical debt.

---

## Session Goal

UX flow updates and data display improvements across both the main prediction app and the eval dashboard. The user may also want to run evals and iterate on prompts based on what the dashboard reveals. Come prepared to discuss options — the user wants to define next steps collaboratively, not follow a predetermined plan.

## CRITICAL — Read the Project Update FIRST

**Before doing anything else**, read `docs/project-updates/31-project-update-v4-7a-eval-completion-and-dashboard-spec.md` in full. This is the living narrative of the current session. It covers three phases: V4-7a-3 completion (verification eval baselines), V4-7a-4 execution (calibration runner + React dashboard + DDB report store), and the production deploy (API Gateway + SnapStart). Read the whole thing — it captures the SnapStart deployment saga, the DDB table import workaround, the browser auth question, and the calibration baseline results.

## CRITICAL — Live Documentation Workflow

This project maintains a running narrative across 31+ project updates. After every milestone:
1. Update or create `docs/project-updates/NN-project-update-*.md` with execution results and narrative
2. Update `docs/project-updates/decision-log.md` (current highest: 136)
3. Update `docs/project-updates/project-summary.md`
4. Update `docs/project-updates/common-commands.md` with new commands
5. Update `docs/project-updates/backlog.md` if items are addressed or new ones identified

## Read These Files FIRST (in this order)

1. `docs/project-updates/31-project-update-v4-7a-eval-completion-and-dashboard-spec.md` — **THE MOST IMPORTANT FILE.** Full session narrative with decisions 131-136, calibration baseline results, SnapStart deployment saga, DDB import workaround.
2. `README.md` — Updated project overview with eval system emphasis and current baselines.
3. `.kiro/steering/project-documentation.md` — MANDATORY documentation workflow
4. `.kiro/steering/agentcore-architecture.md` — MANDATORY architecture guardrails
5. `docs/project-updates/project-summary.md` — Condensed project history and current state
6. `docs/project-updates/backlog.md` — Items 0, 15, 16 are the top priorities

## What's Already Built and Deployed

### The App
- **Creation Agent** — AgentCore Runtime, WebSocket streaming, 3-turn prompt flow (parse → plan → review), verifiability scoring 0.0–1.0, multi-round clarification, DDB bundle save
- **Verification Agent** — AgentCore Runtime, sync handler, Browser + Code Interpreter tools, structured verdicts, DDB evidence write
- **Frontend** — React PWA at `https://d2fngmclz6psil.cloudfront.net`, Cognito auth, streaming prediction display, prediction history list
- **Scanner** — EventBridge every 15 min, queries GSI for pending predictions, invokes verification agent
- **Infrastructure** — 3 CloudFormation stacks, 5 Lambdas with SnapStart, CloudFront + private S3

### The Eval System
- **Creation Agent Eval** (`eval/creation_eval.py`) — 6 Tier 1 deterministic + 2 Tier 2 LLM judges. Baseline: IP=0.88, PQ=0.57, all T1=1.00
- **Verification Agent Eval** (`eval/verification_eval.py`) — 5 Tier 1 + 2 Tier 2. Baseline: VA=0.43, EQ=0.46, all T1=1.00
- **Calibration Runner** (`eval/calibration_eval.py`) — chains creation→verification. Baseline: CA=0.50
- **DDB Report Store** (`eval/report_store.py`) — `calledit-v4-eval-reports` table, 14 reports backfilled
- **React Dashboard** — `/eval` route in frontend-v4, 3 tabs (Creation, Verification, Calibration), data-driven rendering, Recharts scatter plot, expandable case detail
- **Golden Dataset** — 45 base + 23 fuzzy predictions, schema 4.0, 12 smoke test cases, 7 verification-qualifying cases

### Current Baselines (What the Data Says)

**Creation Agent (12 smoke cases):**
- intent_preservation: 0.88 — strong. Parser understands what users mean in 10/12 cases.
- plan_quality: 0.57 — splits by prediction type. Objective 0.80–0.95, personal/subjective 0.20–0.30.
- All Tier 1: 1.00 — structural correctness is solid.

**Verification Agent (7 full cases):**
- verdict_accuracy: 0.43 — 3/7 correct. 4 failures are Browser tool inability, not reasoning errors.
- evidence_quality: 0.46 — vague source names for Code Interpreter results (0.2–0.3), honest failure documentation for Browser failures (0.7–0.8).
- All Tier 1: 1.00.

**Calibration (2 smoke cases):**
- calibration_accuracy: 0.50 — base-002 correct (high score → confirmed), base-011 incorrect (high score → inconclusive due to Browser failure).
- The creation agent scores based on theoretical verifiability, not current tool capability. That's a real calibration gap.

## Areas the User May Want to Explore

### 1. Eval Dashboard UX
The dashboard is functional but minimal. Components exist but aren't all wired:
- `TrendChart.tsx` — built but not integrated into the tab UI (needs multi-run selection)
- `PromptVersionDiff.tsx` — built but not integrated
- Multi-run comparison (Req 9 from V4-7a-4) — filter controls, overlay charts
- Better styling — the dashboard uses inline styles, could benefit from a design pass
- The calibration scatter plot works but only has 2 data points — needs a full calibration run

### 2. Main App UX Flow
- The prediction input flow works but could be more polished
- The prediction list shows basic data — could show verification status, verifiability score indicator
- The clarification flow works but the UI could guide users better
- Mobile responsiveness — it's a PWA but the layout may need work

### 3. Eval Runs and Prompt Iteration
- **Backlog item 15**: Verification planner self-report plans for personal predictions (target: PQ ≥ 0.75)
- **Backlog item 16**: Tool action tracking to identify which tool to add next
- **Backlog item 0**: Verification mode expansion (at_date, before_date, recurring)
- Running a full calibration baseline (7 cases, ~15 min) would give much better calibration data
- The base-010 (full moon) verdict anomaly is worth investigating

## Key Technical Details

**Auth:** Creation agent uses JWT (Cognito), verification agent uses SigV4 (batch agent). Dashboard uses Cognito JWT via API Gateway in production, Vite dev proxy locally.

**Dashboard data flow:** Eval runners write to DDB (`calledit-v4-eval-reports`) + local JSON backup. Dashboard reads from DDB via API Gateway (prod) or Vite proxy (dev). Data-driven rendering — new evaluators/metadata appear automatically.

**SnapStart:** All 5 v4 Lambdas use `AutoPublishAlias: live` + `SnapStart: ApplyOn: PublishedVersions`. Integration URIs use `apigateway:lambda:path` format with `:live` suffix. Decision 135.

**Prompt versions:** prediction_parser v2, verification_planner v1, plan_reviewer v2. Managed via CloudFormation at `infrastructure/prompt-management/template.yaml`. Reports show DRAFT because agents need re-launch for new versions (Decision 128).

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
```

## Import Gotchas (Carried Forward)

- `agentcore launch` and `agentcore invoke` require TTY — ask user to run and paste output
- TTY errors: stop immediately and ask the user to run the command
- AgentCore JWT auth (creation agent only): can't use boto3 SDK — must use HTTPS with bearer token
- AgentCore SigV4 auth (verification agent): use botocore SigV4Auth for request signing
- AgentCore SSE is double-encoded (creation agent): `data: "{\"type\": ...}"` — parse twice
- Verification agent handler returns summary only; full verdict read back from DDB
- `AutoPublishAlias: live` for SnapStart — NOT manual Version/Alias resources (Decision 135)
- DDB Decimal↔float conversion needed in all Lambda handlers and report_store.py
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Frontend dev: `cd frontend-v4 && npm run dev` → `http://localhost:5173/eval`
- Frontend deploy: `npm run build && aws s3 sync dist/ s3://{bucket} --delete && aws cloudfront create-invalidation`

## Testing

- 148 creation agent tests in `calleditv4/tests/`
- 22 verification agent tests in `calleditv4-verification/tests/`
- Creation eval: 6 Tier 1 + 2 Tier 2 evaluators, 12 smoke / 45 full cases
- Verification eval: 5 Tier 1 + 2 Tier 2 evaluators, 2 smoke / 7 full cases
- Calibration eval: chains both agents, 2 smoke / 7 full cases
- React dashboard: TypeScript strict mode, Vitest configured
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
