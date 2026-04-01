#!/bin/bash
# Add all custom permissions to the AgentCore execution role.
#
# Context: The AgentCore auto-created execution role (AmazonBedrockAgentCoreSDKRuntime-*)
# only includes permissions for ECR, CloudWatch, X-Ray, Bedrock model invocation, and
# Code Interpreter. Custom permissions like DynamoDB access, Prompt Management, and
# Browser tool access must be added via iam:PutRolePolicy.
#
# See: https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/permissions.md
#
# Why not CloudFormation? The role is auto-created by `agentcore launch`, not managed
# by any of our CF stacks. Importing it would be fragile — agentcore may recreate it.
# Inline policies via put-role-policy are idempotent and safe to re-run.
#
# This script adds:
# 1. DynamoDB access for calledit-v4 (production predictions)
# 2. DynamoDB access for calledit-v4-eval (eval isolation)
# 3. Bedrock GetPrompt for Prompt Management
# 4. AgentCore Browser tool permissions (Decision 144)
#
# Usage: bash infrastructure/agentcore-permissions/setup_agentcore_permissions.sh
#
# Safe to re-run — all put-role-policy calls are idempotent (upsert).

set -euo pipefail

ROLE_NAME="AmazonBedrockAgentCoreSDKRuntime-us-west-2-37c792a758"
CREATION_ROLE_NAME="AmazonBedrockAgentCoreSDKRuntime-us-west-2-5a297cfdfd"
ACCOUNT_ID="894249332178"
REGION="us-west-2"

echo "=== Adding permissions to AgentCore execution roles ==="
echo "Verification Role: ${ROLE_NAME}"
echo "Creation Role: ${CREATION_ROLE_NAME}"
echo ""

# 1. DynamoDB access for production table
echo "1. Adding DynamoDB permissions for calledit-v4..."
aws iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name "calledit-v4-dynamodb" \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": [
        \"dynamodb:GetItem\",
        \"dynamodb:PutItem\",
        \"dynamodb:UpdateItem\",
        \"dynamodb:Query\"
      ],
      \"Resource\": [
        \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/calledit-v4\",
        \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/calledit-v4/index/*\"
      ]
    }]
  }"
echo "   ✓ calledit-v4-dynamodb policy attached"

# 2. DynamoDB access for eval table
echo "2. Adding DynamoDB permissions for calledit-v4-eval..."
aws iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name "calledit-v4-eval-dynamodb" \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": [
        \"dynamodb:GetItem\",
        \"dynamodb:PutItem\",
        \"dynamodb:UpdateItem\",
        \"dynamodb:DeleteItem\"
      ],
      \"Resource\": \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/calledit-v4-eval\"
    }]
  }"
echo "   ✓ calledit-v4-eval-dynamodb policy attached"

# 2b. DynamoDB access for eval table — CREATION agent role
echo "2b. Adding DynamoDB permissions for calledit-v4-eval (creation agent)..."
aws iam put-role-policy \
  --role-name "${CREATION_ROLE_NAME}" \
  --policy-name "calledit-v4-eval-dynamodb" \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": [
        \"dynamodb:GetItem\",
        \"dynamodb:PutItem\",
        \"dynamodb:UpdateItem\",
        \"dynamodb:DeleteItem\"
      ],
      \"Resource\": \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/calledit-v4-eval\"
    }]
  }"
echo "   ✓ calledit-v4-eval-dynamodb policy attached (creation agent)"

# 3. Bedrock Prompt Management
echo "3. Adding Bedrock GetPrompt permission..."
aws iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name "calledit-bedrock-prompts" \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": [
        \"bedrock:GetPrompt\"
      ],
      \"Resource\": \"arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:prompt/*\"
    }]
  }"
echo "   ✓ calledit-bedrock-prompts policy attached"

# 4. AgentCore Browser tool (Decision 144, fixed in Decision 149)
# The auto-created role includes Code Interpreter but NOT Browser.
# Without this, all Browser tool calls fail with AccessDeniedException.
#
# CRITICAL: The system browser (aws.browser.v1) is an AWS-owned resource
# with ARN arn:aws:bedrock-agentcore:REGION:aws:browser/aws.browser.v1
# (note "aws" instead of account ID). The original policy only covered
# account-scoped resources (ACCOUNT_ID:browser/*), which is why Browser
# failed in the deployed runtime despite having "full" permissions.
echo "4. Adding AgentCore Browser permissions..."
aws iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name "calledit-agentcore-browser" \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Sid\": \"BedrockAgentCoreBrowserAccountScoped\",
      \"Effect\": \"Allow\",
      \"Action\": [
        \"bedrock-agentcore:CreateBrowser\",
        \"bedrock-agentcore:GetBrowser\",
        \"bedrock-agentcore:DeleteBrowser\",
        \"bedrock-agentcore:ListBrowsers\",
        \"bedrock-agentcore:StartBrowserSession\",
        \"bedrock-agentcore:GetBrowserSession\",
        \"bedrock-agentcore:StopBrowserSession\",
        \"bedrock-agentcore:ListBrowserSessions\",
        \"bedrock-agentcore:UpdateBrowserStream\",
        \"bedrock-agentcore:ConnectBrowserAutomationStream\",
        \"bedrock-agentcore:ConnectBrowserLiveViewStream\"
      ],
      \"Resource\": \"arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:browser/*\"
    },
    {
      \"Sid\": \"BedrockAgentCoreBrowserSystemOwned\",
      \"Effect\": \"Allow\",
      \"Action\": [
        \"bedrock-agentcore:StartBrowserSession\",
        \"bedrock-agentcore:GetBrowserSession\",
        \"bedrock-agentcore:StopBrowserSession\",
        \"bedrock-agentcore:ListBrowserSessions\",
        \"bedrock-agentcore:UpdateBrowserStream\",
        \"bedrock-agentcore:ConnectBrowserAutomationStream\",
        \"bedrock-agentcore:ConnectBrowserLiveViewStream\"
      ],
      \"Resource\": \"arn:aws:bedrock-agentcore:${REGION}:aws:browser/*\"
    }]
  }"
echo "   ✓ calledit-agentcore-browser policy attached (account + system-owned)"

# 4b. AgentCore Browser tool — CREATION agent role
# The creation agent needs Browser tool access so the LLM sees correct tool
# schemas during planning/review turns (Requirement 9, Decision 149).
echo "4b. Adding AgentCore Browser permissions (creation agent)..."
aws iam put-role-policy \
  --role-name "${CREATION_ROLE_NAME}" \
  --policy-name "calledit-agentcore-browser" \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Sid\": \"BedrockAgentCoreBrowserAccountScoped\",
      \"Effect\": \"Allow\",
      \"Action\": [
        \"bedrock-agentcore:CreateBrowser\",
        \"bedrock-agentcore:GetBrowser\",
        \"bedrock-agentcore:DeleteBrowser\",
        \"bedrock-agentcore:ListBrowsers\",
        \"bedrock-agentcore:StartBrowserSession\",
        \"bedrock-agentcore:GetBrowserSession\",
        \"bedrock-agentcore:StopBrowserSession\",
        \"bedrock-agentcore:ListBrowserSessions\",
        \"bedrock-agentcore:UpdateBrowserStream\",
        \"bedrock-agentcore:ConnectBrowserAutomationStream\",
        \"bedrock-agentcore:ConnectBrowserLiveViewStream\"
      ],
      \"Resource\": \"arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:browser/*\"
    },
    {
      \"Sid\": \"BedrockAgentCoreBrowserSystemOwned\",
      \"Effect\": \"Allow\",
      \"Action\": [
        \"bedrock-agentcore:StartBrowserSession\",
        \"bedrock-agentcore:GetBrowserSession\",
        \"bedrock-agentcore:StopBrowserSession\",
        \"bedrock-agentcore:ListBrowserSessions\",
        \"bedrock-agentcore:UpdateBrowserStream\",
        \"bedrock-agentcore:ConnectBrowserAutomationStream\",
        \"bedrock-agentcore:ConnectBrowserLiveViewStream\"
      ],
      \"Resource\": \"arn:aws:bedrock-agentcore:${REGION}:aws:browser/*\"
    }]
  }"
echo "   ✓ calledit-agentcore-browser policy attached (creation agent)"

echo ""
echo "=== All permissions applied ==="
echo ""
echo "Verify with:"
echo "  aws iam list-role-policies --role-name ${ROLE_NAME}"
echo ""
echo "Current policies:"
aws iam list-role-policies --role-name "${ROLE_NAME}" --output table
