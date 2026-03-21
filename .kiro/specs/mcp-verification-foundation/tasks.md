# Implementation Plan: MCP Verification Foundation

> **⚠️ SUPERSEDED — DO NOT IMPLEMENT**
>
> This spec was split into two focused specs per Decision 64 (March 20, 2026):
> - **Spec A1** (`verification-teardown-docker`): Infrastructure teardown + Docker Lambda — see `.kiro/specs/verification-teardown-docker/`
> - **Spec A2** (`mcp-tool-integration`): MCP Manager + tool-aware agents — to be created
>
> Tasks 1-3 and 9 are covered by Spec A1. Tasks 4-8 and 10-17 will be covered by Spec A2.
> This spec is kept for reference only. Do not execute any tasks from this file.

## Overview

Replace the DynamoDB-based tool registry with MCP-native tool discovery, make agents tool-aware, tear down the old verification system, and switch to Docker-based Lambda. Implementation follows a risk-minimizing order: teardown first (removes dead code), then new code (MCP Manager), then wiring (graph + agents + prompts), then infrastructure (Docker Lambda, env vars), then tests, then docs, then version bump.

## Tasks

- [ ] 1. Tear down old verification system — SAM template
  - [ ] 1.1 Remove old verification resources from SAM template
    - Remove `VerificationFunction` Lambda resource and its `ScheduledVerification` EventBridge event
    - Remove `VerificationLogsBucket` S3 bucket resource
    - Remove `VerificationNotificationTopic` SNS topic resource
    - Remove `NotificationManagementFunction` Lambda resource (depends on removed SNS topic)
    - Remove corresponding Outputs: `VerificationFunctionArn`, `VerificationLogsBucket`, `VerificationNotificationTopic`
    - Verify no remaining `!Ref` or `!GetAtt` references to removed resources
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [ ] 2. Tear down old verification system — code archive
  - [ ] 2.1 Archive verification handler directory
    - Move `backend/calledit-backend/handlers/verification/` to `docs/historical/verification-v1/`
    - Archive `backend/calledit-backend/handlers/strands_make_call/tool_registry.py` to `docs/historical/verification-v1/tool_registry.py` with a header comment explaining replacement by MCP-native discovery
    - _Requirements: 6.1, 4.3, 4.4_
  - [ ] 2.2 Create archive README
    - Create `docs/historical/verification-v1/README.md` documenting what the old system did, all 19 files it contained (`app.py`, `verification_agent.py`, `verify_predictions.py`, `ddb_scanner.py`, `status_updater.py`, `s3_logger.py`, `email_notifier.py`, `verification_result.py`, `web_search_tool.py`, `seed_web_search_tool.py`, `error_handling.py`, `cleanup_predictions.py`, `inspect_data.py`, `mock_strands.py`, `modernize_data.py`, `recategorize.py`, `test_scanner.py`, `test_verification_result.py`, `requirements.txt`), plus `tool_registry.py`
    - Reference Decisions 18, 19, 20, and Backlog item 7 as context for the replacement
    - Explain that MCP-native tool discovery (Spec A) replaces the DDB tool registry
    - _Requirements: 6.2, 6.3, 6.4_

- [ ] 3. Checkpoint — Verify teardown is clean
  - Ensure SAM template has no dangling references to removed resources
  - Ensure all archived files are in `docs/historical/verification-v1/`
  - Ensure `tool_registry.py` is removed from `handlers/strands_make_call/`
  - Ask the user if questions arise.

- [ ] 4. Build MCP Manager module
  - [ ] 4.1 Create `mcp_manager.py` in `handlers/strands_make_call/`
    - Implement `MCPManager` class with `_initialize()`, `_build_manifest()`, `get_tool_manifest()`, `get_mcp_clients()`, `get_mcp_tools()`, `shutdown()`
    - Configure 3 MCP servers: `@modelcontextprotocol/server-fetch`, `@nicobailon/mcp-brave-search`, `@nicobailon/mcp-playwright`
    - Use `strands.mcp.MCPClient` with `StdioServerParameters` for stdio transport
    - Read `BRAVE_API_KEY` from `os.environ` (not hardcoded)
    - Implement graceful degradation: log and skip failed servers, return empty manifest if all fail
    - Create module-level singleton `mcp_manager = MCPManager()` for Lambda INIT caching
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

- [ ] 5. Wire MCP Manager into prediction graph
  - [ ] 5.1 Update `prediction_graph.py` to use MCP Manager
    - Replace `from tool_registry import read_active_tools, build_tool_manifest` with `from mcp_manager import mcp_manager`
    - Replace `tools = read_active_tools()` / `tool_manifest = build_tool_manifest(tools)` with `tool_manifest = mcp_manager.get_tool_manifest()`
    - Pass `tool_manifest` to `create_verification_builder_agent(tool_manifest)` (new parameter)
    - _Requirements: 4.1, 4.2, 2.1, 3.1_

- [ ] 6. Update Verification Builder agent factory
  - [ ] 6.1 Add `tool_manifest` parameter to `create_verification_builder_agent()`
    - Add `tool_manifest: str = ""` parameter to the factory function signature
    - Pass `tool_manifest` to `fetch_prompt("vb", variables={"tool_manifest": manifest_text})` matching the categorizer pattern
    - Add `AVAILABLE TOOLS:\n{tool_manifest}` section to the bundled `VERIFICATION_BUILDER_SYSTEM_PROMPT` fallback constant
    - _Requirements: 3.2, 3.3, 3.4, 8.6_

- [ ] 7. Update Prompt Management — VB v3 with `{{tool_manifest}}`
  - [ ] 7.1 Update VB prompt in `infrastructure/prompt-management/template.yaml`
    - Add `{{tool_manifest}}` to `InputVariables` list on the VB prompt
    - Add `AVAILABLE TOOLS:` section to VB prompt text referencing `{{tool_manifest}}`
    - Add instructions to use specific tool names in `source` and `steps` fields
    - Add instructions to note "tool not currently available" for `automatable` predictions
    - Add `VBPromptVersionV3` resource with description referencing MCP tool awareness
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 8. Checkpoint — Verify agent wiring is complete
  - Ensure `prediction_graph.py` imports from `mcp_manager`, not `tool_registry`
  - Ensure `create_verification_builder_agent()` accepts `tool_manifest` parameter
  - Ensure VB prompt template has `{{tool_manifest}}` input variable
  - Ask the user if questions arise.

- [ ] 9. Docker Lambda infrastructure change
  - [ ] 9.1 Create Dockerfile for MakeCallStreamFunction
    - Base image: Python 3.12 Lambda base image
    - Install Node.js (for `npx` to run MCP servers as subprocesses)
    - Install Python dependencies from `handlers/strands_make_call/requirements.txt`
    - Copy handler code
    - Set CMD to the Lambda handler
    - _Requirements: 7.3, 7.4_
  - [ ] 9.2 Update SAM template for Docker-based Lambda
    - Change `MakeCallStreamFunction` from `Runtime: python3.12` + `CodeUri` + `Handler` to `PackageType: Image` with `Metadata.DockerContext` and `Metadata.Dockerfile`
    - Retain existing `Timeout: 300`, `MemorySize: 512`, `AutoPublishAlias: live`, `SnapStart`, environment variables, and policies
    - _Requirements: 7.3_

- [ ] 10. Update SAM template environment variables
  - [ ] 10.1 Add `BRAVE_API_KEY` to MakeCallStreamFunction
    - Add `BRAVE_API_KEY` environment variable to `MakeCallStreamFunction` (placeholder value for initial development, sourced from SSM Parameter Store in production)
    - _Requirements: 7.1_

- [ ] 11. Checkpoint — Verify infrastructure changes
  - Ensure Dockerfile builds successfully with both Python 3.12 and Node.js
  - Ensure SAM template is valid with `PackageType: Image`
  - Ensure `BRAVE_API_KEY` env var is present on MakeCallStreamFunction
  - Ask the user if questions arise.


- [ ] 12. Write tests
  - [ ] 12.1 Create `test_mcp_manager.py` in `backend/calledit-backend/tests/strands_make_call/`
    - Create test directory `backend/calledit-backend/tests/strands_make_call/` with `__init__.py` and `conftest.py`
    - Write unit tests: MCPManager initialization with 3 servers, all-fail returns empty manifest, BRAVE_API_KEY read from env, manifest format contains tool names and descriptions
    - Mock `MCPClient` to avoid real subprocess spawning — return configurable tool lists or raise exceptions
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [ ]* 12.2 Write property test: Tool aggregation preserves all tools (Property 1)
    - **Property 1: Tool aggregation preserves all tools**
    - For any set of MCP servers each returning a list of tools, the aggregated list contains every tool from every successfully connected server
    - Use Hypothesis with `st.lists(st.fixed_dictionaries({"name": st.text(min_size=1), "description": st.text(min_size=1)}))` generators
    - **Validates: Requirements 1.3**

  - [ ]* 12.3 Write property test: Partial server failure preserves surviving tools (Property 2)
    - **Property 2: Partial server failure preserves surviving tools**
    - For any subset of MCP servers that fail, the tool list contains exactly the tools from servers that succeeded
    - Use Hypothesis with `st.lists(st.booleans(), min_size=3, max_size=3)` for failure masks
    - **Validates: Requirements 1.5, 1.6**

  - [ ]* 12.4 Write property test: Manifest contains all tool names and descriptions (Property 3)
    - **Property 3: Manifest contains all tool names and descriptions**
    - For any list of tools with names and descriptions, `get_tool_manifest()` output contains every name and description as substrings
    - Use Hypothesis with `st.lists(st.tuples(st.text(min_size=1, alphabet=st.characters(whitelist_categories=('L', 'N'))), st.text(min_size=1, alphabet=st.characters(whitelist_categories=('L', 'N')))))` generators
    - **Validates: Requirements 1.7**

  - [ ]* 12.5 Write property test: VB factory passes tool manifest through to prompt (Property 4)
    - **Property 4: VB factory passes tool manifest through to prompt**
    - For any non-empty tool manifest string, `create_verification_builder_agent(tool_manifest=manifest)` produces an agent whose system prompt contains the manifest
    - Mock `fetch_prompt` to use bundled fallback, verify manifest appears in `agent.system_prompt`
    - **Validates: Requirements 3.2, 8.6**

  - [ ]* 12.6 Write property test: SAM template resource references are internally consistent (Property 5)
    - **Property 5: SAM template resource references are internally consistent**
    - Parse the updated SAM template YAML, extract all `!Ref` and `!GetAtt` targets, verify each referenced resource exists in the Resources section
    - Deterministic test (single template), verifies no dangling references to removed resources
    - **Validates: Requirements 5.6**

  - [ ]* 12.7 Write unit tests for VB agent factory and prediction graph wiring
    - Test `create_verification_builder_agent(tool_manifest="- fetch: ...")` creates agent with manifest in prompt
    - Test `prediction_graph.py` imports from `mcp_manager`, not `tool_registry`
    - Test SAM template does not contain `VerificationFunction`, `VerificationLogsBucket`, `VerificationNotificationTopic`, `NotificationManagementFunction`
    - Test SAM template `MakeCallStreamFunction` has `BRAVE_API_KEY` env var
    - Test archive README contains all 19 filenames and references Decisions 18, 19, 20 and Backlog item 7
    - Test VB prompt template in Prompt Management has `{{tool_manifest}}` input variable
    - _Requirements: 3.2, 4.1, 5.1, 5.2, 5.3, 5.5, 7.1, 8.1, 8.6_

- [ ] 13. Checkpoint — Ensure all tests pass
  - Run all tests with `/home/wsluser/projects/calledit/venv/bin/python -m pytest backend/calledit-backend/tests/strands_make_call/ -v`
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Decision log and backlog updates
  - [ ] 14.1 Add 3 new decisions to `docs/project-updates/decision-log.md`
    - Decision 64: Replace DDB tool registry with MCP-native tool discovery (references Decisions 19, 20, 57)
    - Decision 65: Starter MCP server stack — fetch, brave-search, playwright (references `docs/research/mcp-verification-pipeline.md`)
    - Decision 66: Teardown of old verification system and what replaced it (references Decisions 18, 19, 20)
    - _Requirements: 9.1, 9.2, 9.3_
  - [ ] 14.2 Update backlog item 7
    - Update `docs/project-updates/backlog.md` item 7 (Verification Pipeline via MCP Tools) to mark Spec A (foundation) as complete
    - Note that Spec B (verification execution agent) and Spec C (eval integration) remain
    - _Requirements: 9.4_

- [ ] 15. Version bump — v3
  - [ ] 15.1 Update CHANGELOG.md with v3 entry
    - Add `## [3.0.0]` entry to `CHANGELOG.md` (v1 = pre-graph, v2 = unified graph, v3 = MCP-powered verification pipeline)
    - Document: MCP Manager module, 3 MCP server connections, tool-aware Categorizer and VB agents, old verification system teardown, Docker-based Lambda, Prompt Management VB v3
    - List removed resources: VerificationFunction, VerificationLogsBucket, VerificationNotificationTopic, NotificationManagementFunction
    - List archived code: `handlers/verification/` → `docs/historical/verification-v1/`, `tool_registry.py` archived
    - _Requirements: all_

- [ ] 16. Final checkpoint — Ensure all tests pass
  - Run full test suite
  - Ensure all tests pass, ask the user if questions arise.

- [ ]* 17. Deploy and validate
  - [ ]* 17.1 Build and deploy with SAM
    - Run `sam build` and `sam deploy` to deploy the updated stack
    - Verify deployment succeeds without errors from missing resource references
    - Verify MCP server connections initialize during Lambda cold start
    - _Requirements: 5.6, 7.4_
  - [ ]* 17.2 Validate end-to-end
    - Send a test prediction via WebSocket and verify the pipeline completes
    - Verify Categorizer and VB agents receive tool manifest in their prompts
    - Verify prompt version manifest shows VB v3
    - _Requirements: 2.2, 3.3, 8.5_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- The user will handle deployment (task 17) — marked optional
- All Python commands must use `/home/wsluser/projects/calledit/venv/bin/python`
- Tests go in `backend/calledit-backend/tests/strands_make_call/`
- `tool_registry.py` is in `handlers/strands_make_call/` (not `handlers/verification/`) — archived separately
