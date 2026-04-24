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
# Dev mode — runs at http://localhost:5173/eval
cd /home/wsluser/projects/calledit/frontend-v4
npm run dev
# Navigate to http://localhost:5173/eval
```

## Eval Runs — Strands Evals SDK (CURRENT)

All eval commands run from the project root:

```bash
cd /home/wsluser/projects/calledit
source .env
```

### Batched Pipeline (standard)

```bash
# Dry run — list cases
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py --dry-run

# Smoke test — 12 cases, Tier 1 deterministic only
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py --tier smoke --description "smoke test"

# Full run — all 70 cases, all evaluators
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --tier full --description "full baseline"

# With dynamic dataset
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --dynamic-dataset eval/dynamic_golden_dataset.json --tier full --description "with dynamic"

# Single case
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --case base-002 --tier full --description "single case"

# Qualifying only (skip non-qualifying cases)
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --qualifying-only --tier full --description "qualifying only"

# Creation only (skip verification)
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --creation-only --tier smoke --description "creation only"

# Verify only (skip creation, use existing DDB bundles)
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --verify-only --tier smoke --description "verify only"

# Resume interrupted run
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --resume --tier full --description "resumed"

# Skip cleanup (leave bundles in eval table)
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --skip-cleanup --tier smoke --description "debug"
```

### Continuous Eval (create once, verify repeatedly)

```bash
# Full continuous run — create all cases, verify every 15 min, stop after 3 passes
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --continuous --max-passes 3 --tier smoke --description "continuous 3-pass"

# Single case continuous
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --continuous --max-passes 1 --tier smoke --case base-002

# Re-verify only (skip creation, single pass)
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --continuous --once --resume --tier smoke

# Resume continuous run from where it left off
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --continuous --resume --max-passes 5 --tier smoke

# Custom interval (30 min between passes)
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --continuous --interval 30 --max-passes 10 --tier smoke

# Re-verify already-resolved cases
PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/run_eval.py \
    --continuous --once --resume --reverify-resolved --tier smoke
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
# Deploy creation agent to AgentCore (uses deploy.sh wrapper)
source /home/wsluser/projects/calledit/.env
cd /home/wsluser/projects/calledit/calleditv4 && ./deploy.sh

# Deploy verification agent to AgentCore (validates BRAVE_API_KEY)
source /home/wsluser/projects/calledit/.env
cd /home/wsluser/projects/calledit/calleditv4-verification && ./deploy.sh

# Deploy CDK permissions stack (IAM policies for both execution roles)
cd /home/wsluser/projects/calledit/infrastructure/agentcore-cdk
npm install && npx cdk deploy

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

# Launch agents (use deploy.sh scripts instead of raw commands)
cd /home/wsluser/projects/calledit/calleditv4 && ./deploy.sh
source /home/wsluser/projects/calledit/.env && cd /home/wsluser/projects/calledit/calleditv4-verification && ./deploy.sh

# Agent status
cd /home/wsluser/projects/calledit/calleditv4 && agentcore status
cd /home/wsluser/projects/calledit/calleditv4-verification && agentcore status

# V4 frontend URL
# https://d2fngmclz6psil.cloudfront.net
```


## Dynamic Golden Dataset

```bash
# Generate fresh dynamic dataset (requires BRAVE_API_KEY for full 16 predictions)
source .env
/home/wsluser/projects/calledit/venv/bin/python eval/generate_dynamic_dataset.py

# Generate deterministic-only (no BRAVE_API_KEY needed, 9 predictions)
/home/wsluser/projects/calledit/venv/bin/python eval/generate_dynamic_dataset.py

# Validate dynamic dataset
/home/wsluser/projects/calledit/venv/bin/python eval/validate_dataset.py eval/dynamic_golden_dataset.json

# Run any eval with merged dataset (add --dynamic-dataset to existing commands)
source .env
/home/wsluser/projects/calledit/venv/bin/python eval/creation_eval.py \
    --dataset eval/golden_dataset.json \
    --dynamic-dataset eval/dynamic_golden_dataset.json \
    --tier full --description "full baseline with dynamic dataset"
```

## Eval Tests

```bash
# All eval tests (129 tests — includes property-based + unit)
/home/wsluser/projects/calledit/venv/bin/python -m pytest eval/tests/ -v

# Continuous eval tests only
/home/wsluser/projects/calledit/venv/bin/python -m pytest eval/tests/test_continuous_state.py eval/tests/test_continuous_metrics.py eval/tests/test_continuous_runner.py -v

# SDK evaluator tests only
/home/wsluser/projects/calledit/venv/bin/python -m pytest eval/tests/test_creation_evaluators.py eval/tests/test_verification_evaluators.py -v
```


## DDB Report Store

```bash
# Backfill historical JSON reports to DDB (idempotent)
/home/wsluser/projects/calledit/venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from eval.report_store import backfill_from_files
result = backfill_from_files('eval/reports')
print(result)
"
```

## Eval Dashboard (React)

```bash
# Dev mode — runs at http://localhost:5173/eval
cd /home/wsluser/projects/calledit/frontend-v4
npm run dev
# Navigate to http://localhost:5173/eval
# Uses ~/.aws/credentials via Vite dev server proxy for DDB access
```


## V4 Frontend Deploy (with eval dashboard)

```bash
# Build and deploy v4-frontend stack (4 Lambdas with SnapStart)
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
    DynamoDBTableArn=arn:aws:dynamodb:us-west-2:894249332178:table/calledit-v4 \
    EvalReportsTableName=calledit-v4-eval-reports \
    EvalReportsTableArn=arn:aws:dynamodb:us-west-2:894249332178:table/calledit-v4-eval-reports

# Build frontend, sync to S3, invalidate CloudFront
cd /home/wsluser/projects/calledit/frontend-v4
npm run build
aws s3 sync dist/ s3://calledit-v4-persistent-resources-v4frontendbucket-tjqdqan1gbuy --delete
aws cloudfront create-invalidation --distribution-id E1V0EF85NP9DXQ --paths "/*"

# Production dashboard URL
# https://d2fngmclz6psil.cloudfront.net/eval
```
