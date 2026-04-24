# Requirements Document

## Introduction

Migrate the two AgentCore agent deployments (creation agent and verification agent) from the deprecated `.bedrock_agentcore.yaml` Python toolkit to the new `@aws/agentcore` npm CLI with CDK-based deployment. This replaces three deployment mechanisms — two `.bedrock_agentcore.yaml` files and one manual IAM shell script — with two declarative `agentcore.json` configurations and a single CDK stack for IAM permissions. Agent source code (Python) remains unchanged. The four existing SAM/CloudFormation stacks remain untouched.

## Glossary

- **Creation_Agent**: The user-facing AgentCore runtime (`calleditv4/`) that handles prediction creation via WebSocket streaming with JWT/Cognito auth. Agent ID: `calleditv4_Agent-AJiwpKBxRW`.
- **Verification_Agent**: The batch AgentCore runtime (`calleditv4-verification/`) that verifies predictions via SigV4 HTTPS invocation. Agent ID: `calleditv4_verification_Agent-77DiT7GHdH`.
- **AgentCore_CLI**: The `@aws/agentcore` npm package that replaces the deprecated Python toolkit. Uses `agentcore.json` for declarative configuration and `agentcore deploy` for deployment.
- **Deployment_Config**: An `agentcore.json` file in each agent directory that declaratively specifies runtime type, entrypoint, environment variables, network mode, memory mode, authorizer configuration, and AWS settings.
- **CDK_Permissions_Stack**: A CDK stack (`infrastructure/agentcore-cdk/`) that manages IAM inline policies on the AgentCore execution roles, replacing the manual `setup_agentcore_permissions.sh` shell script.
- **Execution_Role**: The IAM role assumed by an AgentCore runtime during execution. Each agent has its own auto-created role.
- **Scanner_Lambda**: The EventBridge-triggered Lambda (`infrastructure/verification-scanner/`) that invokes the Verification_Agent by agent ID. Its `samconfig.toml` contains the `VerificationAgentId` parameter.

## Requirements

### Requirement 1: Creation Agent Deployment Config

**User Story:** As a developer, I want the Creation_Agent deployment to be defined in a declarative `agentcore.json` file, so that deployment configuration is version-controlled and reproducible.

#### Acceptance Criteria

1. THE Deployment_Config for the Creation_Agent SHALL be located at `calleditv4/agentcore.json`
2. THE Deployment_Config SHALL specify `runtimeType` as `PYTHON_3_12`, `platform` as `linux/arm64`, `networkMode` as `PUBLIC`, and `serverProtocol` as `HTTP`
3. THE Deployment_Config SHALL specify the `entrypoint` as `src/main.py` and `sourcePath` as the agent project root
4. THE Deployment_Config SHALL specify `memoryMode` as `STM_ONLY` with the existing memory ID `calleditv4_Agent_mem-JVB6D78I1x`
5. THE Deployment_Config SHALL specify the Cognito JWT authorizer with `discoveryUrl` pointing to `https://cognito-idp.us-west-2.amazonaws.com/us-west-2_GOEwUjJtv/.well-known/openid-configuration` and `allowedClients` containing `753gn25jle081ajqabpd4lbin9`
6. THE Deployment_Config SHALL specify `requestHeaderAllowlist` containing `Authorization`
7. THE Deployment_Config SHALL specify the existing execution role ARN `arn:aws:iam::894249332178:role/AmazonBedrockAgentCoreSDKRuntime-us-west-2-5a297cfdfd`
8. THE Deployment_Config SHALL specify the existing agent ID `calleditv4_Agent-AJiwpKBxRW` so that deployment updates the existing runtime rather than creating a new one
9. WHEN `agentcore deploy` is run from the `calleditv4/` directory, THE AgentCore_CLI SHALL deploy the Creation_Agent using the configuration from `agentcore.json`

### Requirement 2: Verification Agent Deployment Config

**User Story:** As a developer, I want the Verification_Agent deployment to be defined in a declarative `agentcore.json` file with environment variables included, so that critical env vars like BRAVE_API_KEY are never forgotten during deployment.

#### Acceptance Criteria

1. THE Deployment_Config for the Verification_Agent SHALL be located at `calleditv4-verification/agentcore.json`
2. THE Deployment_Config SHALL specify `runtimeType` as `PYTHON_3_10`, `platform` as `linux/amd64`, `networkMode` as `PUBLIC`, and `serverProtocol` as `HTTP`
3. THE Deployment_Config SHALL specify the `entrypoint` as `src/main.py` and `sourcePath` as the agent project root
4. THE Deployment_Config SHALL specify `memoryMode` as `NO_MEMORY`
5. THE Deployment_Config SHALL specify the existing execution role ARN `arn:aws:iam::894249332178:role/AmazonBedrockAgentCoreSDKRuntime-us-west-2-37c792a758`
6. THE Deployment_Config SHALL specify the existing agent ID `calleditv4_verification_Agent-77DiT7GHdH` so that deployment updates the existing runtime rather than creating a new one
7. THE Deployment_Config SHALL declare environment variables `BRAVE_API_KEY` and `VERIFICATION_TOOLS` so that they are set on every deployment without manual `--env` flags
8. THE Deployment_Config SHALL reference `BRAVE_API_KEY` via an environment variable substitution pattern (e.g., `${BRAVE_API_KEY}`) so that the secret value is never hardcoded in the config file
9. WHEN `agentcore deploy` is run from the `calleditv4-verification/` directory, THE AgentCore_CLI SHALL deploy the Verification_Agent with all declared environment variables applied

### Requirement 3: CDK Stack for IAM Permissions

**User Story:** As a developer, I want IAM permissions for both AgentCore execution roles to be managed by a CDK stack, so that permissions are version-controlled, auditable, and reproducible without running manual shell scripts.

#### Acceptance Criteria

1. THE CDK_Permissions_Stack SHALL be located in `infrastructure/agentcore-cdk/`
2. THE CDK_Permissions_Stack SHALL attach inline policies to the Verification_Agent execution role granting DynamoDB access to `calledit-v4` (GetItem, PutItem, UpdateItem, Query on table and indexes) and `calledit-v4-eval` (GetItem, PutItem, UpdateItem, DeleteItem)
3. THE CDK_Permissions_Stack SHALL attach an inline policy to the Verification_Agent execution role granting `bedrock:GetPrompt` on all prompts in the account
4. THE CDK_Permissions_Stack SHALL attach inline policies to both execution roles granting AgentCore Browser permissions on both account-scoped and AWS system-owned browser resources
5. THE CDK_Permissions_Stack SHALL attach an inline policy to the Creation_Agent execution role granting DynamoDB access to `calledit-v4-eval` (GetItem, PutItem, UpdateItem, DeleteItem)
6. THE CDK_Permissions_Stack SHALL import the existing execution roles by ARN using `iam.Role.fromRoleArn()` rather than creating new roles
7. THE CDK_Permissions_Stack SHALL produce identical effective permissions to the current `setup_agentcore_permissions.sh` script
8. IF the CDK stack deployment fails, THEN THE CDK_Permissions_Stack SHALL not modify any existing inline policies (CloudFormation rollback behavior)

### Requirement 4: Agent Identity Preservation

**User Story:** As a developer, I want the migration to preserve existing agent IDs and ARNs, so that the Scanner_Lambda and other integrations continue to work without modification.

#### Acceptance Criteria

1. WHEN the Creation_Agent is deployed via the AgentCore_CLI, THE Creation_Agent SHALL retain agent ID `calleditv4_Agent-AJiwpKBxRW` and ARN `arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_Agent-AJiwpKBxRW`
2. WHEN the Verification_Agent is deployed via the AgentCore_CLI, THE Verification_Agent SHALL retain agent ID `calleditv4_verification_Agent-77DiT7GHdH` and ARN `arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_verification_Agent-77DiT7GHdH`
3. THE Scanner_Lambda `samconfig.toml` parameter `VerificationAgentId` SHALL remain `calleditv4_verification_Agent-77DiT7GHdH` with no changes required
4. THE Scanner_Lambda template SHALL NOT be modified as part of this migration

### Requirement 5: Deprecated Config Cleanup

**User Story:** As a developer, I want the deprecated `.bedrock_agentcore.yaml` files and the manual IAM script to be clearly marked as superseded, so that no one accidentally uses the old deployment path.

#### Acceptance Criteria

1. WHEN the migration is complete, THE `.bedrock_agentcore.yaml` file in `calleditv4/` SHALL be deleted or renamed to `.bedrock_agentcore.yaml.deprecated`
2. WHEN the migration is complete, THE `.bedrock_agentcore.yaml` file in `calleditv4-verification/` SHALL be deleted or renamed to `.bedrock_agentcore.yaml.deprecated`
3. WHEN the migration is complete, THE `setup_agentcore_permissions.sh` script SHALL be deleted or renamed to `setup_agentcore_permissions.sh.deprecated`
4. WHEN the migration is complete, THE `.bedrock_agentcore/` directories in both agent folders SHALL be deleted or added to `.gitignore`

### Requirement 6: Agent Source Code Preservation

**User Story:** As a developer, I want the agent Python source code to remain completely unchanged, so that the migration is purely a deployment wrapper change with zero risk to agent behavior.

#### Acceptance Criteria

1. THE migration SHALL NOT modify any Python files in `calleditv4/src/`
2. THE migration SHALL NOT modify any Python files in `calleditv4-verification/src/`
3. THE migration SHALL NOT modify `calleditv4/pyproject.toml` or `calleditv4-verification/pyproject.toml`
4. THE migration SHALL NOT modify any files in the four SAM stack directories (`infrastructure/v4-persistent-resources/`, `infrastructure/v4-frontend/`, `infrastructure/verification-scanner/`, `infrastructure/prompt-management/`)

### Requirement 7: Deployment Documentation

**User Story:** As a developer, I want clear deployment instructions for the new CDK + agentcore.json workflow, so that future deployments are straightforward and don't regress to the old manual process.

#### Acceptance Criteria

1. THE migration SHALL include a `README.md` in `infrastructure/agentcore-cdk/` documenting how to deploy the CDK permissions stack
2. THE migration SHALL include deployment instructions in each agent's `agentcore.json` directory (or update existing READMEs) documenting the `agentcore deploy` command
3. THE documentation SHALL specify that `BRAVE_API_KEY` must be set as a shell environment variable before deploying the Verification_Agent
4. THE documentation SHALL list the prerequisite: `npm install -g @aws/agentcore` (or equivalent local install)
