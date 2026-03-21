# Requirements Document

> **⚠️ SUPERSEDED — DO NOT IMPLEMENT**
>
> This spec was split into Spec A1 (`verification-teardown-docker`) and Spec A2 (`mcp-tool-integration`) per Decision 64.
> See `.kiro/specs/verification-teardown-docker/` for the active infrastructure spec.
> Spec A2 will be created separately for MCP Manager + tool-aware agents.

## Introduction

Connect the CalledIt prediction pipeline to real MCP (Model Context Protocol) tool servers, replace the DynamoDB-based tool registry with MCP-native tool discovery, make the Categorizer and Verification Builder agents tool-aware using live MCP tool lists, and tear down the old verification system (Lambda, EventBridge, S3 bucket, SNS topic). This is Spec A of a 3-spec verification pipeline build — it establishes the MCP foundation and tool-aware agents. It does NOT build the verification execution agent (Spec B) or eval framework integration (Spec C).

The old verification system in `handlers/verification/` was a primitive attempt at automated verification: an EventBridge rule triggered a Lambda every 15 minutes to scan DynamoDB for pending predictions and verify them using a Strands agent with only a datetime tool and reasoning. It used a DynamoDB tool registry (`TOOL#{tool_id}` records) with only `web_search` registered, and a custom `@tool` DuckDuckGo wrapper. The system never worked well — it could only verify trivially reasoned predictions and returned INCONCLUSIVE for everything else. The MCP approach replaces this with real, capable tool servers that both the planning agents (Categorizer, VB) and the future execution agent (Spec B) share.

## Glossary

- **MCP_Server**: An external process that exposes tools via the Model Context Protocol standard, connected to the prediction pipeline via Strands `MCPClient`
- **MCPClient**: The `strands.mcp.MCPClient` class that connects to an MCP server and provides `list_tools_sync()` for tool discovery and tool proxies for agent invocation
- **MCP_Tool_List**: The list of tool definitions returned by `MCPClient.list_tools_sync()`, each containing tool name, description, and input JSON schema
- **Tool_Manifest**: A human-readable string representation of available MCP tools, injected into the Categorizer prompt via the `{{tool_manifest}}` template variable
- **Tool_Registry**: The current DynamoDB-based tool registry using `PK=TOOL#{tool_id}` records in `calledit-db`, being replaced by MCP-native discovery
- **Prediction_Graph**: The `prediction_graph.py` module that creates the 4-agent graph (Parser → Categorizer → VB → Review) as a module-level singleton, cached by SnapStart
- **Categorizer_Agent**: The agent that classifies predictions into `auto_verifiable`, `automatable`, or `human_only` based on available tools and prediction content
- **VB_Agent**: The Verification Builder agent that creates verification plans (sources, criteria, steps) for predictions
- **Old_Verification_System**: The `handlers/verification/` directory containing `app.py` (Lambda handler), `verification_agent.py`, `verify_predictions.py`, `ddb_scanner.py`, `status_updater.py`, `s3_logger.py`, `email_notifier.py`, and supporting files, plus the SAM template resources `VerificationFunction`, `VerificationLogsBucket`, `VerificationNotificationTopic`, and the EventBridge schedule
- **SAM_Template**: The `backend/calledit-backend/template.yaml` that defines all Lambda functions and infrastructure resources
- **Fetch_Server**: The `@modelcontextprotocol/server-fetch` MCP server that fetches any URL and converts HTML to markdown
- **Brave_Search_Server**: The `@nicobailon/mcp-brave-search` MCP server that provides web search via the Brave Search API
- **Playwright_Server**: The `@nicobailon/mcp-playwright` MCP server that provides browser automation for dynamic web content
- **MCP_Manager**: A new module that manages MCP server connections, performs tool discovery, and builds the tool manifest for agent consumption

## Requirements

### Requirement 1: MCP Server Connection Management

**User Story:** As a prediction pipeline, I want a centralized module that connects to MCP servers and discovers available tools at startup, so that all agents in the graph share the same live tool registry.

#### Acceptance Criteria

1. THE MCP_Manager SHALL connect to three MCP servers at initialization: Fetch_Server, Brave_Search_Server, and Playwright_Server
2. THE MCP_Manager SHALL use Strands `MCPClient` with stdio transport to connect to each MCP server as a subprocess
3. WHEN the MCP_Manager initializes, THE MCP_Manager SHALL call `list_tools_sync()` on each connected MCPClient and aggregate the results into a single MCP_Tool_List
4. THE MCP_Manager SHALL store the Brave Search API key as an environment variable (`BRAVE_API_KEY`) read at runtime, not hardcoded in source code
5. IF an MCP server connection fails during initialization, THEN THE MCP_Manager SHALL log the error, skip that server, and continue with the remaining servers
6. IF all MCP server connections fail, THEN THE MCP_Manager SHALL return an empty MCP_Tool_List and log a warning that the pipeline is operating in reasoning-only mode
7. THE MCP_Manager SHALL expose a `get_tool_manifest()` function that converts the MCP_Tool_List into a human-readable Tool_Manifest string containing each tool's name, description, and capabilities
8. THE MCP_Manager SHALL expose a `get_mcp_tools()` function that returns the raw MCP tool objects for passing directly to Strands Agent `tools` parameter

### Requirement 2: Tool-Aware Categorizer Agent

**User Story:** As a categorizer, I want to check the live MCP tool list when classifying predictions, so that `auto_verifiable` means a matching tool actually exists right now rather than a guess.

#### Acceptance Criteria

1. WHEN the Prediction_Graph creates the Categorizer_Agent, THE Prediction_Graph SHALL pass the MCP_Manager's Tool_Manifest to `create_categorizer_agent()` instead of the DynamoDB-based manifest from `tool_registry.py`
2. THE Categorizer_Agent SHALL classify a prediction as `auto_verifiable` when a tool in the MCP_Tool_List has capabilities matching the prediction's verification needs
3. THE Categorizer_Agent SHALL classify a prediction as `automatable` when no tool in the MCP_Tool_List matches but a tool could plausibly exist for that prediction type
4. THE Categorizer_Agent SHALL classify a prediction as `human_only` when the prediction requires subjective judgment, physical observation, or private information that no tool can provide
5. WHEN the MCP_Tool_List is empty, THE Categorizer_Agent SHALL fall back to reasoning-only mode where only pure-reasoning predictions qualify as `auto_verifiable`

### Requirement 3: Tool-Aware Verification Builder Agent

**User Story:** As a verification builder, I want to reference real MCP tools when writing verification plans, so that plans are directly executable by the future verification execution agent (Spec B).

#### Acceptance Criteria

1. WHEN the Prediction_Graph creates the VB_Agent, THE Prediction_Graph SHALL pass the MCP_Manager's MCP_Tool_List to `create_verification_builder_agent()`
2. THE VB_Agent system prompt SHALL include an `AVAILABLE TOOLS` section listing the MCP tools by name and description, matching the format used in the Categorizer_Agent prompt
3. WHEN the VB_Agent writes a verification plan for an `auto_verifiable` prediction, THE VB_Agent SHALL reference specific MCP tool names in the `source` and `steps` fields of the verification method
4. WHEN the VB_Agent writes a verification plan for an `automatable` prediction, THE VB_Agent SHALL note which tool type would be needed and that it is not currently available
5. THE VB_Agent prompt in Prompt Management SHALL include a `{{tool_manifest}}` template variable, matching the pattern already used by the Categorizer prompt

### Requirement 4: Replace DynamoDB Tool Registry with MCP Discovery

**User Story:** As a developer, I want to remove the DynamoDB tool registry pattern and replace it with MCP-native tool discovery, so that there is a single source of truth for available tools.

#### Acceptance Criteria

1. THE Prediction_Graph SHALL import tool discovery from MCP_Manager instead of `tool_registry.py`
2. THE Prediction_Graph SHALL remove the `from tool_registry import read_active_tools, build_tool_manifest` import and the DynamoDB read logic in `create_prediction_graph()`
3. THE `tool_registry.py` module SHALL be archived to `docs/historical/verification-v1/tool_registry.py` with a header comment explaining it was replaced by MCP-native discovery
4. THE `web_search_tool.py` module in `handlers/verification/` SHALL be archived alongside `tool_registry.py` since the custom `@tool` web_search is replaced by the Brave_Search_Server MCP tool
5. THE DynamoDB `TOOL#` records SHALL remain in the database for historical reference but SHALL NOT be read by any production code path

### Requirement 5: Old Verification System Teardown — SAM Template

**User Story:** As a DevOps engineer, I want the old verification infrastructure removed from the SAM template, so that there are no orphaned resources running in production.

#### Acceptance Criteria

1. THE SAM_Template SHALL remove the `VerificationFunction` Lambda resource and its EventBridge schedule event (`ScheduledVerification`)
2. THE SAM_Template SHALL remove the `VerificationLogsBucket` S3 bucket resource
3. THE SAM_Template SHALL remove the `VerificationNotificationTopic` SNS topic resource
4. THE SAM_Template SHALL remove the `VerificationFunctionArn`, `VerificationLogsBucket`, and `VerificationNotificationTopic` entries from the Outputs section
5. THE SAM_Template SHALL retain the `NotificationManagementFunction` resource, which depends on the SNS topic — IF the NotificationManagementFunction references the removed SNS topic, THEN THE SAM_Template SHALL update or remove the NotificationManagementFunction accordingly
6. WHEN the updated SAM template is deployed, THE deployment SHALL succeed without errors from missing resource references

### Requirement 6: Old Verification System Teardown — Code Archive

**User Story:** As a developer, I want the old verification handler code archived with documentation explaining what it was and why it was replaced, so that the project history is preserved.

#### Acceptance Criteria

1. THE old verification handler directory (`handlers/verification/`) SHALL be moved to `docs/historical/verification-v1/`
2. THE archive SHALL include a `README.md` documenting what the old system did, what files it contained, why it was replaced, and what replaced it
3. THE archive README SHALL list all files in the old system: `app.py`, `verification_agent.py`, `verify_predictions.py`, `ddb_scanner.py`, `status_updater.py`, `s3_logger.py`, `email_notifier.py`, `verification_result.py`, `web_search_tool.py`, `seed_web_search_tool.py`, `error_handling.py`, `cleanup_predictions.py`, `inspect_data.py`, `mock_strands.py`, `modernize_data.py`, `recategorize.py`, `test_scanner.py`, `test_verification_result.py`, and `requirements.txt`
4. THE archive README SHALL reference Decision 18 (3 verifiability categories), Decision 19 (DDB tool registry), Decision 20 (web search as first tool), and Backlog item 7 (verification pipeline via MCP tools) as context for the replacement

### Requirement 7: MCP Server Configuration for Lambda Deployment

**User Story:** As a DevOps engineer, I want the MCP server dependencies and configuration defined in the SAM template, so that the Lambda can start MCP server subprocesses at initialization.

#### Acceptance Criteria

1. THE MakeCallStreamFunction Lambda SHALL include the `BRAVE_API_KEY` as an environment variable, sourced from an AWS Systems Manager Parameter Store parameter or hardcoded placeholder for initial development
2. THE MakeCallStreamFunction Lambda requirements.txt SHALL include `strands-agents-tools` (or the appropriate package providing `strands.mcp.MCPClient`) if not already present
3. THE MakeCallStreamFunction Lambda SHALL have sufficient memory (512MB minimum, current setting) and timeout (300s, current setting) to support MCP server subprocess initialization alongside agent execution
4. WHEN the Lambda cold-starts, THE MCP_Manager SHALL initialize MCP server connections during Lambda INIT phase so they are cached by SnapStart for warm invocations
5. IF an MCP server subprocess dies during a warm Lambda invocation, THEN THE MCP_Manager SHALL detect the failure and attempt reconnection before returning an empty tool list for that server

### Requirement 8: Prompt Management Updates for Tool-Aware VB

**User Story:** As a prompt engineer, I want the Verification Builder prompt in Bedrock Prompt Management updated to include a tool manifest variable, so that the VB agent references real tools when writing verification plans.

#### Acceptance Criteria

1. THE VB prompt in the Prompt_Management_Stack (`infrastructure/prompt-management/template.yaml`) SHALL add a `{{tool_manifest}}` input variable to the VB prompt template
2. THE VB prompt text SHALL include an `AVAILABLE TOOLS` section that references the `{{tool_manifest}}` variable, instructing the agent to reference these tools in verification plans
3. THE VB prompt SHALL instruct the agent to use specific tool names from the manifest in the `source` field when tools match the verification need
4. THE VB prompt SHALL instruct the agent to note "tool not currently available" in the `steps` field when no matching tool exists for an `automatable` prediction
5. WHEN a new prompt version is created, THE Prompt_Management_Stack SHALL add a new `AWS::Bedrock::PromptVersion` resource (VB v3) with a description referencing MCP tool awareness
6. THE `create_verification_builder_agent()` factory function SHALL accept a `tool_manifest` parameter and pass it to `fetch_prompt()` as a variable, matching the pattern used by `create_categorizer_agent()`

### Requirement 9: Decision Log and Backlog Updates

**User Story:** As a project maintainer, I want the decision log and backlog updated to reflect the MCP foundation work, so that future specs have accurate context.

#### Acceptance Criteria

1. THE decision log SHALL record a new decision documenting the choice to replace the DDB tool registry with MCP-native tool discovery, referencing Decisions 19, 20, and 57
2. THE decision log SHALL record a new decision documenting the choice of the 3 MCP servers (fetch, brave-search, playwright) as the starter stack, referencing the MCP research document
3. THE decision log SHALL record a new decision documenting the teardown of the old verification system and what replaced it
4. THE backlog SHALL update item 7 (Verification Pipeline via MCP Tools) to mark the foundation work (Spec A) as complete and note that Spec B (execution agent) and Spec C (eval integration) remain
