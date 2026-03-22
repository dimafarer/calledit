# Implementation Plan: AgentCore Foundation (V4-1)

## Overview

Set up the AgentCore project at `/home/wsluser/projects/calledit/calleditv4/`, configure the agent entrypoint with Claude Sonnet 4 and error handling, write unit and property-based tests, then validate manually via the dev server. All commands use the venv at `/home/wsluser/projects/calledit/venv`.

## Tasks

- [x] 1. Install AgentCore starter toolkit
  - Run `/home/wsluser/projects/calledit/venv/bin/pip install bedrock-agentcore-starter-toolkit`
  - Verify the `agentcore` CLI is available in the venv
  - _Requirements: 1.1_

- [x] 2. Scaffold the AgentCore project
  - Run `agentcore create --non-interactive --project-name calleditv4 --template basic --agent-framework Strands --model-provider Bedrock` from `/home/wsluser/projects/calledit/`
  - Verify the `calleditv4/` directory was created with `.bedrock_agentcore.yaml` and the entrypoint file
  - _Requirements: 1.2, 1.3, 1.4_

- [x] 3. Checkpoint — Verify project scaffolding
  - Ensure the generated `.bedrock_agentcore.yaml` contains project name `calleditv4`, template `basic`, agent framework `Strands`, model provider `Bedrock`
  - Ensure the entrypoint file contains `BedrockAgentCoreApp`, `@app.entrypoint`, and `app.run()`
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Modify the agent entrypoint
  - [x] 4.1 Replace the generated entrypoint with the design's `main.py` implementation
    - Set `MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"`
    - Set `SYSTEM_PROMPT` with CalledIt v4 foundation agent placeholder text
    - Add payload validation: return structured error JSON if `"prompt"` key is missing
    - Add try/except around agent invocation: log with `logger.error(..., exc_info=True)`, return structured error JSON
    - Agent created per-invocation (no shared state)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 4.3_

- [x] 5. Write unit tests for the entrypoint
  - [x] 5.1 Create test file `calleditv4/tests/test_entrypoint.py` with unit tests
    - Test that `MODEL_ID` constant equals `us.anthropic.claude-sonnet-4-20250514-v1:0`
    - Test that `SYSTEM_PROMPT` contains "CalledIt v4"
    - Test that empty payload `{}` returns error JSON mentioning "prompt"
    - Test that payload with wrong key `{"message": "hi"}` returns error JSON mentioning "prompt"
    - Test that valid payload passes prompt to mocked Agent and returns string response
    - Mock `strands.Agent` to avoid real Bedrock calls (Decision 78)
    - _Requirements: 2.1, 2.4, 4.3_

  - [x]* 5.2 Write property test: Valid prompt passthrough
    - **Property 1: Valid prompt passthrough**
    - Use `@given(prompt=st.text(min_size=1))` with `@settings(max_examples=100)`
    - Mock `Agent` — assert the mock agent instance is called with the exact prompt string
    - **Validates: Requirements 2.2**

  - [x]* 5.3 Write property test: Response is always a string
    - **Property 2: Response is always a string**
    - Use `@given(prompt=st.text(min_size=1))` with `@settings(max_examples=100)`
    - Mock `Agent` to return various values — assert handler always returns `str`
    - **Validates: Requirements 2.3**

  - [x]* 5.4 Write property test: Agent exceptions produce structured error responses
    - **Property 3: Agent exceptions produce structured error responses**
    - Use `@given(prompt=st.text(min_size=1), error_msg=st.text(min_size=1))` with `@settings(max_examples=100)`
    - Mock `Agent` to raise `Exception(error_msg)` — assert response is JSON with `"error"` key containing the error message
    - **Validates: Requirements 2.5**

  - [x]* 5.5 Write property test: Missing prompt key produces structured error response
    - **Property 4: Missing prompt key produces structured error response**
    - Use `@given(payload=st.dictionaries(st.text().filter(lambda k: k != "prompt"), st.text()))` with `@settings(max_examples=100)`
    - Assert response is JSON with `"error"` key mentioning "prompt", and Agent is never called
    - **Validates: Requirements 4.3**

- [x] 6. Checkpoint — Run all tests
  - Run `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/test_entrypoint.py -v` from the project root
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Manual validation — Start dev server
  - User runs `cd /home/wsluser/projects/calledit/calleditv4 && agentcore dev` in their terminal
  - Verify the dev server starts and logs the local endpoint address
  - Verify hot reload is active (dev server detects file changes)
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 8. Manual validation — Invoke agent
  - User runs `agentcore invoke --dev '{"prompt": "Hello, are you working?"}'` — expect non-empty text response
  - User runs `agentcore invoke --dev '{"prompt": "What model are you running on?"}'` — expect non-empty text response
  - User runs `agentcore invoke --dev '{"not_prompt": "test"}'` — expect structured error response about missing prompt field
  - _Requirements: 4.1, 4.2, 4.3_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Property tests use Hypothesis with `@settings(max_examples=100)`
- Unit tests and property tests mock `strands.Agent` — no real Bedrock API calls (Decision 78)
- Tasks 7 and 8 are manual — `agentcore dev` and `agentcore invoke --dev` must be run by the user in their terminal (TTY requirement)
- All pip/python commands use the venv at `/home/wsluser/projects/calledit/venv`
