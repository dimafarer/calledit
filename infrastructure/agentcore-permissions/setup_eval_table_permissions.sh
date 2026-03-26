#!/bin/bash
# Add required permissions to the AgentCore execution role for the verification agent eval.
#
# Context: The AgentCore auto-created execution role (AmazonBedrockAgentCoreSDKRuntime-*)
# only includes permissions for ECR, CloudWatch, X-Ray, and Bedrock model invocation.
# Custom permissions like DynamoDB access and Prompt Management must be added via
# iam:PutRolePolicy.
# See: https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/permissions.md
#
# This script adds:
# 1. DynamoDB access for calledit-v4-eval table (eval isolation)
# 2. Bedrock GetPrompt for Prompt Management (verification executor prompt)
#
# The creation agent's role already has these via inline policies added in Update 29.
# This script ensures the verification agent has them too.
#
# Usage: bash infrastructure/agentcore-permissions/setup_eval_table_permissions.sh

set -euo pipefail

ROLE_NAME="AmazonBedrockAgentCoreSDKRuntime-us-west-2-37c792a758"
ACCOUNT_ID="894249332178"
REGION="us-west-2"

echo "=== Adding permissions to AgentCore execution role ==="
echo "Role: ${ROLE_NAME}"
echo ""

# 1. DynamoDB access for eval table
echo "1. Adding DynamoDB permissions for calledit-v4-eval..."
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

# 2. Bedrock Prompt Management + Model Invocation
# (The auto-created role has InvokeModel but may not have GetPrompt)
echo "2. Adding Bedrock GetPrompt permission..."
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

echo ""
echo "=== All permissions applied ==="
echo ""
echo "Verify with:"
echo "  aws iam list-role-policies --role-name ${ROLE_NAME}"
