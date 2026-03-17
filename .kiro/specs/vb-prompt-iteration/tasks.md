# Implementation Plan: VB Prompt Iteration

## Overview

Iterates on the VB prompt, Review prompt, and golden dataset ground truth to fix over-engineering of subjective predictions and specificity mismatch failures. Each change is isolated with its own eval run to attribute score deltas to a single variable. All eval runs are manual — exact commands are provided for the user to execute.

## Tasks

- [x] 1. Update golden dataset ground truth for subjective test cases
  - [x] 1.1 Update the 7 subjective test cases in `eval/golden_dataset.json`
    - Bump `dataset_version` from `"3.0"` to `"3.1"`
    - Update `expected_verification_criteria` and `expected_verification_method` for base-027, base-028, base-030, base-032, base-034, base-036, base-041
    - Track 1 (operationalize): base-028, base-036, base-041 — measurable conditions / binary outcomes
    - Track 2 (self-report): base-027, base-030, base-032, base-034 — structured self-report with timing and yes/no prompt
    - Use exact ground truth values from the design document Data Models section
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

  - [ ]* 1.2 Write property test: Two-track ground truth correctness (Property 1)
    - **Property 1: Two-track ground truth correctness**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.6**
    - Create `tests/strands_make_call/test_vb_prompt_iteration.py`
    - Use Hypothesis to sample from the 7 subjective test cases
    - Assert operationalizable cases (base-028, base-036, base-041) contain measurable conditions or observable outcomes
    - Assert self-report cases (base-027, base-030, base-032, base-034) contain self-report plan with yes/no prompt
    - Assert all 7 cases contain at least one checkable true/false condition

  - [ ]* 1.3 Write property test: Method-criteria consistency (Property 2)
    - **Property 2: Method-criteria consistency**
    - **Validates: Requirements 4.4**
    - In `tests/strands_make_call/test_vb_prompt_iteration.py`
    - Use Hypothesis to sample from the 7 subjective test cases
    - Assert self-report criteria are paired with user-prompt methods
    - Assert operationalized criteria are paired with outcome-reporting methods

  - [x] 1.4 Validate golden dataset JSON integrity
    - Run `python -m json.tool eval/golden_dataset.json` to confirm valid JSON
    - Confirm `dataset_version` is `"3.1"` and all 7 test case IDs are present with updated fields
    - _Requirements: 4.5, 4.7_

- [x] 2. Checkpoint — Golden dataset validated
  - Ensure all tests pass, ask the user if questions arise.
  - Provide the user with the Run 1 baseline eval command to execute manually:
    ```
    cd /home/wsluser/projects/calledit/backend/calledit-backend/handlers/strands_make_call
    PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 \
    PROMPT_VERSION_VB=1 PROMPT_VERSION_REVIEW=1 \
    /home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
      --dataset ../../../../eval/golden_dataset.json --judge
    ```
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 3. Update VB prompt with operationalization and specificity matching instructions
  - [x] 3.1 Append Block A (operationalization instructions) and Block B (specificity matching instructions) to the VB prompt in `infrastructure/prompt-management/template.yaml`
    - Append after the existing "Realistic and achievable" line, before the REFINEMENT MODE section
    - Block A: two-track approach (operationalize vs self-report), two worked examples, assumption flagging for ReviewAgent
    - Block B: specificity matching rules (no adding unstated conditions, no omitting stated conditions), one worked example
    - Use exact text from the design document Data Models section
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4_

  - [x] 3.2 Add `VBPromptVersionV2` resource to `infrastructure/prompt-management/template.yaml`
    - Type: `AWS::Bedrock::PromptVersion`
    - `DependsOn: VBPromptVersion`
    - `Description: "v2 — operationalization instructions and specificity matching"`
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 3.3 Write property test: VB prompt contains required instruction blocks (Property 3)
    - **Property 3: VB prompt contains required instruction blocks**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4**
    - In `tests/strands_make_call/test_vb_prompt_iteration.py`
    - Parse `infrastructure/prompt-management/template.yaml` and extract VB prompt text
    - Assert presence of: operationalization instructions, self-report instructions, two worked examples, assumption-flagging directive, specificity matching rules (add/omit), specificity worked example

  - [ ]* 3.4 Write property test: CloudFormation version resource structure (Property 4)
    - **Property 4: CloudFormation version resource structure**
    - **Validates: Requirements 3.1, 3.2, 3.3, 5.4, 8.2**
    - In `tests/strands_make_call/test_vb_prompt_iteration.py`
    - Parse `infrastructure/prompt-management/template.yaml`
    - For each `AWS::Bedrock::PromptVersion` resource, assert it has `DependsOn` and `Description` fields

- [ ] 4. Checkpoint — VB v2 prompt deployed, ready for eval
  - Ensure all tests pass, ask the user if questions arise.
  - Remind user to deploy the template before running eval:
    ```
    cd /home/wsluser/projects/calledit/infrastructure/prompt-management
    aws cloudformation deploy --template-file template.yaml --stack-name calledit-prompts
    ```
  - Provide the user with the Run 2 eval command to execute manually:
    ```
    cd /home/wsluser/projects/calledit/backend/calledit-backend/handlers/strands_make_call
    PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 \
    PROMPT_VERSION_VB=2 PROMPT_VERSION_REVIEW=1 \
    /home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
      --dataset ../../../../eval/golden_dataset.json --judge --compare
    ```
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 5. Update Review prompt with operationalization validation instructions
  - [x] 5.1 Append Block C (operationalization validation) to the Review prompt in `infrastructure/prompt-management/template.yaml`
    - Append after the existing EVALUATION CRITERIA section, before the JSON return format
    - Directive to identify operationalization assumptions
    - Directive to generate specific clarification questions (not generic)
    - Directive to ask questions leading to verifiable reformulations for subjective predictions
    - Use exact text from the design document Data Models section
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 5.2 Add `ReviewPromptVersionV2` resource to `infrastructure/prompt-management/template.yaml`
    - Type: `AWS::Bedrock::PromptVersion`
    - `DependsOn: ReviewPromptVersion`
    - `Description: "v2 — operationalization validation questions"`
    - _Requirements: 5.4_

- [ ] 6. Final checkpoint — All changes complete, ready for Review v2 eval
  - Ensure all tests pass, ask the user if questions arise.
  - Remind user to deploy the updated template:
    ```
    cd /home/wsluser/projects/calledit/infrastructure/prompt-management
    aws cloudformation deploy --template-file template.yaml --stack-name calledit-prompts
    ```
  - Provide the user with the Run 3 eval command to execute manually:
    ```
    cd /home/wsluser/projects/calledit/backend/calledit-backend/handlers/strands_make_call
    PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 \
    PROMPT_VERSION_VB=2 PROMPT_VERSION_REVIEW=2 \
    /home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
      --dataset ../../../../eval/golden_dataset.json --judge --compare
    ```
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.3, 8.5_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- All eval runs are manual — commands are provided at checkpoints for the user to execute
- Each eval run changes exactly one variable from the previous run (isolation principle)
- Property tests use Hypothesis and live in `tests/strands_make_call/test_vb_prompt_iteration.py`
- Run all tests with: `/home/wsluser/projects/calledit/venv/bin/python -m pytest tests/strands_make_call/test_vb_prompt_iteration.py -v`
- Success criteria: IntentPreservation avg ≥ 0.80 and CriteriaMethodAlignment avg ≥ 0.80, or measurable improvement within 3 iterations
