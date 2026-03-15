# Eval Framework Rules

Rules for running evaluations and managing prompt versions in the CalledIt eval framework.

## Prompt Version Pinning — MANDATORY

**RULE**: Always pin to numbered prompt versions for eval runs. Never use DRAFT.

**Why**: Eval reports record the prompt version manifest (e.g., `{"categorizer": "2"}`).
If you use DRAFT, multiple runs show the same version label even when the prompt
text changed between runs. This makes before/after comparison impossible.

**Correct Pattern**:
```bash
# Pin all prompts to specific versions
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 \
PROMPT_VERSION_VB=1 PROMPT_VERSION_REVIEW=1 \
python eval_runner.py --dataset ../../../../eval/golden_dataset.json --judge
```

**Wrong Pattern**:
```bash
# DRAFT versions — can't distinguish runs
python eval_runner.py --dataset ../../../../eval/golden_dataset.json
```

## Prompt Change Workflow

1. Edit the prompt text in `infrastructure/prompt-management/template.yaml`
2. Add a new `AWS::Bedrock::PromptVersion` resource (v2, v3, etc.)
3. Deploy: `aws cloudformation deploy --template-file template.yaml --stack-name calledit-prompts`
4. Run eval with the new version pinned: `PROMPT_VERSION_CATEGORIZER=2 python eval_runner.py ...`
5. Compare results against previous run — the version manifest shows exactly what changed

## Eval Run Commands

All eval commands must be run from the strands_make_call directory:
```bash
cd /home/wsluser/projects/calledit/backend/calledit-backend/handlers/strands_make_call
```

**Dry run** (no Bedrock calls):
```bash
python eval_runner.py --dataset ../../../../eval/golden_dataset.json --dry-run
```

**Deterministic only** (~$3, ~15 min):
```bash
python eval_runner.py --dataset ../../../../eval/golden_dataset.json
```

**With judge** (~$13, ~30 min):
```bash
python eval_runner.py --dataset ../../../../eval/golden_dataset.json --judge
```

**With comparison to previous run**:
```bash
python eval_runner.py --dataset ../../../../eval/golden_dataset.json --judge --compare
```

## Two System Goals

Every eval decision should drive toward:
1. **Understand the full intent** of the user's raw prediction
2. **Repackage with 100% intent preservation** in a structure that enables verification at the right time
