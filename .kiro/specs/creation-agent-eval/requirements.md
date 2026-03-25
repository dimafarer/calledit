# Requirements Document

## Introduction

Build a complete eval experiment for the v4 creation agent using the Strands Evals SDK. The creation agent converts natural-language predictions into structured bundles (`ParsedClaim`, `VerificationPlan`, `PlanReview` Pydantic models) via a deployed AgentCore runtime. This eval experiment measures bundle quality through a tiered evaluator strategy: 6 Tier 1 deterministic evaluators run on every eval (instant, free), and 2 Tier 2 LLM judge evaluators run on-demand for deeper quality assessment. An AgentCore backend invokes the deployed creation agent via `invoke_agent_runtime()` (HTTP streaming), and each run carries structured metadata for dashboard context. A CLI runner orchestrates case loading, backend invocation, evaluator execution, and JSON report generation across configurable run tiers (smoke, smoke+judges, full). Per Decisions 122–127 from Project Update 30 (Spec V4-7a-2). Depends on V4-7a-1 (Golden Dataset Reshape) for the v4-native dataset.

## Glossary

- **Eval_Runner**: The CLI entry point (`eval/creation_eval.py`) that orchestrates case loading, backend invocation, evaluator execution, and report generation for a creation agent eval run
- **AgentCore_Backend**: The module (`eval/backends/agentcore_backend.py`) that invokes the deployed creation agent via `bedrock_agentcore.runtime.AgentCoreRuntimeClient.invoke_agent_runtime()` and parses the streaming response into the eval framework's expected format
- **Creation_Agent**: The deployed v4 creation agent at ARN `arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_Agent-AJiwpKBxRW` that converts prediction text into a structured bundle
- **Prediction_Bundle**: The structured output of the Creation_Agent consisting of a `ParsedClaim`, a `VerificationPlan`, and a `PlanReview`
- **Eval_Case**: A single test case loaded from the golden dataset, containing `input` (prediction text), `expected_output` (ground truth), and `metadata` (dimension tags, difficulty, smoke test flag)
- **Golden_Dataset**: The v4-reshaped dataset at `eval/golden_dataset.json` produced by Spec V4-7a-1, containing base predictions with v4-native ground truth fields
- **Tier_1_Evaluator**: A deterministic evaluator that runs on every eval, performs fast structural checks on the Prediction_Bundle, and returns a binary pass/fail score
- **Tier_2_Evaluator**: An LLM judge evaluator that runs on-demand, assesses semantic quality of the Prediction_Bundle using a rubric, and returns a score between 0.0 and 1.0
- **Run_Tier**: One of three execution modes — `smoke` (smoke test cases, Tier 1 only), `smoke+judges` (smoke test cases, Tier 1 + Tier 2), or `full` (all cases, Tier 1 + Tier 2)
- **Run_Metadata**: Structured metadata attached to each eval run: `description`, `prompt_versions`, `run_tier`, `dataset_version`, `agent`, `timestamp`, `duration_seconds`, `case_count`
- **Eval_Report**: A JSON file saved to `eval/reports/creation-eval-{timestamp}.json` containing Run_Metadata, per-case scores, aggregate metrics, and a smoke test summary
- **Flow_Complete_Event**: The final event in the Creation_Agent's streaming response containing the full Prediction_Bundle as its data payload
- **ParsedClaim**: Pydantic model from Turn 1 — `statement`, `verification_date` (ISO 8601), `date_reasoning`
- **VerificationPlan**: Pydantic model from Turn 2 — `sources` (list), `criteria` (list), `steps` (list)
- **PlanReview**: Pydantic model from Turn 3 — `verifiability_score` (0.0–1.0), `verifiability_reasoning`, `reviewable_sections`, `score_tier`, `score_label`, `score_guidance`, `dimension_assessments` (exactly 5)
- **DimensionAssessment**: A sub-model of PlanReview — `dimension`, `assessment` (strong/moderate/weak), `explanation`

## Requirements

### Requirement 1: AgentCore Backend Invokes Deployed Creation Agent

**User Story:** As an eval framework developer, I want the eval backend to invoke the deployed creation agent via HTTP streaming and extract the prediction bundle, so that eval cases run against the real production agent without local agent instantiation.

#### Acceptance Criteria

1. WHEN the AgentCore_Backend receives a prediction text, THE AgentCore_Backend SHALL send a JSON payload containing `prediction_text`, `user_id` set to `"eval-runner"`, and `timezone` set to `"UTC"` to the Creation_Agent via `invoke_agent_runtime()`
2. WHEN the Creation_Agent returns a streaming response, THE AgentCore_Backend SHALL parse the stream and extract the data payload from the Flow_Complete_Event
3. WHEN the Flow_Complete_Event contains a valid Prediction_Bundle, THE AgentCore_Backend SHALL return a dictionary with keys `parsed_claim`, `verification_plan`, and `plan_review` containing the deserialized bundle data
4. IF the Creation_Agent stream does not contain a Flow_Complete_Event, THEN THE AgentCore_Backend SHALL raise an error with a message identifying the missing event and the Eval_Case id
5. IF the Creation_Agent invocation fails with a network or service error, THEN THE AgentCore_Backend SHALL raise an error with the HTTP status code and the Eval_Case id

### Requirement 2: Eval Case Loading from Golden Dataset

**User Story:** As an eval framework developer, I want eval cases loaded from the v4 golden dataset with proper field mapping, so that each prediction becomes a testable case with input, expected output, and metadata.

#### Acceptance Criteria

1. WHEN the Eval_Runner loads the Golden_Dataset, THE Eval_Runner SHALL create one Eval_Case per base prediction in the dataset
2. THE Eval_Runner SHALL set each Eval_Case's `input` to the base prediction's `prediction_text` field
3. THE Eval_Runner SHALL set each Eval_Case's `expected_output` to the base prediction's `ground_truth` object
4. THE Eval_Runner SHALL set each Eval_Case's `metadata` to include the base prediction's `dimension_tags`, `difficulty`, `smoke_test` flag, `id`, and `evaluation_rubric`
5. IF the Golden_Dataset file cannot be parsed as valid JSON, THEN THE Eval_Runner SHALL exit with a non-zero status code and a descriptive error message
6. IF the Golden_Dataset file does not contain a `base_predictions` array, THEN THE Eval_Runner SHALL exit with a non-zero status code and a descriptive error message

### Requirement 3: Schema Validity Evaluator (Tier 1)

**User Story:** As an eval framework developer, I want a deterministic evaluator that checks whether the creation agent's output conforms to the ParsedClaim, VerificationPlan, and PlanReview Pydantic models, so that structural regressions are caught instantly.

#### Acceptance Criteria

1. WHEN the Schema_Validity evaluator receives a Prediction_Bundle, THE Schema_Validity evaluator SHALL validate the `parsed_claim` data against the ParsedClaim Pydantic model
2. WHEN the Schema_Validity evaluator receives a Prediction_Bundle, THE Schema_Validity evaluator SHALL validate the `verification_plan` data against the VerificationPlan Pydantic model
3. WHEN the Schema_Validity evaluator receives a Prediction_Bundle, THE Schema_Validity evaluator SHALL validate the `plan_review` data against the PlanReview Pydantic model
4. WHEN all three model validations succeed, THE Schema_Validity evaluator SHALL return a score of 1.0
5. WHEN any model validation fails, THE Schema_Validity evaluator SHALL return a score of 0.0 and include the Pydantic validation error details in the evaluator output

### Requirement 4: Field Completeness Evaluator (Tier 1)

**User Story:** As an eval framework developer, I want a deterministic evaluator that checks whether key list fields in the prediction bundle are non-empty, so that the creation agent is not producing hollow plans with empty lists.

#### Acceptance Criteria

1. WHEN the Field_Completeness evaluator receives a Prediction_Bundle, THE Field_Completeness evaluator SHALL check that the `sources` field in the VerificationPlan is a non-empty list
2. WHEN the Field_Completeness evaluator receives a Prediction_Bundle, THE Field_Completeness evaluator SHALL check that the `criteria` field in the VerificationPlan is a non-empty list
3. WHEN the Field_Completeness evaluator receives a Prediction_Bundle, THE Field_Completeness evaluator SHALL check that the `steps` field in the VerificationPlan is a non-empty list
4. WHEN all three list fields are non-empty, THE Field_Completeness evaluator SHALL return a score of 1.0
5. WHEN any list field is empty, THE Field_Completeness evaluator SHALL return a score of 0.0 and identify which fields are empty in the evaluator output

### Requirement 5: Score Range Evaluator (Tier 1)

**User Story:** As an eval framework developer, I want a deterministic evaluator that checks whether the verifiability score is within the valid range, so that out-of-bounds scores are caught immediately.

#### Acceptance Criteria

1. WHEN the Score_Range evaluator receives a Prediction_Bundle, THE Score_Range evaluator SHALL check that the `verifiability_score` field in the PlanReview is a float
2. WHEN the `verifiability_score` is a float between 0.0 and 1.0 inclusive, THE Score_Range evaluator SHALL return a score of 1.0
3. WHEN the `verifiability_score` is outside the range [0.0, 1.0] or is not a float, THE Score_Range evaluator SHALL return a score of 0.0 and include the actual value in the evaluator output

### Requirement 6: Date Resolution Evaluator (Tier 1)

**User Story:** As an eval framework developer, I want a deterministic evaluator that checks whether the parsed claim contains a valid ISO 8601 date, so that date resolution failures are caught immediately.

#### Acceptance Criteria

1. WHEN the Date_Resolution evaluator receives a Prediction_Bundle, THE Date_Resolution evaluator SHALL check that the `verification_date` field in the ParsedClaim is a valid ISO 8601 datetime string
2. WHEN the `verification_date` is a valid ISO 8601 datetime string, THE Date_Resolution evaluator SHALL return a score of 1.0
3. WHEN the `verification_date` is not a valid ISO 8601 datetime string or is missing, THE Date_Resolution evaluator SHALL return a score of 0.0 and include the actual value in the evaluator output

### Requirement 7: Dimension Count Evaluator (Tier 1)

**User Story:** As an eval framework developer, I want a deterministic evaluator that checks whether the plan review contains exactly 5 dimension assessments, so that missing or extra dimensions are caught immediately.

#### Acceptance Criteria

1. WHEN the Dimension_Count evaluator receives a Prediction_Bundle, THE Dimension_Count evaluator SHALL count the entries in the `dimension_assessments` list in the PlanReview
2. WHEN the `dimension_assessments` list contains exactly 5 entries, THE Dimension_Count evaluator SHALL return a score of 1.0
3. WHEN the `dimension_assessments` list contains fewer or more than 5 entries, THE Dimension_Count evaluator SHALL return a score of 0.0 and include the actual count in the evaluator output

### Requirement 8: Tier Consistency Evaluator (Tier 1)

**User Story:** As an eval framework developer, I want a deterministic evaluator that checks whether the score tier label matches the verifiability score value, so that tier/score mismatches are caught immediately.

#### Acceptance Criteria

1. WHEN the Tier_Consistency evaluator receives a Prediction_Bundle with a `verifiability_score` of 0.7 or higher, THE Tier_Consistency evaluator SHALL check that the `score_tier` field in the PlanReview equals `"high"`
2. WHEN the Tier_Consistency evaluator receives a Prediction_Bundle with a `verifiability_score` of 0.4 or higher but less than 0.7, THE Tier_Consistency evaluator SHALL check that the `score_tier` field in the PlanReview equals `"moderate"`
3. WHEN the Tier_Consistency evaluator receives a Prediction_Bundle with a `verifiability_score` less than 0.4, THE Tier_Consistency evaluator SHALL check that the `score_tier` field in the PlanReview equals `"low"`
4. WHEN the `score_tier` matches the expected tier for the given `verifiability_score`, THE Tier_Consistency evaluator SHALL return a score of 1.0
5. WHEN the `score_tier` does not match the expected tier, THE Tier_Consistency evaluator SHALL return a score of 0.0 and include the actual score, actual tier, and expected tier in the evaluator output

### Requirement 9: Intent Preservation Evaluator (Tier 2)

**User Story:** As an eval framework developer, I want an LLM judge evaluator that assesses whether the parsed claim and verification plan faithfully represent the user's original prediction, so that intent drift is detected before it compounds into verification failures.

#### Acceptance Criteria

1. WHEN the Intent_Preservation evaluator receives a Prediction_Bundle and the original prediction text, THE Intent_Preservation evaluator SHALL prompt an LLM judge to assess whether the ParsedClaim's `statement` captures the user's actual prediction without reinterpretation
2. WHEN the Intent_Preservation evaluator receives a Prediction_Bundle and the original prediction text, THE Intent_Preservation evaluator SHALL prompt an LLM judge to assess whether the VerificationPlan tests what the user meant, not a reinterpretation of the prediction
3. THE Intent_Preservation evaluator SHALL use a rubric that focuses on: fidelity of the parsed statement to the original prediction, preservation of temporal intent, preservation of scope and specificity, and absence of added assumptions not present in the original text
4. THE Intent_Preservation evaluator SHALL return a score between 0.0 and 1.0 representing the degree of intent preservation
5. THE Intent_Preservation evaluator SHALL include the LLM judge's reasoning in the evaluator output

### Requirement 10: Plan Quality Evaluator (Tier 2)

**User Story:** As an eval framework developer, I want an LLM judge evaluator that assesses whether the verification plan is actionable and executable, so that plans that look structurally valid but are practically useless are identified.

#### Acceptance Criteria

1. WHEN the Plan_Quality evaluator receives a Prediction_Bundle, THE Plan_Quality evaluator SHALL prompt an LLM judge to assess whether the verification criteria are measurable and unambiguous
2. WHEN the Plan_Quality evaluator receives a Prediction_Bundle, THE Plan_Quality evaluator SHALL prompt an LLM judge to assess whether the verification sources are real and accessible via Browser or Code Interpreter tools
3. WHEN the Plan_Quality evaluator receives a Prediction_Bundle, THE Plan_Quality evaluator SHALL prompt an LLM judge to assess whether the verification steps are ordered and executable in sequence
4. THE Plan_Quality evaluator SHALL use a rubric that focuses on: specificity and measurability of criteria, existence and accessibility of sources, logical ordering and executability of steps, and absence of vague or untestable language
5. THE Plan_Quality evaluator SHALL return a score between 0.0 and 1.0 representing the overall plan quality
6. THE Plan_Quality evaluator SHALL include the LLM judge's reasoning in the evaluator output

### Requirement 11: Run Tier Filtering

**User Story:** As an eval framework developer, I want the eval runner to support three run tiers that control which cases and evaluators execute, so that I can trade off speed versus coverage depending on the iteration stage.

#### Acceptance Criteria

1. WHEN the Eval_Runner is invoked with `--tier smoke`, THE Eval_Runner SHALL execute only Eval_Cases where the `smoke_test` metadata flag is `true` and run only Tier_1_Evaluators
2. WHEN the Eval_Runner is invoked with `--tier smoke+judges`, THE Eval_Runner SHALL execute only Eval_Cases where the `smoke_test` metadata flag is `true` and run both Tier_1_Evaluators and Tier_2_Evaluators
3. WHEN the Eval_Runner is invoked with `--tier full`, THE Eval_Runner SHALL execute all Eval_Cases and run both Tier_1_Evaluators and Tier_2_Evaluators
4. WHEN the Eval_Runner is invoked without a `--tier` flag, THE Eval_Runner SHALL default to the `smoke` tier

### Requirement 12: CLI Interface

**User Story:** As an eval framework developer, I want a CLI with flags for dataset path, run tier, description, output directory, dry run, and single case execution, so that eval runs are configurable without editing code.

#### Acceptance Criteria

1. THE Eval_Runner SHALL accept a `--dataset` flag specifying the path to the Golden_Dataset file, defaulting to `eval/golden_dataset.json`
2. THE Eval_Runner SHALL accept a `--tier` flag specifying the Run_Tier, defaulting to `smoke`
3. THE Eval_Runner SHALL accept a `--description` flag specifying a one-line description for the run; WHEN omitted, THE Eval_Runner SHALL auto-generate a description from the run tier and timestamp
4. THE Eval_Runner SHALL accept an `--output-dir` flag specifying the directory for report output, defaulting to `eval/reports/`
5. WHEN the Eval_Runner is invoked with `--dry-run`, THE Eval_Runner SHALL list all cases that would be executed with their ids and metadata without invoking the Creation_Agent or running evaluators
6. WHEN the Eval_Runner is invoked with `--case` followed by a case id, THE Eval_Runner SHALL execute only the Eval_Case matching that id regardless of the Run_Tier's case filtering
7. IF the `--case` flag specifies an id that does not exist in the Golden_Dataset, THEN THE Eval_Runner SHALL exit with a non-zero status code and a descriptive error message

### Requirement 13: Structured Run Metadata

**User Story:** As an eval framework developer, I want each eval run to carry structured metadata, so that the dashboard dropdown shows meaningful context instead of raw filenames per Decision 127.

#### Acceptance Criteria

1. THE Eval_Runner SHALL record a `description` field in the Run_Metadata, sourced from the `--description` CLI flag or auto-generated
2. THE Eval_Runner SHALL record a `prompt_versions` field in the Run_Metadata containing the prompt version manifest active during the run
3. THE Eval_Runner SHALL record a `run_tier` field in the Run_Metadata containing the Run_Tier value used for the run
4. THE Eval_Runner SHALL record a `dataset_version` field in the Run_Metadata sourced from the Golden_Dataset's `dataset_version` field
5. THE Eval_Runner SHALL record an `agent` field in the Run_Metadata set to `"creation"`
6. THE Eval_Runner SHALL record a `timestamp` field in the Run_Metadata containing the ISO 8601 datetime when the run started
7. THE Eval_Runner SHALL record a `duration_seconds` field in the Run_Metadata containing the total wall-clock time of the run in seconds
8. THE Eval_Runner SHALL record a `case_count` field in the Run_Metadata containing the number of Eval_Cases executed in the run

### Requirement 14: Eval Report Output

**User Story:** As an eval framework developer, I want each eval run to produce a JSON report with per-case scores, aggregate metrics, and run metadata, so that results are machine-readable and comparable across runs.

#### Acceptance Criteria

1. THE Eval_Runner SHALL save the Eval_Report as a JSON file at `{output_dir}/creation-eval-{timestamp}.json` where `{timestamp}` is formatted as `YYYYMMDD-HHMMSS`
2. THE Eval_Report SHALL contain a `run_metadata` object with all fields specified in Requirement 13
3. THE Eval_Report SHALL contain an `aggregate_scores` object with per-evaluator average scores and an overall pass rate computed as the fraction of Eval_Cases where all Tier_1_Evaluators returned a score of 1.0
4. THE Eval_Report SHALL contain a `case_results` array with one entry per executed Eval_Case, each containing the case `id`, the case `input`, and a per-evaluator score breakdown
5. THE Eval_Report SHALL contain a `smoke_test_summary` object with aggregate scores computed only from Eval_Cases where the `smoke_test` metadata flag is `true`, even when the Run_Tier is `full`
6. THE Eval_Report SHALL produce valid JSON output with consistent 2-space indentation
7. IF the output directory does not exist, THEN THE Eval_Runner SHALL create the directory before writing the report
