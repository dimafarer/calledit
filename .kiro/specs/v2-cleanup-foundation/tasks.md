# Implementation Plan: v2 Cleanup & Foundation

## Overview

Incremental cleanup and refactoring of the CalledIt prediction pipeline, following the dependency order: Dead Code → ReviewAgent Rewrite → Model Upgrade + Prompt Hardening + Parsing Simplification → Response Consolidation → SAM Route Cleanup. Each task preserves v1 behavior. All code should include verbose comments explaining what, why, and alternatives (learning-oriented).

## Tasks

- [x] 1. Dead code cleanup — delete unused node functions from agent files
  - [x] 1.1 Delete `parser_node_function()` from `parser_agent.py`, `categorizer_node_function()` from `categorizer_agent.py`, and `verification_builder_node_function()` from `verification_builder_agent.py`
    - Remove the entire function definitions and any imports used only by those functions
    - Verify that `create_*_agent()` factory functions remain intact and unchanged
    - Run `grep -r "node_function" backend/calledit-backend/handlers/strands_make_call/` to confirm zero results
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 1.2 Write unit tests for dead code removal in `tests/test_dead_code_cleanup.py`
    - Verify `parser_node_function` is not defined in `parser_agent.py` (use AST or import check)
    - Verify `categorizer_node_function` is not defined in `categorizer_agent.py`
    - Verify `verification_builder_node_function` is not defined in `verification_builder_agent.py`
    - Verify no `node_function` string appears in any agent file
    - Verify all existing factory functions (`create_parser_agent`, `create_categorizer_agent`, `create_verification_builder_agent`) still exist and are importable
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Checkpoint — Verify dead code removal
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. ReviewAgent rewrite as factory function
  - [x] 3.1 Rewrite `review_agent.py` — replace `ReviewAgent` class with `create_review_agent()` factory function
    - Delete the `ReviewAgent` class entirely (including `__init__`, `review_prediction`, `generate_improvement_questions`, `regenerate_section`)
    - Delete the stale `from error_handling import safe_agent_call, with_agent_fallback` import
    - Create a `REVIEW_SYSTEM_PROMPT` module-level constant with the meta-analysis prompt (keep the review/improvable-sections focus from the existing class)
    - Create `create_review_agent(callback_handler=None)` factory function that returns a Strands `Agent` configured with the system prompt and optional callback handler
    - Add verbose comments explaining: why factory function over class, why callback_handler is a parameter, how this matches the other 3 agent patterns
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.2 Update Lambda handler (`strands_make_call_graph.py`) to use the new `create_review_agent()` factory function
    - Replace `ReviewAgent` class import with `create_review_agent` import
    - Replace `ReviewAgent(callback_handler=cb).review_prediction(data)` with: create agent via factory, invoke with prompt, parse JSON result
    - Wrap invocation in simple try/except per Strands best practices (no custom wrapper functions)
    - Add verbose comments explaining the invocation pattern and error handling approach
    - _Requirements: 2.5_

  - [ ]* 3.3 Write unit tests for ReviewAgent factory in `tests/test_review_agent_factory.py`
    - Verify `create_review_agent()` returns a Strands `Agent` instance
    - Verify the agent's system prompt contains meta-analysis keywords (e.g., "reviewable_sections", "improvable")
    - Verify `ReviewAgent` class no longer exists in `review_agent.py` (import check)
    - Verify `error_handling` import no longer exists in `review_agent.py` (source text check)
    - Verify `generate_improvement_questions` and `regenerate_section` no longer exist in the module
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6_

- [x] 4. Checkpoint — Verify ReviewAgent rewrite
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Model upgrade and prompt hardening
  - [x] 5.1 Upgrade model ID from Claude 3.5 Sonnet to Claude Sonnet 4 in all four agent factory functions
    - Change `model="anthropic.claude-3-5-sonnet-20241022-v2:0"` to `model="anthropic.claude-sonnet-4-20250514-v1:0"` in `create_parser_agent()`, `create_categorizer_agent()`, `create_verification_builder_agent()`, and `create_review_agent()`
    - If cross-region inference is needed, use `us.anthropic.claude-sonnet-4-20250514-v1:0` prefix
    - Add comments explaining why Sonnet 4 (better instruction following, same tier cost, Strands default)
    - _Requirements: 3.1_

  - [x] 5.2 Harden all four agent system prompts with explicit JSON output instructions
    - Add to each agent's system prompt: "Return ONLY the raw JSON object. Do not wrap in markdown code blocks. Do not include any text before or after the JSON."
    - Replace any existing ambiguous "Return JSON:" phrasing with the explicit instruction
    - Add comments explaining why explicit negative instructions work better than implicit positive ones
    - _Requirements: 3.2_

  - [ ]* 5.3 Write property test for prompt JSON instructions in `tests/test_parse_graph_results.py`
    - **Property 3: All agent prompts contain explicit JSON output instructions**
    - Test that all four factory functions produce agents whose system prompts contain "Return ONLY the raw JSON object" and "Do not wrap in markdown code blocks"
    - **Validates: Requirements 3.2**

- [x] 6. Prompt testing harness (integration test)
  - [x] 6.1 Create prompt testing harness at `tests/test_prompt_json_output.py`
    - Create integration test that invokes each of the 4 agents with representative prediction inputs
    - Run each agent at least 3 times to account for LLM output variance
    - Validate that `json.loads(str(result))` succeeds without regex extraction for each invocation
    - Report per-agent success rates and log raw outputs that fail direct `json.loads()` parsing
    - Mark tests with `@pytest.mark.integration` so they can be run separately from fast unit tests
    - Ensure runnable via `/home/wsluser/projects/calledit/venv/bin/python -m pytest tests/test_prompt_json_output.py -v`
    - Add verbose comments explaining: why 3 runs per agent, why this gates the parsing simplification, what to do if tests fail
    - _Requirements: 3.3, 3.4, 3.7_

- [x] 7. Checkpoint — Verify model upgrade and prompt hardening
  - Ensure all tests pass (including the prompt testing harness against real LLM). Ask the user if questions arise. Do NOT proceed to parsing simplification until the harness passes.

- [x] 8. Simplify JSON parsing in `prediction_graph.py`
  - [x] 8.1 Delete `extract_json_from_text()` and simplify `parse_graph_results()` to single `json.loads()` per agent
    - Delete the `extract_json_from_text()` helper function entirely
    - Replace each agent's parsing block in `parse_graph_results()` with: `json.loads(str(result))` + `JSONDecodeError` fallback with ERROR-level logging
    - Preserve the same fallback default values (prediction_statement → user prompt, verification_date → current local datetime, verifiable_category → "human_verifiable_only", etc.)
    - Add verbose comments explaining: why we can now trust json.loads directly, why ERROR-level logging on parse failure, what the fallback defaults are and why
    - _Requirements: 3.5, 3.6_

  - [ ]* 8.2 Write property test for parsing round-trip in `tests/test_parse_graph_results.py`
    - **Property 4: Simplified parsing round-trip**
    - Use Hypothesis to generate valid JSON strings matching each agent's output schema
    - Verify `json.loads(json.dumps(original))` recovers original field values
    - Verify non-JSON strings produce fallback defaults without raising exceptions
    - **Validates: Requirements 3.5, 3.6**

  - [ ]* 8.3 Write unit tests for parsing edge cases in `tests/test_parse_graph_results.py`
    - Test `parse_graph_results` with clean JSON input → correct parsing
    - Test with non-JSON input → fallback defaults, no exception
    - Test with markdown-wrapped JSON → fallback defaults (no longer rescued by regex)
    - Test with empty string → fallback defaults
    - Test with partial JSON → fallback defaults
    - _Requirements: 3.5, 3.6_

- [x] 9. Checkpoint — Verify parsing simplification
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Consolidate response building into Lambda handler
  - [x] 10.1 Update `execute_prediction_graph()` in `prediction_graph.py` to return only raw agent outputs
    - Remove metadata field additions (`user_timezone`, `current_datetime_utc`, `current_datetime_local`)
    - Remove fallback default logic from `execute_prediction_graph()`
    - Return dict should contain only: `prediction_statement`, `verification_date`, `date_reasoning`, `verifiable_category`, `category_reasoning`, `verification_method`, and optionally `error`
    - Update error return path to also exclude metadata keys
    - Add comments explaining: why raw outputs only, where metadata and fallbacks now live (Lambda handler)
    - _Requirements: 4.1_

  - [x] 10.2 Update Lambda handler (`strands_make_call_graph.py`) to be the single response assembly location
    - Move all metadata field additions (`prediction_date`, `timezone`, `user_timezone`, `local_prediction_date`, `initial_status`) into the Lambda handler
    - Move all fallback default logic into the Lambda handler
    - Ensure there is exactly one code path that builds the `call_response` WebSocket message
    - Preserve the existing wire format exactly (no field additions, removals, or renames)
    - Add comments explaining: why single location for response building, what each metadata field is and where it comes from
    - _Requirements: 4.2, 4.3, 4.4_

  - [ ]* 10.3 Write property test for execute_prediction_graph return keys in `tests/test_response_building.py`
    - **Property 5: execute_prediction_graph returns only agent output fields**
    - Verify returned dict keys are a subset of `{prediction_statement, verification_date, date_reasoning, verifiable_category, category_reasoning, verification_method, error}`
    - Verify no forbidden keys (`user_timezone`, `current_datetime_utc`, `current_datetime_local`) are present
    - **Validates: Requirements 4.1**

  - [ ]* 10.4 Write property test for response assembly wire format in `tests/test_response_building.py`
    - **Property 6: Response assembly preserves wire format**
    - Use Hypothesis to generate valid raw agent outputs and metadata inputs
    - Verify assembled response contains all required wire format fields: `prediction_statement`, `verification_date`, `prediction_date`, `timezone`, `user_timezone`, `local_prediction_date`, `verifiable_category`, `category_reasoning`, `verification_method`, `initial_status`, `date_reasoning`
    - **Validates: Requirements 4.4**

  - [ ]* 10.5 Write unit tests for response building edge cases in `tests/test_response_building.py`
    - Test with complete agent outputs → all wire format fields present
    - Test with missing agent output fields → fallback defaults applied correctly
    - Test that metadata fields are added by Lambda handler (not by execute_prediction_graph)
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 11. Checkpoint — Verify response consolidation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Remove stale SAM routes and HITL WebSocket actions
  - [x] 12.1 Delete stale route and permission resources from `template.yaml`
    - Delete `ImproveSectionRoute` resource
    - Delete `ImprovementAnswersRoute` resource
    - Delete `ImproveSectionFunctionPermission` resource
    - Delete `ImprovementAnswersFunctionPermission` resource
    - Update `WebSocketDeployment` `DependsOn` list to remove references to deleted routes
    - Add YAML comments explaining what was removed and why (learning-oriented)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 12.2 Verify Lambda handler has no routing logic for deleted actions
    - Check `strands_make_call_graph.py` for any `improve_section` or `improvement_answers` action routing
    - Remove any such routing logic if found
    - Ensure handler cleanly ignores unknown actions
    - _Requirements: 5.6_

  - [ ]* 12.3 Write unit tests for SAM route cleanup in `tests/test_sam_route_cleanup.py`
    - Verify `ImproveSectionRoute` not in template.yaml
    - Verify `ImprovementAnswersRoute` not in template.yaml
    - Verify `ImproveSectionFunctionPermission` not in template.yaml
    - Verify `ImprovementAnswersFunctionPermission` not in template.yaml
    - Verify `WebSocketDeployment.DependsOn` does not reference deleted routes
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 13. Final checkpoint — Verify all cleanup complete
  - Ensure all tests pass, ask the user if questions arise.
  - Run full test suite: `/home/wsluser/projects/calledit/venv/bin/python -m pytest tests/ -v`
  - Verify no regressions in existing functionality.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation — do not skip ahead past a failing checkpoint
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The prompt testing harness (task 6) is the gate for parsing simplification (task 8) — do not simplify parsing until the harness passes
- All code should include verbose comments explaining what, why, and alternatives per the user's learning goals
- All Python commands must use the venv at `/home/wsluser/projects/calledit/venv`
