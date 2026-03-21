# Requirements Document

## Introduction

Wire MCP (Model Context Protocol) tool servers into the CalledIt prediction pipeline's application logic. This is Spec A2 — the companion to Spec A1 (`verification-teardown-docker`) which deployed the Docker Lambda infrastructure and archived the old verification system. Spec A2 introduces a centralized `mcp_manager.py` module that connects to 3 MCP servers (fetch, brave-search, playwright) via Strands `MCPClient` with stdio transport, discovers tools at Lambda INIT time, and provides a human-readable tool manifest for agent prompts. The Categorizer and Verification Builder agents become tool-aware using this live manifest, replacing the deleted DynamoDB tool registry import in `prediction_graph.py`. The Prompt Management stack gets a VB v3 prompt with `{{tool_manifest}}` support.

This spec does NOT cover: old verification system teardown (done in Spec A1), Docker Lambda infrastructure (done in Spec A1), verification execution agent (Spec B — future), eval framework integration (Spec C — future), or version bump to v3 (happens after A2 completes).

## Glossary

- **MCP_Manager**: A new module (`mcp_manager.py` in `handlers/strands_make_call/`) that manages MCP server connections, performs tool discovery at Lambda INIT, and provides both a human-readable Tool_Manifest and raw MCP tool objects
- **MCPClient**: The `strands.mcp.MCPClient` class that connects to an MCP server via stdio transport and provides `list_tools_sync()` for tool discovery
- **MCP_Tool_List**: The aggregated list of tool definitions returned by `MCPClient.list_tools_sync()` across all connected servers, each containing tool name, description, and input JSON schema
- **Tool_Manifest**: A human-readable string representation of available MCP tools (name + description per tool), injected into agent system prompts via template variables
- **Prediction_Graph**: The `prediction_graph.py` module that creates the 4-agent graph (Parser → Categorizer → VB → Review) as a module-level singleton
- **Categorizer_Agent**: The agent that classifies predictions into `auto_verifiable`, `automatable`, or `human_only` based on available tools and prediction content; already accepts a `tool_manifest` parameter
- **VB_Agent**: The Verification Builder agent that creates verification plans (sources, criteria, steps) for predictions; does not yet accept a `tool_manifest` parameter
- **Fetch_Server**: The `@modelcontextprotocol/server-fetch` MCP server — fetches any URL and converts HTML to markdown, no API key needed
- **Brave_Search_Server**: The `@nicobailon/mcp-brave-search` MCP server — web search via Brave Search API, requires `BRAVE_API_KEY`
- **Playwright_Server**: The `@nicobailon/mcp-playwright` MCP server — browser automation for dynamic web content, no API key needed
- **SAM_Template**: The `backend/calledit-backend/template.yaml` that defines the MakeCallStreamFunction (Docker Lambda deployed in Spec A1)
- **Prompt_Management_Stack**: The `infrastructure/prompt-management/template.yaml` CloudFormation stack that manages Bedrock Prompt resources for all 4 agents

## Requirements

### Requirement 1: MCP Manager Module

**User Story:** As a prediction pipeline, I want a centralized module that connects to MCP servers and discovers available tools at Lambda INIT time, so that all agents in the graph share the same live tool registry without DynamoDB dependencies.

#### Acceptance Criteria

1. THE MCP_Manager SHALL be implemented as a Python module at `handlers/strands_make_call/mcp_manager.py`
2. THE MCP_Manager SHALL connect to three MCP servers at initialization: Fetch_Server, Brave_Search_Server, and Playwright_Server
3. THE MCP_Manager SHALL use Strands `MCPClient` with stdio transport to connect to each MCP server as a subprocess invoked via `npx`
4. WHEN the MCP_Manager initializes, THE MCP_Manager SHALL call `list_tools_sync()` on each connected MCPClient and aggregate the results into a single MCP_Tool_List
5. THE MCP_Manager SHALL read the Brave Search API key from the `BRAVE_API_KEY` environment variable at runtime, not hardcoded in source code
6. IF an MCP server connection fails during initialization, THEN THE MCP_Manager SHALL log the error, skip that server, and continue initializing the remaining servers
7. IF all MCP server connections fail, THEN THE MCP_Manager SHALL return an empty MCP_Tool_List and log a warning that the pipeline is operating in reasoning-only mode
8. THE MCP_Manager SHALL expose a `get_tool_manifest()` method that returns a human-readable Tool_Manifest string containing each tool's name and description
9. THE MCP_Manager SHALL expose a `get_mcp_clients()` method that returns the list of connected MCPClient instances for future use by the verification execution agent (Spec B)
10. THE MCP_Manager SHALL expose a `get_mcp_tools()` method that returns the raw MCP tool objects from the aggregated MCP_Tool_List
11. THE MCP_Manager SHALL be instantiated as a module-level singleton so that connections are established during Lambda INIT and reused across warm invocations

### Requirement 2: Replace Tool Registry Import in Prediction Graph

**User Story:** As a developer, I want `prediction_graph.py` to source its tool manifest from MCP_Manager instead of the deleted `tool_registry.py`, so that the pipeline uses live MCP tool discovery.

#### Acceptance Criteria

1. THE Prediction_Graph SHALL import `mcp_manager` from the MCP_Manager module instead of importing `read_active_tools` and `build_tool_manifest` from `tool_registry`
2. THE Prediction_Graph SHALL call `mcp_manager.get_tool_manifest()` to obtain the Tool_Manifest string for agent creation
3. THE Prediction_Graph SHALL remove the try/except block that imports from `tool_registry` and falls back to an empty manifest
4. THE Prediction_Graph SHALL pass the MCP_Manager's Tool_Manifest to all 4 agent factories: `create_parser_agent(tool_manifest)`, `create_categorizer_agent(tool_manifest)`, `create_verification_builder_agent(tool_manifest)`, and `create_review_agent(tool_manifest)`
5. IF the MCP_Manager returns an empty Tool_Manifest, THEN THE Prediction_Graph SHALL pass the empty string to all 4 agent factories, preserving the existing graceful degradation to reasoning-only mode

### Requirement 3: Tool-Aware Verification Builder Agent

**User Story:** As a verification builder, I want to reference real MCP tools when writing verification plans, so that plans name specific tools the future execution agent (Spec B) can invoke.

#### Acceptance Criteria

1. THE `create_verification_builder_agent()` factory function SHALL accept a `tool_manifest` parameter with a default value of empty string, matching the pattern used by `create_categorizer_agent()`
2. WHEN `tool_manifest` is non-empty, THE VB_Agent factory SHALL pass the manifest text to `fetch_prompt("vb", variables={"tool_manifest": manifest_text})`
3. WHEN `tool_manifest` is empty, THE VB_Agent factory SHALL pass a fallback string indicating no tools are currently registered
4. THE bundled `VERIFICATION_BUILDER_SYSTEM_PROMPT` constant SHALL include an `AVAILABLE TOOLS` section with a `{tool_manifest}` placeholder, so the fallback prompt also receives the manifest
5. THE VB_Agent system prompt SHALL instruct the agent to reference specific MCP tool names in the `source` and `steps` fields when a matching tool exists for the verification need
6. THE VB_Agent system prompt SHALL instruct the agent to note "tool not currently available" in the `steps` field when no matching tool exists for an `automatable` prediction

### Requirement 6: Tool-Aware Review Agent

**User Story:** As a review agent, I want to know what verification tools are available, so that I can ask targeted clarification questions about whether the Verification Builder's tool choices and verification steps are appropriate for the prediction.

#### Acceptance Criteria

1. THE `create_review_agent()` factory function SHALL accept a `tool_manifest` parameter with a default value of empty string, matching the pattern used by `create_categorizer_agent()` and `create_verification_builder_agent()`
2. WHEN `tool_manifest` is non-empty, THE Review_Agent factory SHALL pass the manifest text to `fetch_prompt("review", variables={"tool_manifest": manifest_text})`
3. WHEN `tool_manifest` is empty, THE Review_Agent factory SHALL pass a fallback string indicating no tools are currently registered
4. THE bundled `REVIEW_SYSTEM_PROMPT` constant SHALL include an `AVAILABLE TOOLS` section with a `{tool_manifest}` placeholder, so the fallback prompt also receives the manifest
5. THE Review_Agent system prompt SHALL instruct the agent to consider whether the VB's chosen tools and sources are the best match from the available tool list, and to question tool choices that seem suboptimal
6. THE Prediction_Graph SHALL pass the MCP_Manager's Tool_Manifest to `create_review_agent(tool_manifest)` in addition to the Categorizer and VB agents

### Requirement 4: Prompt Management VB v3

**User Story:** As a prompt engineer, I want the VB prompt in Bedrock Prompt Management updated with a `{{tool_manifest}}` variable and tool-referencing instructions, so that the managed prompt matches the tool-aware bundled prompt.

#### Acceptance Criteria

1. THE VB prompt in the Prompt_Management_Stack SHALL add a `{{tool_manifest}}` input variable to the template configuration, matching the pattern used by the Categorizer prompt
2. THE VB prompt text SHALL include an `AVAILABLE TOOLS` section that displays the `{{tool_manifest}}` variable content
3. THE VB prompt text SHALL instruct the agent to use specific tool names from the manifest in the `source` field when tools match the verification need
4. THE VB prompt text SHALL instruct the agent to note "tool not currently available" in the `steps` field when no matching tool exists for an `automatable` prediction
5. THE Prompt_Management_Stack SHALL add a new `VBPromptVersionV3` resource of type `AWS::Bedrock::PromptVersion` with a description referencing MCP tool awareness
6. THE `VBPromptVersionV3` resource SHALL depend on `VBPromptVersionV2` to ensure correct version ordering

### Requirement 5: SAM Template Environment Variable

**User Story:** As a DevOps engineer, I want the `BRAVE_API_KEY` environment variable added to the MakeCallStreamFunction, so that the Brave Search MCP server can authenticate at runtime.

#### Acceptance Criteria

1. THE MakeCallStreamFunction in the SAM_Template SHALL include `BRAVE_API_KEY` in its Environment Variables section
2. THE `BRAVE_API_KEY` value SHALL use a placeholder string for initial development, to be replaced with an SSM Parameter Store reference before production deployment
3. THE SAM_Template SHALL retain all existing environment variables (`PROMPT_VERSION_PARSER`, `PROMPT_VERSION_CATEGORIZER`, `PROMPT_VERSION_VB`, `PROMPT_VERSION_REVIEW`) unchanged

### Requirement 7: Tool-Aware Parser Agent (Consistency)

**User Story:** As a developer, I want all 4 agent factories to accept the same `tool_manifest` parameter, so that the prediction graph has a uniform interface and the parser has context about available tools if needed.

#### Acceptance Criteria

1. THE `create_parser_agent()` factory function SHALL accept a `tool_manifest` parameter with a default value of empty string, matching the pattern used by the other 3 agent factories
2. THE Parser_Agent factory SHALL accept the parameter but is NOT required to inject it into the system prompt — the parameter exists for interface consistency and future use
3. THE bundled `PARSER_SYSTEM_PROMPT` constant MAY optionally include an `AVAILABLE TOOLS` section with a `{tool_manifest}` placeholder, but this is not required for Spec A2
