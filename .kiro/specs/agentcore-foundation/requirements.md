# Requirements Document — Spec V4-1: AgentCore Foundation

## Introduction

Set up the Amazon Bedrock AgentCore project structure for CalledIt v4, get the local development server running, and validate basic agent invocation. This is the first spec in the v4 clean rebuild — pure infrastructure scaffolding with no business logic. The goal is to answer one question: "Can we run a Strands agent on AgentCore?"

This spec has no dependencies. All subsequent v4 specs (V4-2 through V4-8, V4-7a through V4-7c) depend on this foundation being in place.

This spec does NOT cover: tools (V4-2), creation agent logic (V4-3a), verification agent logic (V4-5), memory integration (V4-6), eval framework (V4-7a), or production deployment (V4-8).

## Glossary

- **AgentCore_CLI**: The `agentcore` command-line tool provided by the `bedrock-agentcore-starter-toolkit` pip package. Used to create projects (`agentcore create`), run the local dev server (`agentcore dev`), and invoke agents locally (`agentcore invoke --dev`)
- **BedrockAgentCoreApp**: The runtime wrapper class from `bedrock_agentcore.runtime` that provides the `@app.entrypoint` decorator and `app.run()` method for defining AgentCore-compatible agent entrypoints
- **Dev_Server**: The local development server started by `agentcore dev` that hosts the agent with hot reload, simulating the AgentCore Runtime environment without deploying to AWS
- **Project_Config**: The `.bedrock_agentcore.yaml` file at the project root that configures the AgentCore project name, template, agent framework, and model provider
- **Strands_Agent**: An agent instance created via `strands.Agent` with a model, system prompt, and optional tools. The core execution unit inside the BedrockAgentCoreApp entrypoint
- **Entrypoint**: A Python function decorated with `@app.entrypoint` that receives a payload dict and context object, creates and invokes a Strands_Agent, and returns the response string
- **Virtual_Environment**: The project Python virtual environment at `/home/wsluser/projects/calledit/venv` used for all Python commands

## Requirements

### Requirement 1: AgentCore Toolkit Installation and Project Creation

**User Story:** As a developer, I want the AgentCore starter toolkit installed and a new project scaffolded, so that I have the standard AgentCore project structure to build on.

#### Acceptance Criteria

1. THE Virtual_Environment SHALL have the `bedrock-agentcore-starter-toolkit` package installed via `/home/wsluser/projects/calledit/venv/bin/pip install bedrock-agentcore-starter-toolkit`
2. WHEN `agentcore create --non-interactive --project-name calleditv4 --template basic --agent-framework Strands --model-provider Bedrock` is executed, THE AgentCore_CLI SHALL generate a project directory at `calleditv4/` containing the standard AgentCore project structure
3. THE generated project directory SHALL contain a valid Project_Config file (`.bedrock_agentcore.yaml`) with project name `calleditv4`, template `basic`, agent framework `Strands`, and model provider `Bedrock`
4. THE generated project directory SHALL contain a Python entrypoint file using the BedrockAgentCoreApp wrapper pattern with `@app.entrypoint` decorator and `app.run()` call

### Requirement 2: Agent Entrypoint Configuration

**User Story:** As a developer, I want the generated agent entrypoint configured with the correct Bedrock model and a minimal system prompt, so that the agent is ready for local invocation.

#### Acceptance Criteria

1. THE Entrypoint SHALL create a Strands_Agent configured with model `us.anthropic.claude-sonnet-4-20250514-v1:0` (Claude Sonnet 4 cross-region inference profile)
2. THE Entrypoint SHALL accept a payload dict containing a `prompt` key and pass the prompt value to the Strands_Agent for processing
3. THE Entrypoint SHALL return the Strands_Agent response as a string
4. THE Entrypoint SHALL use a minimal system prompt that identifies the agent as the CalledIt v4 foundation agent (placeholder text sufficient for validation — business logic prompts are added in V4-3a via Prompt Management)
5. IF the Strands_Agent raises an exception during invocation, THEN THE Entrypoint SHALL log the error with the exception details and return a structured error response containing the error message

### Requirement 3: Local Development Server

**User Story:** As a developer, I want the local dev server running with hot reload, so that I can iterate on the agent code without restarting manually.

#### Acceptance Criteria

1. WHEN `agentcore dev` is executed from the `calleditv4/` project directory, THE Dev_Server SHALL start and listen for incoming invocation requests
2. WHILE the Dev_Server is running, THE Dev_Server SHALL detect changes to the agent entrypoint file and reload the agent code without requiring a manual restart
3. WHILE the Dev_Server is running, THE Dev_Server SHALL log startup confirmation including the local endpoint address to the console
4. IF the Dev_Server fails to start due to a configuration error in Project_Config, THEN THE Dev_Server SHALL display a descriptive error message identifying the misconfiguration

### Requirement 4: Agent Invocation Validation

**User Story:** As a developer, I want to invoke the agent locally and confirm it responds correctly, so that I have confidence the AgentCore foundation is working before building on it.

#### Acceptance Criteria

1. WHEN `agentcore invoke --dev '{"prompt": "Hello, are you working?"}'` is executed while the Dev_Server is running, THE Strands_Agent SHALL return a non-empty text response acknowledging the prompt
2. WHEN `agentcore invoke --dev '{"prompt": "What model are you running on?"}'` is executed, THE Strands_Agent SHALL return a response (the content is model-dependent — the acceptance criterion is that invocation succeeds and returns a non-empty string, not that the response contains specific text)
3. IF `agentcore invoke --dev` is executed with a payload missing the `prompt` key, THEN THE Entrypoint SHALL return a structured error response indicating the missing field rather than an unhandled exception
4. IF `agentcore invoke --dev` is executed while the Dev_Server is not running, THEN THE AgentCore_CLI SHALL display an error message indicating the dev server is not available
