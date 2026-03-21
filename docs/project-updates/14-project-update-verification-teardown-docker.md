# Project Update 14 — Verification Teardown & Docker Lambda (Spec A1)

**Date:** March 20, 2026
**Context:** Executed Spec A1 — removed old verification system, archived code, switched MakeCallStreamFunction to Docker Lambda. Deployed and confirmed pipeline works.
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/verification-teardown-docker/` — Spec A1: Verification Teardown + Docker Lambda (COMPLETE)
- `.kiro/specs/mcp-verification-foundation/` — Combined spec (SUPERSEDED, marked in all 3 files)
- Spec A2: MCP Tool Integration (next — to be created)

### Prerequisite Reading
- `docs/project-updates/13-project-update-verification-pipeline-planning.md` — Spec split planning
- `docs/project-updates/decision-log.md` — Decisions through 70

---

## What Happened This Session

### Spec A1 Execution (Complete)

**SAM Template Changes (Task 1 — done previously):**
- Removed 4 resources: VerificationFunction, VerificationLogsBucket, VerificationNotificationTopic, NotificationManagementFunction
- Removed 3 outputs: VerificationFunctionArn, VerificationLogsBucket, VerificationNotificationTopic
- Removed MakeCallStreamFunctionAliasPermission (no more `:live` alias)
- Updated MakeCallStreamIntegration to unqualified function ARN
- Removed SnapStart + AutoPublishAlias from MakeCallStreamFunction

**Code Archive (Task 2):**
- Moved 19 verification handler files to `docs/historical/verification-v1/`
- Moved 2 notification_management files to `docs/historical/verification-v1/notification_management/`
- Archived `tool_registry.py` from `handlers/strands_make_call/`
- Created archive README with decision references (18, 19, 20, 64, Backlog 7)
- Deleted all original source directories

**Docker Lambda (Task 4):**
- Created `backend/calledit-backend/Dockerfile`: Python 3.12 + Node.js v20 LTS
- Hit `tar: command not found` on first build — AL2023 minimal doesn't include tar/xz (Decision 69)
- Fixed with `dnf install -y tar xz` before Node.js extraction
- Updated MakeCallStreamFunction to `PackageType: Image` with Metadata section

**Superseded Spec Marking:**
- Added SUPERSEDED banners to all 3 files in `.kiro/specs/mcp-verification-foundation/` (requirements, design, tasks)
- Clear pointers to Spec A1 and future Spec A2

### Deployment

- Docker Desktop WSL integration needed enabling before `sam build` could find Docker
- `sam deploy --guided` required for ECR repository setup (new for Docker images)
- VerificationLogsBucket deletion failed (non-empty bucket) — orphaned but harmless (Decision 70)
- All other resources deployed successfully
- Pipeline confirmed working: "Friday is a beach day" prediction processed correctly

### Beach Day Test Result
Categorizer labeled the weather prediction as `human_only` despite reasoning that "weather APIs are common and accessible, making this automatable in principle." This is the empty tool manifest issue — with no tools registered, the categorizer is overly conservative. Spec A2 fixes this by wiring real MCP tools into the categorizer's context.

## Decisions Made

- Decision 69: Dockerfile requires tar/xz install on AL2023 Lambda base image
- Decision 70: Orphaned S3 bucket acceptable during teardown deployment

## What the Next Agent Should Do

### Immediate
1. Create Spec A2 (mcp-tool-integration) — requirements, design, tasks
2. The superseded mcp-verification-foundation spec has useful design material for A2 (MCP Manager, tool-aware agents, Prompt Management VB v3) — reference but don't implement from it directly

### Spec A2 Scope
- MCP Manager module (`mcp_manager.py`) with 3 MCP servers (fetch, brave-search, playwright)
- Wire tool manifest into Categorizer and Verification Builder agents
- Update Prompt Management with VB v3 (`{{tool_manifest}}` variable)
- Replace `tool_registry.py` import in `prediction_graph.py` with `mcp_manager`
- Add `BRAVE_API_KEY` env var to SAM template

### After Spec A2
- Version bump to v3 (CHANGELOG.md)
- Begin Spec B (verification execution agent)

### Key Files
- `.kiro/specs/verification-teardown-docker/` — Spec A1 (COMPLETE)
- `.kiro/specs/mcp-verification-foundation/` — SUPERSEDED (reference material for A2)
- `backend/calledit-backend/template.yaml` — SAM template (Docker Lambda deployed)
- `backend/calledit-backend/Dockerfile` — Docker image definition
- `docs/historical/verification-v1/` — Archived old verification system
- `docs/research/mcp-verification-pipeline.md` — MCP ecosystem research
