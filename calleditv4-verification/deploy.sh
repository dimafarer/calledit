#!/bin/bash
# Deploy the CalledIt v4 Verification Agent to AgentCore Runtime.
#
# IMPORTANT: BRAVE_API_KEY must be set in your shell environment.
# The key comes from .env (gitignored) — never hardcode it.
#
# Prerequisites:
#   - source .env (for AWS credentials + BRAVE_API_KEY)
#   - agentcore CLI installed (pip install bedrock-agentcore-starter-toolkit)
#
# Usage:
#   source ../.env && cd calleditv4-verification && ./deploy.sh

set -euo pipefail

# Validate required env vars
if [ -z "${BRAVE_API_KEY:-}" ]; then
  echo "❌ ERROR: BRAVE_API_KEY must be set in your shell environment" >&2
  echo "   Run: source .env" >&2
  exit 1
fi

echo "🚀 Deploying Verification Agent to AgentCore..."
echo "   BRAVE_API_KEY: set (${#BRAVE_API_KEY} chars)"
echo "   VERIFICATION_TOOLS: ${VERIFICATION_TOOLS:-brave}"

/home/wsluser/projects/calledit/venv/bin/agentcore deploy \
  --env "BRAVE_API_KEY=$BRAVE_API_KEY" \
  --env "VERIFICATION_TOOLS=${VERIFICATION_TOOLS:-brave}" \
  --auto-update-on-conflict

echo "✅ Verification Agent deployed with BRAVE_API_KEY"
