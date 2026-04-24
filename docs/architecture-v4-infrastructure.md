# CalledIt V4 Infrastructure Architecture

**Generated:** March 30, 2026
**Purpose:** Verified mapping of CloudFormation stacks, DDB tables, and data flow

---

## CloudFormation Stacks (CalledIt-related only)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        V4 INFRASTRUCTURE                                │
│                     (infrastructure/ directory)                          │
│                                                                         │
│  ┌─────────────────────────────────────────┐                            │
│  │  calledit-v4-persistent-resources       │                            │
│  │  (infrastructure/v4-persistent-resources)│                           │
│  │                                         │                            │
│  │  • S3 Bucket (frontend assets)          │                            │
│  │  • DDB: calledit-v4          ◄──────────┼── Main predictions table   │
│  │  • DDB: calledit-v4-eval-reports        │   Eval reports table       │
│  │  (Retain on delete)                     │                            │
│  └─────────────────────────────────────────┘                            │
│                                                                         │
│  ┌─────────────────────────────────────────┐                            │
│  │  calledit-v4-frontend                   │                            │
│  │  (infrastructure/v4-frontend)           │                            │
│  │                                         │                            │
│  │  • CloudFront + OAC → private S3        │                            │
│  │  • HTTP API Gateway + Cognito JWT auth  │                            │
│  │  • 4 Lambdas (all SnapStart):           │                            │
│  │    - PresignedUrl (AgentCore WebSocket)  │                            │
│  │    - ListPredictions → calledit-v4 GSI  │                            │
│  │    - ListEvalReports → calledit-v4-eval-reports                      │
│  │    - GetEvalReport → calledit-v4-eval-reports                        │
│  │  • Uses Cognito from calledit-backend   │                            │
│  └─────────────────────────────────────────┘                            │
│                                                                         │
│  ┌─────────────────────────────────────────┐                            │
│  │  calledit-v4-scanner                    │                            │
│  │  (infrastructure/verification-scanner)  │                            │
│  │                                         │                            │
│  │  • EventBridge every 15 min             │                            │
│  │  • Scanner Lambda → calledit-v4 GSI    │                            │
│  │  • SigV4 HTTPS → AgentCore Runtime      │                            │
│  │  (verification agent)                   │                            │
│  └─────────────────────────────────────────┘                            │
│                                                                         │
│  ┌─────────────────────────────────────────┐                            │
│  │  calledit-prompts                       │                            │
│  │  (infrastructure/prompt-management)     │                            │
│  │                                         │                            │
│  │  • Bedrock Prompt Management            │                            │
│  │  • Shared by v3 AND v4 agents           │                            │
│  │  • prediction_parser, verification_     │                            │
│  │    planner, plan_reviewer,              │                            │
│  │    verification_executor                │                            │
│  └─────────────────────────────────────────┘                            │
│                                                                         │
│  ┌─────────────────────────────────────────┐                            │
│  │  infrastructure/agentcore-permissions   │                            │
│  │  (shell script, not a CF stack)         │                            │
│  │                                         │                            │
│  │  • IAM policies for AgentCore exec role │                            │
│  │  • DDB access for verification agent    │                            │
│  └─────────────────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     V3 INFRASTRUCTURE (LEGACY)                          │
│                     (backend/ directory)                                 │
│                                                                         │
│  ┌─────────────────────────────────────────┐                            │
│  │  calledit-backend                       │                            │
│  │  (backend/calledit-backend)             │                            │
│  │                                         │                            │
│  │  SHARED WITH V4:                        │                            │
│  │  • Cognito User Pool ◄──────────────────┼── V4 frontend uses this    │
│  │  • Cognito User Pool Client             │                            │
│  │  • Cognito Domain                       │                            │
│  │                                         │                            │
│  │  V3-ONLY (legacy, still deployed):      │                            │
│  │  • REST API Gateway (CallitAPI)         │                            │
│  │  • WebSocket API (v3 streaming)         │                            │
│  │  • LogCall Lambda → calledit-db         │                            │
│  │  • ListPredictions Lambda → calledit-db │                            │
│  │  • AuthToken Lambda                     │                            │
│  │  • Connect/Disconnect Lambdas           │                            │
│  │  • MakeCallStream (Docker Lambda)       │                            │
│  │  • VerificationScanner (Docker, v3)     │                            │
│  │  • DDB: calledit-eval-reasoning         │                            │
│  └─────────────────────────────────────────┘                            │
│                                                                         │
│  ┌─────────────────────────────────────────┐                            │
│  │  calledit-verification-scanner (DEAD)   │                            │
│  │  (old v3 scanner, separate stack)       │                            │
│  │                                         │                            │
│  │  • Points to calledit-db                │                            │
│  │  • VERIFICATION_AGENT_ID = "" (empty)   │                            │
│  │  • Effectively non-functional           │                            │
│  └─────────────────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────┘
```

## DynamoDB Tables

```
┌──────────────────────────────────────────────────────────────────────┐
│                        DDB TABLES                                    │
│                                                                      │
│  V4 TABLES (active):                                                 │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  calledit-v4  (main predictions table)                        │  │
│  │  PK: PRED#{prediction_id}  SK: BUNDLE                         │  │
│  │  GSIs: user_id-created_at-index, status-verification_date-idx │  │
│  │                                                                │  │
│  │  Current contents (69 items):                                  │  │
│  │    user_id=eval-runner:     50 items (scanner-verified evals)  │  │
│  │    user_id=anonymous:       13 items (test predictions)        │  │
│  │    user_id=f8f16330-...:     5 items (YOUR real predictions)   │  │
│  │    user_id=eval-debug:       1 item  (debug test)             │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  calledit-v4-eval-reports  (eval dashboard data)              │  │
│  │  PK: AGENT#{type}  SK: RUN#{timestamp}                        │  │
│  │  Used by: eval runners (write), dashboard Lambdas (read)      │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  calledit-v4-eval  (temp eval bundles — SEPARATE from main)   │  │
│  │  PK: PRED#{id}  SK: BUNDLE                                    │  │
│  │  Used by: verification_eval.py + calibration_eval.py          │  │
│  │  Bundles written before verification, cleaned up after.       │  │
│  │  Currently: 0 items (cleanup working correctly)               │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  V3 TABLES (legacy):                                                 │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  calledit-db  (v3 predictions — NOW EMPTY)                    │  │
│  │  Was: PK=USER:{cognito_sub}  SK=PREDICTION#{timestamp}        │  │
│  │  All 18 items deleted this session (9 v3 + 9 test leftovers)  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  calledit-eval-reasoning  (v3 eval traces)                    │  │
│  │  PK: eval_run_id  SK: record_key                              │  │
│  │  Created by calledit-backend stack. Legacy.                   │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
                    ┌──────────────┐
                    │   Frontend   │
                    │  (React PWA) │
                    │  CloudFront  │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
     ┌────────────┐ ┌───────────┐ ┌──────────────┐
     │ Presigned  │ │   List    │ │  Eval Report │
     │ URL Lambda │ │Predictions│ │   Lambdas    │
     └─────┬──────┘ │  Lambda   │ └──────┬───────┘
           │        └─────┬─────┘        │
           │              │              │
           ▼              ▼              ▼
     ┌───────────┐  ┌──────────┐  ┌──────────────────┐
     │ AgentCore │  │calledit- │  │calledit-v4-eval- │
     │ Creation  │  │   v4     │  │    reports        │
     │  Agent    │  │  (GSI)   │  │                   │
     │ (WebSocket│  └──────────┘  └──────────────────┘
     │ streaming)│        ▲
     └─────┬─────┘        │
           │              │
           ▼              │
     ┌──────────┐         │
     │calledit- │─────────┘
     │   v4     │  (write bundle)
     └──────────┘
           ▲
           │ (read bundle, write verdict)
     ┌─────┴─────┐
     │ AgentCore │
     │Verification│
     │  Agent     │
     └─────▲─────┘
           │ (SigV4 HTTPS)
     ┌─────┴─────┐
     │  Scanner  │◄── EventBridge (15 min)
     │  Lambda   │
     └───────────┘
           │
           ▼
     ┌──────────┐
     │calledit- │  (query GSI for pending)
     │   v4     │
     └──────────┘


     EVAL FLOW (separate from production):

     ┌──────────────┐
     │  eval runner  │  (local Python scripts)
     │  (creation/   │
     │  verification/│
     │  calibration) │
     └──────┬───────┘
            │
            ├──► AgentCore Creation Agent (HTTPS + JWT)
            │         │
            │         ▼
            │    calledit-v4  (production bundles — creation eval)
            │
            ├──► calledit-v4-eval  (temp bundles — verification/calibration eval)
            │         │
            │         ▼
            │    AgentCore Verification Agent (SigV4)
            │         │
            │         ▼
            │    calledit-v4-eval  (verdict written back, then cleaned up)
            │
            └──► calledit-v4-eval-reports  (final eval report stored)
```

## Key Observations

1. **calledit-v4** is the main production table. The 50 `eval-runner` and 13 `anonymous`
   items are from the scanner processing eval-created bundles that were written to the
   main table (not the eval table). This is a data hygiene issue — see note below.

2. **calledit-v4-eval** is the correct separate eval table. Verification and calibration
   eval runners write temp bundles here, invoke the agent with `table_name` override,
   then clean up. Currently 0 items (working correctly).

3. **Creation eval** writes bundles to **calledit-v4** (the main table) because the
   creation agent's handler always writes to its configured table. This is why there
   are 50 `eval-runner` items in the main table — they were created by eval runs and
   then the scanner picked them up and verified them.

4. **calledit-db** is now empty. Was the v3 table with `USER:{cognito_sub}` PK format.
   The v4 frontend's ListPredictions Lambda queries `calledit-v4` using the
   `user_id-created_at-index` GSI, which is why you only see 5 predictions (your real
   Cognito sub `f8f16330-...`).

5. **Cognito** lives in the `calledit-backend` (v3) stack. The v4 frontend stack takes
   `CognitoUserPoolId` and `CognitoUserPoolClientId` as parameters. Eventually this
   should migrate to v4 infrastructure, but not now.

6. **calledit-verification-scanner** (old v3 stack) is still deployed but dead —
   `VERIFICATION_AGENT_ID=""` and points to `calledit-db`. Should be deleted eventually.

## Data Hygiene Issue: eval-runner items in calledit-v4

The 50 `eval-runner` + 13 `anonymous` + 1 `eval-debug` items in `calledit-v4` are
eval/test artifacts that leaked into the production table. The creation eval runner
invokes the real AgentCore creation agent, which writes to `calledit-v4` (its configured
table). The scanner then picked these up and verified them.

These items don't affect your 5 real predictions (the ListPredictions Lambda filters by
`user_id` via GSI), but they do consume scanner invocations and clutter the table.

**Options:**
- Delete the 64 non-real items (user_id != f8f16330-...)
- Add a `source` field to eval-created bundles so the scanner can skip them
- Both


---

## Planned: AgentCore CDK Migration (Spec: agentcore-cdk-migration)

**Date:** April 24, 2026
**Status:** Specced (requirements + design + tasks complete), not yet executed

### Current Deployment (Deprecated)

Both AgentCore agents are deployed via the deprecated `.bedrock_agentcore.yaml` Python toolkit:
- `calleditv4/.bedrock_agentcore.yaml` → Creation Agent
- `calleditv4-verification/.bedrock_agentcore.yaml` → Verification Agent
- `infrastructure/agentcore-permissions/setup_agentcore_permissions.sh` → Manual IAM script

**Problem:** Environment variables are not declaratively configured. The `BRAVE_API_KEY` was missing from the deployed verification agent (Decision 157), causing all verifications to silently fail. The `--env KEY=VALUE` flag must be manually passed on every `agentcore deploy` command.

### Target Deployment (CDK + agentcore.json)

```
calleditv4/
├── agentcore.json          ← NEW: declarative config (replaces .bedrock_agentcore.yaml)
├── deploy.sh               ← NEW: simple deploy wrapper
└── src/main.py             ← UNCHANGED

calleditv4-verification/
├── agentcore.json          ← NEW: declarative config with env var declarations
├── deploy.sh               ← NEW: validates BRAVE_API_KEY before deploy
└── src/main.py             ← UNCHANGED

infrastructure/agentcore-cdk/
├── bin/agentcore-cdk.ts    ← NEW: CDK app entry
├── lib/agentcore-permissions-stack.ts  ← NEW: IAM policies (replaces shell script)
├── package.json
├── cdk.json
└── README.md
```

**Deployment order:** CDK stack (IAM) → Creation Agent → Verification Agent

### What Changes

| Component | Before | After |
|---|---|---|
| Agent config | `.bedrock_agentcore.yaml` (deprecated) | `agentcore.json` (`@aws/agentcore` CLI) |
| IAM permissions | Manual shell script | CDK stack (CloudFormation) |
| Env vars | Manual `--env` flags | Declared in deploy script, validated before deploy |
| Agent source code | Python | **UNCHANGED** |
| SAM stacks | 4 stacks | **UNCHANGED** |
| Agent IDs/ARNs | Existing | **PRESERVED** |

### Decisions

- Decision 157: Missing BRAVE_API_KEY root cause → motivates declarative env vars
- Decision 158 (planned): CDK migration for AgentCore deployment
