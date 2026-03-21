# Requirements Document — Spec B1: Verification Executor Agent

## Introduction

Build the verification execution agent (Spec B1 in the verification pipeline roadmap, Decision 74) — a Strands agent that receives a verification plan produced by the Verification Builder and actually executes it by invoking MCP tools (`brave_web_search`, `fetch`) to gather evidence. The agent evaluates gathered evidence against the verification criteria and produces a verification outcome (confirmed/refuted/inconclusive with confidence score and reasoning).

This spec builds on Spec A2 (`mcp-tool-integration`) which wired MCP servers into the pipeline and made all agents tool-aware via `tool_manifest`. The verification execution agent reuses the same MCP Manager singleton — the same tools available for planning are now available for execution.

This is the first of three specs split from the original 9-requirement Spec B (same reasoning as Decision 3 and Decision 64 — smaller specs, higher confidence):
- **Spec B1** (this spec): Verification Executor agent — build and test the agent in isolation
- **Spec B2** (`verification-triggers`): DynamoDB storage, immediate trigger, scheduled scanner — wire B1 into the pipeline
- **Spec B3** (`verification-eval-integration`): Eval framework extension with `--verify` mode and 4 new evaluators

This spec does NOT cover: DynamoDB result storage (Spec B2), pipeline trigger integration (Spec B2), EventBridge scanner (Spec B2), eval framework extension (Spec B3), AgentCore migration (Decision 68, 73), cold start optimization, or frontend display.

## Glossary

- **Verification_Executor**: A new Strands Agent (`verification_executor_agent.py` in `handlers/strands_make_call/`) that receives a verification plan and executes it using MCP tools to produce a verification outcome
- **Verification_Plan**: The output of the Verification Builder agent — a dict with `source` (list of sources to check), `criteria` (list of measurable criteria), and `steps` (list of verification steps to execute)
- **Verification_Outcome**: The output of the Verification_Executor — a dict with `status` (confirmed/refuted/inconclusive), `confidence` (0.0-1.0), `evidence` (list of evidence items gathered), and `reasoning` (explanation of the verdict)
- **Evidence_Item**: A single piece of evidence gathered during verification — a dict with `source` (tool or URL used), `content` (relevant extracted content), and `relevance` (how the evidence relates to the criteria)
- **MCP_Manager**: The existing singleton module (`mcp_manager.py`) that manages MCP server connections and provides tool discovery and MCP tool objects
- **MCP_Tools**: The raw tool objects from `mcp_manager.get_mcp_tools()` that can be passed to `Agent(tools=[...])` for direct tool invocation
- **Prediction_Record**: An existing DynamoDB item in `calledit-db` with `PK=USER:{userId}` and `SK=PREDICTION#{timestamp}`, containing the prediction statement, verification method, and other pipeline outputs

## Requirements

### Requirement 1: Verification Executor Agent

**User Story:** As a verification pipeline, I want a Strands agent that can invoke MCP tools to gather evidence and evaluate it against verification criteria, so that predictions categorized as `auto_verifiable` can be verified without human intervention.

#### Acceptance Criteria

1. THE Verification_Executor SHALL be implemented as a Strands Agent in a new module at `handlers/strands_make_call/verification_executor_agent.py`
2. THE Verification_Executor SHALL accept MCP_Tools from the MCP_Manager as its `tools` parameter, enabling direct invocation of `brave_web_search`, `fetch`, and other discovered MCP tools
3. THE Verification_Executor SHALL have a focused system prompt (20-30 lines) with single responsibility: execute a verification plan and produce a verdict
4. THE Verification_Executor system prompt SHALL instruct the agent to invoke the tools named in the verification plan's `steps` field to gather evidence
5. THE Verification_Executor system prompt SHALL instruct the agent to evaluate gathered evidence against each criterion in the verification plan's `criteria` field
6. THE Verification_Executor SHALL return a JSON Verification_Outcome containing `status`, `confidence`, `evidence`, and `reasoning` fields
7. WHEN the Verification_Executor cannot gather sufficient evidence to make a determination, THE Verification_Executor SHALL return a status of `inconclusive` with reasoning explaining what evidence was missing
8. IF an MCP tool invocation fails during execution, THEN THE Verification_Executor SHALL log the error, note the failure in the evidence list, and continue with remaining tools and steps

### Requirement 2: Verification Outcome Data Model

**User Story:** As a developer, I want a well-defined data model for verification outcomes, so that results are structured consistently for storage and future display.

#### Acceptance Criteria

1. THE Verification_Outcome SHALL contain a `status` field with exactly one of three values: `confirmed`, `refuted`, or `inconclusive`
2. THE Verification_Outcome SHALL contain a `confidence` field as a float between 0.0 and 1.0 inclusive, representing the agent's confidence in the verdict
3. THE Verification_Outcome SHALL contain an `evidence` field as a list of Evidence_Item dicts, each with `source`, `content`, and `relevance` string fields
4. THE Verification_Outcome SHALL contain a `reasoning` field as a string explaining how the evidence maps to the criteria and why the status was chosen
5. THE Verification_Outcome SHALL contain a `verified_at` field as an ISO 8601 UTC timestamp recording when verification completed
6. THE Verification_Outcome SHALL contain a `tools_used` field as a list of tool name strings that were actually invoked during execution

### Requirement 3: Verification Execution Entry Point

**User Story:** As a pipeline operator, I want a function that takes a prediction record and runs the verification execution pipeline, so that verification can be triggered for any `auto_verifiable` prediction.

#### Acceptance Criteria

1. THE module SHALL expose a `run_verification(prediction_record: dict) -> dict` function that accepts a Prediction_Record and returns a Verification_Outcome
2. WHEN `run_verification` is called, it SHALL extract the `verification_method` (containing `source`, `criteria`, `steps`) from the Prediction_Record and pass it to the Verification_Executor as a structured prompt
3. WHEN `run_verification` is called, it SHALL also pass the `prediction_statement` and `verifiable_category` from the Prediction_Record to provide context to the Verification_Executor
4. IF the Prediction_Record has no `verification_method` or the method is empty, THEN `run_verification` SHALL return an `inconclusive` outcome with reasoning indicating no verification plan was available
5. IF the Verification_Executor raises an exception, THEN `run_verification` SHALL catch the error and return an `inconclusive` outcome with the error message in the reasoning field

### Requirement 4: MCP Tool Wiring

**User Story:** As a verification executor, I want the same MCP tools that the Verification Builder references in plans to be available for direct invocation, so that plans can be executed faithfully.

#### Acceptance Criteria

1. THE Verification_Executor factory function SHALL obtain MCP tool objects by calling `mcp_manager.get_mcp_tools()` from the existing MCP_Manager singleton
2. THE Verification_Executor factory function SHALL pass the MCP tool objects to the Strands `Agent(tools=[...])` constructor, enabling the agent to invoke tools directly
3. IF the MCP_Manager returns an empty tool list, THEN THE Verification_Executor SHALL operate in reasoning-only mode and return `inconclusive` outcomes with reasoning indicating no tools were available
4. THE Verification_Executor SHALL reuse the same MCP_Manager singleton instance used by the prediction pipeline — no separate MCP server connections

### Requirement 5: Agent Factory Pattern

**User Story:** As a developer, I want the verification executor agent to follow the same factory pattern as the other 4 agents, so that the codebase remains consistent and the agent can be tested in isolation.

#### Acceptance Criteria

1. THE `create_verification_executor_agent()` factory function SHALL accept `model_id: str = None` as an optional parameter, defaulting to Claude Sonnet 4 via Bedrock
2. THE factory function SHALL use the bundled system prompt constant with a fallback pattern matching the other agent factories
3. THE factory function SHALL be importable independently for unit testing without requiring MCP server connections
4. THE Verification_Executor Agent SHALL be created as a module-level singleton, reused across warm Lambda invocations, following the same pattern as the prediction pipeline agents
