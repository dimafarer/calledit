# Project Update 04 — Verifiability Category Simplification & Tool Registry

**Date:** March 13, 2026
**Context:** Simplify verifiability categories from 5 to 3, add tool registry, add web search tool
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/category-simplification/` — Spec 7: Category Simplification & Tool Registry
  - `requirements.md` — IN PROGRESS
  - `design.md` — NOT YET CREATED
  - `tasks.md` — NOT YET CREATED

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

1. Read this update for full context
2. Read `.kiro/specs/category-simplification/` for the spec
3. Execute the spec tasks
4. After completion, proceed to Update 05 (eval framework)
