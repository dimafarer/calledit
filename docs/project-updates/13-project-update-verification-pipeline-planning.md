# Project Update 13 — Verification Pipeline Planning & Spec Split

**Date:** March 20, 2026
**Context:** Planned the MCP verification pipeline build, split the combined spec into focused specs, identified Docker Lambda + SnapStart tradeoff, established the v3 version boundary and AgentCore migration path
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/production-prompt-management/` — Spec 12: Production Prompt Management Wiring (COMPLETE)
- `.kiro/specs/mcp-verification-foundation/` — Combined spec (SUPERSEDED by split below)
- `.kiro/specs/verification-teardown-docker/` — Spec A1: Verification Teardown + Docker Lambda (DESIGNED, tasks pending)
- Spec A2: MCP Tool Integration (planned, not yet created)

### Prerequisite Reading
- `docs/project-updates/12-project-update-production-prompt-management.md` — Spec 12, production prompt wiring
- `docs/project-updates/decision-log.md` — All decisions through Decision 68
- `docs/research/mcp-verification-pipeline.md` — MCP ecosystem research

---

## What Happened This Session

### Spec 12: Production Prompt Management (Completed)
- Discovered production was running stale v1 hardcoded prompts — Lambda lacked `bedrock-agent:GetPrompt` IAM permission and `PROMPT_VERSION_*` env vars
- Added both to SAM template, pinned to eval-validated versions (parser 1, categorizer 2, VB 2, review 3)
- Updated all 4 fallback constants to match latest Prompt Management text
- Deployed and confirmed new prompts are live — categorizer now produces v2 reasoning

### Beach Day Demo Insight
Tested with "Friday is a beach day" → clarified with "70 degrees, winds under 10 mph, Far Rockaways NYC." Categorizer correctly identified this as verifiable with a weather tool but conservatively labeled it because no weather tool is registered. The reasoning: "While no weather API tool is currently available, such tools commonly exist and could be integrated." This confirms the categorizer is working correctly — the fix is real tools, not better prompts.

### Verification Pipeline Planning
Reviewed the old verification system (EventBridge-triggered Lambda, DDB tool registry, custom web_search tool). Decided on a 4-spec approach:
- Spec A1: Teardown old system + Docker Lambda infrastructure
- Spec A2: MCP Manager + tool-aware agents + Prompt Management
- Spec B: Verification execution agent
- Spec C: Eval framework integration with outcome-based metrics

### The Spec Split (Decision 64)
The combined "mcp-verification-foundation" spec had 17 tasks — too large. Split at the natural boundary between infrastructure (teardown + Docker) and application logic (MCP Manager + agents). Same reasoning as Decision 3: smaller specs, higher confidence.

### Docker Lambda + SnapStart Tradeoff (Decisions 65-66)
MCP servers are npm packages needing `npx` → need Node.js → need Docker Lambda. But SnapStart only supports zip packages, not container images. Accepted the tradeoff: cold starts ~2-5s slower, but MCP subprocess startup would invalidate SnapStart anyway, and AgentCore migration is planned shortly after.

### Version Bump to v3 (Decision 67)
v1 = pre-graph, v2 = unified graph, v3 = MCP-powered verification pipeline. Breaking change: removes old verification system, changes Lambda packaging, replaces tool registry. Version bump after Spec A2 completes.

### AgentCore Migration Path (Decision 68)
Docker Lambda is a stepping stone toward AgentCore. The container-based architecture transfers directly. Current SAM architecture was for the class; now showing best-in-class agent architecture.

## Decisions Made

- Decision 61: Production prompts via Bedrock Prompt Management with version pinning
- Decision 62: Composite score weights need empirical grounding
- Decision 63: Pre-graph (v1) backend as eval comparison target
- Decision 64: Split MCP verification foundation into two specs
- Decision 65: Docker Lambda for MCP subprocess support
- Decision 66: Accept SnapStart loss on MakeCallStreamFunction
- Decision 67: Project version bump to v3
- Decision 68: AgentCore as post-verification migration target

## What the Next Agent Should Do

### Immediate
1. Generate tasks for Spec A1 (verification-teardown-docker) — design is complete
2. Execute Spec A1: remove old verification resources from SAM, archive code, create Dockerfile, switch to PackageType: Image
3. Deploy and validate pipeline works in Docker container

### After Spec A1
4. Create Spec A2 (mcp-tool-integration) — requirements, design, tasks
5. Execute Spec A2: MCP Manager module, tool-aware categorizer/VB, Prompt Management VB v3
6. Deploy and validate tool-aware pipeline (beach day prediction should route correctly)

### After Spec A2
7. Version bump to v3 (CHANGELOG.md)
8. Begin Spec B (verification execution agent)

### Key Files
- `.kiro/specs/verification-teardown-docker/` — Spec A1 (requirements + design complete)
- `.kiro/specs/mcp-verification-foundation/` — Combined spec (superseded, keep for reference)
- `backend/calledit-backend/template.yaml` — SAM template (needs resource removal + Docker switch)
- `backend/calledit-backend/handlers/verification/` — Old verification code to archive
- `docs/research/mcp-verification-pipeline.md` — MCP ecosystem research
