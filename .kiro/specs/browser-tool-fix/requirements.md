# Requirements Document

## Introduction

The AgentCore Browser tool works when invoked from the local machine (via Kiro MCP powers and direct boto3 calls) but fails silently inside the deployed AgentCore Runtime container with "unavailable due to access restrictions." Code Interpreter works fine in the same container with the same execution role. IAM permissions for Browser have been added (Decision 144) and the agent was relaunched with no change. The Browser tool has a two-layer architecture: Layer 1 (API) uses boto3 to call bedrock-agentcore data plane APIs (same as Code Interpreter), and Layer 2 (WebSocket + Playwright) creates a SigV4-signed WebSocket URL and connects via Playwright CDP — a layer Code Interpreter does not have. The failure is suspected in Layer 2.

This feature covers: (1) building a minimal Browser PoC agent to isolate the failure, (2) diagnosing and fixing the root cause, (3) making verification tools configurable so Browser and Brave Search can coexist and be switched, (4) integrating the fix back into the verification agent, and (5) validating with eval runs.

## Glossary

- **Browser_Tool**: The Strands `AgentCoreBrowser` wrapper that provides web browsing capability via the AgentCore Browser service. Uses a two-layer architecture: Layer 1 (boto3 API calls to `bedrock-agentcore`) and Layer 2 (SigV4-signed WebSocket + Playwright CDP connection).
- **Brave_Search_Tool**: The custom `brave_web_search` Strands tool that uses the Brave Search REST API for web search. Current workaround for Browser_Tool failure (Decision 145).
- **Browser_PoC_Agent**: A minimal AgentCore agent (`browser-poc/`) that does one thing: start a Browser session, navigate to a URL, and return the page title. No LLM, no other tools, no DDB. Fully instrumented with logging.
- **Verification_Agent**: The AgentCore-deployed agent (`calleditv4-verification/`) that reads a prediction bundle from DDB, gathers evidence via web tools and Code Interpreter, and produces a verdict.
- **Tool_Config**: The configuration mechanism that controls which verification tools (Browser_Tool, Brave_Search_Tool, or both) are active in the Verification_Agent at runtime.
- **AgentCore_Runtime**: The deployed container environment where agents run after `agentcore launch`. Uses an execution role for AWS API access.
- **Execution_Role**: The IAM role `AmazonBedrockAgentCoreSDKRuntime-us-west-2-37c792a758` assumed by the Verification_Agent in the AgentCore_Runtime.
- **Layer_1**: The boto3-based API layer of Browser_Tool that calls `start_browser_session` and other bedrock-agentcore data plane APIs.
- **Layer_2**: The WebSocket + Playwright layer of Browser_Tool that generates SigV4-signed WebSocket headers and connects via Chrome DevTools Protocol (CDP).
- **Unified_Pipeline**: The single eval runner (`eval/unified_eval.py`) that orchestrates creation → verification → evaluation → report.
- **Code_Interpreter_Tool**: The Strands `AgentCoreCodeInterpreter` wrapper that provides code execution capability. Works correctly in the AgentCore_Runtime (used as a control comparison).
- **Creation_Agent**: The AgentCore-deployed agent (`calleditv4/`) that receives a raw prediction, runs a 3-turn streaming flow (parse → plan → review), and saves a prediction bundle to DDB. Does not execute verification tools, but needs to know which tools the Verification_Agent has so the planner and reviewer reference the correct tools by name.

## Requirements

### Requirement 1: Minimal Browser PoC Agent

**User Story:** As a developer, I want a minimal PoC agent that exercises only the Browser tool in isolation, so that I can diagnose whether the failure is in the Browser tool itself or in the verification agent's environment.

#### Acceptance Criteria

1. THE Browser_PoC_Agent SHALL be a standalone AgentCore agent in the `browser-poc/` directory with its own `.bedrock_agentcore.yaml`, `pyproject.toml`, and entrypoint.
2. WHEN invoked with a payload containing a `url` field, THE Browser_PoC_Agent SHALL start a Browser session, navigate to the specified URL, and return the page title and a success indicator.
3. THE Browser_PoC_Agent SHALL log each step of the Browser_Tool lifecycle: session creation request, session creation response, WebSocket header generation, Playwright CDP connection attempt, navigation request, navigation response, and session cleanup.
4. IF any step of the Browser_Tool lifecycle fails, THEN THE Browser_PoC_Agent SHALL log the full exception with stack trace, the step that failed, and any available error details (HTTP status, error message, response body).
5. THE Browser_PoC_Agent SHALL not use an LLM, Brave_Search_Tool, Code_Interpreter_Tool, or DynamoDB. The agent SHALL use only the Browser_Tool.
6. THE Browser_PoC_Agent SHALL use the same Execution_Role as the Verification_Agent.

### Requirement 2: Local vs Deployed Diagnosis

**User Story:** As a developer, I want to compare Browser tool behavior between local (`agentcore dev`) and deployed (`agentcore launch`) execution, so that I can isolate whether the failure is environment-specific.

#### Acceptance Criteria

1. WHEN the Browser_PoC_Agent is run locally via `agentcore dev`, THE Browser_PoC_Agent SHALL log the credential source (environment variables, instance profile, or assumed role) and the AWS region used for Browser_Tool API calls.
2. WHEN the Browser_PoC_Agent is run in the AgentCore_Runtime via `agentcore launch`, THE Browser_PoC_Agent SHALL log the same credential and region information for comparison.
3. THE Browser_PoC_Agent SHALL log all environment variables with the prefix `AWS_` (excluding secret values) at startup to enable comparison between local and deployed environments.
4. IF the Browser_Tool fails in the AgentCore_Runtime but succeeds locally, THEN THE Browser_PoC_Agent logs SHALL contain sufficient detail to identify the divergence point (Layer_1 API failure vs Layer_2 WebSocket/Playwright failure).

### Requirement 3: Root Cause Fix

**User Story:** As a developer, I want the root cause of the Browser tool failure in the AgentCore Runtime to be identified and fixed, so that Browser can be used reliably in deployed agents.

#### Acceptance Criteria

1. WHEN the root cause is identified, THE fix SHALL be documented in the decision log with the diagnosis, the fix applied, and verification that the fix works in the AgentCore_Runtime.
2. AFTER the fix is applied, THE Browser_PoC_Agent SHALL successfully navigate to `https://en.wikipedia.org/wiki/Main_Page` and return the page title when running in the AgentCore_Runtime.
3. IF the root cause is an IAM permission gap, THEN THE fix SHALL be added to `infrastructure/agentcore-permissions/setup_agentcore_permissions.sh` so the permission is applied on re-runs.
4. IF the root cause is a missing dependency (Playwright, nest-asyncio, or other), THEN THE fix SHALL be added to the `pyproject.toml` dependencies of both the Browser_PoC_Agent and the Verification_Agent.
5. IF the root cause is a network or runtime environment limitation that cannot be fixed, THEN THE diagnosis SHALL be documented and the Brave_Search_Tool SHALL remain the primary web tool with Browser_Tool marked as unsupported in the AgentCore_Runtime.

### Requirement 4: Configurable Verification Tools

**User Story:** As a developer, I want to configure which web verification tools (Browser, Brave Search, or both) are active in the Verification Agent, so that I can switch between them or use both without code changes.

#### Acceptance Criteria

1. THE Verification_Agent SHALL read a `VERIFICATION_TOOLS` environment variable at startup to determine which web tools to activate.
2. WHEN `VERIFICATION_TOOLS` is set to `browser`, THE Verification_Agent SHALL include only Browser_Tool (and Code_Interpreter_Tool and current_time) in the agent's tool list.
3. WHEN `VERIFICATION_TOOLS` is set to `brave`, THE Verification_Agent SHALL include only Brave_Search_Tool (and Code_Interpreter_Tool and current_time) in the agent's tool list.
4. WHEN `VERIFICATION_TOOLS` is set to `both`, THE Verification_Agent SHALL include Browser_Tool and Brave_Search_Tool (and Code_Interpreter_Tool and current_time) in the agent's tool list.
5. WHEN `VERIFICATION_TOOLS` is not set or is empty, THE Verification_Agent SHALL default to `brave` (maintaining current behavior as a safe fallback).
6. THE Verification_Agent SHALL log which tools are active at startup, including the value of `VERIFICATION_TOOLS` that was read.
7. IF `VERIFICATION_TOOLS` contains an unrecognized value, THEN THE Verification_Agent SHALL log a warning and fall back to `brave`.

### Requirement 5: Browser Integration into Verification Agent

**User Story:** As a developer, I want Browser wired back into the verification agent using the configurable tool system, so that the agent can use Browser for web evidence gathering once the fix is deployed.

#### Acceptance Criteria

1. WHEN `VERIFICATION_TOOLS` includes Browser_Tool, THE Verification_Agent SHALL initialize `AgentCoreBrowser(region="us-west-2")` and include its `.browser` method in the tool list.
2. WHEN `VERIFICATION_TOOLS` includes Brave_Search_Tool, THE Verification_Agent SHALL initialize `brave_web_search` and include it in the tool list.
3. THE Verification_Agent SHALL pass the configured tool list to the Strands Agent constructor, replacing the current hardcoded TOOLS list.
4. WHEN the Verification_Agent is relaunched with `VERIFICATION_TOOLS=browser`, THE Verification_Agent SHALL use Browser_Tool for all web evidence gathering instead of Brave_Search_Tool.
5. WHEN the Verification_Agent is relaunched with `VERIFICATION_TOOLS=both`, THE Verification_Agent SHALL make both Browser_Tool and Brave_Search_Tool available, allowing the LLM to choose which tool to use per query.

### Requirement 6: Smoke Test with Browser

**User Story:** As a developer, I want to run the two previously-failing eval cases (base-013 Wikipedia references, dyn-rec-003 Wikipedia accessibility) with Browser enabled, so that I can confirm Browser works for real verification tasks.

#### Acceptance Criteria

1. WHEN the Verification_Agent is deployed with `VERIFICATION_TOOLS=browser`, THE Unified_Pipeline SHALL be able to run case `base-013` (Wikipedia references) through the full creation → verification → evaluation flow.
2. WHEN the Verification_Agent is deployed with `VERIFICATION_TOOLS=browser`, THE Unified_Pipeline SHALL be able to run case `dyn-rec-003` (Wikipedia accessibility) through the full creation → verification → evaluation flow.
3. THE smoke test results for both cases SHALL produce a non-error verdict (confirmed, refuted, or inconclusive with valid reasoning), not a tool failure or "unavailable due to access restrictions" error.
4. IF either smoke test case fails due to Browser_Tool errors, THEN THE failure details SHALL be logged with full stack traces for further diagnosis.

### Requirement 7: Full Eval Suite Validation

**User Story:** As a developer, I want to run the full unified eval pipeline with Browser enabled, so that I can establish a new baseline and confirm Browser does not regress other cases.

#### Acceptance Criteria

1. WHEN the smoke tests pass, THE Unified_Pipeline SHALL be run with the full merged Golden_Dataset (static + dynamic, all qualifying cases) using `VERIFICATION_TOOLS=browser`.
2. THE full eval run SHALL produce a Unified_Report with creation metrics, verification metrics, and calibration metrics.
3. THE full eval results SHALL be compared against the current baseline (IP=0.89, PQ=0.88, VA=0.89, CA≈0.91 with 23 cases) to identify any regressions or improvements.
4. IF the full eval results show a regression of more than 0.05 in any headline metric (IP, PQ, VA, CA) compared to the current baseline, THEN THE regression SHALL be investigated and documented before Browser is made the default tool.
5. WHEN the full eval completes without significant regression, THE results SHALL be recorded as the new baseline in the project updates.

### Requirement 9: Creation Agent Tool Synchronization

**User Story:** As a developer, I want the creation agent to have the same tool awareness as the verification agent, so that the verification planner writes plans referencing the correct tools and the plan reviewer scores verifiability accurately against the actual tool set.

#### Acceptance Criteria

1. THE Creation_Agent SHALL read the `VERIFICATION_TOOLS` environment variable at startup to determine which web tools the Verification_Agent has access to.
2. WHEN `VERIFICATION_TOOLS` is set to `browser`, THE Creation_Agent's `_get_tool_manifest()` SHALL return a manifest describing Browser_Tool (not Brave_Search_Tool) alongside Code_Interpreter_Tool and current_time.
3. WHEN `VERIFICATION_TOOLS` is set to `brave`, THE Creation_Agent's `_get_tool_manifest()` SHALL return a manifest describing Brave_Search_Tool (not Browser_Tool) alongside Code_Interpreter_Tool and current_time.
4. WHEN `VERIFICATION_TOOLS` is set to `both`, THE Creation_Agent's `_get_tool_manifest()` SHALL return a manifest describing both Browser_Tool and Brave_Search_Tool alongside Code_Interpreter_Tool and current_time.
5. WHEN `VERIFICATION_TOOLS` is not set or is empty, THE Creation_Agent SHALL default to `brave` (matching the Verification_Agent's default behavior from Requirement 4.5).
6. THE Creation_Agent's `TOOLS` list (passed to the Strands Agent constructor) SHALL include the tool callables matching the configured `VERIFICATION_TOOLS` value, so that the LLM sees the correct tool schemas during the planning and review turns.
7. THE Creation_Agent's `SIMPLE_PROMPT_SYSTEM` (backward compatibility mode) SHALL describe the tools matching the configured `VERIFICATION_TOOLS` value, not a hardcoded tool list.
8. IF `VERIFICATION_TOOLS` contains an unrecognized value, THEN THE Creation_Agent SHALL log a warning and fall back to `brave` (matching the Verification_Agent's fallback behavior from Requirement 4.7).
9. WHEN `VERIFICATION_TOOLS` is changed, both the Creation_Agent and the Verification_Agent SHALL be relaunched with the new value for the change to take effect.
10. FOR ALL valid `VERIFICATION_TOOLS` values, THE Creation_Agent's tool manifest and TOOLS list SHALL reference the same set of web tools as the Verification_Agent's tool list (tool set equivalence property).

### Requirement 8: Documentation and Decision Logging

**User Story:** As a developer, I want all diagnosis findings, fixes, and configuration changes documented in the project's decision log and updates, so that the investigation trail is preserved.

#### Acceptance Criteria

1. WHEN the root cause is identified, THE decision log SHALL be updated with a new decision entry documenting the diagnosis, root cause, and fix applied.
2. WHEN the configurable tool system is implemented, THE decision log SHALL be updated with a new decision entry documenting the configuration mechanism and default behavior.
3. WHEN the full eval baseline is established with Browser, THE project updates SHALL include a new update entry with the eval results and comparison to the previous baseline.
4. THE backlog item 17 (Browser debug) SHALL be marked as resolved with a reference to the decision log entries.
