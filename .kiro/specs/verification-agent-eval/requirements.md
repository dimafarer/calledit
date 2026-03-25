# Requirements Document

## Introduction

Build a separate eval experiment for the v4 verification agent, parallel to the creation agent eval (V4-7a-2). The verification agent receives a prediction bundle from DynamoDB, gathers evidence using AgentCore Browser and Code Interpreter tools, and produces a structured verdict (`confirmed`/`refuted`/`inconclusive` + confidence + evidence + reasoning). This eval experiment measures verdict quality through a tiered evaluator strategy: 5 Tier 1 deterministic evaluators run on every eval (instant, free), and 2 Tier 2 evaluators run on-demand (1 deterministic verdict accuracy check in golden mode, 1 LLM judge for evidence quality).

**Scope: `immediate` verification mode only.** This spec intentionally covers only predictions with `verification_mode: "immediate"` — those verifiable right now with a single agent invocation and a definitive true/false answer. This is the cleanest starting point: unambiguous ground truth, no timing complexity, evaluator assumptions are explicit. Support for `at_date`, `before_date`, and `recurring` verification modes is tracked in backlog item 0 and will be added as mode-aware evaluator variants without changing what's built here.

The eval runner supports two data sources via a `--source` flag: `golden` mode writes qualifying cases to a dedicated `calledit-v4-eval` DynamoDB table (with `verification_mode: "immediate"` in each bundle), invokes the agent, compares verdicts against ground truth, and cleans up; `ddb` mode queries the real `calledit-v4` table for `verification_readiness: immediate` predictions and runs in judge-only mode. The verification agent handler requires a small change to accept an optional `table_name` payload override so eval runs do not contaminate production data. Per V4-7a-3 design decisions. Depends on V4-7a-1 (golden dataset) and V4-7a-2 (creation agent eval) for framework patterns.

## Glossary

- **Eval_Runner**: The CLI entry point (`eval/verification_eval.py`) that orchestrates eval table setup, case loading, backend invocation, evaluator execution, report generation, and eval table cleanup
- **Verification_Agent**: The deployed v4 verification agent at ARN `arn:aws:bedrock-agentcore:us-west-2:894249332178:runtime/calleditv4_verification_Agent-77DiT7GHdH` that loads a prediction bundle from DynamoDB, gathers evidence, and returns a structured verdict
- **Verification_Backend**: The module (`eval/backends/verification_backend.py`) that invokes the deployed Verification_Agent via HTTPS with JWT bearer token auth and parses the synchronous JSON response
- **VerificationResult**: The Pydantic model from `calleditv4-verification/src/models.py` — `verdict` (str), `confidence` (float 0.0–1.0), `evidence` (list of EvidenceItem), `reasoning` (str)
- **EvidenceItem**: Sub-model of VerificationResult — `source` (str), `finding` (str), `relevant_to_criteria` (str)
- **Eval_Table**: The DynamoDB table `calledit-v4-eval` used exclusively for eval runs; same schema as `calledit-v4` with PK=`PRED#{prediction_id}`, SK=`BUNDLE`
- **Golden_Dataset**: The v4-reshaped dataset at `eval/golden_dataset.json` produced by V4-7a-1, containing base predictions with `verification_readiness` and `expected_verification_outcome` fields
- **Qualifying_Case**: A base prediction in the Golden_Dataset where both `verification_readiness` equals `"immediate"` and `expected_verification_outcome` is non-null; the 7 qualifying cases are base-001, base-002, base-009, base-010, base-011, base-013, base-040
- **Verification_Mode**: A field in the prediction bundle that tells the verification agent how to interpret the prediction's timing. This spec uses only `"immediate"` — verifiable right now with a single check and a definitive answer. Other modes (`at_date`, `before_date`, `recurring`) are out of scope for V4-7a-3 (see backlog item 0).
- **Eval_Case**: A single test case for the eval runner, containing `prediction_id`, `bundle` (the DDB item to write, always with `verification_mode: "immediate"`), `expected_verdict` (from `expected_verification_outcome`), and `metadata` (difficulty, smoke_test flag, id)
- **Source_Mode**: One of two execution modes — `golden` (uses Qualifying_Cases from Golden_Dataset, writes to Eval_Table, compares against ground truth, cleans up) or `ddb` (queries real `calledit-v4` table for `verification_readiness: immediate` predictions, no ground truth comparison)
- **Run_Tier**: One of three execution modes — `smoke` (smoke_test cases only, Tier 1 only), `smoke+judges` (smoke_test cases only, Tier 1 + Tier 2), `full` (all qualifying cases, Tier 1 + Tier 2); only applies in `golden` source mode
- **Eval_Report**: A JSON file saved to `eval/reports/verification-eval-{timestamp}.json` containing run metadata, per-case scores, and aggregate metrics
- **Run_Metadata**: Structured metadata attached to each eval run: `description`, `agent`, `source`, `run_tier`, `dataset_version`, `timestamp`, `duration_seconds`, `case_count`
- **Verdict_Accuracy_Evaluator**: Deterministic Tier 2 evaluator (golden mode only) — exact match of `verdict` against `expected_verification_outcome` ground truth
- **Evidence_Quality_Evaluator**: LLM judge Tier 2 evaluator — assesses whether sources are real, findings are specific, and criteria linkage is clear

## Requirements

### Requirement 1: Verification Agent table_name Override

**User Story:** As an eval framework developer, I want the verification agent to accept an optional `table_name` field in its payload, so that eval runs can target the `calledit-v4-eval` table without contaminating production data.

#### Acceptance Criteria

1. WHEN the Verification_Agent receives a payload containing a `table_name` field, THE Verification_Agent SHALL use the provided `table_name` value as the DynamoDB table name instead of the `DYNAMODB_TABLE_NAME` environment variable
2. WHEN the Verification_Agent receives a payload without a `table_name` field, THE Verification_Agent SHALL use the `DYNAMODB_TABLE_NAME` environment variable as the DynamoDB table name (existing behavior preserved)
3. THE Verification_Agent SHALL apply the `table_name` override before loading the prediction bundle from DynamoDB

### Requirement 2: Eval Table Management

**User Story:** As an eval framework developer, I want the eval runner to manage a dedicated `calledit-v4-eval` DynamoDB table, so that golden mode runs have isolated test data that does not affect production.

#### Acceptance Criteria

1. WHEN the Eval_Runner starts a golden mode run, THE Eval_Runner SHALL create the `calledit-v4-eval` table if it does not already exist, using the same schema as `calledit-v4` (PK=`PRED#{prediction_id}`, SK=`BUNDLE`)
2. WHEN the Eval_Runner starts a golden mode run, THE Eval_Runner SHALL write all Qualifying_Case bundles to the Eval_Table before invoking the Verification_Agent for any case
3. WHEN a golden mode run completes (successfully or with errors), THE Eval_Runner SHALL delete all items written to the Eval_Table during that run
4. THE Eval_Runner SHALL shape each Qualifying_Case bundle from the Golden_Dataset's `ground_truth` fields into the format the Verification_Agent expects when loading from DynamoDB, including `verification_mode: "immediate"` in every bundle written to the Eval_Table
5. IF the Eval_Table already exists when the Eval_Runner starts, THE Eval_Runner SHALL use the existing table without attempting to recreate it

### Requirement 3: Verification Backend Invokes Deployed Verification Agent

**User Story:** As an eval framework developer, I want the eval backend to invoke the deployed verification agent via HTTPS with JWT auth and extract the verdict, so that eval cases run against the real production agent.

#### Acceptance Criteria

1. WHEN the Verification_Backend receives a `prediction_id`, THE Verification_Backend SHALL send a JSON payload containing `prediction_id` and `table_name` set to `"calledit-v4-eval"` to the Verification_Agent via HTTPS with JWT bearer token auth
2. WHEN the Verification_Agent returns a synchronous JSON response, THE Verification_Backend SHALL parse the response body as JSON and extract the verdict summary
3. WHEN the Verification_Agent response contains a valid verdict summary, THE Verification_Backend SHALL return a dict with keys `verdict`, `confidence`, `status`, and `prediction_id`
4. IF the Verification_Agent invocation fails with a network or HTTP error, THEN THE Verification_Backend SHALL raise an error with the HTTP status code and the prediction_id
5. THE Verification_Backend SHALL reuse `get_cognito_token()` from `eval/backends/agentcore_backend.py` for JWT authentication
6. WHEN invoked in `ddb` source mode, THE Verification_Backend SHALL send a payload containing only `prediction_id` (no `table_name` override)

### Requirement 4: Golden Mode Case Loading

**User Story:** As an eval framework developer, I want the eval runner to load qualifying cases from the golden dataset for golden mode runs, so that each case has a known expected verdict for accuracy measurement.

#### Acceptance Criteria

1. WHEN the Eval_Runner loads cases in golden mode, THE Eval_Runner SHALL select only Qualifying_Cases where `verification_readiness` equals `"immediate"` and `expected_verification_outcome` is non-null
2. THE Eval_Runner SHALL set each Eval_Case's `prediction_id` to the base prediction's `id` field
3. THE Eval_Runner SHALL set each Eval_Case's `expected_verdict` to the base prediction's `expected_verification_outcome` field
4. THE Eval_Runner SHALL set each Eval_Case's `metadata` to include `difficulty`, `smoke_test`, and `id`
5. WHEN the Eval_Runner is invoked with `--tier smoke` or `--tier smoke+judges`, THE Eval_Runner SHALL further filter to only Qualifying_Cases where `smoke_test` is `true`
6. IF no Qualifying_Cases exist in the Golden_Dataset, THEN THE Eval_Runner SHALL exit with a non-zero status code and a descriptive error message

### Requirement 5: DDB Mode Case Loading

**User Story:** As an eval framework developer, I want the eval runner to query the real calledit-v4 table for ddb mode runs, so that I can measure verification quality on live predictions without ground truth comparison.

#### Acceptance Criteria

1. WHEN the Eval_Runner loads cases in ddb mode, THE Eval_Runner SHALL query the `calledit-v4` DynamoDB table for items where `verification_readiness` equals `"immediate"`
2. THE Eval_Runner SHALL set each Eval_Case's `prediction_id` from the DDB item's prediction id
3. THE Eval_Runner SHALL set each Eval_Case's `expected_verdict` to `null` in ddb mode (no ground truth available)
4. IF no items with `verification_readiness: immediate` exist in the `calledit-v4` table, THEN THE Eval_Runner SHALL exit with a non-zero status code and a descriptive error message

### Requirement 6: Schema Validity Evaluator (Tier 1)

**User Story:** As an eval framework developer, I want a deterministic evaluator that checks whether the verification agent's response contains all required VerificationResult fields with correct types, so that structural regressions are caught instantly.

#### Acceptance Criteria

1. WHEN the Schema_Validity evaluator receives a verdict response, THE Schema_Validity evaluator SHALL check that `verdict` is present and is a string
2. WHEN the Schema_Validity evaluator receives a verdict response, THE Schema_Validity evaluator SHALL check that `confidence` is present and is a float
3. WHEN the Schema_Validity evaluator receives a verdict response, THE Schema_Validity evaluator SHALL check that `evidence` is present and is a list
4. WHEN the Schema_Validity evaluator receives a verdict response, THE Schema_Validity evaluator SHALL check that `reasoning` is present and is a string
5. WHEN all four fields are present with correct types, THE Schema_Validity evaluator SHALL return a score of 1.0
6. WHEN any field is missing or has an incorrect type, THE Schema_Validity evaluator SHALL return a score of 0.0 and identify which fields failed in the evaluator output

### Requirement 7: Verdict Validity Evaluator (Tier 1)

**User Story:** As an eval framework developer, I want a deterministic evaluator that checks whether the verdict value is one of the three allowed values, so that invalid verdict strings are caught immediately.

#### Acceptance Criteria

1. WHEN the Verdict_Validity evaluator receives a verdict response where `verdict` is one of `"confirmed"`, `"refuted"`, or `"inconclusive"`, THE Verdict_Validity evaluator SHALL return a score of 1.0
2. WHEN the Verdict_Validity evaluator receives a verdict response where `verdict` is any other value, THE Verdict_Validity evaluator SHALL return a score of 0.0 and include the actual value in the evaluator output

### Requirement 8: Confidence Range Evaluator (Tier 1)

**User Story:** As an eval framework developer, I want a deterministic evaluator that checks whether the confidence value is within the valid range, so that out-of-bounds confidence scores are caught immediately.

#### Acceptance Criteria

1. WHEN the Confidence_Range evaluator receives a verdict response where `confidence` is a float between 0.0 and 1.0 inclusive, THE Confidence_Range evaluator SHALL return a score of 1.0
2. WHEN the Confidence_Range evaluator receives a verdict response where `confidence` is outside the range [0.0, 1.0] or is not a float, THE Confidence_Range evaluator SHALL return a score of 0.0 and include the actual value in the evaluator output

### Requirement 9: Evidence Completeness Evaluator (Tier 1)

**User Story:** As an eval framework developer, I want a deterministic evaluator that checks whether the evidence list is non-empty, so that verdicts with no supporting evidence are flagged immediately.

#### Acceptance Criteria

1. WHEN the Evidence_Completeness evaluator receives a verdict response where `evidence` is a non-empty list, THE Evidence_Completeness evaluator SHALL return a score of 1.0
2. WHEN the Evidence_Completeness evaluator receives a verdict response where `evidence` is an empty list, THE Evidence_Completeness evaluator SHALL return a score of 0.0

### Requirement 10: Evidence Structure Evaluator (Tier 1)

**User Story:** As an eval framework developer, I want a deterministic evaluator that checks whether each EvidenceItem has all required fields, so that malformed evidence items are caught immediately.

#### Acceptance Criteria

1. WHEN the Evidence_Structure evaluator receives a verdict response, THE Evidence_Structure evaluator SHALL check that each item in the `evidence` list contains `source`, `finding`, and `relevant_to_criteria` fields
2. WHEN all evidence items contain all three required fields, THE Evidence_Structure evaluator SHALL return a score of 1.0
3. WHEN any evidence item is missing any required field, THE Evidence_Structure evaluator SHALL return a score of 0.0 and identify which items and fields failed in the evaluator output
4. WHEN the `evidence` list is empty, THE Evidence_Structure evaluator SHALL return a score of 1.0 (vacuously true — no items to fail)

### Requirement 11: Verdict Accuracy Evaluator (Tier 2, Golden Mode Only)

**User Story:** As an eval framework developer, I want a deterministic evaluator that compares the agent's verdict against the expected ground truth outcome, so that I can measure accuracy on the golden dataset.

#### Acceptance Criteria

1. WHEN the Verdict_Accuracy evaluator receives a verdict response and a non-null `expected_verdict`, THE Verdict_Accuracy evaluator SHALL return a score of 1.0 if the `verdict` field exactly matches the `expected_verdict` string
2. WHEN the `verdict` field does not exactly match the `expected_verdict` string, THE Verdict_Accuracy evaluator SHALL return a score of 0.0 and include both the actual verdict and expected verdict in the evaluator output
3. WHEN the `expected_verdict` is null (ddb mode), THE Verdict_Accuracy evaluator SHALL be skipped and not included in the evaluator output
4. THE Eval_Runner SHALL note in the run metadata that all 7 qualifying cases have `confirmed` expected outcomes and that `refuted`/`inconclusive` accuracy cannot be measured deterministically with the current golden dataset

### Requirement 12: Evidence Quality Evaluator (Tier 2)

**User Story:** As an eval framework developer, I want an LLM judge evaluator that assesses whether the evidence items are high quality, so that verdicts backed by vague or fabricated evidence are identified.

#### Acceptance Criteria

1. WHEN the Evidence_Quality evaluator receives a verdict response, THE Evidence_Quality evaluator SHALL prompt an LLM judge to assess whether the `source` fields reference real, accessible sources (URLs or named data sources)
2. WHEN the Evidence_Quality evaluator receives a verdict response, THE Evidence_Quality evaluator SHALL prompt an LLM judge to assess whether the `finding` fields contain specific, concrete observations rather than vague summaries
3. WHEN the Evidence_Quality evaluator receives a verdict response, THE Evidence_Quality evaluator SHALL prompt an LLM judge to assess whether the `relevant_to_criteria` fields clearly link each piece of evidence to a specific verification criterion
4. THE Evidence_Quality evaluator SHALL use a rubric that focuses on: source authenticity and accessibility, finding specificity and concreteness, and criteria linkage clarity
5. THE Evidence_Quality evaluator SHALL return a score between 0.0 and 1.0 representing overall evidence quality
6. THE Evidence_Quality evaluator SHALL include the LLM judge's reasoning in the evaluator output

### Requirement 13: Run Tier Filtering (Golden Mode)

**User Story:** As an eval framework developer, I want the eval runner to support three run tiers in golden mode that control which cases and evaluators execute, so that I can trade off speed versus coverage.

#### Acceptance Criteria

1. WHEN the Eval_Runner is invoked with `--tier smoke`, THE Eval_Runner SHALL execute only Qualifying_Cases where `smoke_test` is `true` and run only Tier 1 evaluators
2. WHEN the Eval_Runner is invoked with `--tier smoke+judges`, THE Eval_Runner SHALL execute only Qualifying_Cases where `smoke_test` is `true` and run both Tier 1 evaluators and Tier 2 evaluators
3. WHEN the Eval_Runner is invoked with `--tier full`, THE Eval_Runner SHALL execute all Qualifying_Cases and run both Tier 1 evaluators and Tier 2 evaluators
4. WHEN the Eval_Runner is invoked without a `--tier` flag, THE Eval_Runner SHALL default to the `smoke` tier
5. WHEN the Eval_Runner is invoked with `--source ddb`, THE Eval_Runner SHALL ignore the `--tier` flag and run all available cases with Tier 1 + Tier 2 evaluators (except Verdict_Accuracy which requires ground truth)

### Requirement 14: CLI Interface

**User Story:** As an eval framework developer, I want a CLI with flags for source mode, dataset path, run tier, description, output directory, dry run, and single case execution, so that eval runs are configurable without editing code.

#### Acceptance Criteria

1. THE Eval_Runner SHALL accept a `--source` flag with values `golden` (default) or `ddb`
2. THE Eval_Runner SHALL accept a `--dataset` flag specifying the path to the Golden_Dataset file, defaulting to `eval/golden_dataset.json`
3. THE Eval_Runner SHALL accept a `--tier` flag specifying the Run_Tier, defaulting to `smoke`
4. THE Eval_Runner SHALL accept a `--description` flag specifying a one-line description for the run; WHEN omitted, THE Eval_Runner SHALL auto-generate a description from the source mode, run tier, and timestamp
5. THE Eval_Runner SHALL accept an `--output-dir` flag specifying the directory for report output, defaulting to `eval/reports/`
6. WHEN the Eval_Runner is invoked with `--dry-run`, THE Eval_Runner SHALL list all cases that would be executed with their ids and metadata without writing to the Eval_Table, invoking the Verification_Agent, or running evaluators
7. WHEN the Eval_Runner is invoked with `--case` followed by a case id, THE Eval_Runner SHALL execute only the Eval_Case matching that id regardless of the Run_Tier's case filtering (golden mode only)
8. IF the `--case` flag specifies an id that does not exist in the Qualifying_Cases, THEN THE Eval_Runner SHALL exit with a non-zero status code and a descriptive error message

### Requirement 15: Structured Run Metadata

**User Story:** As an eval framework developer, I want each eval run to carry structured metadata, so that reports are comparable across runs and the dashboard shows meaningful context.

#### Acceptance Criteria

1. THE Eval_Runner SHALL record a `description` field in the Run_Metadata, sourced from the `--description` CLI flag or auto-generated
2. THE Eval_Runner SHALL record an `agent` field in the Run_Metadata set to `"verification"`
3. THE Eval_Runner SHALL record a `source` field in the Run_Metadata set to `"golden"` or `"ddb"` matching the `--source` flag
4. THE Eval_Runner SHALL record a `run_tier` field in the Run_Metadata containing the Run_Tier value used for the run (or `"all"` for ddb mode)
5. THE Eval_Runner SHALL record a `dataset_version` field in the Run_Metadata sourced from the Golden_Dataset's `dataset_version` field (golden mode) or `"ddb-live"` (ddb mode)
6. THE Eval_Runner SHALL record a `timestamp` field in the Run_Metadata containing the ISO 8601 datetime when the run started
7. THE Eval_Runner SHALL record a `duration_seconds` field in the Run_Metadata containing the total wall-clock time of the run in seconds
8. THE Eval_Runner SHALL record a `case_count` field in the Run_Metadata containing the number of Eval_Cases executed in the run
9. THE Eval_Runner SHALL record a `ground_truth_limitation` field in the Run_Metadata noting that all 7 qualifying golden cases have `confirmed` expected outcomes

### Requirement 16: Eval Report Output

**User Story:** As an eval framework developer, I want each eval run to produce a JSON report with per-case scores, aggregate metrics, and run metadata, so that results are machine-readable and comparable across runs.

#### Acceptance Criteria

1. THE Eval_Runner SHALL save the Eval_Report as a JSON file at `{output_dir}/verification-eval-{timestamp}.json` where `{timestamp}` is formatted as `YYYYMMDD-HHMMSS`
2. THE Eval_Report SHALL contain a `run_metadata` object with all fields specified in Requirement 15
3. THE Eval_Report SHALL contain an `aggregate_scores` object with per-evaluator average scores and an overall pass rate computed as the fraction of Eval_Cases where all Tier 1 evaluators returned a score of 1.0
4. THE Eval_Report SHALL contain a `case_results` array with one entry per executed Eval_Case, each containing `prediction_id`, `expected_verdict` (or null in ddb mode), and a per-evaluator score breakdown
5. THE Eval_Report SHALL produce valid JSON output with consistent 2-space indentation
6. IF the output directory does not exist, THEN THE Eval_Runner SHALL create the directory before writing the report
