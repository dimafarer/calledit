# AgentCore Permissions CDK Stack

Manages IAM inline policies on the auto-created AgentCore execution roles. Replaces the manual `setup_agentcore_permissions.sh` shell script with IaC.

## What This Stack Manages

| Policy | Role | Resources |
|--------|------|-----------|
| DynamoDB calledit-v4 | Verification | GetItem, PutItem, UpdateItem, Query on table + indexes |
| DynamoDB calledit-v4-eval | Both | GetItem, PutItem, UpdateItem, DeleteItem |
| Bedrock GetPrompt | Verification | All prompts in account |
| AgentCore Browser (account) | Both | All 11 browser actions on account-scoped resources |
| AgentCore Browser (system) | Both | 8 session actions on AWS system-owned browser |

## Prerequisites

- Node.js 18+
- AWS CDK bootstrapped in us-west-2 (`npx cdk bootstrap aws://894249332178/us-west-2`)
- AWS credentials configured

## Deploy

```bash
cd infrastructure/agentcore-cdk
npm install
npx cdk deploy
```

## Verify

```bash
aws iam list-role-policies --role-name AmazonBedrockAgentCoreSDKRuntime-us-west-2-37c792a758
aws iam list-role-policies --role-name AmazonBedrockAgentCoreSDKRuntime-us-west-2-5a297cfdfd
```

## Rollback

```bash
npx cdk destroy
```

Then re-run `setup_agentcore_permissions.sh` if needed.

## Agent Deployment

After the CDK stack is deployed, deploy agents using the helper scripts:

```bash
# Creation agent
source .env
cd calleditv4 && ./deploy.sh

# Verification agent (validates BRAVE_API_KEY is set)
source .env
cd calleditv4-verification && ./deploy.sh
```

## Full Deployment Order

1. `cd infrastructure/agentcore-cdk && npx cdk deploy` — IAM permissions
2. `cd calleditv4 && ./deploy.sh` — Creation agent
3. `source .env && cd calleditv4-verification && ./deploy.sh` — Verification agent (needs BRAVE_API_KEY)
