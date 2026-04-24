#!/bin/bash
# Deploy the CalledIt v4 Creation Agent to AgentCore Runtime.
#
# Prerequisites:
#   - source .env (for AWS credentials)
#   - agentcore CLI installed (pip install bedrock-agentcore-starter-toolkit)
#
# Usage:
#   cd calleditv4 && ./deploy.sh

set -euo pipefail

echo "🚀 Deploying Creation Agent to AgentCore..."
/home/wsluser/projects/calledit/venv/bin/agentcore deploy --auto-update-on-conflict
echo "✅ Creation Agent deployed"
