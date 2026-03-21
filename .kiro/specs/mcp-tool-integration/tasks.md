# Implementation Plan: MCP Tool Integration (Spec A2)

## Overview

Wire MCP tool servers into the CalledIt prediction pipeline. Build the MCP Manager module first (foundation), then wire it into the prediction graph, update all 4 agent factories for uniform `tool_manifest` interface, update Prompt Management templates, and add BRAVE_API_KEY to the SAM template. All code is Python, tests use Hypothesis for property-based testing and pytest for unit tests.

## Tasks

- [x] 1. Create MCP Manager module
  - [x] 1.1 Create `backend/calledit-backend/handlers/strands_make_call/mcp_manager.py` with `MCPManager` class
    - Implement `MCP_SERVERS` config dict with fetch, brave_search, playwright entries
    - Implement `MCPManager.__init__()` calling `_initialize()` to connect servers via `MCPClient` + `StdioServerParameters`
    - Implement `_initialize()` with per-server try/except for graceful partial failure
    - Implement `_build_manifest()` producing `"- name: description"` lines from tool list
    - Implement `get_tool_manifest()`, `get_mcp_clients()`, `get_mcp_tools()`, `shutdown()`
    - Instantiate module-level singleton: `mcp_manager = MCPManager()`
    - `BRAVE_API_KEY` read from `os.environ.get("BRAVE_API_KEY", "")` at config time
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11_

  - [ ]* 1.2 Write property test: Tool aggregation with partial failure resilience (Property 1)
    - **Property 1: Tool aggregation with partial failure resilience**
    - Generate random tool lists per server + random failure mask, verify aggregate matches surviving tools
    - Test file: `backend/calledit-backend/tests/test_mcp_manager.py`
    - Mock `MCPClient` to return configurable tool lists or raise exceptions
    - **Validates: Requirements 1.4, 1.6, 1.7**

  - [ ]* 1.3 Write property test: Manifest contains all tool names and descriptions (Property 2)
    - **Property 2: Manifest contains all tool names and descriptions**
    - Generate random tool names/descriptions, verify all appear in manifest string; empty list → empty string
    - Test file: `backend/calledit-backend/tests/test_mcp_manager.py`
    - **Validates: Requirements 1.8**

  - [ ]* 1.4 Write unit tests for MCP Manager
    - Test `MCP_SERVERS` has 3 entries: fetch, brave_search, playwright
    - Test `BRAVE_API_KEY` reads from `os.environ`, not hardcoded
    - Test all-servers-fail returns empty manifest, empty tool list, empty clients
    - Test file: `backend/calledit-backend/tests/test_mcp_manager.py`
    - _Requirements: 1.2, 1.5, 1.7_

- [x] 2. Checkpoint — MCP Manager tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [-] 3. Wire MCP Manager into prediction graph
  - [-] 3.1 Update `backend/calledit-backend/handlers/strands_make_call/prediction_graph.py`
    - Replace `from tool_registry import read_active_tools, build_tool_manifest` try/except block with `from mcp_manager import mcp_manager` and `tool_manifest = mcp_manager.get_tool_manifest()`
    - Pass `tool_manifest` to all 4 agent factories: `create_parser_agent(tool_manifest)`, `create_categorizer_agent(tool_manifest)`, `create_verification_builder_agent(tool_manifest)`, `create_review_agent(tool_manifest)`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 3.2 Write unit tests for prediction graph wiring
    - Verify `mcp_manager` is imported, `tool_registry` is not referenced
    - Verify all 4 factory calls receive `tool_manifest` argument
    - Test file: `backend/calledit-backend/tests/test_mcp_manager.py`
    - _Requirements: 2.1, 2.4_

- [ ] 4. Update all 4 agent factories
  - [ ] 4.1 Update `create_parser_agent()` in `parser_agent.py` to accept `tool_manifest: str = ""`
    - Add parameter for interface consistency; parser does NOT inject it into its prompt
    - _Requirements: 7.1, 7.2_

  - [ ] 4.2 Update `create_verification_builder_agent()` in `verification_builder_agent.py`
    - Add `tool_manifest: str = ""` parameter
    - Add `AVAILABLE TOOLS` section with `{tool_manifest}` placeholder to bundled `VERIFICATION_BUILDER_SYSTEM_PROMPT`
    - Add tool-referencing instructions (reference tool names in source/steps, note unavailable tools)
    - Pass manifest to `fetch_prompt("vb", variables={"tool_manifest": manifest_text})` on API path
    - Format into bundled prompt on fallback path
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ] 4.3 Update `create_review_agent()` in `review_agent.py`
    - Add `tool_manifest: str = ""` parameter
    - Add `AVAILABLE TOOLS` section with `{tool_manifest}` placeholder to bundled `REVIEW_SYSTEM_PROMPT`
    - Add tool-awareness instructions for reviewing tool choices
    - Pass manifest to `fetch_prompt("review", variables={"tool_manifest": manifest_text})` on API path
    - Format into bundled prompt on fallback path
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 4.4 Write property test: VB factory passes tool manifest through to prompt (Property 3)
    - **Property 3: VB factory passes tool manifest through to prompt**
    - Generate random manifest strings, verify they appear in agent's `system_prompt`
    - Mock `fetch_prompt` to use bundled prompt with variable substitution
    - Test file: `backend/calledit-backend/tests/test_mcp_manager.py`
    - **Validates: Requirements 3.1, 3.2**

  - [ ]* 4.5 Write property test: Categorizer factory preserves tool manifest in prompt (Property 4)
    - **Property 4: Categorizer factory preserves tool manifest in prompt**
    - Generate random manifest strings, verify they appear in agent's `system_prompt`
    - Regression guard — categorizer already has this capability
    - Test file: `backend/calledit-backend/tests/test_mcp_manager.py`
    - **Validates: Requirements 2.4**

  - [ ]* 4.6 Write property test: Review agent factory passes tool manifest through to prompt (Property 5)
    - **Property 5: Review agent factory passes tool manifest through to prompt**
    - Generate random manifest strings, verify they appear in agent's `system_prompt`
    - Mock `fetch_prompt` to use bundled prompt with variable substitution
    - Test file: `backend/calledit-backend/tests/test_mcp_manager.py`
    - **Validates: Requirements 6.1, 6.2**

  - [ ]* 4.7 Write unit tests for agent factory signatures and bundled prompt content
    - Test VB factory accepts `tool_manifest="test"` parameter
    - Test VB bundled prompt contains `AVAILABLE TOOLS` section and `{tool_manifest}` placeholder
    - Test Review factory accepts `tool_manifest="test"` parameter
    - Test Review bundled prompt contains `AVAILABLE TOOLS` section and `{tool_manifest}` placeholder
    - Test Parser factory accepts `tool_manifest="test"` parameter
    - Test file: `backend/calledit-backend/tests/test_mcp_manager.py`
    - _Requirements: 3.1, 3.4, 6.1, 6.4, 7.1_

- [ ] 5. Checkpoint — Agent factory tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Update Prompt Management templates
  - [ ] 6.1 Update VB prompt in `infrastructure/prompt-management/template.yaml`
    - Add `{{tool_manifest}}` input variable to VB prompt's `TemplateConfiguration`
    - Add `AVAILABLE TOOLS` section with `{{tool_manifest}}` to VB prompt text
    - Add tool-referencing instructions to VB prompt text
    - Add `VBPromptVersionV3` resource depending on `VBPromptVersionV2`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ] 6.2 Update Review prompt in `infrastructure/prompt-management/template.yaml`
    - Add `{{tool_manifest}}` input variable to Review prompt's `TemplateConfiguration`
    - Add `AVAILABLE TOOLS` section with `{{tool_manifest}}` to Review prompt text
    - Add tool-awareness instructions for reviewing tool choices
    - Add `ReviewPromptVersionV4` resource depending on `ReviewPromptVersionV3`
    - _Requirements: 6.1, 6.2, 6.4, 6.5_

  - [ ]* 6.3 Write unit tests for Prompt Management templates
    - Test VB prompt template contains `{{tool_manifest}}` input variable and `AVAILABLE TOOLS` section
    - Test Review prompt template contains `{{tool_manifest}}` input variable and `AVAILABLE TOOLS` section
    - Test `VBPromptVersionV3` resource exists and depends on `VBPromptVersionV2`
    - Test `ReviewPromptVersionV4` resource exists and depends on `ReviewPromptVersionV3`
    - Test file: `backend/calledit-backend/tests/test_mcp_manager.py`
    - _Requirements: 4.1, 4.5, 4.6_

- [ ] 7. Add BRAVE_API_KEY to SAM template
  - [ ] 7.1 Update `backend/calledit-backend/template.yaml`
    - Add `BRAVE_API_KEY: "PLACEHOLDER_REPLACE_BEFORE_DEPLOY"` to MakeCallStreamFunction environment variables
    - Verify all existing env vars (`PROMPT_VERSION_PARSER`, `PROMPT_VERSION_CATEGORIZER`, `PROMPT_VERSION_VB`, `PROMPT_VERSION_REVIEW`) remain unchanged
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 7.2 Write unit tests for SAM template
    - Test `BRAVE_API_KEY` present in MakeCallStreamFunction environment variables
    - Test all 4 `PROMPT_VERSION_*` vars still present and unchanged
    - Test file: `backend/calledit-backend/tests/test_mcp_manager.py`
    - _Requirements: 5.1, 5.3_

- [ ] 8. Final checkpoint — All tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All tests go in `backend/calledit-backend/tests/test_mcp_manager.py` — single test file since components are tightly coupled
- All Python commands must use `/home/wsluser/projects/calledit/venv/bin/python`
