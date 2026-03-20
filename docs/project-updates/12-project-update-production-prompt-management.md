# Project Update 12 — Production Prompt Management Wiring

**Date:** March 20, 2026
**Context:** Wired production Lambda to Bedrock Prompt Management, deployed eval-validated prompts to production, confirmed new prompts are live
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/production-prompt-management/` — Spec 12: Production Prompt Management Wiring (COMPLETE)

### Prerequisite Reading
- `docs/project-updates/11-project-update-comparative-dashboard-and-analysis.md` — Spec 11, architecture comparison, prompt change decisions
- `docs/project-updates/decision-log.md` — All decisions through Decision 63
- `docs/project-updates/eval-run-log.md` — All 16 eval runs

---

## The Problem

Production was running stale v1 hardcoded prompts while the eval framework had validated v2/v3 prompts with significant improvements (review v3: +13% serial, +21% single). The `prompt_client.py` fetch logic existed and worked, but the Lambda was missing two things:

1. **No IAM permission** — `bedrock-agent:GetPrompt` was not in the SAM template. Every `fetch_prompt()` call failed silently and fell back to the hardcoded `*_SYSTEM_PROMPT` constants.
2. **No environment variables** — `PROMPT_VERSION_*` env vars were not set, so even if the API call worked, it would default to `DRAFT` instead of pinned numbered versions.

This was discovered during a demo where "Friday is a beach day" stayed `human_only` even after the user clarified with specific weather thresholds (70°F, winds under 10 mph, Far Rockaways NYC). The old v1 categorizer prompt lacked the nuanced `automatable` vs `human_only` distinction from v2.

## What Was Done

### SAM Template Changes
- Added `bedrock-agent:GetPrompt` IAM policy statement (separate from `bedrock:InvokeModel` because `bedrock-agent` is a different IAM service prefix)
- Added `Environment.Variables` block with 4 version-pinned env vars:
  - `PROMPT_VERSION_PARSER: "1"`
  - `PROMPT_VERSION_CATEGORIZER: "2"`
  - `PROMPT_VERSION_VB: "2"`
  - `PROMPT_VERSION_REVIEW: "3"`

### Fallback Constant Updates
All 4 hardcoded `*_SYSTEM_PROMPT` constants updated to match their Prompt Management versions so even fallback mode uses current prompts:
- **Parser**: JSON output instruction updated to match v1 ("The first character of your response must be { and the last must be }.")
- **Categorizer**: Already matched v2 (expanded `human_only` definition). JSON instruction updated.
- **Verification Builder**: Replaced short v1 with full v2 (operationalization Track 1/Track 2 + specificity matching)
- **Review**: Replaced generic "meta-analysis" v1 with targeted v3 ("find specific assumptions in the Verification Builder's output")

### No Changes to prompt_client.py
The fetch-and-fallback logic was already complete. It reads `PROMPT_VERSION_{AGENT_NAME}` from env vars, calls `bedrock-agent:GetPrompt`, resolves `{{variable}}` templates, and falls back to bundled constants on failure.

## Production Validation

Deployed and tested with the same "beach day" prediction. The categorizer now produces v2 reasoning:

> "With the user's specific criteria (sunny, 70+ degrees, winds under 10 mph at Rockaway Beach NYC), this prediction can now be objectively verified using weather data. While no weather API tool is currently available, such tools commonly exist and could be integrated."

The categorizer correctly identifies this as verifiable with a weather tool but conservatively labels it because no weather tool is registered. This is the expected behavior — the verification pipeline (next spec) will fix this by providing real MCP tools.

## Decisions Made

- **Decision 61**: Production prompts via Bedrock Prompt Management with version pinning. Rollback is a single env var change.
- **Decision 62**: Composite score weights need empirical grounding — current weights are judgment calls, not data-derived. Deferred until verification pipeline produces real outcome data.
- **Decision 63**: Pre-graph (v1) backend as eval comparison target — add `backends/pregraph.py` to data-drive the "was v1 better?" question.

## Backlog Updates

- Added item 10: Pre-graph (v1) backend through eval framework
- Added item 11: Composite score weight recalibration from verification outcome data
- Renumbered item 9 → 12: Per-architecture prompt management

## What the Next Agent Should Do

1. Begin verification pipeline implementation (backlog item 7)
   - Start with MCP servers: `server-fetch`, `mcp-brave-search`, `mcp-playwright`
   - Wire tool registry into Verification Builder and categorizer via Strands `MCPClient`
   - Build verification execution agent
   - See `docs/research/mcp-verification-pipeline.md` for full plan
2. After verification pipeline: revisit eval framework — derive evaluation metrics and rubrics from actual verification outcomes, recalibrate composite weights, tune prompts and architecture

### Key Files
- `backend/calledit-backend/template.yaml` — SAM template (now has IAM + env vars)
- `backend/calledit-backend/handlers/strands_make_call/prompt_client.py` — Prompt Management client (unchanged)
- `backend/calledit-backend/handlers/strands_make_call/*_agent.py` — Agent factories (fallback constants updated)
- `infrastructure/prompt-management/template.yaml` — Prompt Management CloudFormation stack
