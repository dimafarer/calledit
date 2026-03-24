# Common Commands

All commands assume you're in `/home/wsluser/projects/calledit` and the venv is active.
Always `source .env` before commands that need BRAVE_API_KEY or other secrets.

---

## SAM Build and Deploy

```bash
cd /home/wsluser/projects/calledit/backend/calledit-backend

# Full rebuild (needed when Docker image code changes — rm -rf .aws-sam clears cache)
source /home/wsluser/projects/calledit/.env
rm -rf .aws-sam && sam build
sam deploy --parameter-overrides BraveApiKey=$BRAVE_API_KEY

# Standard build + deploy (when only non-Docker code changed)
sam build
sam deploy --parameter-overrides BraveApiKey=$BRAVE_API_KEY

# Force rebuild without deleting .aws-sam
sam build --no-cached
```

## Prompt Management Deploy

```bash
cd /home/wsluser/projects/calledit/infrastructure/prompt-management
aws cloudformation deploy --template-file template.yaml --stack-name calledit-prompts
```

## Tests — Verification Executor (Spec B1)

```bash
# Run from strands_make_call directory
cd /home/wsluser/projects/calledit/backend/calledit-backend/handlers/strands_make_call

# Pure function tests only (instant, no Bedrock/MCP)
/home/wsluser/projects/calledit/venv/bin/python -m pytest \
    /home/wsluser/projects/calledit/backend/calledit-backend/tests/test_verification_executor.py -v \
    -k "not integration"

# Integration tests (real Bedrock + MCP, ~75s, needs source .env)
source /home/wsluser/projects/calledit/.env
/home/wsluser/projects/calledit/venv/bin/python -m pytest \
    /home/wsluser/projects/calledit/backend/calledit-backend/tests/test_verification_executor.py -v \
    -m integration
```

## Tests — Verification Triggers (Spec B2)

```bash
cd /home/wsluser/projects/calledit/backend/calledit-backend/handlers/strands_make_call

# All trigger tests (real DynamoDB, ~3s)
source /home/wsluser/projects/calledit/.env
/home/wsluser/projects/calledit/venv/bin/python -m pytest \
    /home/wsluser/projects/calledit/backend/calledit-backend/tests/test_verification_triggers.py -v \
    -k "not integration"
```

## Tests — General

```bash
# All tests in tests/ directory
cd /home/wsluser/projects/calledit/backend/calledit-backend/handlers/strands_make_call
/home/wsluser/projects/calledit/venv/bin/python -m pytest \
    /home/wsluser/projects/calledit/backend/calledit-backend/tests/ -v

# Specific test file
/home/wsluser/projects/calledit/venv/bin/python -m pytest \
    /home/wsluser/projects/calledit/backend/calledit-backend/tests/test_mcp_manager.py -v
```

## Verification Scanner — Manual Invoke

```bash
# Invoke the scanner Lambda directly (after deploy)
aws lambda invoke \
    --function-name <stack-name>-VerificationScannerFunction-<id> \
    --payload '{}' \
    /tmp/scanner-output.json && cat /tmp/scanner-output.json

# Check scanner CloudWatch logs
aws logs tail /aws/lambda/<stack-name>-VerificationScannerFunction-<id> --since 30m --format short
```

## MCP Local Test

```bash
cd /home/wsluser/projects/calledit/backend/calledit-backend
source /home/wsluser/projects/calledit/.env
/home/wsluser/projects/calledit/venv/bin/python test_mcp_local.py
```

## Dashboard

```bash
/home/wsluser/projects/calledit/venv/bin/python -m streamlit run eval/dashboard/app.py
```

## Eval Runs

All eval commands run from the strands_make_call directory:

```bash
cd /home/wsluser/projects/calledit/backend/calledit-backend/handlers/strands_make_call
```

### Serial backend with judge (current best prompts — v3 pipeline)
```bash
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=3 PROMPT_VERSION_REVIEW=4 \
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
    --dataset ../../../../eval/golden_dataset.json --backend serial --judge
```

### Single backend with judge
```bash
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=3 PROMPT_VERSION_REVIEW=4 \
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
    --dataset ../../../../eval/golden_dataset.json --backend single --judge
```

### Dry run (no Bedrock calls, check test case count)
```bash
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
    --dataset ../../../../eval/golden_dataset.json --dry-run
```

### Deterministic only (no judge, cheaper/faster)
```bash
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=3 PROMPT_VERSION_REVIEW=4 \
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
    --dataset ../../../../eval/golden_dataset.json --backend serial
```

### Single prediction test (quick smoke test)
```bash
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=3 PROMPT_VERSION_REVIEW=4 \
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
    --dataset ../../../../eval/golden_dataset.json --backend serial --judge --name base-001
```

### With comparison to previous run
```bash
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
    --dataset ../../../../eval/golden_dataset.json --judge --compare
```

### List available backends
```bash
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py --list-backends
```

### With verification (--verify, deterministic evaluators only)
```bash
source /home/wsluser/projects/calledit/.env
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=3 PROMPT_VERSION_REVIEW=4 \
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
    --dataset ../../../../eval/golden_dataset.json --backend serial --verify
```

### With verification + judge (all 4 verification evaluators)
```bash
source /home/wsluser/projects/calledit/.env
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=3 PROMPT_VERSION_REVIEW=4 \
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
    --dataset ../../../../eval/golden_dataset.json --backend serial --verify --judge
```

### Single test case with verification (fast iteration, ~20-120s)
```bash
source /home/wsluser/projects/calledit/.env
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=3 PROMPT_VERSION_REVIEW=4 \
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
    --dataset ../../../../eval/golden_dataset.json --backend serial --verify --name base-002
```

## CloudWatch Logs

```bash
# MCP Manager logs (check server connections)
aws logs tail /aws/lambda/calledit-backend-MakeCallStreamFunction-U5p4yuEq1F1x --since 10m --filter-pattern "MCP" --format short

# All recent logs for MakeCallStream
aws logs tail /aws/lambda/calledit-backend-MakeCallStreamFunction-U5p4yuEq1F1x --since 5m --format short

# List Lambda function names
aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'calledit')].FunctionName" --output text
```

## Install Dependencies

```bash
# Dev dependencies (root)
/home/wsluser/projects/calledit/venv/bin/pip install -r requirements.txt

# Lambda runtime dependencies
/home/wsluser/projects/calledit/venv/bin/pip install -r backend/calledit-backend/handlers/strands_make_call/requirements.txt
```

## Git

```bash
git branch --show-current
git checkout main
git merge feature/prompt-eval-framework
git push origin main
```


## AgentCore v4 (calleditv4/)

```bash
# Start dev server (requires TTY — run in terminal)
cd /home/wsluser/projects/calledit/calleditv4 && agentcore dev

# Invoke agent locally (requires dev server running)
agentcore invoke --dev '{"prompt": "Hello, are you working?"}'

# Test browser tool — web search
agentcore invoke --dev '{"prompt": "Search the web for the current weather in Seattle"}'

# Test code interpreter — calculation
agentcore invoke --dev '{"prompt": "Calculate the compound interest on $10000 at 5% for 10 years"}'

# Test missing prompt key (should return error JSON)
agentcore invoke --dev '{"not_prompt": "test"}'

# Run v4 unit tests (all test files)
/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/ -v

# --- V4-3a Creation Flow Commands ---

# Test creation flow — basic prediction
agentcore invoke --dev '{"prediction_text": "Lakers win tonight", "user_id": "test-user"}'

# Test creation flow — no user_id (defaults to anonymous)
agentcore invoke --dev '{"prediction_text": "It will rain tomorrow in Seattle"}'

# Test missing fields (should return error JSON)
agentcore invoke --dev '{"foo": "bar"}'

# Run all v4 tests (136 tests)
/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/ -v

# Run specific v4 test files
/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/test_models.py -v
/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/test_bundle.py -v
/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/test_prompt_client.py -v
/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/test_cfn_prompts.py -v
/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/test_entrypoint.py -v

# Check v4 creation prompt IDs from CloudFormation
aws cloudformation describe-stacks --stack-name calledit-prompts --query "Stacks[0].Outputs[?contains(OutputKey, 'PredictionParser') || contains(OutputKey, 'VerificationPlanner') || contains(OutputKey, 'PlanReviewer')]" --output table

# --- V4-3b Clarification & Streaming Commands ---

# Test streaming creation flow with timezone (Decision 101)
agentcore invoke --dev '{"prediction_text": "Lakers win tonight", "user_id": "test-user", "timezone": "America/Los_Angeles"}'

# Test clarification round (use prediction_id from creation output)
agentcore invoke --dev '{"prediction_id": "pred-xxx", "clarification_answers": [{"question": "Does win include overtime?", "answer": "Yes"}], "timezone": "America/Los_Angeles"}'

# Test clarification cap (run 6 rounds — 6th should yield error)
# Use prediction_id from creation, repeat clarification 6 times

# Test missing fields (should yield error stream event)
agentcore invoke --dev '{"foo": "bar"}'
```

## AgentCore v4 — Verification Agent (calleditv4-verification/)

```bash
# Start verification agent dev server (requires TTY — run in terminal)
cd /home/wsluser/projects/calledit/calleditv4-verification && agentcore dev

# Invoke verification agent with a prediction_id
agentcore invoke --dev '{"prediction_id": "pred-3f52a1b2-97b1-4c59-ac1c-f3cc26886156"}'

# Run verification agent unit tests (22 tests)
/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4-verification/tests/ -v

# Check DDB for verification result
aws dynamodb get-item --table-name calledit-db --key '{"PK":{"S":"PRED#pred-xxx"},"SK":{"S":"BUNDLE"}}' --projection-expression "#s,verdict,confidence,reasoning,verified_at" --expression-attribute-names '{"#s":"status"}' --output json

# Find pending predictions for testing
aws dynamodb scan --table-name calledit-db --filter-expression "#s = :pending" --expression-attribute-names '{"#s":"status"}' --expression-attribute-values '{":pending":{"S":"pending"}}' --projection-expression "PK,parsed_claim.statement" --max-items 5 --output json

# Check verification executor prompt ID
aws cloudformation describe-stacks --stack-name calledit-prompts --query "Stacks[0].Outputs[?contains(OutputKey, 'VerificationExecutor')]" --output table
```

## Verification Scanner (V4-5b)

```bash
# Create GSI (one-time setup)
bash infrastructure/verification-scanner/setup_gsi.sh

# Check GSI status
aws dynamodb describe-table --table-name calledit-db --query "Table.GlobalSecondaryIndexes[?IndexName=='status-verification_date-index'].IndexStatus" --output text

# Deploy scanner Lambda
cd /home/wsluser/projects/calledit/infrastructure/verification-scanner
sam build && sam deploy --guided

# Test scanner locally (requires verification agent dev server running)
# Set VERIFICATION_AGENT_ENDPOINT=http://localhost:8080 in template.yaml params
# Then invoke the scanner Lambda directly

# Check table stats
aws dynamodb describe-table --table-name calledit-db --query "Table.{ItemCount:ItemCount,TableSizeBytes:TableSizeBytes,BillingMode:BillingModeSummary.BillingMode,GSIs:GlobalSecondaryIndexes[*].{Name:IndexName,ItemCount:ItemCount,SizeBytes:IndexSizeBytes,Status:IndexStatus}}" --output json
```


## V4 Infrastructure Deployment

```bash
# Deploy persistent resources (S3 bucket + DDB table)
cd /home/wsluser/projects/calledit
aws cloudformation deploy \
  --template-file infrastructure/v4-persistent-resources/template.yaml \
  --stack-name calledit-v4-persistent-resources

# Deploy frontend stack (CloudFront + HTTP API + Lambdas)
cd /home/wsluser/projects/calledit/infrastructure/v4-frontend
sam build && sam deploy \
  --stack-name calledit-v4-frontend \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --parameter-overrides \
    CognitoUserPoolId=us-west-2_GOEwUjJtv \
    CognitoUserPoolClientId=753gn25jle081ajqabpd4lbin9 \
    CreationAgentRuntimeArn=arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_Agent-AJiwpKBxRW \
    FrontendBucketName=calledit-v4-persistent-resources-v4frontendbucket-tjqdqan1gbuy \
    FrontendBucketArn=arn:aws:s3:::calledit-v4-persistent-resources-v4frontendbucket-tjqdqan1gbuy \
    FrontendBucketDomainName=calledit-v4-persistent-resources-v4frontendbucket-tjqdqan1gbuy.s3.us-west-2.amazonaws.com \
    DynamoDBTableArn=arn:aws:dynamodb:us-west-2:894249332178:table/calledit-v4

# Deploy scanner Lambda
cd /home/wsluser/projects/calledit/infrastructure/verification-scanner
sam build && sam deploy \
  --stack-name calledit-v4-scanner \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --parameter-overrides \
    DynamoDBTableName=calledit-v4 \
    VerificationAgentId=calleditv4_verification_Agent-77DiT7GHdH

# Build and deploy frontend-v4
cd /home/wsluser/projects/calledit/frontend-v4
npm run build
aws s3 sync dist/ s3://calledit-v4-persistent-resources-v4frontendbucket-tjqdqan1gbuy --delete
aws cloudfront create-invalidation --distribution-id E1V0EF85NP9DXQ --paths "/*"

# Check stack outputs
aws cloudformation describe-stacks --stack-name calledit-v4-persistent-resources --query "Stacks[0].Outputs" --output table
aws cloudformation describe-stacks --stack-name calledit-v4-frontend --query "Stacks[0].Outputs" --output table

# Launch agents (requires TTY)
cd /home/wsluser/projects/calledit/calleditv4 && agentcore launch
cd /home/wsluser/projects/calledit/calleditv4-verification && agentcore launch

# Agent status
cd /home/wsluser/projects/calledit/calleditv4 && agentcore status
cd /home/wsluser/projects/calledit/calleditv4-verification && agentcore status

# V4 frontend URL
# https://d2fngmclz6psil.cloudfront.net
```
