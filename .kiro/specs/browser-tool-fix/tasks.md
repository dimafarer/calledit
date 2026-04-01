# Implementation Plan: Browser Tool Fix

## Overview

Diagnose and fix the AgentCore Browser tool failure in the deployed runtime, make verification tools configurable via `VERIFICATION_TOOLS` env var, synchronize tool awareness between the creation and verification agents, and validate with eval runs. The approach is: PoC first (diagnose), fix, refactor tool config, wire into both agents, smoke test, full eval, document.

All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`. Commands requiring TTY (`agentcore dev`, `agentcore launch`, `agentcore invoke`) must be run by the user manually.

## Tasks

- [x] 1. Build Browser PoC Agent
  - [x] 1.1 Create `browser-poc/` project structure
    - Create `browser-poc/.bedrock_agentcore.yaml` (use same execution role as verification agent: `AmazonBedrockAgentCoreSDKRuntime-us-west-2-37c792a758`)
    - Create `browser-poc/pyproject.toml` with dependencies: `strands-agents`, `strands-agents-tools`, `bedrock-agentcore-sdk`, `playwright`, `boto3`
    - Create `browser-poc/src/main.py` entrypoint with `BedrockAgentCoreApp`
    - _Requirements: 1.1, 1.5, 1.6_

  - [x] 1.2 Implement PoC diagnostic functions
    - Implement `log_environment()` — log all `AWS_`-prefixed env vars (mask SECRET/TOKEN/SESSION values), detect credential source
    - Implement `filter_aws_env_vars(env_dict)` — pure function that filters and masks env vars (testable)
    - Implement `test_layer1(region)` — call `start_browser_session` via boto3, return session_id
    - Implement `test_layer2(session_id)` — generate SigV4 WebSocket headers, attempt Playwright CDP connect
    - Implement `test_navigation(page, url)` — navigate to URL, return page title
    - Implement `cleanup(session_id)` — call `stop_browser_session`
    - Implement `handler(payload, context)` — orchestrate all steps with independent try/except per step, return `BrowserPocResult` JSON
    - Each step logs success/failure with full stack traces on error
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 2.1, 2.3, 2.4_

  - [x]* 1.3 Write property test for AWS env var filtering (Property 1)
    - **Property 1: AWS environment variable filtering masks secrets**
    - Test file: `browser-poc/tests/test_env_filter.py`
    - Generate random dicts with `hypothesis`, assert only `AWS_`-prefixed keys returned, sensitive values masked
    - **Validates: Requirements 2.3**

  - [x]* 1.4 Write unit tests for PoC models and env filtering
    - Test file: `browser-poc/tests/test_env_filter.py` (append unit tests)
    - Test empty dict, no AWS_ keys, `AWS_REGION` visible, `AWS_SECRET_ACCESS_KEY` masked, `AWS_SESSION_TOKEN` masked, non-AWS keys excluded
    - _Requirements: 2.3_

- [x] 2. Local vs Deployed PoC Testing
  - [x] 2.1 Test PoC locally with `agentcore dev`
    - **User must run**: `cd browser-poc && agentcore dev` then `agentcore invoke --payload '{"url": "https://en.wikipedia.org/wiki/Main_Page"}'`
    - User pastes the output — examine credential source, region, step results
    - _Requirements: 2.1, 2.4_

  - [x] 2.2 Test PoC deployed with `agentcore launch`
    - **User must run**: `cd browser-poc && agentcore launch` then `agentcore invoke --payload '{"url": "https://en.wikipedia.org/wiki/Main_Page"}'`
    - User pastes the output — compare credential chain, env vars, and step results against local run
    - Identify divergence point (Layer 1 vs Layer 2 failure)
    - _Requirements: 2.2, 2.4_

- [x] 3. Checkpoint — PoC diagnosis complete
  - Ensure PoC tests pass, review local vs deployed comparison output. Ask the user if questions arise.
  - The root cause should be identified at this point.

- [x] 4. Root Cause Fix
  - [x] 4.1 Apply the fix based on PoC diagnosis
    - This task is exploratory — the fix depends on what the PoC reveals:
      - If IAM: update `infrastructure/agentcore-permissions/setup_agentcore_permissions.sh`
      - If missing dependency: update `pyproject.toml` in `browser-poc/` and `calleditv4-verification/`
      - If network/runtime limitation: document the limitation, keep Brave Search as primary
    - After applying the fix, **user must re-deploy and re-test**: `cd browser-poc && agentcore launch` then invoke with Wikipedia URL
    - Verify the PoC returns `success: true` with the page title from the deployed runtime
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 4.2 Document root cause in decision log
    - Add Decision 149 to `docs/project-updates/decision-log.md` documenting: diagnosis, root cause, fix applied, verification result
    - _Requirements: 3.1, 8.1_

- [x] 5. Checkpoint — Root cause fixed and documented
  - Ensure the PoC succeeds in the deployed runtime. Ask the user if questions arise.

- [-] 6. Shared Tool Configuration
  - [x] 6.1 Implement `build_tools()` in verification agent
    - Add `build_tools(verification_tools_env: str | None) -> list` to `calleditv4-verification/src/main.py`
    - Read `VERIFICATION_TOOLS` env var: `"browser"` → browser + code_interpreter + current_time; `"brave"` (or None/empty/unrecognized) → brave_web_search + code_interpreter + current_time; `"both"` → all four
    - Replace hardcoded `TOOLS` list with `TOOLS = build_tools(os.environ.get("VERIFICATION_TOOLS"))`
    - Log which tools are active at startup with the env var value
    - Log warning for unrecognized values before falling back to brave
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.1, 5.2, 5.3_

  - [ ]* 6.2 Write property test for tool configuration (Property 2)
    - **Property 2: Tool configuration correctness**
    - Test file: `calleditv4-verification/tests/test_tool_config.py`
    - Generate random strings with `hypothesis`; for `"browser"`, `"brave"`, `"both"` assert correct composition; for all others assert brave default; always assert code_interpreter + current_time present
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.7, 5.1, 5.2**

  - [ ]* 6.3 Write unit tests for `build_tools()`
    - Test file: `calleditv4-verification/tests/test_tool_config.py` (append)
    - Test specific cases: `"browser"`, `"brave"`, `"both"`, `None`, `""`, `"BROWSER"` (case handling), `"invalid"` (warning logged)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.7_

  - [x] 6.4 Implement `build_tools()`, `build_tool_manifest()`, `build_simple_prompt_system()` in creation agent
    - Add all three functions to `calleditv4/src/main.py`
    - `build_tools()` — same logic as verification agent (same env var, same tool mapping)
    - `build_tool_manifest()` — returns human-readable tool descriptions matching configured tools (replaces `_get_tool_manifest()`)
    - `build_simple_prompt_system()` — returns backward-compat system prompt with correct tool descriptions (replaces hardcoded `SIMPLE_PROMPT_SYSTEM`)
    - Replace hardcoded `TOOLS`, `_get_tool_manifest()`, and `SIMPLE_PROMPT_SYSTEM` with calls to these functions
    - Log which tools are active at startup
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.10_

  - [ ]* 6.5 Write property test for creation agent tool sync (Property 3)
    - **Property 3: Creation agent tool set equivalence**
    - Test file: `calleditv4/tests/test_tool_sync.py`
    - Generate random strings with `hypothesis`; for each value call `build_tools()`, `build_tool_manifest()`, `build_simple_prompt_system()`; extract web tool names from each; assert all three sets identical
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.6, 9.7, 9.10**

  - [ ]* 6.6 Write unit tests for `build_tool_manifest()` and `build_simple_prompt_system()`
    - Test file: `calleditv4/tests/test_tool_sync.py` (append)
    - Test `"browser"` → manifest mentions Browser not Brave; `"brave"` → mentions Brave not Browser; `"both"` → mentions both; `None` → defaults to brave; `"invalid"` → defaults to brave
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 9.7_

- [ ] 7. Checkpoint — Tool configuration complete
  - Ensure all tests pass: `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4-verification/tests/test_tool_config.py calleditv4/tests/test_tool_sync.py browser-poc/tests/test_env_filter.py -v`
  - Ask the user if questions arise.

- [x] 8. Relaunch Both Agents with Browser
  - [x] 8.1 Relaunch verification agent with `VERIFICATION_TOOLS=browser`
    - **User must run**: `cd calleditv4-verification && agentcore launch --env VERIFICATION_TOOLS=browser`
    - User pastes output confirming successful launch
    - _Requirements: 5.4_

  - [x] 8.2 Relaunch creation agent with `VERIFICATION_TOOLS=browser`
    - **User must run**: `cd calleditv4 && agentcore launch --env VERIFICATION_TOOLS=browser`
    - User pastes output confirming successful launch
    - _Requirements: 9.9_

- [x] 9. Smoke Test
  - [x] 9.1 Run base-013 and dyn-rec-003 through unified eval
    - Run: `/home/wsluser/projects/calledit/venv/bin/python eval/unified_eval.py --cases base-013,dyn-rec-003`
    - Verify both cases produce non-error verdicts (confirmed, refuted, or inconclusive with valid reasoning)
    - Verify no "unavailable due to access restrictions" errors in output
    - If either case fails due to Browser errors, capture full stack traces for diagnosis
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 10. Full Eval Suite
  - [x] 10.1 Run full unified eval with static + dynamic dataset
    - Run: `/home/wsluser/projects/calledit/venv/bin/python eval/unified_eval.py --dynamic-dataset`
    - Compare results against baseline: IP=0.89, PQ=0.88, VA=0.89, CA≈0.91 (23 cases)
    - If any headline metric regresses by >0.05, investigate before making Browser the default
    - Record results as new baseline
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 11. Documentation
  - [x] 11.1 Update decision log with tool configuration decision
    - Add Decision 150 (or next available) to `docs/project-updates/decision-log.md` documenting the `VERIFICATION_TOOLS` configuration mechanism and default behavior
    - _Requirements: 8.2_

  - [x] 11.2 Create project update 37
    - Create `docs/project-updates/37-project-update-browser-tool-fix.md` with: diagnosis narrative, fix applied, eval results with Browser, comparison to previous baseline
    - Update `docs/project-updates/project-summary.md` with new baseline numbers
    - _Requirements: 8.3_

  - [x] 11.3 Update backlog
    - Mark backlog item 17 (Browser debug) as resolved in `docs/project-updates/backlog.md` with references to Decision 149 and Decision 150
    - _Requirements: 8.4_

- [x] 12. Final checkpoint — All tasks complete
  - Ensure all tests pass, eval results recorded, documentation updated. Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Property tests use `hypothesis` (already installed in venv)
- `agentcore dev`, `agentcore launch`, and `agentcore invoke` require TTY — user must run these manually and paste output
- Task 4 (Root Cause Fix) is intentionally flexible since the fix depends on PoC diagnosis results
- The `browser-poc/` directory does not exist yet — Task 1.1 creates it
- Decision log is at 148, next decision is 149; project updates at 36, next is 37
