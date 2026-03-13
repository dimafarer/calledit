# Requirements Document

## Introduction

This feature simplifies the CalledIt prediction verifiability system from 5 categories to 3, introduces a DynamoDB-backed tool registry, adds a web search tool as the first registered tool, builds a re-categorization pipeline for graduating predictions when new tools are added, upgrades the verification agent model to Sonnet 4, and cleans up legacy prediction data.

The core insight: `auto_verifiable` should be a growing bucket. Every time a tool is added, predictions naturally promote from `automatable` to `auto_verifiable` without changing the category taxonomy. The old 5-category system encoded implementation details (which tool) rather than meaningful verifiability distinctions.

Future direction: User context profiles (stored personal info like names, locations, preferences) could further reduce `human_only` predictions by providing context that makes them `automatable` or `auto_verifiable`. This is a separate future spec.

## Glossary

- **Categorizer_Agent**: The Strands agent in the prediction pipeline that classifies predictions into verifiability categories. Located at `categorizer_agent.py`.
- **Verification_Agent**: The Strands agent that verifies predictions after their verification date. Located at `verification_agent.py`. Currently uses `claude-3-sonnet-20241022`.
- **Prediction_Pipeline**: The 4-agent graph (Parser → Categorizer → Verification Builder → Review) that processes user predictions. Located at `prediction_graph.py`.
- **Tool_Registry**: A collection of DynamoDB records in the `calledit-db` table that describe available verification tools, their capabilities, schemas, and status.
- **Tool_Record**: A single DynamoDB item representing a registered tool, keyed by `PK=TOOL#{tool_id}` and `SK=METADATA`.
- **Web_Search_Tool**: A custom Strands `@tool` using Python `requests` that performs HTTP requests to verify factual claims (weather, sports, stocks, etc.).
- **Re-categorization_Pipeline**: A triggerable process that scans `automatable` predictions and re-runs each through the full Prediction_Pipeline to determine if they can graduate to `auto_verifiable`.
- **calledit-db**: The existing DynamoDB table used for all CalledIt data (predictions, connections, and now tool records).
- **VALID_CATEGORIES**: The set of allowed verifiability category strings used by the Categorizer_Agent for validation.
- **Verification_Builder_Agent**: The Strands agent that constructs verification method plans (source, criteria, steps) for each prediction.
- **Review_Agent**: The Strands agent that performs meta-analysis on completed prediction responses.

## Requirements

### Requirement 1: Simplify Verifiability Categories from 5 to 3

**User Story:** As a system maintainer, I want the verifiability categories reduced from 5 to 3, so that the category taxonomy reflects meaningful verifiability distinctions rather than implementation details about specific tools.

#### Acceptance Criteria

1. THE Categorizer_Agent SHALL classify predictions into exactly one of three categories: `auto_verifiable`, `automatable`, or `human_only`.
2. THE Categorizer_Agent SHALL assign `auto_verifiable` WHEN the prediction can be verified using the agent's current active toolset (reasoning plus any registered active tools).
3. THE Categorizer_Agent SHALL assign `automatable` WHEN the prediction cannot be verified today but an agent could plausibly find or build a tool to verify it. This is the "automatable in principle" bucket.
4. THE Categorizer_Agent SHALL assign `human_only` WHEN the prediction requires subjective judgment or information that cannot be obtained through any tool or stored context.
5. THE VALID_CATEGORIES set in `categorizer_agent.py` SHALL contain exactly three values: `auto_verifiable`, `automatable`, and `human_only`.
6. THE Categorizer_Agent system prompt SHALL describe the three categories with examples and instruct the agent to select exactly one.

### Requirement 2: Update Verification Agent Category Routing

**User Story:** As a system maintainer, I want the verification agent to route predictions based on the new 3-category system, so that verification logic aligns with the simplified categories.

#### Acceptance Criteria

1. THE Verification_Agent SHALL route `auto_verifiable` predictions to verification using all available active tools from the Tool_Registry.
2. THE Verification_Agent SHALL route `automatable` predictions to an inconclusive result with a tool gap indication, since the required tool does not yet exist.
3. THE Verification_Agent SHALL route `human_only` predictions to an inconclusive result indicating human assessment is required.
4. THE Verification_Agent SHALL handle unknown category values by falling back to inconclusive status with an explanatory message.
5. THE Verification_Agent `verify_prediction()` method SHALL contain routing logic for exactly three categories plus an unknown-category fallback.

### Requirement 3: Upgrade Verification Agent to Sonnet 4

**User Story:** As a system maintainer, I want the verification agent upgraded to Claude Sonnet 4, so that all agents in the system use the same model for consistency and improved instruction following.

#### Acceptance Criteria

1. THE Verification_Agent SHALL use model `us.anthropic.claude-sonnet-4-20250514-v1:0` for all verification invocations.
2. THE Verification_Agent model identifier SHALL match the model used by the Parser, Categorizer, Verification_Builder, and Review agents in the Prediction_Pipeline.

### Requirement 4: Tool Registry in DynamoDB

**User Story:** As a system maintainer, I want a tool registry stored in DynamoDB, so that both the Categorizer_Agent and Verification_Agent can discover available tools at runtime and make informed decisions.

#### Acceptance Criteria

1. THE Tool_Registry SHALL store Tool_Records in the existing `calledit-db` DynamoDB table.
2. WHEN a Tool_Record is stored, THE Tool_Registry SHALL use `TOOL#{tool_id}` as the partition key (PK) and `METADATA` as the sort key (SK).
3. THE Tool_Record SHALL contain the following fields: `name` (string), `description` (string), `capabilities` (list of strings describing what the tool can verify), `input_schema` (dict), `output_schema` (dict), `status` (string: `active` or `inactive`), and `added_date` (ISO 8601 string).
4. THE Tool_Registry SHALL support querying all active tools by filtering on `status = active`.
5. IF a Tool_Record has `status = inactive`, THEN THE Categorizer_Agent and Verification_Agent SHALL treat the tool as unavailable.

### Requirement 5: Categorizer Agent Tool Awareness

**User Story:** As a system maintainer, I want the categorizer agent to be aware of registered tools, so that it can accurately distinguish between `auto_verifiable` (tool exists) and `automatable` (tool could exist but does not).

#### Acceptance Criteria

1. THE Prediction_Pipeline SHALL read all active Tool_Records from the Tool_Registry at graph creation time (module level, cached by SnapStart).
2. THE Categorizer_Agent system prompt SHALL include a manifest of active tools listing each tool's name, description, and capabilities.
3. WHEN an active tool's capabilities match a prediction's verification needs, THE Categorizer_Agent SHALL classify the prediction as `auto_verifiable`.
4. WHEN no active tool's capabilities match a prediction's verification needs but a reasonable tool could exist, THE Categorizer_Agent SHALL classify the prediction as `automatable`.
5. IF the Tool_Registry contains zero active tools, THEN THE Categorizer_Agent SHALL rely on pure reasoning capabilities to determine if a prediction is `auto_verifiable` (reasoning alone suffices) or `automatable` (external data needed).

### Requirement 6: Verification Agent Tool Loading

**User Story:** As a system maintainer, I want the verification agent to load active tools from the registry, so that it can use registered tools for verifying `auto_verifiable` predictions.

#### Acceptance Criteria

1. THE Verification_Agent SHALL read active Tool_Records from the Tool_Registry to determine available verification methods.
2. WHEN verifying an `auto_verifiable` prediction, THE Verification_Agent SHALL have access to all active registered tools in its tool list.
3. IF a registered tool fails during verification, THEN THE Verification_Agent SHALL log the error and fall back to reasoning-based verification.

### Requirement 7: Web Search Tool

**User Story:** As a system maintainer, I want a web search tool registered in the tool registry, so that the verification agent can verify factual claims about weather, sports scores, stock prices, and other web-accessible data.

#### Acceptance Criteria

1. THE Web_Search_Tool SHALL be implemented as a Strands `@tool` decorated function using the Python `requests` library for HTTP requests.
2. THE Web_Search_Tool SHALL accept a search query string as input and return structured results the Verification_Agent can reason about.
3. THE Web_Search_Tool SHALL be registered in the Tool_Registry with a Tool_Record containing: name, description, capabilities (list of verifiable claim types), input_schema, output_schema, status `active`, and added_date.
4. WHEN the Web_Search_Tool is registered and active, THE Verification_Agent SHALL include the Web_Search_Tool in its available tools for verifying `auto_verifiable` predictions.
5. IF the Web_Search_Tool HTTP request fails or times out, THEN THE Web_Search_Tool SHALL return a structured error response rather than raising an exception.

### Requirement 8: Pipeline Result Parsing Compatibility

**User Story:** As a system maintainer, I want the pipeline result parsing to work with the new 3-category system, so that fallback defaults and error handling remain correct.

#### Acceptance Criteria

1. THE Prediction_Pipeline result parser SHALL use `human_only` as the fallback category when the Categorizer_Agent output cannot be parsed.
2. THE `write_to_db` handler SHALL persist the new category values (`auto_verifiable`, `automatable`, `human_only`) to DynamoDB without requiring code changes, since the prediction dict is spread into the DDB item.
3. WHEN a prediction is stored in DynamoDB, THE stored `verifiable_category` field SHALL contain one of the three valid category values.

### Requirement 9: Re-categorization Pipeline

**User Story:** As a system maintainer, I want a triggerable re-categorization pipeline, so that when a new tool is added to the registry, existing `automatable` predictions can be re-evaluated and graduated to `auto_verifiable` if the new tool matches their verification needs.

#### Acceptance Criteria

1. THE Re-categorization_Pipeline SHALL scan all predictions in `calledit-db` with `verifiable_category = automatable`.
2. THE Re-categorization_Pipeline SHALL re-run each scanned prediction through the full Prediction_Pipeline (Parser → Categorizer → Verification Builder → Review).
3. WHEN the Prediction_Pipeline re-categorizes a prediction as `auto_verifiable`, THE Re-categorization_Pipeline SHALL update the DynamoDB record with the new category, verification_method, and any other changed fields.
4. WHEN the Prediction_Pipeline re-categorizes a prediction and the category remains `automatable`, THE Re-categorization_Pipeline SHALL retain the existing DynamoDB record without modification.
5. THE Re-categorization_Pipeline SHALL be invocable via Lambda invocation or script execution, not triggered automatically.
6. THE Re-categorization_Pipeline SHALL log the count of predictions scanned, re-categorized, and unchanged.

### Requirement 10: SAM Template Policy Updates

**User Story:** As a system maintainer, I want the SAM template updated with necessary IAM policies, so that Lambda functions can read from the tool registry in DynamoDB.

#### Acceptance Criteria

1. THE MakeCallStreamFunction (Prediction_Pipeline Lambda) SHALL have DynamoDB read permissions for Tool_Registry records in the `calledit-db` table.
2. THE VerificationFunction SHALL have DynamoDB read permissions for Tool_Registry records in the `calledit-db` table.
3. WHEN the existing `DynamoDBCrudPolicy` for `calledit-db` already covers Tool_Registry access, THE SAM template SHALL require no additional policy changes for that function.

### Requirement 11: Clean Up Legacy Prediction Data

**User Story:** As a system maintainer, I want legacy prediction data removed from DynamoDB, so that the system starts fresh with the new 3-category taxonomy and no stale data from the old 5-category system.

#### Acceptance Criteria

1. ALL existing prediction records (PK starting with `USER:`, SK starting with `PREDICTION#`) SHALL be deleted from the `calledit-db` table before deploying the new category system.
2. THE cleanup SHALL NOT delete Tool_Registry records, connection records, or any non-prediction data.
3. THE cleanup SHALL be performed as a one-time manual operation (script or console), not as an automated deployment step.
