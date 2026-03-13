# Project Update 03 — Lambda SnapStart Optimization

**Date:** March 9–13, 2026
**Context:** SnapStart enablement across all Lambda functions (Specs 4 + 6)
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/lambda-cold-start-optimization/` — Spec 4: Lambda Cold Start Optimization
  - `requirements.md` — COMPLETE
  - `design.md` — COMPLETE
  - `tasks.md` — COMPLETE (EXECUTED)
- `.kiro/specs/websocket-snapstart/` — Spec 6: WebSocket SnapStart Completion
  - `requirements.md` — COMPLETE
  - `design.md` — COMPLETE
  - `tasks.md` — COMPLETE (EXECUTED)

### Prerequisite Reading
- `docs/project-updates/01-project-update-v2-architecture-planning.md` — Specs 1 and 2 narrative
- `docs/project-updates/02-project-update-frontend-v2-alignment.md` — Spec 3 narrative and execution

---

## Strands Graph Guide

Created `docs/guides/strands-graph-guide.md` — a layered guide from "Graph for Dummies" to production patterns, using CalledIt's implementation as the running example. Seven levels covering input propagation, topologies, execution modes, streaming events, conditional edges, the singleton pattern, two-push delivery, and lessons learned.

## MCP Server Configuration

Set up workspace-level MCP config at `.kiro/settings/mcp.json` with three servers:

1. **awslabs.lambda-tool-mcp-server** — Direct Lambda function invocation and inspection. Configured with `FUNCTION_PREFIX: calledit-backend` to scope to our functions.
2. **awslabs.aws-iac-mcp-server** — CloudFormation template validation, compliance checking, deployment troubleshooting.
3. **awslabs.aws-serverless-mcp-server** — SAM lifecycle (init, build, deploy), Lambda observability (logs, metrics), serverless guidance.

Rejected **awslabs.cfn-mcp-server** (Cloud Control API wrapper) — it's for ad-hoc resource management, not SAM-based projects.

---

## Spec 4: Lambda Cold Start Optimization — March 9, 2026

### The Problem

MakeCallStreamFunction has a 2,441ms cold start caused by heavy imports (strands-agents, dateparser, pytz) and module-level graph compilation (4 Agent instances + GraphBuilder).

### Key Discovery: SnapStart for Python

SnapStart now supports Python 3.12+. $0 additional cost vs ~$39/month for Provisioned Concurrency. Clear winner for a demo project.

### Design Decisions

- **Decision 1:** Phased deployment — MakeCallStreamFunction first, secondary functions second
- **Decision 2:** Skip ConnectFunction/DisconnectFunction (imports only `json`, risk > benefit)
- **Decision 3:** Runtime hooks are defensive (MakeCallStreamFunction creates api_gateway_client per-invocation)
- **Decision 4:** Singleton graph pattern is ideal for SnapStart (snapshot includes compiled graph)

### Cold Start Measurements

| Measurement | Duration | Improvement |
|-------------|----------|-------------|
| Baseline INIT (no SnapStart) | 2,441ms | — |
| SnapStart restore (buggy graph validation) | 1,844ms | 25% |
| SnapStart restore (fixed validation) | 726ms | 70% |
| Latest SnapStart restore | 444ms | 82% |

### Bug: Graph Validation Attribute Error

`prediction_graph.graph.nodes.keys()` → `prediction_graph.nodes.keys()`. Strands `Graph` has `nodes` as a direct attribute.

### WebSocket Integration Fix

Changed IntegrationUri from `${MakeCallStreamFunction.Arn}` to `${MakeCallStreamFunction.Arn}:live` + added `MakeCallStreamFunctionAliasPermission`.

### Decision 11: Skip Connect/Disconnect (reversed in Spec 6)
### Decision 12: Provisioned Concurrency Not Needed (444ms restore is sufficient)

---

## Spec 6: WebSocket SnapStart Completion — March 13, 2026

Added SnapStart to ConnectFunction and DisconnectFunction for stack consistency. SAM template only — no handler code changes.

### Changes

| Resource | Change |
|----------|--------|
| ConnectFunction | Added `AutoPublishAlias: live` + `SnapStart: { ApplyOn: PublishedVersions }` |
| DisconnectFunction | Added `AutoPublishAlias: live` + `SnapStart: { ApplyOn: PublishedVersions }` |
| ConnectIntegration | IntegrationUri → `${ConnectFunction.Arn}:live/invocations` |
| DisconnectIntegration | IntegrationUri → `${DisconnectFunction.Arn}:live/invocations` |
| ConnectFunctionAliasPermission | NEW — alias invoke permission scoped to `$connect` |
| DisconnectFunctionAliasPermission | NEW — alias invoke permission scoped to `$disconnect` |

### Bug: Alias DependsOn Race Condition

First deploy failed: `Cannot find alias arn: ...DisconnectFunction...:live`. CloudFormation created alias permission before alias existed.

Fix: Added `DependsOn: {FunctionName}Aliaslive` to all alias-referencing resources (including retroactive fix for MakeCallStreamFunction).

### Decision 16: Add SnapStart to WebSocket Lifecycle Functions (reversed Decision 11)
### Decision 17: DependsOn Required for All Alias References

### SnapStart Coverage — Final State

All 8 Lambda functions now have SnapStart enabled.

| Function | SnapStart | Restore Hook | Alias Integration |
|----------|-----------|--------------|-------------------|
| MakeCallStreamFunction | ✅ | Yes (graph validation) | ✅ `:live` |
| ConnectFunction | ✅ | No | ✅ `:live` |
| DisconnectFunction | ✅ | No | ✅ `:live` |
| LogCall | ✅ | No | N/A (REST API) |
| ListPredictions | ✅ | No | N/A (REST API) |
| AuthTokenFunction | ✅ | No | N/A (REST API) |
| VerificationFunction | ✅ | No | N/A (EventBridge) |
| NotificationManagementFunction | ✅ | Yes (sns_client) | N/A (REST API) |
