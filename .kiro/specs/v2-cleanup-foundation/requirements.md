# Requirements Document — Spec 1: v2 Cleanup & Foundation

## Introduction

This spec covers the cleanup and refactoring work needed to prepare the CalledIt prediction pipeline for the v2 unified graph architecture. It addresses dead code, architectural debt, and code organization issues that should be resolved before building new features on top.

All changes in this spec preserve existing v1 behavior — the 3-agent graph (Parser → Categorizer → Verification Builder) continues to work exactly as it does today. The goal is a cleaner, simpler codebase that's ready for Spec 2 (unified graph with stateful refinement).

### Why a Separate Spec

During requirements review for the full v2 feature, we identified that the codebase has accumulated debt from earlier architecture iterations (custom nodes → plain agents, error_handling module deletion, duplicated response building). Mixing cleanup with new feature work in a single spec creates risk: if the new graph topology has issues, you're debugging against a codebase that was also refactored in the same pass. Separating cleanup into its own spec means:

1. Each change is independently deployable and testable
2. v1 behavior is preserved throughout — no regression risk
3. The codebase is clean before Spec 2 adds new complexity
4. From a learning perspective, you understand the existing patterns before extending them

### Relationship to Spec 2

This spec is a prerequisite for `.kiro/specs/v2-unified-graph-refinement/`. Spec 2 assumes the cleanup work here is complete:
- ReviewAgent is a factory function (not a class with HITL methods)
- Dead node functions are gone
- JSON parsing is simplified
- Response building happens in one place
- Stale SAM routes are removed

## Glossary

- **PredictionGraphState**: The TypedDict schema that carries state through the graph
- **Pipeline Agents**: Parser, Categorizer, Verification Builder — the three sequential agents in the current graph
- **ReviewAgent**: The meta-analysis agent that identifies improvable sections in a prediction
- **Lambda_Handler**: The `strands_make_call_graph.py` entry point
- **Node Functions**: The `*_node_function()` functions in agent files — dead code from a previous custom-node architecture
- **HITL Methods**: `generate_improvement_questions()` and `regenerate_section()` in ReviewAgent — v1 improvement loop methods being removed

## Requirements

### Requirement 1: Dead Code Cleanup

**User Story:** As a developer, I want all dead code from previous architecture iterations removed, so that the codebase has a single clear code path with no orphaned functions or stale imports.

**Why this requirement exists:** The codebase has several pieces of dead code left over from the custom-node architecture that was replaced by the plain Agent pattern. These functions are never imported or called, but they add confusion for anyone reading the code — especially someone learning Strands patterns. The `review_agent.py` file also imports a deleted module (`error_handling`), which would crash if anything tried to load it.

**What's dead and why:**
- `parser_node_function()`, `categorizer_node_function()`, `verification_builder_node_function()` — Leftover from a custom-node architecture. The graph uses `create_*_agent()` factory functions; the node functions are never imported or called by any module.
- `review_agent.py` imports `from error_handling import safe_agent_call, with_agent_fallback` — but `error_handling.py` was deleted from `handlers/strands_make_call/` during the January 2026 cleanup. This import would crash on load.

#### Acceptance Criteria

1. THE `parser_node_function()` function SHALL be deleted from `parser_agent.py`.
2. THE `categorizer_node_function()` function SHALL be deleted from `categorizer_agent.py`.
3. THE `verification_builder_node_function()` function SHALL be deleted from `verification_builder_agent.py`.
4. NO agent file SHALL contain functions that are not imported or called by any other module in the codebase.
5. ALL existing tests SHALL continue to pass after dead code removal.

### Requirement 2: ReviewAgent Rewrite as Factory Function

**User Story:** As a developer, I want ReviewAgent refactored from a standalone class with multiple methods to a simple `create_review_agent()` factory function, consistent with the pattern used by the other three agents, so that all agents follow the same pattern and the stale `error_handling` import is eliminated.

**Why this requirement exists:** ReviewAgent is currently a class (`ReviewAgent`) with three methods: `review_prediction()`, `generate_improvement_questions()`, and `regenerate_section()`. The latter two are HITL methods that will be replaced by full graph re-trigger in Spec 2. The class also imports the deleted `error_handling` module. Rewriting it as a factory function now means Spec 2 can simply add it as a graph node without dealing with the broken import or dead methods.

**What changes:**
- Class → factory function (`create_review_agent()`)
- Remove `generate_improvement_questions()` and `regenerate_section()` (HITL methods replaced by graph re-trigger in Spec 2)
- Remove `error_handling` import
- Keep the meta-analysis capability (identify improvable sections)
- System prompt stays focused on review/meta-analysis

**What stays the same:**
- The Lambda handler still calls ReviewAgent standalone (outside the graph) — moving it into the graph is Spec 2's job
- The review output format (reviewable_sections list) stays the same

#### Acceptance Criteria

1. THE ReviewAgent SHALL be refactored from a class to a Strands Agent created by a `create_review_agent()` factory function, matching the pattern of `create_parser_agent()`, `create_categorizer_agent()`, and `create_verification_builder_agent()`.
2. THE `create_review_agent()` function SHALL return an Agent configured with a system prompt focused on meta-analysis: identifying improvable sections and generating questions.
3. THE `generate_improvement_questions()` and `regenerate_section()` methods SHALL be removed.
4. THE stale `from error_handling import safe_agent_call, with_agent_fallback` import SHALL be removed.
5. THE Lambda_Handler SHALL be updated to call the new `create_review_agent()` factory function and invoke the agent directly, replacing the `ReviewAgent` class instantiation.
6. THE review output format SHALL remain unchanged: a JSON object with a `reviewable_sections` list.

### Requirement 3: Model Upgrade, Prompt Hardening, and Simplified JSON Parsing

**User Story:** As a developer, I want to upgrade from Claude 3.5 Sonnet to Claude Sonnet 4, harden agent system prompts to produce clean JSON reliably, validate with a prompt testing harness, and then simplify the parsing code from 120 lines of regex fallbacks to a single `json.loads()` per agent.

**Why this requirement exists:** The current `parse_graph_results()` function in `prediction_graph.py` is ~90 lines of defensive JSON extraction with a ~30-line `extract_json_from_text()` helper that tries 5 different regex strategies to find JSON in agent output. This defensive code exists for a reason — the agents were actually returning malformed output (markdown-wrapped JSON, extra text around the JSON). The current prompts say `Return JSON:` followed by an example, but they don't explicitly prohibit markdown wrapping or extra text. Claude models will often helpfully wrap output in ` ```json ``` ` blocks when they see that pattern.

Additionally, all agents currently use `anthropic.claude-3-5-sonnet-20241022-v2:0` (Claude 3.5 Sonnet v2, October 2024). The Strands SDK default is now Claude Sonnet 4 (`anthropic.claude-sonnet-4-20250514-v1:0`), which has better instruction following — directly relevant to our JSON output problem. Upgrading the model before hardening prompts means we validate against the model we'll actually run in production.

The fix is a four-step approach: (0) upgrade the model, (1) harden the prompts, (2) validate with a testing harness, (3) then simplify the parsing. We don't rip out the safety net until we've proven the new model + new prompts work.

**Root cause analysis:** The current prompts use `Return JSON:` which is ambiguous. Claude interprets this as an invitation to be helpful and wraps the output. The fix is explicit: "Return ONLY the raw JSON object. No markdown, no code blocks, no explanation text before or after." Claude Sonnet 4 follows these explicit negative instructions more reliably than 3.5 Sonnet.

**Why Claude Sonnet 4 (not Haiku, not Opus):** Same Sonnet tier means similar latency and cost — not a jump to Opus pricing. Haiku is too weak for the categorization and verification method generation tasks. Sonnet 4 is the current Strands default, meaning the framework is optimized for it. It also supports `Agent.structured_output()` if we ever want to use it in the future.

**Alternative considered:** Keep `extract_json_from_text()` permanently as a safety net. We rejected this because it masks prompt quality issues and makes debugging harder. But we're not removing it blindly; we're proving the new model + prompts work first.

#### Acceptance Criteria

1. ALL agent factory functions (Parser, Categorizer, Verification Builder, ReviewAgent) SHALL upgrade the model ID from `anthropic.claude-3-5-sonnet-20241022-v2:0` to `anthropic.claude-sonnet-4-20250514-v1:0` (Claude Sonnet 4). If cross-region inference is needed, use `us.anthropic.claude-sonnet-4-20250514-v1:0`.
2. ALL agent system prompts SHALL include explicit JSON output instructions: "Return ONLY the raw JSON object. Do not wrap in markdown code blocks. Do not include any text before or after the JSON."
3. A prompt testing script SHALL be created at `tests/test_prompt_json_output.py` that invokes each agent with representative inputs and validates that `json.loads(str(result))` succeeds without regex extraction — running each agent at least 3 times to account for LLM output variance.
4. THE prompt testing script SHALL report per-agent success rates and log any raw outputs that fail direct `json.loads()` parsing, so prompt issues are visible and debuggable.
5. AFTER the prompt testing script demonstrates reliable clean JSON output (all agents passing direct `json.loads()` on all test runs), THE `extract_json_from_text()` function SHALL be removed from `prediction_graph.py`.
6. THE `parse_graph_results()` function SHALL be simplified to a single `json.loads(str(result))` call per agent result, with a simple fallback to default values on `JSONDecodeError` and ERROR-level logging of the raw output.
7. THE prompt testing script SHALL be runnable via `venv/bin/python -m pytest tests/test_prompt_json_output.py -v` and SHALL be added to the project's test suite for ongoing regression detection.

### Requirement 4: Single Response Building Location

**User Story:** As a developer, I want the WebSocket response to be assembled in one place (the Lambda handler), not split across `execute_prediction_graph()` and `lambda_handler()`, so that there's a single source of truth for what the client receives.

**Why this requirement exists:** Currently, `execute_prediction_graph()` adds metadata fields (`user_timezone`, `current_datetime_utc`, `current_datetime_local`) and applies fallback defaults, then `lambda_handler()` builds a separate `response_data` dict with its own field mapping and additional metadata (`prediction_date`, `timezone`, `local_prediction_date`, `initial_status`). This means two layers of "ensure fields exist" logic in two files. The graph execution function should return raw agent outputs, and the Lambda handler should be the single place that assembles the response.

#### Acceptance Criteria

1. THE `execute_prediction_graph()` function SHALL return only the parsed agent outputs (prediction_statement, verification_date, date_reasoning, verifiable_category, category_reasoning, verification_method) without adding metadata fields or applying fallback defaults.
2. THE Lambda_Handler SHALL be the single location that assembles the `call_response` WebSocket message, adding metadata fields (prediction_date, timezone, user_timezone, local_prediction_date, initial_status) and applying fallback defaults.
3. THERE SHALL be exactly one code path that builds the WebSocket response payload — not two layers of field assembly across different files.
4. THE existing `call_response` message format SHALL remain unchanged — this spec does not change the wire protocol (that's Spec 2's job).

### Requirement 5: Remove Stale SAM Routes and HITL WebSocket Actions

**User Story:** As a developer, I want the `improve_section` and `improvement_answers` WebSocket routes removed from the SAM template, since the HITL methods they routed to are being deleted in this spec.

**Why this requirement exists:** The SAM template defines `ImproveSectionRoute` and `ImprovementAnswersRoute` WebSocket routes that map to the MakeCallStreamFunction. These routes invoke the ReviewAgent's `generate_improvement_questions()` and `regenerate_section()` methods, which are being removed in Requirement 2. The routes and their Lambda permissions should be removed to avoid dead configuration.

**Note:** This spec removes the routes but does NOT add the new `clarify` route — that's Spec 2's job, since the clarify action requires the unified graph with stateful refinement.

#### Acceptance Criteria

1. THE SAM template SHALL remove the `ImproveSectionRoute` WebSocket route resource.
2. THE SAM template SHALL remove the `ImprovementAnswersRoute` WebSocket route resource.
3. THE SAM template SHALL remove the `ImproveSectionFunctionPermission` Lambda permission resource.
4. THE SAM template SHALL remove the `ImprovementAnswersFunctionPermission` Lambda permission resource.
5. THE SAM template deployment stage `DependsOn` list SHALL be updated to remove references to the deleted routes.
6. THE Lambda_Handler SHALL remove any routing logic for the `improve_section` and `improvement_answers` actions.
