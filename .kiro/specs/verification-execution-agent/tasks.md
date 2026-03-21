# Implementation Plan: Verification Executor Agent (Spec B1)

## Overview

Create the verification executor agent module at `backend/calledit-backend/handlers/strands_make_call/verification_executor_agent.py` and its test file. The module contains: the system prompt constant, a factory function that wires MCP tools from the existing `mcp_manager` singleton, a module-level singleton, and the `run_verification()` entry point that orchestrates invocation, JSON parsing, output validation, and error handling. All code is Python, tests use Hypothesis for property-based testing and pytest for unit tests.

## Tasks

- [x] 1. Create verification executor agent module
  - [x] 1.1 Create `backend/calledit-backend/handlers/strands_make_call/verification_executor_agent.py` with system prompt and factory
    - Define `VERIFICATION_EXECUTOR_SYSTEM_PROMPT` constant (~25 lines, from design doc)
    - Implement `create_verification_executor_agent(model_id=None)` factory function
    - Factory calls `mcp_manager.get_mcp_tools()` and passes tool objects to `Agent(tools=[...])`
    - If empty tool list, agent operates in reasoning-only mode (no tools kwarg or empty list)
    - Use model `us.anthropic.claude-sonnet-4-20250514-v1:0` as default
    - Follow same factory pattern as `verification_builder_agent.py` and `review_agent.py`
    - Create module-level singleton: `verification_executor_agent = create_verification_executor_agent()`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.1, 4.2, 4.4, 5.1, 5.2, 5.4_

  - [x] 1.2 Implement `run_verification(prediction_record: dict) -> dict` entry point in the same module
    - Extract `verification_method`, `prediction_statement`, `verifiable_category` from record
    - If `verification_method` is missing, None, or empty dict → return immediate inconclusive
    - Build user prompt using `.replace()` substitution (Decision 72), not `.format()`
    - Invoke `verification_executor_agent(user_prompt)` and parse JSON response with `json.loads()` + try/except (Decision 4)
    - Validate output fields: `status` in `{"confirmed", "refuted", "inconclusive"}`, `confidence` clamped to `[0.0, 1.0]`, `evidence` is list, `reasoning` is non-empty string, `tools_used` is list
    - Add `verified_at` ISO 8601 UTC timestamp
    - Catch all exceptions — never raises, always returns valid inconclusive outcome on error
    - _Requirements: 1.6, 1.7, 1.8, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 3.5, 4.3_

- [x] 2. Checkpoint — Module structure verified
  - Ensure module imports cleanly, ask the user if questions arise.

- [x] 3. Write tests for verification executor
  - [x] 3.1 Create `backend/calledit-backend/tests/test_verification_executor.py` with unit tests
    - Test factory creates Agent with correct model and MCP tools (mock `mcp_manager`)
    - Test system prompt contains required instructions (verdict rules, JSON format, tool invocation)
    - Test system prompt line count is 20-30 lines
    - Test module-level singleton exists and is an Agent instance
    - Test `run_verification()` builds correct user prompt from prediction record (mock agent)
    - Test `run_verification()` passes prediction_statement and verifiable_category to agent
    - Test error scenario: agent raises RuntimeError → returns inconclusive
    - Test error scenario: agent returns markdown-wrapped JSON → returns inconclusive
    - Test error scenario: agent returns empty string → returns inconclusive
    - Test MCP Manager returns empty tool list → agent created without tools
    - Test missing `prediction_statement` → uses empty string fallback
    - Test missing `verifiable_category` → uses `"unknown"` fallback
    - _Requirements: 1.1, 1.2, 1.3, 1.6, 1.7, 1.8, 2.1, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.3, 5.1, 5.2, 5.3_

  - [ ]* 3.2 Write property test: Structural validity of Verification_Outcome (Property 1)
    - **Property 1: Structural validity of Verification_Outcome**
    - Generate random prediction records with valid verification_method → verify output has correct fields/types
    - `status` in `{"confirmed", "refuted", "inconclusive"}`, `confidence` in `[0.0, 1.0]`, `evidence` is list of dicts with `source`/`content`/`relevance` strings, `reasoning` is non-empty string, `verified_at` is valid ISO 8601, `tools_used` is list of strings
    - Mock agent to return valid JSON with random status/confidence values
    - Test file: `backend/calledit-backend/tests/test_verification_executor.py`
    - **Validates: Requirements 1.6, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

  - [ ]* 3.3 Write property test: run_verification never raises (Property 2)
    - **Property 2: run_verification never raises**
    - Generate arbitrary dicts (missing keys, wrong types, None values, random structures) → verify no exceptions raised and output satisfies Property 1 structure
    - Mock agent to randomly return valid JSON, invalid JSON, or raise exceptions
    - Test file: `backend/calledit-backend/tests/test_verification_executor.py`
    - **Validates: Requirements 3.4, 3.5**

  - [ ]* 3.4 Write property test: Missing or empty verification plan yields inconclusive (Property 3)
    - **Property 3: Missing or empty verification plan yields inconclusive**
    - Generate prediction records where `verification_method` is missing, None, or empty dict → verify `status == "inconclusive"` and `reasoning` contains indication of missing plan
    - Agent should NOT be invoked (mock agent and assert not called)
    - Test file: `backend/calledit-backend/tests/test_verification_executor.py`
    - **Validates: Requirements 3.4**

- [x] 4. Final checkpoint — All tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate the 3 correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All tests go in `backend/calledit-backend/tests/test_verification_executor.py`
- All Python commands must use `/home/wsluser/projects/calledit/venv/bin/python`
- Tests mock `mcp_manager` and the Strands `Agent` — no Bedrock or MCP server calls needed
