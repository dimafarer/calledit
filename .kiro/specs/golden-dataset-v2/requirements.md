# Requirements Document

## Introduction

A comprehensive golden dataset v2 for the CalledIt prediction evaluation framework, expanding from 15 base + 5 fuzzy predictions to ~40-50 base + 20-30 fuzzy predictions with rich ground truth metadata per prediction. The dataset uses persona-driven generation across a 5-dimension matrix (domain, stakes, time horizon, expected category, fuzziness potential) to cover the full spectrum of human prediction behavior. Each prediction captures ground truth reasoning — verifiability rationale, verification date derivation, methods, sources, criteria, and steps — so expected labels can be re-derived when verification categories evolve rather than manually re-tagging the entire dataset. The dataset stores in git with an explicit version field, includes adversarial boundary cases for the categorizer, and feeds into the existing eval framework (5 evaluators, score history, chart generation). A DynamoDB table captures full eval reasoning traces for deep analysis.

## Glossary

- **Golden_Dataset_V2**: The expanded JSON dataset file (`eval/golden_dataset.json`) containing 40-50 base predictions and 20-30 fuzzy variants with ground truth metadata, schema version "2.0"
- **Ground_Truth_Metadata**: Per-prediction metadata capturing WHY a prediction has its expected category — verifiability reasoning, date derivation logic, verification methods, data sources, objectivity assessment, and criteria — enabling label re-derivation when categories change
- **Persona**: A human archetype (parent, commuter, sports fan, investor, student, chef, etc.) used to generate realistic predictions spanning diverse domains and stakes
- **Dimension_Matrix**: A 5-axis classification system for predictions: domain, stakes, time horizon, expected category, and fuzziness potential
- **Fuzziness_Level**: A degradation tier for fuzzy predictions — Level 0 (perfectly specified, no ambiguity), Level 1 (missing one detail), Level 2 (missing multiple details), Level 3 (highly ambiguous with slang, idioms, or implicit context)
- **Verifiability_Category**: One of three classification values: auto_verifiable (verifiable now with current tools), automatable (could be verified with a plausible tool), human_only (requires subjective human judgment)
- **Prediction_Graph**: The 4-agent Strands graph (Parser → Categorizer → Verification Builder → ReviewAgent) that processes predictions
- **Eval_Runner**: The CLI tool (`eval_runner.py`) that executes golden dataset test cases through the Prediction_Graph and scores results using evaluators
- **Eval_Reasoning_Store**: A DynamoDB table storing full model reasoning traces, intermediate agent outputs, judge reasoning, and token counts from evaluation runs
- **Cross_Agent_Coherence**: The property that parser date extraction, categorizer verifiability judgment, and Verification Builder methods/sources/criteria/steps tell a consistent, non-contradictory story for a given prediction
- **Boundary_Case**: An adversarial or tricky prediction designed to trip up the categorizer — predictions near category boundaries, with temporal ambiguity, or where tool availability changes the expected category
- **Dataset_Version**: An explicit version identifier (e.g., "2.0") stored in the dataset JSON and referenced in eval reports and score history for traceability
- **Expected_Outputs**: Per-agent expected outputs for a test case — only `expected_category` is required; parser, verification_builder, and review outputs are optional rubric guidance

## Requirements

### Requirement 1: Ground Truth Metadata Schema

**User Story:** As a developer, I want each prediction in the golden dataset to capture WHY it has its expected category through structured ground truth metadata, so that when verification categories change in the future, expected labels can be re-derived from ground truth rather than manually re-tagging 50+ test cases.

#### Acceptance Criteria

1. WHEN a base prediction is defined in the Golden_Dataset_V2, THE Ground_Truth_Metadata SHALL include a `verifiability_reasoning` field (non-empty string) explaining why the prediction falls into its expected Verifiability_Category
2. WHEN a base prediction is defined in the Golden_Dataset_V2, THE Ground_Truth_Metadata SHALL include a `date_derivation` field (non-empty string) explaining how the verification date is determined from the prediction text (explicit date, relative reference, implied deadline, or estimated timeframe)
3. WHEN a base prediction is defined in the Golden_Dataset_V2, THE Ground_Truth_Metadata SHALL include a `verification_sources` field (non-empty list of strings) identifying the data sources or observation methods needed to verify the prediction
4. WHEN a base prediction is defined in the Golden_Dataset_V2, THE Ground_Truth_Metadata SHALL include an `objectivity_assessment` field with value "objective", "subjective", or "mixed", indicating whether the prediction outcome can be measured without human judgment
5. WHEN a base prediction is defined in the Golden_Dataset_V2, THE Ground_Truth_Metadata SHALL include a `verification_criteria` field (non-empty list of strings) specifying the measurable or observable conditions that determine prediction truth
6. WHEN a base prediction is defined in the Golden_Dataset_V2, THE Ground_Truth_Metadata SHALL include a `verification_steps` field (non-empty list of strings) describing the ordered actions needed to verify the prediction
7. THE Ground_Truth_Metadata fields (verifiability_reasoning, date_derivation, verification_sources, objectivity_assessment, verification_criteria, verification_steps) SHALL form a coherent narrative — the sources SHALL support the criteria, the criteria SHALL align with the objectivity_assessment, and the reasoning SHALL reference the sources and criteria

### Requirement 2: Persona-Driven Prediction Generation

**User Story:** As a developer, I want the golden dataset to contain 40-50 base predictions generated from diverse human personas across a 5-dimension matrix, so that the eval framework tests the Prediction_Graph against the full spectrum of real human prediction behavior.

#### Acceptance Criteria

1. THE Golden_Dataset_V2 SHALL contain between 40 and 50 base predictions (inclusive)
2. THE Golden_Dataset_V2 SHALL include predictions generated from at least 12 distinct Personas (e.g., parent, commuter, sports fan, investor, student, chef, traveler, manager, gardener, gamer, retiree, athlete)
3. THE Golden_Dataset_V2 SHALL include predictions spanning at least 8 distinct domains from the Dimension_Matrix (weather, sports, finance, personal, health, tech, social, work, food, travel, entertainment, nature, politics)
4. THE Golden_Dataset_V2 SHALL include predictions across all four stakes levels: life-changing, significant, moderate, and trivial — with at least 3 predictions per stakes level
5. THE Golden_Dataset_V2 SHALL include predictions across at least 4 distinct time horizons: minutes-to-hours, days, weeks-to-months, and months-to-years — with at least 3 predictions per time horizon
6. THE Golden_Dataset_V2 SHALL include at least 12 auto_verifiable, at least 12 automatable, and at least 12 human_only base predictions
7. THE Golden_Dataset_V2 SHALL include at least 5 Boundary_Cases — adversarial or tricky predictions designed to challenge the categorizer at category boundaries (e.g., predictions where tool availability changes the category, temporal ambiguity affects verifiability, or subjective-seeming predictions have objective criteria)

### Requirement 3: Fuzzy Prediction Variants with Fuzziness Levels

**User Story:** As a developer, I want 20-30 fuzzy prediction variants with explicit fuzziness levels (0-3) and multi-level degradation, so that the eval framework can test the ReviewAgent's clarification quality across a realistic range of ambiguity.

#### Acceptance Criteria

1. THE Golden_Dataset_V2 SHALL contain between 20 and 30 fuzzy predictions (inclusive), each referencing a corresponding base prediction by ID
2. WHEN a fuzzy prediction is defined, THE Golden_Dataset_V2 SHALL assign a `fuzziness_level` integer: 0 (perfectly specified, no ambiguity — used as a control), 1 (missing one detail such as location, time, or threshold), 2 (missing multiple details such as vague subject and vague criteria), or 3 (highly ambiguous with slang, idioms, or implicit context)
3. THE Golden_Dataset_V2 SHALL include at least 3 fuzzy predictions at Fuzziness_Level 0 (control cases where the ReviewAgent should find no clarification needed)
4. THE Golden_Dataset_V2 SHALL include at least 5 fuzzy predictions at Fuzziness_Level 1, at least 5 at Fuzziness_Level 2, and at least 5 at Fuzziness_Level 3
5. WHEN a fuzzy prediction is defined, THE Golden_Dataset_V2 SHALL include `simulated_clarifications` (list of answer strings), `expected_clarification_topics` (list of keyword strings), and `expected_post_clarification_outputs` containing at minimum the expected Verifiability_Category after clarification
6. THE Golden_Dataset_V2 SHALL include at least 5 fuzzy predictions where clarification improves precision without changing the Verifiability_Category (human_only remains human_only after clarification)
7. WHEN a base prediction has multiple fuzzy variants at different Fuzziness_Levels, THE Golden_Dataset_V2 SHALL store each variant as a separate fuzzy prediction entry referencing the same base prediction ID

### Requirement 4: Expected Outputs Structure with Lightweight Rubrics

**User Story:** As a developer, I want the expected outputs per prediction to require only the expected category while making other agent outputs optional rubric guidance, so that maintaining the dataset is practical at 50+ predictions without requiring exact expected outputs for every agent.

#### Acceptance Criteria

1. WHEN a base prediction defines `expected_per_agent_outputs`, THE Golden_Dataset_V2 SHALL require only the `categorizer.expected_category` field (one of auto_verifiable, automatable, human_only) — parser, verification_builder, and review expected outputs SHALL be optional
2. WHEN optional expected outputs are provided for parser, verification_builder, or review agents, THE Golden_Dataset_V2 SHALL treat the values as rubric guidance for the LLM-as-judge evaluator rather than exact-match targets
3. WHEN a base prediction includes an `evaluation_rubric` field, THE Golden_Dataset_V2 SHALL store a free-text string describing what the LLM-as-judge should look for in agent reasoning (e.g., "categorizer reasoning should reference astronomical knowledge")
4. THE Golden_Dataset_V2 SHALL validate that every base prediction and every fuzzy prediction post-clarification output includes a non-empty `expected_category` value from the set {auto_verifiable, automatable, human_only}

### Requirement 5: Cross-Agent Coherence Testability

**User Story:** As a developer, I want the golden dataset to enable measuring cross-agent coherence — whether the parser's date extraction, categorizer's verifiability judgment, and Verification Builder's methods/sources/criteria/steps tell a consistent story — so that I can detect when agents produce individually correct but collectively incoherent outputs.

#### Acceptance Criteria

1. WHEN a base prediction includes Ground_Truth_Metadata, THE Ground_Truth_Metadata verification_sources SHALL align with the expected verification_builder sources (if provided) — the ground truth sources represent what a correct Verification Builder should reference
2. WHEN a base prediction includes Ground_Truth_Metadata, THE Ground_Truth_Metadata date_derivation SHALL describe the same temporal logic that a correct parser should apply to extract the verification_date
3. THE Golden_Dataset_V2 SHALL include at least 5 base predictions with complete expected outputs for all four agents (parser, categorizer, verification_builder, review) to serve as Cross_Agent_Coherence test anchors
4. WHEN a base prediction is tagged as a Boundary_Case, THE Ground_Truth_Metadata verifiability_reasoning SHALL explicitly document the boundary condition (e.g., "tool availability changes category from automatable to auto_verifiable", "temporal ambiguity makes date extraction non-trivial")

### Requirement 6: DynamoDB Eval Reasoning Store

**User Story:** As a developer, I want full model reasoning traces, intermediate agent outputs, judge reasoning, and token counts stored in DynamoDB during evaluation runs, so that I can analyze agent behavior patterns, identify failure modes, and correlate reasoning quality with scores.

#### Acceptance Criteria

1. WHEN an evaluation run executes a test case through the Prediction_Graph, THE Eval_Reasoning_Store SHALL capture the full text output from each of the four agents (parser, categorizer, verification_builder, review) as separate items keyed by eval run ID and test case ID
2. WHEN an evaluation run scores a test case using the LLM-as-judge evaluator, THE Eval_Reasoning_Store SHALL capture the judge model's reasoning explanation, the numeric score, and the judge model ID
3. WHEN an evaluation run executes a test case, THE Eval_Reasoning_Store SHALL capture token counts (input tokens and output tokens) for each agent invocation and for each judge invocation
4. WHEN an evaluation run completes, THE Eval_Reasoning_Store SHALL record the prompt version manifest, dataset version, timestamp, and overall evaluation metadata (total test cases, pass rate, execution duration)
5. THE Eval_Reasoning_Store DynamoDB table SHALL use a partition key of `eval_run_id` (string) and a sort key of `record_type#test_case_id` (string) to support querying all records for a run and filtering by record type
6. IF the DynamoDB write fails during an evaluation run, THEN THE Eval_Runner SHALL log the write failure at WARN level and continue the evaluation without blocking — eval results SHALL still be written to the local score history file

### Requirement 7: Dataset Schema Evolution and Versioning

**User Story:** As a developer, I want the golden dataset to have explicit versioning, a defined schema, and a clear migration path, so that the dataset can evolve over time without breaking the eval runner or invalidating historical score comparisons.

#### Acceptance Criteria

1. THE Golden_Dataset_V2 SHALL include a top-level `dataset_version` field (string, e.g., "2.0") distinct from the existing `schema_version` field — `schema_version` tracks the JSON structure format while `dataset_version` tracks the content revision
2. WHEN the Eval_Runner loads the Golden_Dataset_V2, THE Eval_Runner SHALL validate that the `schema_version` is supported and raise a descriptive error if the schema version is unrecognized
3. WHEN an evaluation report is generated, THE evaluation report SHALL include both the `dataset_version` and `schema_version` alongside the prompt version manifest for full traceability
4. WHEN the score history records an evaluation, THE score history SHALL include the `dataset_version` so that score comparisons across different dataset versions are flagged with a warning
5. THE Golden_Dataset_V2 SHALL be stored in git as `eval/golden_dataset.json` with the `dataset_version` field serving as the primary version identifier
6. WHEN the dataset exceeds 100 test cases, THE Golden_Dataset_V2 storage SHALL migrate to a private S3 bucket with versioning enabled, public access blocked, and encryption at rest using AES256

### Requirement 8: Dataset Maintenance Process

**User Story:** As a developer, I want a structured process for adding new test cases, re-deriving labels when categories change, and validating dataset integrity, so that the golden dataset remains accurate and useful as the system evolves.

#### Acceptance Criteria

1. THE Golden_Dataset_V2 SHALL include a validation script that checks all structural constraints: required fields present, field types correct, all fuzzy prediction `base_prediction_id` references resolve to existing base predictions, all `expected_category` values are valid, and Ground_Truth_Metadata coherence (sources support criteria, criteria align with objectivity_assessment)
2. WHEN a new base prediction is added to the Golden_Dataset_V2, THE validation script SHALL verify that the prediction has all required fields including Ground_Truth_Metadata and that the `dataset_version` has been incremented
3. WHEN Verifiability_Categories are redefined (e.g., categories renamed, split, or merged), THE Ground_Truth_Metadata SHALL provide sufficient information (verifiability_reasoning, objectivity_assessment, verification_sources) to re-derive the expected_category under the new category definitions without re-analyzing each prediction from scratch
4. THE Golden_Dataset_V2 SHALL assign a unique string ID to each base prediction (format: `base-NNN`) and each fuzzy prediction (format: `fuzzy-NNN`) with IDs that are stable across dataset versions — existing IDs SHALL NOT be reassigned or reused

### Requirement 9: Dataset Round-Trip Integrity

**User Story:** As a developer, I want the golden dataset to maintain integrity through serialization and deserialization, so that loading and saving the dataset never silently corrupts test cases.

#### Acceptance Criteria

1. FOR ALL valid Golden_Dataset_V2 JSON files, loading the dataset into Python objects and serializing back to JSON SHALL produce a file that, when loaded again, yields an equivalent dataset with identical field values for all base predictions and fuzzy predictions (round-trip property)
2. WHEN the validation script checks the Golden_Dataset_V2, THE validation script SHALL verify that all base prediction IDs are unique, all fuzzy prediction IDs are unique, and no ID collisions exist between base and fuzzy prediction ID namespaces
3. WHEN the Golden_Dataset_V2 is loaded, THE loader SHALL verify that the total count of base predictions and fuzzy predictions matches the expected counts declared in the dataset metadata (if present) to detect truncation or corruption
