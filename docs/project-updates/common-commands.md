# Common Commands

All commands assume you're in `/home/wsluser/projects/calledit` and the venv is active.

---

## Dashboard

```bash
/home/wsluser/projects/calledit/venv/bin/python -m streamlit run eval/dashboard/app.py
```

## Eval Runs

All eval commands run from the strands_make_call directory:

```bash
cd /home/wsluser/projects/calledit/backend/calledit-backend/handlers/strands_make_call
```

### Serial backend with judge (current best prompts)
```bash
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=2 PROMPT_VERSION_REVIEW=2 \
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
--dataset ../../../../eval/golden_dataset.json --backend serial --judge
```

### Single backend with judge (current best prompts)
```bash
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=2 PROMPT_VERSION_REVIEW=2 \
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
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=2 PROMPT_VERSION_REVIEW=2 \
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
--dataset ../../../../eval/golden_dataset.json --backend serial
```

### Single prediction test (quick smoke test)
```bash
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=2 PROMPT_VERSION_REVIEW=2 \
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
--dataset ../../../../eval/golden_dataset.json --backend serial --judge --name base-001
```

### List available backends
```bash
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py --list-backends
```

## Tests

```bash
# All tests
/home/wsluser/projects/calledit/venv/bin/python -m pytest tests/ -v

# Dashboard tests only
/home/wsluser/projects/calledit/venv/bin/python -m pytest tests/dashboard/ -v

# Specific test file
/home/wsluser/projects/calledit/venv/bin/python -m pytest tests/strands_make_call/test_utils.py -v
```

## SAM Build and Deploy

```bash
cd /home/wsluser/projects/calledit/backend/calledit-backend

# Standard build + deploy
sam build
sam deploy --stack-name calledit-backend --no-confirm-changeset

# Force rebuild (needed after code changes when Docker cache is stale)
sam build --no-cached
sam deploy --stack-name calledit-backend --no-confirm-changeset

# Deploy with BRAVE_API_KEY (source .env first for the key)
source /home/wsluser/projects/calledit/.env
sam deploy --parameter-overrides BraveApiKey=$BRAVE_API_KEY
```

## Prompt Management Deploy

```bash
cd /home/wsluser/projects/calledit/infrastructure/prompt-management
aws cloudformation deploy --template-file template.yaml --stack-name calledit-prompts
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

## Git

```bash
git branch --show-current
git checkout main
git merge feature/prompt-eval-framework
git push origin main
```

## Install Dependencies

```bash
/home/wsluser/projects/calledit/venv/bin/pip install -r requirements.txt
```
