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
sam build
sam deploy --stack-name calledit-backend --no-confirm-changeset
```

## Prompt Management Deploy

```bash
cd /home/wsluser/projects/calledit/infrastructure/prompt-management
aws cloudformation deploy --template-file template.yaml --stack-name calledit-prompts
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
