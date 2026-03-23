# Requirements Document — Spec V4-2: Built-in Tools

## Introduction

Wire AgentCore Browser and AgentCore Code Interpreter into the CalledIt v4 agent entrypoint so the agent can browse the web and execute Python code. This is the second spec in the v4 clean rebuild, building directly on V4-1 (AgentCore Foundation) which delivered the `calleditv4/` project with a working Strands agent entrypoint.

The two built-in tools replace the local MCP subprocesses from v3 (Decision 91), eliminating the 30-second cold start. Both tools run in AWS infrastructure (Firecracker microVMs for Browser, secure sandboxes for Code Interpreter) and require only IAM permissions — zero external API keys, zero Gateway setup (Decision 93).

This spec does NOT cover: Gateway with domain-specific APIs (Phase 2), Prompt Management wiring (V4-3a), DynamoDB save (V4-3a), Memory integration (V4-6), Verification agent (V4-5), or production deployment (V4-8).

## Glossary

- **AgentCore_Browser**: The built-in browser tool from `strands_tools.browser.AgentCoreBrowser` that provides a full Chromium browser running in a Firecracker microVM in AWS. Enables URL navigation, web search, content extraction, and element interaction. Instantiated with a region parameter and wired into the Strands_Agent via `tools=[browser_tool.browser]`
- **AgentCore_Code_Interpreter**: The built-in code interpreter tool from `strands_tools.code_interpreter.AgentCoreCodeInterpreter` that provides a secure Python sandbox in AWS. Enables calculations, data analysis, and date math. Instantiated with a region parameter and wired into the Strands_Agent via `tools=[code_interpreter_tool.code_interpreter]`
- **Strands_Agent**: An agent instance created via `strands.Agent` with a model, system prompt, and tools list. The core execution unit inside the BedrockAgentCoreApp entrypoint
- **Entrypoint**: The Python function decorated with `@app.entrypoint` in `calleditv4/src/main.py` that receives a payload dict and context object, creates and invokes a Strands_Agent with tools, and returns the response string
- **Tool_List**: The Python list of tool callables passed to the Strands_Agent constructor via the `tools` parameter, containing the browser and code interpreter tool references
- **AWS_Region**: The AWS region used for AgentCore built-in tool sessions, configurable via the `AWS_REGION` environment variable with a default of `us-west-2`
- **System_Prompt**: The hardcoded prompt string in the Entrypoint that instructs the Strands_Agent about its identity and available tools
- **Virtual_Environment**: The project Python virtual environment at `/home/wsluser/projects/calledit/venv` used for all Python commands

## Requirements

### Requirement 1: Tool Dependencies and Configuration

**User Story:** As a developer, I want the AgentCore Browser and Code Interpreter dependencies installed and configured with the correct region, so that the tools are ready to use in the agent entrypoint.

#### Acceptance Criteria

1. THE Virtual_Environment SHALL have the `strands-agents-tools` package installed, which provides both `strands_tools.browser.AgentCoreBrowser` and `strands_tools.code_interpreter.AgentCoreCodeInterpreter`
2. THE Entrypoint SHALL instantiate the AgentCore_Browser with the AWS_Region value
3. THE Entrypoint SHALL instantiate the AgentCore_Code_Interpreter with the AWS_Region value
4. THE Entrypoint SHALL read the AWS_Region from the `AWS_REGION` environment variable, defaulting to `us-west-2` when the environment variable is not set
5. THE Entrypoint SHALL wire both tool instances into the Strands_Agent constructor via the `tools` parameter as a Tool_List containing `browser_tool.browser` and `code_interpreter_tool.code_interpreter`
6. THE Entrypoint SHALL NOT require `playwright` or `nest-asyncio` as local dependencies — `AgentCoreBrowser` communicates with the AWS-hosted Chromium session via the AgentCore SDK, not via local Playwright

### Requirement 2: Browser Tool Integration

**User Story:** As a developer, I want the agent to browse the web when prompted, so that it can navigate URLs, search for information, and extract content from web pages.

#### Acceptance Criteria

1. WHEN a user prompt requests web navigation, THE Strands_Agent SHALL use the AgentCore_Browser tool to navigate to the specified URL and return the page content
2. WHEN a user prompt requests a web search, THE Strands_Agent SHALL use the AgentCore_Browser tool to perform the search and return relevant results
3. WHEN a user prompt requests content extraction from a web page, THE Strands_Agent SHALL use the AgentCore_Browser tool to navigate to the page and extract the requested information
4. THE System_Prompt SHALL describe the AgentCore_Browser capability so the Strands_Agent knows when to use the browser tool
5. IF the AgentCore_Browser tool raises an exception during a browser session, THEN THE Entrypoint SHALL catch the error and return a structured error response containing the error message

### Requirement 3: Code Interpreter Integration

**User Story:** As a developer, I want the agent to execute Python code when prompted, so that it can perform calculations, date math, and data analysis.

#### Acceptance Criteria

1. WHEN a user prompt requires a numerical calculation, THE Strands_Agent SHALL use the AgentCore_Code_Interpreter tool to execute Python code and return the computed result
2. WHEN a user prompt requires date or time computation, THE Strands_Agent SHALL use the AgentCore_Code_Interpreter tool to execute Python date math and return the result
3. WHEN a user prompt requires data analysis or transformation, THE Strands_Agent SHALL use the AgentCore_Code_Interpreter tool to execute Python code for the analysis and return the result
4. THE System_Prompt SHALL describe the AgentCore_Code_Interpreter capability so the Strands_Agent knows when to use the code interpreter tool
5. IF the AgentCore_Code_Interpreter tool raises an exception during code execution, THEN THE Entrypoint SHALL catch the error and return a structured error response containing the error message
