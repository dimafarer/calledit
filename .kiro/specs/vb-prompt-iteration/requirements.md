# Requirements Document

## Introduction

The CalledIt eval suite now has two verification-centric evaluators (IntentPreservation avg: 0.66, CriteriaMethodAlignment avg: 0.71) that measure the Verification Builder's core job: understanding prediction intent and producing executable verification plans. Analysis of the worst-scoring test cases revealed two systematic failure patterns in the VB v1 prompt: (1) over-engineering subjective predictions with philosophical hedging instead of operationalizing vague terms into measurable conditions, and (2) producing criteria that don't match the prediction's specificity level. This spec iterates on the VB prompt, updates golden dataset ground truth for subjective predictions to reflect the two-track approach from Decision 47, updates the ReviewAgent prompt to generate operationalization-validating clarification questions, and runs eval cycles to measure improvement against the 0.66/0.71 baseline.

## Glossary

- **VB_Prompt**: The Verification Builder system prompt managed in Bedrock Prompt Management (`infrastructure/prompt-management/template.yaml`), resource `VBPrompt`. Currently at v1.
- **VB_Prompt_Version**: An `AWS::Bedrock::PromptVersion` CloudFormation resource that pins a snapshot of the VB_Prompt text. Each iteration creates a new version (v2, v3, etc.) for reproducible eval comparison.
- **Review_Prompt**: The Review Agent system prompt managed in Bedrock Prompt Management, resource `ReviewPrompt`. Currently at v1.
- **Golden_Dataset**: JSON file (`eval/golden_dataset.json`, schema 3.0) containing 45 base predictions and 23 fuzzy predictions with ground truth including `expected_verification_criteria` and `expected_verification_method`.
- **Operationalization**: The process of converting a vague or subjective term (e.g., "nice weather", "taste good") into measurable, checkable conditions (e.g., temperature 60-80°F, precipitation < 30%).
- **Two_Track_Approach**: Decision 47's strategy for vague predictions — operationalize when external proxies exist (weather, observable outcomes), acknowledge subjectivity and use self-report when no external proxy exists (emotions, taste).
- **Specificity_Matching**: The principle that VB criteria must match the precision level of the original prediction — not adding conditions the prediction didn't claim (e.g., "before or after 6pm" when prediction says "after 6pm").
- **Eval_Runner**: Python module (`eval_runner.py`) that orchestrates evaluation runs with pinned prompt versions.
- **Prompt_Management_Template**: CloudFormation template (`infrastructure/prompt-management/template.yaml`) that defines all Bedrock-managed prompts and their versions.
- **IntentPreservation_Score**: LLM-as-judge score (0.0-1.0) measuring whether VB criteria captures the prediction's meaning. Current baseline: 0.66 average.
- **CriteriaMethodAlignment_Score**: LLM-as-judge score (0.0-1.0) measuring whether the VB method provides a realistic verification plan. Current baseline: 0.71 average.
- **Subjective_Test_Cases**: Golden dataset entries for predictions involving subjective judgments: base-027 (enjoy movie), base-028 (meeting go well), base-030 (feel happy), base-032 (daughter love present), base-034 (dinner taste good), base-036 (beat game level), base-041 (code compile first try).

## Requirements

### Requirement 1: VB Prompt V2 — Operationalization Instructions

**User Story:** As an eval developer, I want the VB prompt to include explicit instructions for operationalizing vague terms into measurable conditions, so that the VB produces checkable criteria instead of subjective hedging.

#### Acceptance Criteria

1. THE VB_Prompt SHALL include instructions directing the Verification_Builder to convert vague or subjective terms (e.g., "nice weather", "go well", "taste good") into specific, measurable conditions with default thresholds when external proxies exist.
2. THE VB_Prompt SHALL include instructions directing the Verification_Builder to use self-report verification with targeted prompts when a prediction involves truly subjective internal states (e.g., "feel happy", "enjoy") where no external proxy exists.
3. THE VB_Prompt SHALL include at least two worked examples demonstrating the Two_Track_Approach: one operationalizable prediction (e.g., "nice weather" → temperature/precipitation thresholds) and one truly subjective prediction (e.g., "feel happy" → self-report with timing).
4. THE VB_Prompt SHALL instruct the Verification_Builder to state its operationalization assumptions explicitly in the criteria (e.g., "assuming 'nice weather' means temperature between 60-80°F and precipitation probability below 30%").
5. WHEN the Verification_Builder operationalizes a vague term, THE VB_Prompt SHALL instruct the Verification_Builder to note that the ReviewAgent should generate clarification questions to validate the assumed thresholds.

### Requirement 2: VB Prompt V2 — Specificity Matching Instructions

**User Story:** As an eval developer, I want the VB prompt to include instructions for matching criteria specificity to the prediction's precision level, so that the VB does not add or remove conditions the prediction didn't claim.

#### Acceptance Criteria

1. THE VB_Prompt SHALL include instructions directing the Verification_Builder to match the specificity of the criteria to the specificity of the original prediction text.
2. THE VB_Prompt SHALL include an explicit rule that criteria must not introduce conditions the prediction did not state (e.g., if the prediction says "after 6pm", the criteria must not weaken to "before or after 6pm").
3. THE VB_Prompt SHALL include an explicit rule that criteria must not omit conditions the prediction did state (e.g., if the prediction says "at least 70°F", the criteria must include the 70°F threshold).
4. THE VB_Prompt SHALL include at least one worked example demonstrating Specificity_Matching: showing a prediction with a directional claim and the correct criteria that preserves the direction.

### Requirement 3: VB Prompt Version Management

**User Story:** As an eval developer, I want each VB prompt iteration deployed as a numbered Bedrock Prompt Version, so that eval runs can be compared against specific prompt snapshots.

#### Acceptance Criteria

1. WHEN the VB_Prompt text is updated in the Prompt_Management_Template, THE template SHALL include a new `AWS::Bedrock::PromptVersion` resource (e.g., `VBPromptVersionV2`) that pins the updated prompt text.
2. THE new VB_Prompt_Version resource SHALL have a `DependsOn` reference to the previous version resource to ensure correct version ordering during deployment.
3. THE new VB_Prompt_Version resource SHALL include a `Description` field summarizing the changes (e.g., "v2 — operationalization instructions and specificity matching").
4. WHEN subsequent iterations are made, THE Prompt_Management_Template SHALL add additional `AWS::Bedrock::PromptVersion` resources (v3, v4, etc.) following the same pattern.

### Requirement 4: Golden Dataset Ground Truth Update for Subjective Predictions

**User Story:** As an eval developer, I want the golden dataset `expected_verification_criteria` for subjective predictions updated to reflect the Two_Track_Approach, so that the evaluators score the VB against the correct ground truth.

#### Acceptance Criteria

1. WHEN a subjective prediction has an operationalizable vague term with external proxies (e.g., base-028 "go well" for a meeting, base-036 "beat game level"), THE Golden_Dataset `expected_verification_criteria` SHALL include measurable conditions or observable outcomes rather than only "user reports X."
2. WHEN a subjective prediction involves a truly internal emotional state with no external proxy (e.g., base-027 "enjoy movie", base-030 "feel happy"), THE Golden_Dataset `expected_verification_criteria` SHALL describe a self-report approach with specific timing and prompt text.
3. WHEN a subjective prediction involves taste or sensory experience (e.g., base-034 "taste good"), THE Golden_Dataset `expected_verification_criteria` SHALL describe a self-report approach since taste is inherently personal.
4. THE Golden_Dataset `expected_verification_method` for each updated Subjective_Test_Case SHALL be consistent with the updated `expected_verification_criteria` — operationalized criteria paired with data-source methods, self-report criteria paired with user-prompt methods.
5. THE Golden_Dataset SHALL maintain `dataset_version` incremented to reflect the ground truth update.
6. FOR ALL updated Subjective_Test_Cases, THE `expected_verification_criteria` SHALL contain at least one checkable true/false condition (not vague descriptions).
7. THE Golden_Dataset updates SHALL cover all seven Subjective_Test_Cases: base-027, base-028, base-030, base-032, base-034, base-036, and base-041.

### Requirement 5: ReviewAgent Prompt Update for Operationalization Validation

**User Story:** As an eval developer, I want the ReviewAgent prompt to generate clarification questions that validate the VB's operationalization assumptions, so that the review loop helps refine vague predictions into precise verifiable claims.

#### Acceptance Criteria

1. THE Review_Prompt SHALL include instructions directing the ReviewAgent to identify operationalization assumptions made by the Verification_Builder (e.g., assumed temperature thresholds for "nice weather").
2. THE Review_Prompt SHALL include instructions directing the ReviewAgent to generate clarification questions that validate specific assumptions (e.g., "Do you consider 60°F a nice day?" rather than generic "Can you be more specific?").
3. THE Review_Prompt SHALL include instructions directing the ReviewAgent to ask questions that could lead to verifiable reformulations for truly subjective predictions (e.g., "What would make you feel happy tomorrow morning? Getting 8 hours of sleep? A good breakfast?").
4. WHEN the Review_Prompt text is updated in the Prompt_Management_Template, THE template SHALL include a new `AWS::Bedrock::PromptVersion` resource for the ReviewPrompt (e.g., `ReviewPromptVersionV2`).

### Requirement 6: Baseline Eval Run

**User Story:** As an eval developer, I want a baseline eval run with the current VB v1 prompt and updated golden dataset ground truth, so that I have a clean comparison point before applying VB v2.

#### Acceptance Criteria

1. THE baseline eval run SHALL use pinned prompt versions: parser v1, categorizer v2, VB v1, review v1.
2. THE baseline eval run SHALL use the `--judge` flag to invoke IntentPreservation and CriteriaMethodAlignment evaluators.
3. THE baseline eval run SHALL use the updated Golden_Dataset (with revised subjective test case ground truth from Requirement 4).
4. THE baseline eval run report SHALL be saved to `eval/reports/` with the prompt version manifest recorded in the report.
5. THE baseline eval run SHALL record IntentPreservation and CriteriaMethodAlignment average scores as the new baseline for comparison.

### Requirement 7: VB V2 Eval Run and Comparison

**User Story:** As an eval developer, I want to run eval with the VB v2 prompt and compare IntentPreservation and CriteriaMethodAlignment scores against the baseline, so that I can measure whether the prompt changes improved verification quality.

#### Acceptance Criteria

1. THE VB v2 eval run SHALL use pinned prompt versions: parser v1, categorizer v2, VB v2, review v1 (or review v2 if Requirement 5 is deployed in the same iteration).
2. THE VB v2 eval run SHALL use the `--judge --compare` flags to invoke evaluators and compare against the previous run.
3. WHEN the eval run completes, THE report SHALL show per-test-case IntentPreservation and CriteriaMethodAlignment scores alongside the baseline.
4. THE eval run report SHALL identify test cases where scores improved, regressed, or remained unchanged compared to the baseline.
5. IF the VB v2 eval run shows IntentPreservation average below the baseline, THEN the eval report SHALL flag a regression for investigation.
6. IF the VB v2 eval run shows CriteriaMethodAlignment average below the baseline, THEN the eval report SHALL flag a regression for investigation.

### Requirement 8: Iterative Refinement Cycle

**User Story:** As an eval developer, I want a structured process for making targeted prompt adjustments and re-running eval, so that each iteration is a single change with measurable impact.

#### Acceptance Criteria

1. WHEN an eval run reveals specific test cases with low scores, THE next prompt iteration SHALL target the identified failure pattern with a single, focused change.
2. WHEN a new prompt iteration is created, THE Prompt_Management_Template SHALL include a new `AWS::Bedrock::PromptVersion` resource for the iteration (v3, v4, etc.).
3. THE eval run for each iteration SHALL use the `--compare` flag to show delta against the previous iteration.
4. WHEN an iteration causes a regression in previously passing test cases, THE next iteration SHALL address the regression before making further changes.
5. THE iterative refinement process SHALL continue until IntentPreservation average reaches 0.80 or above and CriteriaMethodAlignment average reaches 0.80 or above, or until three iterations have been completed, whichever comes first.
