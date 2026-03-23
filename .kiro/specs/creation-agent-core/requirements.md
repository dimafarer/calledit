# Requirements Document — Spec V4-3a: Creation Agent Core

## Introduction

Implement the 3-turn creation flow that transforms raw prediction text into a structured prediction bundle, saves it to DynamoDB, and returns the bundle. This is the first v4 spec with real business logic, building on V4-1 (AgentCore Foundation) and V4-2 (Built-in Tools).

The creation agent uses a single Strands Agent with 3 sequential prompt turns (evolved from Decision 94's original 4-turn design): parse → plan → review. The original score and review turns are merged into a single review turn that both scores verifiability and generates clarification questions — these are two perspectives on the same analysis of the verification plan. Each turn is a separate versioned prompt fetched from Bedrock Prompt Management. The agent sees its full conversation history at each step — no silo problem.

Prompt names follow a descriptive `calledit-` prefix convention:
- `calledit-prediction-parser` — Turn 1: extract claim and resolve dates
- `calledit-verification-planner` — Turn 2: build verification plan with sources, criteria, steps
- `calledit-plan-reviewer` — Turn 3: score verifiability AND identify assumptions for clarification

This spec ports and cleans up the v3 `prompt_client.py` into `calleditv4/src/`, creates 3 new creation prompts in the CloudFormation template, wires the 3-turn flow into the existing entrypoint, saves the prediction bundle to the existing `calledit-db` DynamoDB table, and returns the bundle.

Key Strands SDK feature leveraged: Strands `structured_output_model` parameter (Pydantic models) enables type-safe, validated JSON extraction from each turn without manual JSON parsing. Each turn passes a different Pydantic model to `agent(prompt, structured_output_model=Model)`, and the SDK handles validation and retry automatically. This eliminates the v3 regex JSON parsing problem entirely. Confirmed by Strands docs: conversation history accumulates naturally across multiple `agent()` calls on the same instance, and per-invocation `structured_output_model` overrides are supported.

This spec does NOT cover: clarification rounds (V4-3b), streaming/WebSocket (V4-3b), verifiability score indicator UI (V4-4), Memory integration (V4-6), or production deployment (V4-8).

## Glossary

- **Creation_Agent**: A single Strands_Agent instance that processes 3 sequential prompt turns to transform raw prediction text into a structured Prediction_Bundle. Uses the same agent instance across all 3 turns so conversation history accumulates naturally. Each turn uses Strands `structured_output_model` parameter with a turn-specific Pydantic model for type-safe, validated JSON extraction (confirmed by Strands structured output docs: per-invocation model overrides are supported on the same agent instance)
- **Structured_Output_Model**: A Pydantic BaseModel class passed to `agent(prompt, structured_output_model=Model)` that tells Strands to extract and validate the agent's response into a typed object. The result is available via `result.structured_output`. Strands handles validation and auto-retry on schema mismatch. Each of the 3 turns uses a different model: ParsedClaim, VerificationPlan, PlanReview
- **Prompt_Client**: The module at `calleditv4/src/prompt_client.py` that fetches versioned prompt text from Bedrock Prompt Management via the `bedrock-agent` client `get_prompt()` API. Ported from v3 `backend/calledit-backend/handlers/strands_make_call/prompt_client.py` with Decision 98 fallback behavior
- **Prompt_Management**: AWS Bedrock Prompt Management service that stores versioned prompt text. Prompts are fetched by their 10-character Prompt ID and an optional version number. The CloudFormation stack is at `infrastructure/prompt-management/template.yaml`
- **Prediction_Bundle**: The structured JSON object containing all outputs from the 3-turn creation flow: parsed_claim, verification_plan, verifiability_score, verifiability_reasoning, reviewable_sections, and metadata. Saved to DynamoDB and returned to the caller
- **DDB_Table**: The existing `calledit-db` DynamoDB table used for prediction storage. Prediction bundles are stored with PK `PRED#{prediction_id}` and SK `BUNDLE`
- **Entrypoint**: The Python function decorated with `@app.entrypoint` in `calleditv4/src/main.py` that receives a payload dict, orchestrates the 3-turn creation flow, saves to DynamoDB, and returns the Prediction_Bundle
- **Turn**: A single prompt-response cycle within the Creation_Agent's conversation. Each turn uses a different system-level instruction fetched from Prompt_Management. The 3 turns are: Parse (`calledit-prediction-parser`), Plan (`calledit-verification-planner`), Review (`calledit-plan-reviewer`)
- **Version_Manifest**: A dict tracking which prompt version was used for each turn (e.g., `{"prediction_parser": "1", "verification_planner": "2", "plan_reviewer": "1"}`). Stored in the Prediction_Bundle for observability and reproducibility
- **Verifiability_Score**: A float between 0.0 and 1.0 representing the likelihood that the verification agent will successfully determine the prediction's truth value. Scored across 5 dimensions: criteria specificity (30%), source availability (25%), temporal clarity (20%), outcome objectivity (15%), tool coverage (10%)
- **Environment_Mode**: The runtime environment determined by the `CALLEDIT_ENV` environment variable. Values: `production` (graceful fallback to hardcoded prompts) or any other value including unset (fail clearly on Prompt Management errors). Implements Decision 98
- **Virtual_Environment**: The project Python virtual environment at `/home/wsluser/projects/calledit/venv` used for all Python commands
- **AWS_Region**: The AWS region for Bedrock and DynamoDB clients, resolved by the AWS SDK from the standard AWS configuration chain (CLI config, environment variables, instance metadata). No hardcoded default — the region must be configured via `aws configure` or `AWS_REGION` / `AWS_DEFAULT_REGION` environment variables

## Requirements

### Requirement 1: Prompt Client — Port and Clean Up

**User Story:** As a developer, I want a clean prompt client module in `calleditv4/src/` that fetches versioned prompts from Bedrock Prompt Management, so that all prompt text is managed externally and the agent code contains no hardcoded prompts.

#### Acceptance Criteria

1. THE Prompt_Client SHALL fetch prompt text from Prompt_Management using the `bedrock-agent` client `get_prompt(promptIdentifier, promptVersion)` API, extracting the text from `variants[0].templateConfiguration.text.text` in the response
2. THE Prompt_Client SHALL resolve prompt versions from environment variables named `PROMPT_VERSION_{PROMPT_NAME}` (e.g., `PROMPT_VERSION_PREDICTION_PARSER`), defaulting to `DRAFT` when the environment variable is not set
3. THE Prompt_Client SHALL support variable substitution in prompt text, replacing `{{variable_name}}` placeholders with provided values (e.g., `{{current_date}}` for the parse turn, `{{tool_manifest}}` for the plan turn)
4. THE Prompt_Client SHALL maintain a Version_Manifest dict that records the actual version string returned by Prompt_Management for each fetched prompt, enabling observability of which prompt versions produced a given Prediction_Bundle
5. WHILE Environment_Mode is not `production`, IF a Prompt_Management API call fails, THEN THE Prompt_Client SHALL raise the exception with a clear error message identifying the prompt name and the failure reason
6. WHILE Environment_Mode is `production`, IF a Prompt_Management API call fails, THEN THE Prompt_Client SHALL fall back to a hardcoded default prompt for that turn, log a warning identifying the prompt name and failure reason, and record `fallback` in the Version_Manifest for that prompt
7. THE Prompt_Client SHALL accept a prompt identifier (the 10-character Prompt ID from the CloudFormation stack) and return the resolved prompt text string
8. THE Prompt_Client SHALL NOT import from any v3 agent modules, SHALL NOT use lazy-loaded fallback prompts from external modules, and SHALL NOT reference v3 prompt identifiers

### Requirement 2: Creation Prompts in CloudFormation

**User Story:** As a developer, I want 3 new creation prompts defined in the CloudFormation template, so that the 3-turn creation flow has externally managed, versioned prompt text.

#### Acceptance Criteria

1. THE CloudFormation template at `infrastructure/prompt-management/template.yaml` SHALL define a new Bedrock Prompt resource named `calledit-prediction-parser` with a text variant containing the parse turn instructions: extract the prediction statement, resolve dates relative to the provided current date (via `{{current_date}}` variable), and return structured JSON with `statement`, `verification_date`, and `date_reasoning` fields
2. THE CloudFormation template SHALL define a new Bedrock Prompt resource named `calledit-verification-planner` with a text variant containing the plan turn instructions: build a verification plan with `sources`, `criteria`, and `steps` fields, using the `{{tool_manifest}}` variable to reference available tools
3. THE CloudFormation template SHALL define a new Bedrock Prompt resource named `calledit-plan-reviewer` with a text variant containing the combined review and scoring instructions: evaluate the verification plan across 5 dimensions (criteria specificity 30%, source availability 25%, temporal clarity 20%, outcome objectivity 15%, tool coverage 10%) to produce a `verifiability_score` float (0.0-1.0) with `verifiability_reasoning`, AND identify assumptions in the verification plan to generate targeted clarification questions referencing specific plan elements
4. EACH new prompt resource SHALL have a corresponding `AWS::Bedrock::PromptVersion` resource creating an immutable v1 version
5. EACH new prompt resource SHALL include `Project: calledit` and `Agent: creation` tags
6. THE CloudFormation template SHALL output the Prompt ID and ARN for each new prompt resource
7. THE existing v3 prompt resources (ParserPrompt, CategorizerPrompt, VBPrompt, ReviewPrompt) SHALL remain unchanged in the template — v3 is still live per Decision 95

### Requirement 3: 3-Turn Creation Flow

**User Story:** As a developer, I want the entrypoint to orchestrate 3 sequential prompt turns on a single agent instance, so that raw prediction text is transformed into a structured prediction bundle with full conversation context at each step.

#### Acceptance Criteria

1. WHEN the Entrypoint receives a payload with a `prediction_text` field, THE Entrypoint SHALL create a single Creation_Agent instance and execute 3 sequential turns: Parse, Plan, Review
2. FOR Turn 1 (Parse), THE Entrypoint SHALL fetch the `calledit-prediction-parser` prompt from Prompt_Management with `{{current_date}}` substituted, send it to the Creation_Agent with the raw prediction text using `structured_output_model=ParsedClaim`, and extract the parsed claim (statement, verification_date, date_reasoning) from `result.structured_output`
3. FOR Turn 2 (Plan), THE Entrypoint SHALL fetch the `calledit-verification-planner` prompt from Prompt_Management with `{{tool_manifest}}` substituted with the agent's available tool descriptions, send it to the Creation_Agent (which already has Turn 1 in its conversation history) using `structured_output_model=VerificationPlan`, and extract the verification plan (sources, criteria, steps) from `result.structured_output`
4. FOR Turn 3 (Review), THE Entrypoint SHALL fetch the `calledit-plan-reviewer` prompt from Prompt_Management, send it to the Creation_Agent (which has Turns 1-2 in history) using `structured_output_model=PlanReview`, and extract both the verifiability_score (float 0.0-1.0) with verifiability_reasoning AND the reviewable_sections (clarification questions) from `result.structured_output`
5. THE Entrypoint SHALL assemble the outputs from all 3 turns into a single Prediction_Bundle containing: prediction_id (generated UUID), user_id (from payload), raw_prediction, parsed_claim, verification_plan, verifiability_score, verifiability_reasoning, reviewable_sections, clarification_rounds (0 for V4-3a), created_at (ISO 8601 timestamp), status (`pending`), and prompt_versions (the Version_Manifest)
6. IF any turn raises a `StructuredOutputException` (Strands validation failure), THEN THE Entrypoint SHALL log the raw response and return a structured error identifying which turn failed and the validation issue
7. THE Entrypoint SHALL pass the `user_id` field from the payload to the Prediction_Bundle, defaulting to `anonymous` when the field is not present

### Requirement 4: DynamoDB Save

**User Story:** As a developer, I want the prediction bundle saved to DynamoDB after the 4-turn flow completes, so that the verification agent can load it later and the bundle persists across sessions.

#### Acceptance Criteria

1. WHEN the 3-turn creation flow completes successfully, THE Entrypoint SHALL save the Prediction_Bundle to the DDB_Table with PK `PRED#{prediction_id}` and SK `BUNDLE`
2. THE DDB save SHALL include all Prediction_Bundle fields: prediction_id, user_id, raw_prediction, parsed_claim, verification_plan, verifiability_score, verifiability_reasoning, reviewable_sections, clarification_rounds, created_at, status, and prompt_versions
3. THE DDB save SHALL convert all Python float values to `Decimal` types before writing, using `Decimal(str(value))` for each float field (DynamoDB rejects Python floats per Decision 82)
4. THE Entrypoint SHALL read the DDB_Table name from the `DYNAMODB_TABLE_NAME` environment variable, defaulting to `calledit-db` when the variable is not set
5. IF the DynamoDB `put_item` call fails, THEN THE Entrypoint SHALL log the error with the prediction_id and return the Prediction_Bundle with an additional `save_error` field containing the error message — the bundle is still returned to the caller even if the save fails
6. WHEN the Prediction_Bundle is returned to the caller, THE Entrypoint SHALL return it as a JSON string containing all bundle fields

### Requirement 5: Prediction Bundle Construction and Pydantic Models

**User Story:** As a developer, I want the prediction bundle constructed with consistent field types and validated structure using Pydantic models, so that downstream consumers (verification agent, frontend, eval framework) can rely on the bundle schema, and the Strands structured output feature can validate each turn's response automatically.

#### Acceptance Criteria

1. THE Prediction_Bundle `prediction_id` field SHALL be a UUID v4 string generated at the start of the creation flow, formatted as `pred-{uuid}` (e.g., `pred-550e8400-e29b-41d4-a716-446655440000`)
2. THE codebase SHALL define a `ParsedClaim` Pydantic model with fields: `statement` (str), `verification_date` (str, ISO 8601 datetime), and `date_reasoning` (str) — used as `structured_output_model` for Turn 1
3. THE codebase SHALL define a `VerificationPlan` Pydantic model with fields: `sources` (list[str]), `criteria` (list[str]), and `steps` (list[str]) — used as `structured_output_model` for Turn 2
4. THE codebase SHALL define a `PlanReview` Pydantic model combining scoring and review, with fields: `verifiability_score` (float, ge=0.0, le=1.0), `verifiability_reasoning` (str), and `reviewable_sections` (list of ReviewableSection, each containing `section` (str), `improvable` (bool), `questions` (list[str]), and `reasoning` (str)) — used as `structured_output_model` for Turn 3. Pydantic's field constraints handle score clamping automatically
5. THE Prediction_Bundle `created_at` field SHALL be an ISO 8601 formatted UTC timestamp string generated at bundle assembly time
6. THE Prediction_Bundle `status` field SHALL be the string `pending` for all bundles created by V4-3a
7. THE Prediction_Bundle `prompt_versions` field SHALL be the Version_Manifest dict from the Prompt_Client, containing the actual version string for each of the 3 creation prompts used
8. FOR ALL valid Prediction_Bundles, serializing to JSON then deserializing back SHALL produce an equivalent Prediction_Bundle (round-trip property)
9. THE Prediction_Bundle serializer SHALL format the bundle as a JSON string, and THE Prediction_Bundle deserializer SHALL parse a JSON string back into the bundle dict — both operations SHALL be explicit functions in the codebase for testability
10. ALL Pydantic models SHALL include Field descriptions for each field, enabling Strands to generate accurate tool specifications for the structured output extraction

### Requirement 6: Entrypoint Integration

**User Story:** As a developer, I want the existing entrypoint updated to support the creation flow while preserving backward compatibility with the V4-1/V4-2 simple prompt mode, so that both modes work during development.

#### Acceptance Criteria

1. WHEN the Entrypoint receives a payload containing a `prediction_text` field, THE Entrypoint SHALL execute the 3-turn creation flow and return the Prediction_Bundle as a JSON string
2. WHEN the Entrypoint receives a payload containing a `prompt` field (without `prediction_text`), THE Entrypoint SHALL execute the existing simple prompt mode from V4-1/V4-2 and return the agent response as a string — backward compatibility is preserved
3. IF the Entrypoint receives a payload containing neither `prediction_text` nor `prompt`, THEN THE Entrypoint SHALL return a structured error response indicating the missing field
4. THE Entrypoint SHALL use the same BedrockAgentCoreApp wrapper, `@app.entrypoint` decorator, and `app.run()` pattern established in V4-1
5. THE Entrypoint SHALL configure the Creation_Agent with the Browser and Code Interpreter tools from V4-2, making them available during the Build Plan turn for tool-aware verification planning
6. THE Entrypoint SHALL accept `context` as a `RequestContext` type (from `bedrock_agentcore.context`) instead of a plain dict, aligning with the AgentCore session management pattern documented in AgentCore examples. This enables future session_id support for V4-3b clarification rounds
