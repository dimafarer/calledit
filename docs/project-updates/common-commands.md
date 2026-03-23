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
```
