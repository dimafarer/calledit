# Project Update 04 — Verifiability Category Simplification & Tool Registry

**Date:** March 13, 2026
**Context:** Simplify verifiability categories from 5 to 3, add tool registry, add web search tool
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/category-simplification/` — Spec 7: Category Simplification & Tool Registry
  - `requirements.md` — COMPLETE (11 requirements)
  - `design.md` — COMPLETE (9 components, 11 correctness properties)
  - `tasks.md` — COMPLETE (12 tasks, EXECUTED)

### Prerequisite Reading
- `docs/project-updates/03-project-update-snapstart.md` — SnapStart completion
- `docs/project-updates/05-project-update-eval-strategy.md` — Eval framework (deferred until after this spec)

---

## The Problem

The current 5 verifiability categories (`agent_verifiable`, `current_tool_verifiable`, `strands_tool_verifiable`, `api_tool_verifiable`, `human_verifiable_only`) are too granular. The distinctions between `current_tool_verifiable`, `strands_tool_verifiable`, and `api_tool_verifiable` are implementation details about *which tool* rather than meaningful distinctions about *verifiability*.

As we add tools (starting with web search), predictions should naturally graduate from "needs a tool we don't have" to "the agent can verify this now." The current categories don't support this progression cleanly.

## Decision 18: Simplify to 3 Verifiability Categories

**Old (5 categories):** `agent_verifiable`, `current_tool_verifiable`, `strands_tool_verifiable`, `api_tool_verifiable`, `human_verifiable_only`

**New (3 categories):**

1. `auto_verifiable` — The system can verify this right now, automatically, using reasoning plus current tools.

2. `automatable` — The system can't verify this yet, but it's automatable in principle. An agent could plausibly find or build a tool to verify it. This is the work queue for the future tool-finding agent.

3. `human_only` — Requires subjective judgment or information that cannot be obtained through any tool or stored context. No amount of tooling helps.

**Why:** `auto_verifiable` is a growing bucket. Every time you add a tool, predictions graduate from `automatable`. When you build the tool-finding agent, `automatable` predictions are its work queue. `human_only` is the floor — though future user context profiles may shrink it further.

## Decision 19: Tool Registry in DynamoDB

Both the categorizer and verification agent need to know what tools are available. A tool registry in DynamoDB (`calledit-db`) stores tool records with schemas:

- PK: `TOOL#{tool_id}` (e.g., `TOOL#web_search`)
- SK: `METADATA`
- Fields: name, description, capabilities (list of what it can verify), input_schema, output_schema, status (active/inactive), added_date

The categorizer reads the registry at runtime to determine if a prediction is `auto_verifiable` (matching tool exists and is active) vs `automatable` (no matching tool). The verification agent reads it to know which tools to use.

## Decision 20: Web Search as First Registered Tool

A custom `@tool` using Python `requests` library, registered in the tool registry. This serves as the test case for the entire tool registration workflow:

1. Create the web search tool
2. Register it in DynamoDB tool registry
3. Wire it into the verification agent
4. Re-categorize existing predictions (full graph re-run for `tool_verifiable` predictions)
5. Verify that eligible predictions graduate to `agent_verifiable`

## Decision 21: Re-categorization Runs Full Pipeline

When a tool is added, `tool_verifiable` predictions get re-run through the full graph (parser → categorizer → VB → review), not just the categorizer. The verification_method from the VB also needs updating when the category changes, and the user can log their call at any time after the initial display, so it's fine to take the time for a full re-run.

## Decision 22: Upgrade Verification Agent to Sonnet 4

The verification agent currently uses `claude-3-sonnet-20241022` while all prediction pipeline agents use `us.anthropic.claude-sonnet-4-20250514-v1:0`. Upgrade as part of this work for consistency and better instruction following.

## Scope Summary

1. Simplify categories from 5 → 3 (update categorizer prompt, verification agent routing, DB writes)
2. Tool registry in DynamoDB (schema with input/output definitions)
3. Web search tool (custom `@tool` with `requests`, first registered tool)
4. Re-categorization pipeline (scan `automatable` predictions, re-run full graph)
5. Upgrade verification agent to Sonnet 4
6. Clean up legacy prediction data (old 5-category system)

## What the Next Agent Should Do

1. Read this update and Update 05 for eval framework context
2. Start Spec 5 (prompt-eval-framework) — design → tasks → execute
3. The golden dataset must use the new 3-category system (`auto_verifiable`, `automatable`, `human_only`)

---

## Spec 7 Execution — March 13, 2026

### Data Cleanup

Backed up 62 legacy predictions to S3 (`calledit-backend-verification-logs-{account}/backups/predictions-backup-{timestamp}.json`) and deleted them from DynamoDB. Clean slate for the new 3-category system.

### Category Simplification

Updated `categorizer_agent.py` with new `VALID_CATEGORIES` set and rewritten system prompt describing 3 categories with examples. Added `tool_manifest` parameter to `create_categorizer_agent()` for dynamic tool awareness. Updated all fallback defaults from `human_verifiable_only` to `human_only` in `prediction_graph.py` and `strands_make_call_graph.py`.

### Tool Registry

Created `tool_registry.py` in `handlers/strands_make_call/` with `read_active_tools()` and `build_tool_manifest()`. Reads from DynamoDB at graph creation time (module level, cached by SnapStart). Tool manifest is injected into the categorizer's system prompt.

### Verification Agent Overhaul

Rewrote `verification_agent.py` — upgraded from `claude-3-sonnet-20241022` to `us.anthropic.claude-sonnet-4-20250514-v1:0`. Simplified routing from 5 categories to 3 + unknown fallback. Loads active tools from registry at init. Removed legacy `mock_strands` and `error_handling` imports from the agent (app.py still uses error_handling for its decorator).

Deployment fix: the `sys.path` hack to import `tool_registry` from `strands_make_call` doesn't work in Lambda (different CodeUri). Added inline fallback that reads tools directly from DDB if the module import fails.

### Web Search Tool

Created `web_search_tool.py` — custom `@tool` using Python `requests` + DuckDuckGo Instant Answer API. Handles timeouts, HTTP errors, and connection failures gracefully (returns structured error JSON, never raises). Created `seed_web_search_tool.py` to register the tool record in DDB.

### Frontend Updates

Updated `verifiabilityCategories.ts`, `StreamingCall.tsx`, and `ListPredictions.tsx` with new 3-category labels and icons: 🤖 Auto Verifiable, 🔧 Automatable, 👤 Human Only.

### SnapStart + Tool Registry Interaction

The tool manifest is read during Lambda INIT and cached by SnapStart. Adding a new tool to DDB requires a code deploy to force a new SnapStart snapshot. Added `GRAPH_VERSION` comment in `prediction_graph.py` to bump when forcing a snapshot refresh after tool registry changes.

### Validation Results

| Prediction | Expected | Actual | Status |
|---|---|---|---|
| "The sun will rise tomorrow" | auto_verifiable | 🤖 Auto Verifiable | ✅ |
| "The DR will win the game tonight" | automatable | 🔧 Automatable | ✅ |
| "I'll enjoy the movie I'm seeing tonight" | human_only | 👤 Human Only | ✅ |

Note: "The DR will win the game tonight" stayed `automatable` even after web search tool registration because "DR" is ambiguous. The categorizer correctly identified the ambiguity. With clarification ("Dominican Republic, World Baseball Classic"), it would likely upgrade. This is a prompt tuning issue for the eval framework to address.

### Files Created/Modified

- `backend/calledit-backend/handlers/strands_make_call/categorizer_agent.py` — 3-category system + tool manifest injection
- `backend/calledit-backend/handlers/strands_make_call/tool_registry.py` — NEW: tool registry reader
- `backend/calledit-backend/handlers/strands_make_call/prediction_graph.py` — Tool registry read at graph creation, fallback updates, GRAPH_VERSION
- `backend/calledit-backend/handlers/strands_make_call/strands_make_call_graph.py` — Fallback category update
- `backend/calledit-backend/handlers/verification/verification_agent.py` — Full rewrite: Sonnet 4, 3-category routing, tool loading
- `backend/calledit-backend/handlers/verification/web_search_tool.py` — NEW: web search @tool
- `backend/calledit-backend/handlers/verification/seed_web_search_tool.py` — NEW: tool registry seed script
- `backend/calledit-backend/handlers/verification/cleanup_predictions.py` — NEW: backup + delete legacy data
- `backend/calledit-backend/handlers/verification/recategorize.py` — NEW: re-categorization pipeline
- `frontend/src/utils/verifiabilityCategories.ts` — 3-category labels
- `frontend/src/components/StreamingCall.tsx` — 3-category display
- `frontend/src/components/ListPredictions.tsx` — 3-category display

### Remaining Work

- Optional property-based tests (tasks marked with `*` in tasks.md)
- Real-world testing of `recategorize.py` with actual `automatable` predictions
- Future: user context profiles to shrink `human_only` bucket
- Future: tool-finding agent that uses `automatable` as its work queue
