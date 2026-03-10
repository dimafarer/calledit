# Requirements Document

## Introduction

A prompt evaluation framework for the CalledIt prediction verification system. The framework enables iterative improvement of agent prompts (Parser, Categorizer, Verification Builder, ReviewAgent) with measurable progress tracking. It uses a layered test pyramid: Layer 1 tests fully-specified base predictions for correctness, Layer 2 tests fuzzy predictions for clarification quality and convergence after user clarification. The framework invokes the actual Strands agent graph (Bedrock API calls) and scores outputs against a golden dataset.

## Glossary

- **Eval_Framework**: The prompt evaluation tool that runs golden dataset test cases against the prediction graph and produces scored results
- **Golden_Dataset**: A JSON file containing base predictions and their fuzzy variants with expected outputs, stored in the repository
- **Base_Prediction**: A fully-specified prediction requiring zero clarification, with known expected outputs for all agents (Layer 1)
- **Fuzzy_Prediction**: A degraded version of a base prediction with information removed, requiring clarification to converge to the base prediction's output (Layer 2)
- **Test_Case**: A single entry in the golden dataset containing input, expected outputs, and scoring criteria
- **Prediction_Graph**: The 4-agent Strands graph (Parser → Categorizer → Verification Builder → ReviewAgent) that processes predictions
- **Eval_Run**: A single execution of the Eval_Framework against the golden dataset, producing a scored report
- **Eval_Report**: The output of an Eval_Run containing per-test-case scores and aggregate metrics
- **Score**: A numeric value (0.0 to 1.0) representing how well an agent output matches the expected output
- **Category_Match**: A deterministic binary score (0 or 1) comparing actual verifiable_category to expected verifiable_category
- **Convergence**: The property that a fuzzy prediction, after clarification, produces outputs equivalent to its base prediction
- **Verifiability_Category**: One of: agent_verifiable, current_tool_verifiable, strands_tool_verifiable, api_tool_verifiable, human_verifiable_only

**Important Note — Clarification Is Not Just About Upgrading Verifiability:**
Some predictions will remain `human_verifiable_only` even after clarification (e.g., "Tom will wear that shirt"). The clarification loop still adds value by making the prediction more precise and descriptive for the human who will eventually verify it. A fuzzy `human_verifiable_only` prediction should converge to a more detailed `human_verifiable_only` base prediction — not upgrade to a different category. The golden dataset must include test cases where clarification improves precision without changing the category.

## Requirements

### Requirement 1: Golden Dataset Definition

**User Story:** As a developer, I want a structured golden dataset of test predictions with expected outputs, so that I can evaluate agent prompt quality against known-good answers.

#### Acceptance Criteria

1. THE Golden_Dataset SHALL store test cases in a JSON file within the repository
2. WHEN a base prediction test case is defined, THE Golden_Dataset SHALL include the prediction text, expected verifiable_category, expected verification_method structure, and a flag indicating no clarification is needed
3. WHEN a fuzzy prediction test case is defined, THE Golden_Dataset SHALL include the fuzzy prediction text, a reference to the corresponding base prediction, simulated clarification answers, and expected post-clarification outputs
4. THE Golden_Dataset SHALL contain at least 15 base predictions covering all five verifiability categories (agent_verifiable, current_tool_verifiable, strands_tool_verifiable, api_tool_verifiable, human_verifiable_only)
5. WHEN a fuzzy prediction test case is defined, THE Golden_Dataset SHALL include expected clarification question topics that the ReviewAgent should ask about
6. THE Golden_Dataset SHALL include a schema version field to support future format changes

### Requirement 2: Layer 1 — Base Prediction Evaluation

**User Story:** As a developer, I want to run fully-specified predictions through the graph and score the outputs, so that I can verify agents produce correct results when given complete information.

#### Acceptance Criteria

1. WHEN a base prediction test case is executed, THE Eval_Framework SHALL invoke the Prediction_Graph with the prediction text and capture the full parsed output
2. WHEN a base prediction test case is scored, THE Eval_Framework SHALL compute a Category_Match score (1 if actual verifiable_category equals expected, 0 otherwise)
3. WHEN a base prediction test case is scored, THE Eval_Framework SHALL verify that the Parser output contains valid JSON with prediction_statement, verification_date, and date_reasoning fields
4. WHEN a base prediction test case is scored, THE Eval_Framework SHALL verify that the Verification Builder output contains a verification_method with source, criteria, and steps as non-empty lists
5. WHEN a base prediction test case is scored, THE Eval_Framework SHALL compute an overall test case score as a weighted combination of category match, JSON validity, and verification method structure scores
6. IF the Prediction_Graph returns an error for a base prediction, THEN THE Eval_Framework SHALL record the test case as failed with the error message and assign a score of 0.0

### Requirement 3: Layer 2 — Fuzzy Prediction Evaluation

**User Story:** As a developer, I want to run fuzzy predictions through the clarification loop and score convergence to the base prediction output, so that I can verify the system handles ambiguous input correctly.

#### Acceptance Criteria

1. WHEN a fuzzy prediction test case is executed, THE Eval_Framework SHALL invoke the Prediction_Graph for round 1 with the fuzzy prediction text and capture the output including reviewable_sections
2. WHEN round 1 output is captured, THE Eval_Framework SHALL extract clarification questions from the reviewable_sections and score whether expected question topics are covered
3. WHEN round 1 is complete, THE Eval_Framework SHALL construct a round 2 prompt using the round 1 output, the simulated clarification answers from the test case, and invoke the Prediction_Graph again
4. WHEN round 2 output is captured, THE Eval_Framework SHALL compute a Convergence score by comparing the round 2 verifiable_category to the corresponding base prediction's expected verifiable_category
5. WHEN a fuzzy prediction test case is scored, THE Eval_Framework SHALL compute an overall score combining: round 1 JSON validity, clarification question quality, and post-clarification convergence
6. IF the Prediction_Graph returns an error during any round of a fuzzy prediction evaluation, THEN THE Eval_Framework SHALL record the failing round, the error message, and assign a score of 0.0 for remaining rounds

### Requirement 4: Scoring and Reporting

**User Story:** As a developer, I want detailed per-test-case scores and aggregate metrics in a readable report, so that I can identify which agents and which predictions are failing.

#### Acceptance Criteria

1. WHEN an Eval_Run completes, THE Eval_Framework SHALL produce an Eval_Report containing: per-test-case scores, per-agent pass/fail status, and aggregate metrics
2. WHEN an Eval_Report is generated, THE Eval_Framework SHALL include the overall pass rate (percentage of test cases scoring above a configurable threshold)
3. WHEN an Eval_Report is generated, THE Eval_Framework SHALL include per-category accuracy (percentage of correct Category_Match scores grouped by verifiability category)
4. WHEN an Eval_Report is generated, THE Eval_Framework SHALL display results in a human-readable format to the terminal with color-coded pass/fail indicators
5. WHEN an Eval_Report is generated, THE Eval_Framework SHALL save the full report as a JSON file with a timestamp in the filename
6. THE Eval_Framework SHALL include the wall-clock duration of each test case in the Eval_Report

### Requirement 5: CLI Execution

**User Story:** As a developer, I want to run the full eval suite or individual test cases with a single command, so that I can quickly validate prompt changes.

#### Acceptance Criteria

1. THE Eval_Framework SHALL provide a CLI entry point that runs all test cases in the Golden_Dataset with a single command
2. WHEN the CLI is invoked with a test case filter argument, THE Eval_Framework SHALL run only the test cases matching the filter
3. WHEN the CLI is invoked with a layer filter argument, THE Eval_Framework SHALL run only test cases from the specified layer (base or fuzzy)
4. THE Eval_Framework SHALL print a summary line at the end of execution showing total tests, passed, failed, and overall score
5. IF the overall pass rate falls below the configurable threshold, THEN THE Eval_Framework SHALL exit with a non-zero exit code

### Requirement 6: Score Tracking Over Time

**User Story:** As a developer, I want to compare eval scores across prompt iterations, so that I can verify prompt changes improve overall quality without regressions.

#### Acceptance Criteria

1. WHEN an Eval_Run completes, THE Eval_Framework SHALL append the aggregate scores and timestamp to a local score history file
2. WHEN the CLI is invoked with a compare flag, THE Eval_Framework SHALL display the current run's scores alongside the previous run's scores with delta indicators (improved/regressed/unchanged)
3. WHEN a comparison shows any per-category accuracy decreased, THE Eval_Framework SHALL flag the regressed categories in the comparison output
4. THE Eval_Framework SHALL store the score history in a JSON file within the repository

### Requirement 7: Non-Determinism Handling

**User Story:** As a developer, I want the scoring system to account for LLM output variability, so that non-deterministic differences do not cause false failures.

#### Acceptance Criteria

1. THE Eval_Framework SHALL use deterministic scoring (exact match) for verifiable_category comparisons
2. THE Eval_Framework SHALL use structural scoring (field presence and type checks) for JSON validity rather than exact content matching
3. WHEN scoring clarification question quality, THE Eval_Framework SHALL match on expected topic keywords rather than exact question text
4. WHEN the CLI is invoked with a repeat-count argument, THE Eval_Framework SHALL run each test case the specified number of times and report the pass rate across repetitions

### Requirement 8: Cost and Performance Guardrails

**User Story:** As a developer, I want visibility into the cost of eval runs and the ability to limit scope, so that I can manage Bedrock API costs.

#### Acceptance Criteria

1. WHEN an Eval_Run completes, THE Eval_Framework SHALL report the total number of Prediction_Graph invocations made during the run
2. WHEN the CLI is invoked with a dry-run flag, THE Eval_Framework SHALL list the test cases that would be executed and the estimated number of graph invocations without making any API calls
3. THE Eval_Framework SHALL log the start and end time of each test case execution to enable cost estimation
