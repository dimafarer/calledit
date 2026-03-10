# Project Update 03 — Lambda Cold Start Optimization & Infrastructure

**Date:** March 9, 2026
**Context:** Infrastructure optimization spec + documentation + MCP server setup
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/lambda-cold-start-optimization/` — Spec 4: Lambda Cold Start Optimization
  - `requirements.md` — COMPLETE (7 requirements)
  - `design.md` — COMPLETE (phased deployment, 4 correctness properties)
  - `tasks.md` — COMPLETE (8 tasks, EXECUTED)
- `.kiro/specs/prompt-eval-framework/` — Spec 5: Prompt Evaluation Framework
  - `requirements.md` — COMPLETE (8 requirements)
  - `design.md` — NOT YET CREATED
  - `tasks.md` — NOT YET CREATED

### Referenced Git Commits
- Previous: Spec 3 frontend commits (see Update 02)
- This session: pending commit — Spec 3 execution, Spec 4 execution, Spec 5 requirements, Strands Graph guide, MCP config

### Prerequisite Reading
- `docs/project-updates/01-project-update.md` — Specs 1 and 2 narrative
- `docs/project-updates/02-project-update.md` — Spec 3 narrative and execution

---

## What Happened

After completing Spec 3 (frontend v2 protocol alignment), this session covered three areas: documentation, infrastructure setup, and a new spec for Lambda cold start optimization.

## Strands Graph Guide

Created `docs/guides/strands-graph-guide.md` — a layered guide from "Graph for Dummies" to production patterns, using CalledIt's implementation as the running example. Seven levels covering input propagation, topologies, execution modes, streaming events, conditional edges, the singleton pattern, two-push delivery, and lessons learned.

## MCP Server Configuration

Set up workspace-level MCP config at `.kiro/settings/mcp.json` with three servers:

1. **awslabs.lambda-tool-mcp-server** — Direct Lambda function invocation and inspection. Configured with `FUNCTION_PREFIX: calledit-backend` to scope to our functions.

2. **awslabs.aws-iac-mcp-server** — CloudFormation template validation, compliance checking, deployment troubleshooting. Useful for validating SAM template changes.

3. **awslabs.aws-serverless-mcp-server** — SAM lifecycle (init, build, deploy), Lambda observability (logs, metrics), serverless guidance. The most relevant for this project.

We evaluated and rejected **awslabs.cfn-mcp-server** (Cloud Control API wrapper) — it's for ad-hoc resource management, not SAM-based projects. Using it would bypass the SAM stack and create drift.

The user-level MCP config (`~/.kiro/settings/mcp.json`) had placeholder values from auto-install. We disabled the user-level entries and configured workspace-level ones with correct settings (us-west-2, no profile placeholders).

## Lambda Cold Start Optimization Spec

### The Problem

MakeCallStreamFunction has a 2,441ms cold start (measured via CloudWatch INIT duration). This is caused by heavy imports (strands-agents, dateparser, pytz) and module-level graph compilation (4 Agent instances + GraphBuilder).

### Key Discovery: SnapStart for Python

I initially said SnapStart was Java-only. The user corrected me — SnapStart now supports Python 3.12+. This changes the entire cost analysis:

- **SnapStart**: $0 additional cost. Snapshots the initialized execution environment (imports + singleton graph). Restore time typically 200-500ms.
- **Provisioned Concurrency**: ~$39/month for 1 instance at 512MB. Keeps Lambda warm permanently.

For a demo/educational project with intermittent usage, SnapStart is the clear winner.

### Design Decisions

**Decision 1: Phased deployment**
- Phase 1: MakeCallStreamFunction only (already has `AutoPublishAlias: live`, lowest risk)
- Phase 2: Secondary functions (some need `AutoPublishAlias` added, higher risk)

**Decision 2: Skip ConnectFunction and DisconnectFunction**
These import only `json` — no cold start benefit. Adding `AutoPublishAlias` to WebSocket lifecycle functions is the riskiest change and likely what caused the user's previous Provisioned Concurrency deployment failure.

**Decision 3: Runtime hooks are defensive**
MakeCallStreamFunction creates `api_gateway_client` per-invocation (not at module level), so nothing is actually stale after snapshot restore. The hooks exist for future-proofing and for NotificationManagementFunction's module-level `sns_client`.

**Decision 4: Singleton graph pattern is ideal for SnapStart**
The module-level `prediction_graph = create_prediction_graph()` runs during INIT. SnapStart snapshots this. On restore, the compiled graph with all 4 agents is immediately available — no re-compilation needed.

### Versions and Aliases Risk

SnapStart requires published versions (via `AutoPublishAlias`). Three functions already have it (MakeCallStreamFunction, LogCall, ListPredictions). The others don't. Adding `AutoPublishAlias` changes how API Gateway routes to the function. This is documented as a risk note in Req 3 and is why Phase 2 deploys separately.

### Baseline Measurement

Cold start baseline captured before any changes:
- **INIT Duration: 2,441ms** (2.4 seconds)
- Handler Duration: 21,186ms (graph execution, not cold start)
- Memory: 162MB used of 512MB allocated

## Current State

### Spec 4: Lambda Cold Start Optimization
- **Location:** `.kiro/specs/lambda-cold-start-optimization/`
- **Status:** Requirements COMPLETE, Design COMPLETE, Tasks COMPLETE, Execution STARTED
- **Task 1 (baseline measurement):** COMPLETE — 2,441ms INIT duration recorded
- **Next step:** Task 2 — Create runtime hooks and graph validation

### What the Next Agent Should Do
1. Read this update and Updates 01-02 for full context
2. Read `.kiro/specs/lambda-cold-start-optimization/` (requirements, design, tasks)
3. Continue from Task 2 — create `snapstart_hooks.py`, add graph validation, import in handler
4. Then Task 3 — add `SnapStart: { ApplyOn: PublishedVersions }` to MakeCallStreamFunction in SAM template
5. Deploy Phase 1 and measure improvement (Task 4 checkpoint)
6. Phase 2 secondary functions (Task 5) — deploy separately

### Key Files
- `backend/calledit-backend/template.yaml` — SAM template (add SnapStart property)
- `backend/calledit-backend/handlers/strands_make_call/prediction_graph.py` — Singleton graph
- `backend/calledit-backend/handlers/strands_make_call/strands_make_call_graph.py` — Lambda handler (import hooks here)
- `.kiro/settings/mcp.json` — Workspace MCP server config

---

## Spec 4 Execution — March 9, 2026

All tasks executed successfully. SnapStart is live across 6 Lambda functions.

### Cold Start Measurements

| Measurement | Duration | Improvement |
|-------------|----------|-------------|
| Baseline INIT (no SnapStart) | 2,441ms | — |
| SnapStart restore (buggy graph validation) | 1,844ms | 25% |
| SnapStart restore (fixed validation) | 726ms | 70% |
| Latest SnapStart restore | 444ms | 82% |

### Bug Found: Graph Validation Attribute Error

The `validate_graph_after_restore()` function used `prediction_graph.graph.nodes.keys()` but the Strands `Graph` object has `nodes` as a direct attribute, not nested under `.graph`. This caused an `AttributeError` on every restore, triggering a full graph re-creation (~1 second overhead). Fixed to `prediction_graph.nodes.keys()`.

### WebSocket Integration Fix

SnapStart only works on published versions (via alias), not `$LATEST`. The WebSocket integration URI referenced `${MakeCallStreamFunction.Arn}` which resolves to `$LATEST`. Changed to `${MakeCallStreamFunction.Arn}:live` and added a separate `MakeCallStreamFunctionAliasPermission` for API Gateway to invoke the alias.

### Functions with SnapStart Enabled

| Function | Had AutoPublishAlias? | SnapStart Added | Restore Hook |
|----------|----------------------|-----------------|--------------|
| MakeCallStreamFunction | Yes (existing) | Yes | Yes (graph validation) |
| LogCall | Yes (existing) | Yes | No |
| ListPredictions | Yes (existing) | Yes | No |
| AuthTokenFunction | No (added) | Yes | No |
| VerificationFunction | No (added) | Yes | No |
| NotificationManagementFunction | No (added) | Yes | Yes (sns_client refresh) |
| ConnectFunction | No | Excluded | — |
| DisconnectFunction | No | Excluded | — |

### Decision 11: Skip ConnectFunction and DisconnectFunction

These import only `json` — no cold start benefit. Adding `AutoPublishAlias` to WebSocket lifecycle functions is the riskiest change and likely what caused the user's previous Provisioned Concurrency deployment failure.

### Decision 12: Provisioned Concurrency Not Needed

With SnapStart restoring in 444ms (vs 2,441ms baseline), Provisioned Concurrency (~$39/month) is unnecessary for this demo project. Documented as a fallback in the design doc if SnapStart proves insufficient.

### Files Created/Modified

- `backend/calledit-backend/handlers/strands_make_call/snapstart_hooks.py` — NEW: SnapStart runtime hooks + graph validation
- `backend/calledit-backend/handlers/notification_management/snapstart_hooks.py` — NEW: SNS client restore hook
- `backend/calledit-backend/handlers/strands_make_call/strands_make_call_graph.py` — Added `import snapstart_hooks`
- `backend/calledit-backend/handlers/notification_management/app.py` — Added `import snapstart_hooks`
- `backend/calledit-backend/template.yaml` — SnapStart + AutoPublishAlias on 6 functions, alias integration URI + permission

### MCP Server Usage

Used the AWS Observability power (`awslabs.cloudwatch-mcp-server`) to query CloudWatch Logs directly for restore duration metrics. This was more reliable than CLI commands (TTY issues) and provided the exact `restoreDurationMs` values from platform REPORT logs.

---

## Prompt Evaluation Strategy Discussion — March 9, 2026

### The Problem

During testing, "Tomorrow will be a beautiful day" was correctly categorized as `human_verifiable_only` in round 1. After the user clarified "70+ degrees, sunny, New York," the categorizer should have upgraded to `api_tool_verifiable` — but it didn't. It clung to "beautiful is subjective" reasoning and ignored the clarification.

This revealed two issues:
1. The ReviewAgent over-assumed weather without confirming ("beautiful" could mean anything)
2. The categorizer under-utilized user clarifications — the whole point of the clarification loop is to convert subjective claims into measurable criteria

### Decision 13: Prompt Evaluation Strategy

We need a systematic way to iterate on prompts without going in circles. After discussing strategies, we chose:

**Primary: Golden Dataset + Automated Eval**
- Build ~25 test predictions with expected outcomes
- Run each prompt change against the full set, score automatically
- Catches regressions, provides objective "are we improving?" signal
- Confidence: 8/10

**Secondary: LLM-as-Judge** for nuanced reasoning quality
- Confidence: 6/10 (supplement, not primary)

**Investigated but deferred: Strands Evals SDK**
- Unknown maturity, worth exploring later
- Confidence: 5/10

### Decision 14: Layered Test Pyramid for Predictions

The user proposed a layered approach to building test predictions:

**Layer 1 — Base Predictions (fully specified):**
Predictions that need zero clarification. These are the ground truth — the "perfect input" that the system should handle cleanly. If the system can't get these right, the prompts are fundamentally broken.

Example: "Tomorrow the high temperature in Central Park, New York will reach at least 70°F"
→ Expected: `api_tool_verifiable`, no clarification needed

**Layer 2 — Fuzzy Predictions (degraded versions of base):**
Same predictions with information removed. These test the clarification loop — the system should ask the right questions and, after getting answers, converge to the same structured output as the base prediction.

Example: "Tomorrow will be a beautiful day"
→ Expected round 1: `human_verifiable_only` (correct — it IS subjective without context)
→ Expected: ReviewAgent asks about location, what "beautiful" means
→ After clarification "70+ degrees, sunny, New York": should converge to `api_tool_verifiable`

**Why this works:**
- Base predictions validate core capability (structured conversion)
- Fuzzy versions validate the clarification loop (progressive refinement)
- Convergence is measurable: does fuzzy + clarification → base output?
- Question quality is gradable: did the system ask the right things?

### Next Steps

A new spec will be created for the prompt evaluation framework. The next agent should:
1. Read this update for the strategy discussion
2. Read `.kiro/specs/prompt-eval-framework/requirements.md` (to be created)
3. Build the eval harness, golden dataset, and scoring system
4. Then iterate on the categorizer and review agent prompts with the eval framework in place

### Decision 15: Clarification Improves Precision, Not Just Verifiability

During requirements review, the user identified an edge case: predictions that will always be `human_verifiable_only` (e.g., "Tom will wear that shirt") still benefit from clarification. The system should ask "which Tom?", "which shirt?", "what day?" to make the prediction as specific as possible for the human who will eventually verify it.

This means the golden dataset needs test cases where:
- Base: "John will wear the stained blue Tom Ford polyester shirt tomorrow" → `human_verifiable_only` with rich detail
- Fuzzy: "Tom will wear that shirt" → still `human_verifiable_only` after clarification, but converges to the detailed base version

Convergence isn't just about upgrading the category — it's about improving precision within the same category. A note was added to the Spec 5 requirements to make this explicit.
