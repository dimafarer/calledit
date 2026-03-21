# Project Update 15 — MCP Tool Integration (Spec A2)

**Date:** March 21, 2026
**Context:** Wired MCP tool servers into the prediction pipeline, made all 4 agents tool-aware, debugged package names and JSON parsing, confirmed end-to-end tool-aware categorization and verification planning
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/verification-teardown-docker/` — Spec A1 (COMPLETE)
- `.kiro/specs/mcp-tool-integration/` — Spec A2 (COMPLETE — code deployed, Prompt Management deploy pending)
- `.kiro/specs/mcp-verification-foundation/` — SUPERSEDED

### Prerequisite Reading
- `docs/project-updates/14-project-update-verification-teardown-docker.md` — Spec A1, Docker Lambda
- `docs/project-updates/decision-log.md` — Decisions through 74

---

## What Happened This Session

### Spec A1 Completed and Deployed
- Executed remaining tasks: archived old verification code, created Dockerfile, switched to Docker Lambda
- Hit `tar: command not found` on AL2023 base image — fixed with `dnf install -y tar xz` (Decision 69)
- VerificationLogsBucket deletion failed (non-empty) — orphaned but harmless (Decision 70)
- Pipeline confirmed working with Docker Lambda

### Spec A2 Designed and Implemented
- Created requirements (7 requirements), design (6 components, 5 correctness properties), tasks (8 top-level)
- User caught that ReviewAgent should also be tool-aware — added Requirement 6
- User suggested uniform `tool_manifest` parameter across all 4 agents including Parser — cleaner interface
- Built MCP Manager module, wired into prediction graph, updated all 4 agent factories
- Updated Prompt Management templates (VB v3 + Review v4 with `{{tool_manifest}}`)
- Added BRAVE_API_KEY parameter to SAM template with .env local storage

### MCP Server Debugging Journey
1. All servers failed with "client initialization failed" — `MCPClient` needed `stdio_client()` wrapper, not raw `StdioServerParameters`
2. Package names wrong — `@modelcontextprotocol/server-fetch` doesn't exist as npm (it's Python-only). Fixed to `@tokenizin/mcp-npx-fetch`. Brave search was `@modelcontextprotocol/server-brave-search` not `@nicobailon/mcp-brave-search` (Decision 71)
3. Created `test_mcp_local.py` for fast local iteration — critical for debugging without deploy cycles
4. Lambda needed `HOME=/tmp` and `NPM_CONFIG_CACHE=/tmp/.npm` for writable npm cache
5. Categorizer outputting `{{` in JSON — `.format()` required double-brace escaping in prompt, model mimicked it. Fixed by switching to `.replace()` (Decision 72)

### Beach Day Test — Full Success
After clarification (70+ degrees, winds under 10 mph, sunny, Jones Beach NY):
- Categorizer: `auto_verifiable` — correctly identifies brave_web_search can verify weather data
- VB: References `brave_web_search` by name in sources and steps with GPS coordinates
- Review: Asks tool-aware questions about forecast vs actual data, time windows, weather service preferences
- Frontend: `🤖 Auto Verifiable` label displays correctly

### Cold Start Performance
~30 seconds on cold start (npx downloading packages + Node.js subprocess startup). Validates AgentCore migration priority — tools and agents should be separate execution environments (Decision 73).

### Frontend Label Fix
CloudFront-deployed frontend had stale 5-category labels (`Human Verifiable Only`). Local dev frontend had correct 3-category labels. Not a backend issue — just needed frontend redeploy.

## Decisions Made

- Decision 71: MCP server package names — npm vs Python
- Decision 72: Use .replace() not .format() for tool manifest substitution
- Decision 73: 30-second cold start validates AgentCore migration priority
- Decision 74: Verification pipeline roadmap — build, eval, then migrate

## What the Next Agent Should Do

### Immediate (Remaining A2 Cleanup)
1. Deploy Prompt Management stack (VB v3 + Review v4): `cd infrastructure/prompt-management && aws cloudformation deploy --template-file template.yaml --stack-name calledit-prompts`
2. Bump SAM env vars: `PROMPT_VERSION_VB: "3"`, `PROMPT_VERSION_REVIEW: "4"`
3. Redeploy backend with bumped versions

### After A2 Cleanup
4. Version bump to v3 (CHANGELOG.md) — v1=pre-graph, v2=unified graph, v3=MCP-powered pipeline
5. Create Spec B (verification execution agent) — agent that actually invokes MCP tools to verify predictions
6. Run golden dataset against both prediction builder and verification pipeline to compare quality

### After Spec B
7. Migrate to AgentCore (Decision 68, 73, 74) — tools as always-warm network services, agents in managed runtime

### Key Files
- `backend/calledit-backend/handlers/strands_make_call/mcp_manager.py` — MCP Manager module
- `backend/calledit-backend/handlers/strands_make_call/prediction_graph.py` — graph wiring (uses mcp_manager)
- `backend/calledit-backend/handlers/strands_make_call/categorizer_agent.py` — tool-aware categorizer
- `backend/calledit-backend/handlers/strands_make_call/verification_builder_agent.py` — tool-aware VB
- `backend/calledit-backend/handlers/strands_make_call/review_agent.py` — tool-aware review
- `backend/calledit-backend/test_mcp_local.py` — local MCP connection test script
- `infrastructure/prompt-management/template.yaml` — VB v3 + Review v4 (deploy pending)
- `.env` — BRAVE_API_KEY (gitignored)
