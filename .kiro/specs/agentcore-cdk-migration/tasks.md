# Implementation Plan: AgentCore CDK Migration

## Overview

Migrate two AgentCore agent deployments from deprecated `.bedrock_agentcore.yaml` to `@aws/agentcore` npm CLI with `agentcore.json` configs and a CDK stack for IAM permissions. Agent source code and SAM stacks remain untouched. Implementation order: CDK stack first (IAM permissions), then agent configs, then deploy scripts, then cleanup.

## Tasks

- [x] 1. Create CDK permissions stack
  - [x] 1.1 Initialize CDK project in `infrastructure/agentcore-cdk/`
    - Create `package.json` with `aws-cdk-lib`, `constructs`, and `ts-jest` dependencies
    - Create `tsconfig.json`, `cdk.json`, and `bin/agentcore-cdk.ts` entry point
    - _Requirements: 3.1_

  - [x] 1.2 Implement `AgentcorePermissionsStack` in `lib/agentcore-permissions-stack.ts`
    - Import both existing execution roles by ARN using `iam.Role.fromRoleArn()` with `{ mutable: true }`
    - Attach verification role: DynamoDB calledit-v4 (GetItem, PutItem, UpdateItem, Query on table + indexes)
    - Attach both roles: DynamoDB calledit-v4-eval (GetItem, PutItem, UpdateItem, DeleteItem)
    - Attach verification role: Bedrock GetPrompt on `prompt/*`
    - Attach both roles: AgentCore Browser permissions (account-scoped + system-owned `aws:browser/*`)
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [ ]* 1.3 Write CDK assertion tests in `test/agentcore-permissions-stack.test.ts`
    - Assert no `AWS::IAM::Role` resources are created (roles are imported)
    - Assert verification role has DynamoDB calledit-v4 inline policy with correct actions and resources
    - Assert both roles have DynamoDB calledit-v4-eval inline policy
    - Assert verification role has Bedrock GetPrompt inline policy
    - Assert both roles have Browser permissions (account-scoped and system-owned)
    - Assert system-owned browser policy excludes Create/Delete/ListBrowsers actions
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 2. Checkpoint - Ensure CDK stack synthesizes and tests pass
  - Run `npm install` and `npm test` in `infrastructure/agentcore-cdk/`
  - Run `npx cdk synth` to verify CloudFormation template generates correctly
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Create agent deployment configs
  - [ ] 3.1 Create `calleditv4/agentcore.json` for the creation agent
    - Set `runtimeType: PYTHON_3_12`, `platform: linux/arm64`, `networkMode: PUBLIC`, `protocol: HTTP`
    - Set `entrypoint: src/main.py`, `codeLocation: .`
    - Set `memory: shortTerm` with `memoryConfig.memoryId: calleditv4_Agent_mem-JVB6D78I1x`
    - Set Cognito JWT authorizer with discovery URL and allowed client `753gn25jle081ajqabpd4lbin9`
    - Set `requestHeaderAllowlist: ["Authorization"]`
    - Set `agentId: calleditv4_Agent-AJiwpKBxRW` to preserve existing runtime
    - Set `aws.executionRoleArn` to the creation role ARN
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

  - [ ] 3.2 Create `calleditv4-verification/agentcore.json` for the verification agent
    - Set `runtimeType: PYTHON_3_10`, `platform: linux/amd64`, `networkMode: PUBLIC`, `protocol: HTTP`
    - Set `entrypoint: src/main.py`, `codeLocation: .`
    - Set `memory: none` (no memory)
    - Set `agentId: calleditv4_verification_Agent-77DiT7GHdH` to preserve existing runtime
    - Set `aws.executionRoleArn` to the verification role ARN
    - No authorizer configuration (SigV4 invocation only)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 4. Create deploy helper scripts
  - [x] 4.1 Create `calleditv4/deploy.sh`
    - Simple wrapper that runs `agentcore deploy`
    - Make executable with `chmod +x`
    - _Requirements: 1.9_

  - [x] 4.2 Create `calleditv4-verification/deploy.sh`
    - Validate `BRAVE_API_KEY` is set, exit with error if missing
    - Run `agentcore deploy --env BRAVE_API_KEY=$BRAVE_API_KEY --env VERIFICATION_TOOLS=${VERIFICATION_TOOLS:-brave}`
    - Make executable with `chmod +x`
    - _Requirements: 2.7, 2.8, 2.9_

- [ ] 5. Checkpoint - Verify configs and scripts are correct
  - Validate both `agentcore.json` files have all required fields matching design spec
  - Verify `deploy.sh` scripts are executable and syntactically valid
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Create documentation
  - [x] 6.1 Create `infrastructure/agentcore-cdk/README.md`
    - Document prerequisites (`npm install -g @aws/agentcore`, Node.js)
    - Document CDK deploy command (`cd infrastructure/agentcore-cdk && npm install && npx cdk deploy`)
    - Document what permissions the stack manages and for which roles
    - Document rollback: `npx cdk destroy`
    - _Requirements: 7.1, 7.4_

  - [x] 6.2 Update agent deployment documentation
    - Add deployment instructions to `calleditv4/README.md` for `agentcore deploy` workflow
    - Create or update `calleditv4-verification/README.md` with deploy instructions
    - Document that `BRAVE_API_KEY` must be set before deploying verification agent
    - Document the full deployment order: CDK stack → creation agent → verification agent
    - _Requirements: 7.2, 7.3, 7.4_

- [ ] 7. Deprecate old configuration files
  - [ ] 7.1 Rename deprecated files
    - Rename `calleditv4/.bedrock_agentcore.yaml` to `.bedrock_agentcore.yaml.deprecated`
    - Rename `calleditv4-verification/.bedrock_agentcore.yaml` to `.bedrock_agentcore.yaml.deprecated`
    - Rename `infrastructure/agentcore-permissions/setup_agentcore_permissions.sh` to `setup_agentcore_permissions.sh.deprecated`
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ] 7.2 Update `.gitignore` for old toolkit directories
    - Add `calleditv4/.bedrock_agentcore/` to `.gitignore`
    - Add `calleditv4-verification/.bedrock_agentcore/` to `.gitignore`
    - _Requirements: 5.4_

- [ ] 8. Final checkpoint - Verify migration integrity
  - Confirm no Python files in `calleditv4/src/` or `calleditv4-verification/src/` were modified
  - Confirm no `pyproject.toml` files were modified
  - Confirm no files in the four SAM stack directories were modified
  - Ensure all tests pass, ask the user if questions arise.
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- The CDK stack must be deployed before agent configs to ensure IAM permissions are in place
- Agent IDs are preserved in both `agentcore.json` files to avoid breaking Scanner Lambda and other integrations
