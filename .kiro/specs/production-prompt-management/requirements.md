# Requirements Document

## Introduction

Wire the production MakeCallStreamFunction Lambda to use Bedrock Prompt Management instead of falling back to hardcoded prompt constants. The `prompt_client.py` fetch logic already exists and works, but the Lambda lacks the IAM permission (`bedrock-agent:GetPrompt`) and the environment variables (`PROMPT_VERSION_*`) needed to actually call the Bedrock Prompt Management API. This feature adds those two missing pieces to the SAM template, pins to the latest eval-validated prompt versions (parser 1, categorizer 2, VB 2, review 3), and updates the hardcoded fallback constants to match the Prompt Management versions so that even fallback behavior uses current prompts.

## Glossary

- **SAM_Template**: The `backend/calledit-backend/template.yaml` AWS SAM CloudFormation template that defines the MakeCallStreamFunction Lambda and its configuration
- **MakeCallStreamFunction**: The production Lambda function that runs the 4-agent prediction verification pipeline (parser → categorizer → VB → review)
- **Prompt_Client**: The `prompt_client.py` module that fetches versioned prompts from Bedrock Prompt Management via `bedrock-agent:GetPrompt` API, with fallback to bundled constants
- **Prompt_Management_Stack**: The `infrastructure/prompt-management/template.yaml` CloudFormation stack (`calledit-prompts`) that defines the 4 Bedrock Prompts and their versioned iterations
- **Agent_Factory**: A `create_*_agent()` function in each agent module that calls `fetch_prompt()` and falls back to the hardcoded `*_SYSTEM_PROMPT` constant on failure
- **Fallback_Constant**: The hardcoded `*_SYSTEM_PROMPT` string in each agent module, used when Prompt Management API calls fail
- **Version_Pin**: An environment variable (`PROMPT_VERSION_{AGENT_NAME}`) that tells the Prompt_Client which numbered prompt version to fetch instead of DRAFT

## Requirements

### Requirement 1: IAM Permission for Prompt Management API

**User Story:** As a production Lambda, I want permission to call the Bedrock Prompt Management API, so that `fetch_prompt()` succeeds instead of silently falling back to hardcoded constants.

#### Acceptance Criteria

1. THE SAM_Template SHALL include a `bedrock-agent:GetPrompt` IAM policy statement in the MakeCallStreamFunction Policies section
2. WHEN the MakeCallStreamFunction is deployed, THE MakeCallStreamFunction SHALL have permission to call `bedrock-agent:GetPrompt` on all Bedrock Prompt resources in the account
3. THE SAM_Template SHALL scope the `bedrock-agent:GetPrompt` permission to `Resource: '*'` to match the existing Bedrock InvokeModel permission pattern in the same template

### Requirement 2: Prompt Version Environment Variables

**User Story:** As a DevOps engineer, I want the production Lambda pinned to specific eval-validated prompt versions via environment variables, so that prompt rollback is a simple env var change without code deployment.

#### Acceptance Criteria

1. THE SAM_Template SHALL define a `PROMPT_VERSION_PARSER` environment variable on MakeCallStreamFunction with value `1`
2. THE SAM_Template SHALL define a `PROMPT_VERSION_CATEGORIZER` environment variable on MakeCallStreamFunction with value `2`
3. THE SAM_Template SHALL define a `PROMPT_VERSION_VB` environment variable on MakeCallStreamFunction with value `2`
4. THE SAM_Template SHALL define a `PROMPT_VERSION_REVIEW` environment variable on MakeCallStreamFunction with value `3`
5. WHEN the Prompt_Client reads `PROMPT_VERSION_{AGENT_NAME}` from the environment, THE Prompt_Client SHALL pass that value as the `promptVersion` parameter to the `get_prompt` API call

### Requirement 3: Prompt Client Fallback Integrity

**User Story:** As a reliability engineer, I want the prompt fetch fallback path to remain solid, so that the Lambda always starts even if Bedrock Prompt Management is temporarily unavailable.

#### Acceptance Criteria

1. IF the `bedrock-agent:GetPrompt` API call fails for any reason, THEN THE Prompt_Client SHALL log the error and return the bundled Fallback_Constant for that agent
2. IF the `bedrock-agent:GetPrompt` API call fails, THEN THE Prompt_Client SHALL record `"fallback"` in the prompt version manifest for that agent
3. WHEN the Prompt_Client resolves template variables (e.g., `{{tool_manifest}}` for categorizer), THE Prompt_Client SHALL apply variable substitution on both the Prompt Management response and the Fallback_Constant path
4. THE Prompt_Client SHALL use `{{variable}}` double-brace syntax for Prompt Management responses and `{variable}` single-brace syntax for Fallback_Constant `.format()` calls

### Requirement 4: Fallback Constants Updated to Latest Versions

**User Story:** As a developer, I want the hardcoded fallback prompts to match the latest Prompt Management versions, so that even in fallback mode the Lambda uses current prompts rather than stale v1 text.

#### Acceptance Criteria

1. THE parser_agent module SHALL update `PARSER_SYSTEM_PROMPT` to match the text of Prompt Management parser version 1
2. THE categorizer_agent module SHALL update `CATEGORIZER_SYSTEM_PROMPT` to match the text of Prompt Management categorizer version 2
3. THE verification_builder_agent module SHALL update `VERIFICATION_BUILDER_SYSTEM_PROMPT` to match the text of Prompt Management VB version 2
4. THE review_agent module SHALL update `REVIEW_SYSTEM_PROMPT` to match the text of Prompt Management review version 3
5. WHEN a Fallback_Constant is updated, THE Agent_Factory SHALL preserve the existing variable substitution syntax (`{variable}` for `.format()` calls) in the fallback constant

### Requirement 5: Deployment Validation

**User Story:** As a developer, I want to validate that production is actually using Prompt Management prompts after deployment, so that I can confirm the wiring works end-to-end.

#### Acceptance Criteria

1. WHEN the MakeCallStreamFunction starts after deployment, THE Prompt_Client SHALL log the prompt identifier and version number for each successfully fetched prompt
2. WHEN a prediction is processed after deployment, THE Prompt_Client prompt version manifest SHALL contain numbered versions (e.g., `{"parser": "1", "categorizer": "2", "vb": "2", "review": "3"}`) instead of `"fallback"` entries
3. IF any agent shows `"fallback"` in the version manifest after deployment, THEN THE deployment SHALL be considered incomplete and require investigation
