# Requirements Document

## Introduction

CalledIt's eval suite currently measures proxy metrics (category accuracy, JSON validity, essay-quality reasoning) rather than the system's actual goals: understanding prediction intent and producing executable verification plans. This spec adds verification-centric fields to the golden dataset (v3), builds two new primary evaluators (IntentPreservation, CriteriaMethodAlignment), integrates Strands Evals SDK as the evaluation primitive layer, recalibrates the judge rubric, updates the eval runner to orchestrate the new evaluators, and extends the dashboard to visualize verification-quality metrics.

## Glossary

- **Golden_Dataset**: JSON file (`eval/golden_dataset.json`) containing hand-crafted test cases with ground truth metadata, used as the evaluation benchmark for the agent pipeline.
- **Dataset_Loader**: Python module (`golden_dataset.py`) that parses, validates, and deserializes the Golden_Dataset JSON into typed dataclasses (`BasePrediction`, `FuzzyPrediction`, `GoldenDataset`).
- **Eval_Runner**: Python module (`eval_runner.py`) that orchestrates end-to-end evaluation: loads the dataset, runs the agent pipeline per test case, invokes evaluators, aggregates scores, persists results to DDB and local files.
- **IntentPreservation_Evaluator**: New LLM-as-judge evaluator that scores whether the Verification_Builder's criteria faithfully capture the user's original prediction intent, stripping framing language (e.g., "I bet") to assess semantic equivalence.
- **CriteriaMethodAlignment_Evaluator**: New LLM-as-judge evaluator that scores whether the Verification_Builder's method provides a realistic, actionable plan to determine true/false given the stated criteria.
- **Verification_Builder**: The agent in the CalledIt pipeline that transforms parsed predictions into verification criteria (checkable true/false conditions) and a verification method (a plan for proving the prediction).
- **Strands_Evals_SDK**: The `strands-agents-evals` Python package providing evaluation primitives (`OutputEvaluator`, `Evaluator`, `EvaluationOutput`, `Case`, `Experiment`) that run anywhere Python runs.
- **OutputEvaluator**: A Strands Evals SDK class that implements LLM-as-judge evaluation with a custom rubric string, handling model invocation, response parsing, and structured output.
- **EvaluationOutput**: Strands Evals SDK structured return type with fields: `score`, `test_pass`, `reason`, `label`.
- **Dashboard**: Six-page Streamlit application (`eval/dashboard/`) that visualizes eval run data from DDB and local files.
- **Reasoning_Store**: DDB-backed persistence layer (`eval_reasoning_store.py`) that stores agent outputs, judge reasoning, and run metadata with TTL.
- **Score_History**: JSON file (`score_history.json`) that tracks run-over-run summary data for trend analysis.
- **Judge_Rubric**: The prompt template used by LLM-as-judge evaluators to score agent outputs; defines the scoring criteria and scale.

## Requirements

### Requirement 1: Golden Dataset V3 Schema Extension

**User Story:** As an eval developer, I want the golden dataset to include expected verification criteria and expected verification method per test case, so that the new evaluators have ground truth to compare against.

#### Acceptance Criteria

1. THE Golden_Dataset SHALL include a `schema_version` value of `"3.0"` and a `dataset_version` value of `"3.0"`.
2. WHEN a base prediction is loaded, THE Dataset_Loader SHALL require an `expected_verification_criteria` field inside `ground_truth` containing a non-empty list of strings representing the checkable true/false conditions the Verification_Builder should produce.
3. WHEN a base prediction is loaded, THE Dataset_Loader SHALL require an `expected_verification_method` field inside `ground_truth` containing a non-empty string describing the expected approach for proving the prediction true or false.
4. WHEN a base prediction has `expected_verification_criteria` that is missing, empty, or not a list of strings, THE Dataset_Loader SHALL raise a `ValueError` with a message identifying the prediction ID and the invalid field.
5. WHEN a base prediction has `expected_verification_method` that is missing, empty, or not a string, THE Dataset_Loader SHALL raise a `ValueError` with a message identifying the prediction ID and the invalid field.
6. THE `GroundTruthMetadata` dataclass SHALL include `expected_verification_criteria: List[str]` and `expected_verification_method: str` fields.
7. THE `dataset_to_dict` serializer SHALL include `expected_verification_criteria` and `expected_verification_method` in the serialized ground truth output.
8. THE `validate_dataset.py` script SHALL validate the new fields and report errors for any test case missing or having invalid `expected_verification_criteria` or `expected_verification_method`.

### Requirement 2: Golden Dataset V3 Content Population

**User Story:** As an eval developer, I want all 45 base predictions populated with expected verification criteria and method, so that every test case can be scored by the new evaluators.

#### Acceptance Criteria

1. THE Golden_Dataset SHALL contain `expected_verification_criteria` for all 45 base predictions, where each entry is a list of one or more checkable true/false conditions that capture the prediction's intent without framing language.
2. THE Golden_Dataset SHALL contain `expected_verification_method` for all 45 base predictions, where each entry describes a concrete verification approach referencing specific data sources, tools, or observation methods.
3. WHEN a prediction uses framing language (e.g., "I bet", "I think", "I predict"), THE `expected_verification_criteria` SHALL capture the underlying factual claim, not the framing.
4. WHEN a prediction references a specific data source (e.g., ESPN, weather API, stock ticker), THE `expected_verification_method` SHALL reference that data source or an equivalent publicly accessible source.
5. WHEN a prediction requires human observation (e.g., shirt color, taste), THE `expected_verification_method` SHALL describe the manual verification approach including who observes and when.

### Requirement 3: IntentPreservation Evaluator

**User Story:** As an eval developer, I want an evaluator that scores whether the Verification_Builder's criteria faithfully capture the user's prediction intent, so that I can measure the system's primary goal of intent understanding.

#### Acceptance Criteria

1. THE IntentPreservation_Evaluator SHALL accept the original prediction text, the Verification_Builder's output criteria, and the expected verification criteria from the golden dataset as inputs.
2. THE IntentPreservation_Evaluator SHALL use the Strands Evals SDK `OutputEvaluator` with a rubric that instructs the judge to score semantic equivalence between the Verification_Builder's criteria and the expected criteria.
3. THE IntentPreservation_Evaluator SHALL return a structured result containing `score` (0.0 to 1.0), `evaluator` label `"IntentPreservation"`, `judge_reasoning` (string), and `judge_model` (string).
4. WHEN the Verification_Builder's criteria captures the factual claim but includes framing language (e.g., "user believes X"), THE IntentPreservation_Evaluator SHALL score below 0.7.
5. WHEN the Verification_Builder's criteria captures the factual claim accurately and strips framing language, THE IntentPreservation_Evaluator SHALL score 0.8 or above.
6. IF the Strands Evals SDK `OutputEvaluator` invocation fails, THEN THE IntentPreservation_Evaluator SHALL return a score of 0.0 with the error message in `judge_reasoning`.
7. THE IntentPreservation_Evaluator SHALL use a judge model different from the agent model to avoid self-evaluation bias.

### Requirement 4: CriteriaMethodAlignment Evaluator

**User Story:** As an eval developer, I want an evaluator that scores whether the Verification_Builder's method provides a realistic plan to determine true/false given the criteria, so that I can measure verification executability.

#### Acceptance Criteria

1. THE CriteriaMethodAlignment_Evaluator SHALL accept the Verification_Builder's output criteria, the Verification_Builder's output method, and the expected verification method from the golden dataset as inputs.
2. THE CriteriaMethodAlignment_Evaluator SHALL use the Strands Evals SDK `OutputEvaluator` with a rubric that instructs the judge to score whether the method provides a realistic, actionable plan to verify the criteria.
3. THE CriteriaMethodAlignment_Evaluator SHALL return a structured result containing `score` (0.0 to 1.0), `evaluator` label `"CriteriaMethodAlignment"`, `judge_reasoning` (string), and `judge_model` (string).
4. WHEN the method references a specific, accessible data source appropriate for the criteria (e.g., "check ESPN API for game result" when criteria is about a sports outcome), THE CriteriaMethodAlignment_Evaluator SHALL score 0.8 or above.
5. WHEN the method defaults to "ask the user" as the primary approach for a prediction that has publicly available verification sources, THE CriteriaMethodAlignment_Evaluator SHALL score below 0.5.
6. IF the Strands Evals SDK `OutputEvaluator` invocation fails, THEN THE CriteriaMethodAlignment_Evaluator SHALL return a score of 0.0 with the error message in `judge_reasoning`.
7. THE CriteriaMethodAlignment_Evaluator SHALL use a judge model different from the agent model to avoid self-evaluation bias.

### Requirement 5: Strands Evals SDK Integration

**User Story:** As an eval developer, I want the evaluation primitives to use Strands Evals SDK, so that judge invocation, response parsing, and structured output are handled by a maintained library rather than hand-rolled code.

#### Acceptance Criteria

1. THE `strands-agents-evals` package SHALL be added to the root `requirements.txt` as a development dependency.
2. THE IntentPreservation_Evaluator SHALL instantiate a Strands Evals SDK `OutputEvaluator` with a rubric string, model ID, and `include_inputs=True`.
3. THE CriteriaMethodAlignment_Evaluator SHALL instantiate a Strands Evals SDK `OutputEvaluator` with a rubric string, model ID, and `include_inputs=True`.
4. WHEN an `OutputEvaluator` returns an `EvaluationOutput`, THE evaluator wrapper SHALL map `EvaluationOutput.score` to the CalledIt score format and `EvaluationOutput.reason` to `judge_reasoning`.
5. THE existing `ReasoningQuality` evaluator SHALL remain functional using its current hand-rolled judge implementation until explicitly migrated in a future spec.
6. THE existing deterministic evaluators (`CategoryMatch`, `JSONValidity`, `ClarificationQuality`, `Convergence`) SHALL remain unchanged.

### Requirement 6: Judge Rubric Recalibration

**User Story:** As an eval developer, I want the ReasoningQuality judge rubric to focus on verification executability rather than essay quality, so that the judge measures whether the verification plan would succeed.

#### Acceptance Criteria

1. THE `verification_builder` judge rubric in `reasoning_quality.py` SHALL be updated to score whether the verification plan would succeed at verifying the prediction, replacing the current essay-quality focus.
2. THE updated `verification_builder` rubric SHALL define scoring anchors: 1.0 for a plan that identifies specific data sources and timing for verification; 0.7 for a plan with correct approach but vague sources; 0.4 for a generic plan that could apply to any prediction; 0.0 for a plan that would fail to verify the prediction.
3. THE `categorizer` judge rubric SHALL remain unchanged.
4. THE `review` judge rubric SHALL remain unchanged.

### Requirement 7: Eval Runner Updates

**User Story:** As an eval developer, I want the eval runner to invoke the new evaluators alongside existing ones, so that every eval run produces verification-quality scores.

#### Acceptance Criteria

1. WHEN `use_judge` is True, THE Eval_Runner SHALL invoke the IntentPreservation_Evaluator for each base prediction and include the result in `evaluator_scores` with key `"IntentPreservation"`.
2. WHEN `use_judge` is True, THE Eval_Runner SHALL invoke the CriteriaMethodAlignment_Evaluator for each base prediction and include the result in `evaluator_scores` with key `"CriteriaMethodAlignment"`.
3. THE Eval_Runner SHALL pass the `expected_verification_criteria` and `expected_verification_method` from the test case's `ground_truth` to the respective evaluators.
4. THE Eval_Runner SHALL include `IntentPreservation` and `CriteriaMethodAlignment` scores in the aggregated report under `per_agent_aggregates`.
5. THE Reasoning_Store SHALL persist IntentPreservation and CriteriaMethodAlignment judge reasoning to DDB alongside existing ReasoningQuality reasoning.
6. THE `_aggregate_report` function SHALL compute average scores for `IntentPreservation` and `CriteriaMethodAlignment` across all test cases and include them in the report summary.
7. THE `print_report` function SHALL display IntentPreservation and CriteriaMethodAlignment average scores in the console output.

### Requirement 8: Dashboard Updates

**User Story:** As an eval developer, I want the dashboard to visualize IntentPreservation and CriteriaMethodAlignment scores, so that I can track verification quality over time and identify weak test cases.

#### Acceptance Criteria

1. THE Dashboard Trends page SHALL display IntentPreservation and CriteriaMethodAlignment average scores as separate trend lines alongside existing metrics.
2. THE Dashboard Heatmap page SHALL include IntentPreservation and CriteriaMethodAlignment as columns in the per-test-case score matrix.
3. THE Dashboard Reasoning Explorer page SHALL display IntentPreservation and CriteriaMethodAlignment judge reasoning when drilling into a test case, alongside existing ReasoningQuality reasoning.
4. WHEN a run predates the new evaluators and has no IntentPreservation or CriteriaMethodAlignment scores, THE Dashboard SHALL display "N/A" for those cells rather than 0 or an error.
5. THE Dashboard data loader SHALL handle runs with and without the new evaluator scores without raising exceptions.
