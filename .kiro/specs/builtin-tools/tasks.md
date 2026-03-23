# Implementation Plan: Built-in Tools (V4-2)

## Overview

Wire AgentCore Browser and Code Interpreter into the CalledIt v4 agent entrypoint. Install additional dependencies (`playwright`, `nest-asyncio`), update `calleditv4/src/main.py` with tool imports/instantiation/TOOLS list/updated system prompt, write unit tests and one approved property test, then validate manually via the dev server. All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`. The v3 Lambda backend stays untouched (Decision 95).

## Tasks

- [x] 1. Verify tool dependencies are available
  - Confirm `strands-agents-tools` is installed (already present — provides both `AgentCoreBrowser` and `AgentCoreCodeInterpreter`)
  - Verify imports work: `from strands_tools.browser import AgentCoreBrowser` and `from strands_tools.code_interpreter import AgentCoreCodeInterpreter`
  - Note: `playwright` and `nest-asyncio` are NOT needed — `AgentCoreBrowser` communicates with the AWS-hosted Chromium session directly via the AgentCore SDK, not via local Playwright
  - _Requirements: 1.1_

- [x] 2. Update the agent entrypoint with built-in tools
  - [x] 2.1 Update `calleditv4/src/main.py` with tool imports, instantiation, TOOLS list, and updated system prompt
    - Add `import os`
    - Add `from strands_tools.browser import AgentCoreBrowser`
    - Add `from strands_tools.code_interpreter import AgentCoreCodeInterpreter`
    - Add `AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")` at module level
    - Instantiate `browser_tool = AgentCoreBrowser(region=AWS_REGION)` at module level
    - Instantiate `code_interpreter_tool = AgentCoreCodeInterpreter(region=AWS_REGION)` at module level
    - Create `TOOLS = [browser_tool.browser, code_interpreter_tool.code_interpreter]` at module level
    - Update `SYSTEM_PROMPT` to describe both Browser and Code Interpreter capabilities per the design
    - Pass `tools=TOOLS` to the `Agent()` constructor in `handler()`
    - Do NOT change the existing error handling — tool exceptions bubble through the Agent and are caught by the existing `try/except Exception`
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 2.4, 3.4_

- [x] 3. Checkpoint — Verify entrypoint imports work
  - Run `/home/wsluser/projects/calledit/venv/bin/python -c "import sys; sys.path.insert(0, 'calleditv4/src'); from main import TOOLS, browser_tool, code_interpreter_tool; print(f'TOOLS count: {len(TOOLS)}'); print(f'browser_tool type: {type(browser_tool).__name__}'); print(f'code_interpreter_tool type: {type(code_interpreter_tool).__name__}')"` from the project root
  - Expect output showing TOOLS count: 2, correct types
  - If import fails due to missing dependencies, install them and retry
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Write unit tests
  - [x] 4.1 Create `calleditv4/tests/test_builtin_tools.py` with unit tests for tool wiring and configuration
    - Test `TOOLS` list has exactly 2 elements — _Requirements: 1.5_
    - Test each element in `TOOLS` is callable — _Requirements: 1.5_
    - Test `SYSTEM_PROMPT` contains "Browser" — _Requirements: 2.4_
    - Test `SYSTEM_PROMPT` contains "Code Interpreter" — _Requirements: 3.4_
    - Test `AWS_REGION` defaults to `"us-west-2"` — _Requirements: 1.4_
    - Test `browser_tool` is an `AgentCoreBrowser` instance — _Requirements: 1.2_
    - Test `code_interpreter_tool` is an `AgentCoreCodeInterpreter` instance — _Requirements: 1.3_
    - Test missing prompt key still returns error JSON mentioning "prompt" (regression check, unchanged from V4-1) — _Requirements: 1.5_
    - These tests exercise pure logic (importable constants, list structure) — no mocks, no Bedrock calls
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 2.4, 3.4_


  - [x]* 4.2 Write property test for error handling (Property 1) — APPROVED MOCK EXCEPTION
    - **Property 1: Tool exceptions produce structured error responses**
    - **Validates: Requirements 2.5, 3.5**
    - Use Hypothesis `@given(prompt=st.text(min_size=1), error_msg=st.text(min_size=1))` with `@settings(max_examples=100)`
    - Mock `strands.Agent` to raise `Exception(error_msg)` when called — verify `handler()` returns JSON with `"error"` key containing the error message
    - **Decision 96 exception**: This is the ONLY approved mock in v4. The mock is approved because: (a) testing real tool exceptions requires real AWS infrastructure and non-deterministic failures, (b) the property validates the handler's catch-all error path which is pure logic once the exception is raised, (c) the user explicitly approved this mock. No other mocks are permitted anywhere in the test suite.
    - Tag: `Feature: builtin-tools, Property 1: Tool exceptions produce structured error responses`
    - _Requirements: 2.5, 3.5_

- [x] 5. Checkpoint — Run all tests
  - Run `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/test_builtin_tools.py -v` from the project root
  - Also run `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/test_entrypoint.py -v` to verify V4-1 tests still pass (regression)
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Manual validation — Start dev server
  - User runs `cd /home/wsluser/projects/calledit/calleditv4 && agentcore dev` in their terminal
  - Verify the dev server starts successfully with the updated entrypoint
  - This is a manual task — `agentcore dev` requires TTY
  - _Requirements: 1.5, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3_

- [x] 7. Manual validation — Invoke with tool-exercising prompts
  - User runs each command in a separate terminal (with dev server running):
  - Browser — web search (Req 2.2): `agentcore invoke --dev '{"prompt": "Search the web for the current weather in Seattle"}'`
  - Browser — URL navigation (Req 2.1): `agentcore invoke --dev '{"prompt": "Go to https://example.com and tell me what the page says"}'`
  - Code Interpreter — calculation (Req 3.1): `agentcore invoke --dev '{"prompt": "Calculate the compound interest on $10000 at 5% for 10 years"}'`
  - Code Interpreter — date math (Req 3.2): `agentcore invoke --dev '{"prompt": "How many days between January 15, 2024 and March 30, 2025?"}'`
  - Both tools (Req 2.1, 2.2, 3.1): `agentcore invoke --dev '{"prompt": "Look up the current population of Tokyo and calculate what percentage it is of Japan total population of 125 million"}'`
  - Error case — payload validation (Req 1.5): `agentcore invoke --dev '{"not_prompt": "test"}'` — should return error JSON
  - This is a manual task — `agentcore invoke --dev` requires TTY
  - _Requirements: 1.5, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.5_

- [x] 8. IAM permissions checkpoint
  - If any tool invocation in task 7 fails with an access denied error, document the required IAM policy actions:
    - Browser: `bedrock-agentcore:StartBrowserSession`, `bedrock-agentcore:StopBrowserSession`, `bedrock-agentcore:ConnectBrowserAutomationStream`
    - Code Interpreter: `bedrock-agentcore:StartCodeInterpreterSession`, `bedrock-agentcore:InvokeCodeInterpreter`, `bedrock-agentcore:StopCodeInterpreterSession`
  - Add the required permissions to the developer's IAM policy and retry
  - If all invocations succeed, mark this task complete
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Property test (task 4.2) uses the ONLY approved mock in v4 — explicitly approved by the user as a Decision 96 exception. No other mocks are permitted.
- Property 2 (TOOLS list invariant) is implemented as a unit test in task 4.1, not a Hypothesis property test, because the module-level constant is deterministic.
- Tasks 6, 7, and 8 are manual — `agentcore dev` and `agentcore invoke --dev` require TTY and must be run by the user in their terminal
- `playwright` and `nest-asyncio` are NOT needed — `AgentCoreBrowser` communicates with the AWS-hosted Chromium via the AgentCore SDK, not local Playwright. The AgentCore quickstart docs list them for an alternative Playwright-based integration path.
- The v3 Lambda backend is untouched (Decision 95)
- `calleditv4/.venv/` exists but is NOT used — all commands use `/home/wsluser/projects/calledit/venv`
- All pip/python commands use the venv at `/home/wsluser/projects/calledit/venv`
