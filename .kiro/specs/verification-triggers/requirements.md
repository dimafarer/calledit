# Requirements Document — V4-5b: Verification Triggers

## Introduction

Build the scheduling layer that finds due predictions in DynamoDB and invokes the verification agent (V4-5a) for each one. This is the second half of the V4-5 split (Decision 104).

The verification agent (V4-5a) is complete and integration tested in `calleditv4-verification/`. It is a separate AgentCore runtime that receives `prediction_id`, loads the prediction bundle from DDB (`PK=PRED#{prediction_id}`, `SK=BUNDLE`), runs a Strands Agent with Browser + Code Interpreter + current_time, produces a structured verdict, and updates DDB. Status transitions: `pending` → `verified` (confirmed/refuted) or `inconclusive`.

V4-5b delivers three things:
1. A DynamoDB Global Secondary Index (GSI) on `status` + `verification_date` for efficient queries (backlog item 14)
2. A lightweight scanner Lambda triggered by EventBridge every 15 minutes that queries the GSI and invokes the verification agent for each due prediction
3. SAM/CloudFormation infrastructure-as-code for the GSI and scanner Lambda

The scanner Lambda is a standard Python Lambda (zip package, python3.12) — NOT an AgentCore runtime, NOT a Docker Lambda. It is a scheduler that makes API calls. It does not run verification logic itself.

## Glossary

- **Scanner_Lambda**: A standard Python 3.12 Lambda function triggered by EventBridge every 15 minutes. Queries the DDB GSI for due predictions and invokes the Verification_Agent for each one. Dependencies: boto3 only.
- **Verification_Agent**: The AgentCore runtime deployed from `calleditv4-verification/`. Receives `{"prediction_id": "pred-xxx"}` and returns JSON with `prediction_id`, `verdict`, `confidence`, `status`. Invoked via `AgentCoreRuntimeClient` (deployed) or HTTP POST to `localhost:8080` (dev).
- **Status_Verification_Date_GSI**: A Global Secondary Index on the `calledit-db` DynamoDB table with `status` (String) as partition key and `verification_date` (String, ISO 8601) as sort key. Enables efficient queries for pending predictions due before now. Sparse index — only items with both attributes are indexed.
- **Prediction_Bundle**: An existing DynamoDB item with `PK=PRED#{prediction_id}` and `SK=BUNDLE`, containing `parsed_claim`, `verification_plan`, `verifiability_score`, `status`, `verification_date`, and other fields written by the creation agent.
- **AgentCoreRuntimeClient**: The boto3/SDK client used to invoke a deployed AgentCore runtime. The scanner uses this to invoke the verification agent in production.
- **Invocation_Summary**: A structured log entry produced at the end of each scanner run, containing counts of predictions found, invoked, succeeded, and failed.

## Requirements

### Requirement 1: DynamoDB Global Secondary Index

**User Story:** As a pipeline operator, I want an efficient way to query predictions by status and verification date, so that the scanner can find due predictions without scanning the entire table.

#### Acceptance Criteria

1. THE Status_Verification_Date_GSI SHALL be added to the `calledit-db` DynamoDB table with `status` (String) as partition key and `verification_date` (String) as sort key
2. THE Status_Verification_Date_GSI SHALL project `prediction_id` in addition to the table keys (`PK`, `SK`) to support logging without a separate GetItem call
3. THE Status_Verification_Date_GSI SHALL be a sparse index, indexing only items that have both `status` and `verification_date` attributes
4. THE Status_Verification_Date_GSI SHALL be defined in the SAM/CloudFormation template alongside the scanner Lambda
5. WHEN the GSI is queried with `status = "pending"` AND `verification_date <= <current_ISO_8601_timestamp>`, THE Status_Verification_Date_GSI SHALL return only prediction bundles that are pending and due for verification

### Requirement 2: Scanner Lambda — GSI Query

**User Story:** As a pipeline operator, I want a scheduled process that finds predictions whose verification date has arrived, so that predictions are verified at the right time without manual intervention.

#### Acceptance Criteria

1. THE Scanner_Lambda SHALL be triggered by an EventBridge scheduled rule running every 15 minutes
2. WHEN the Scanner_Lambda runs, THE Scanner_Lambda SHALL query the Status_Verification_Date_GSI for items where `status` equals `pending` AND `verification_date` is less than or equal to the current UTC time in ISO 8601 format
3. THE Scanner_Lambda SHALL handle paginated GSI query results by following `LastEvaluatedKey` until all matching items are retrieved
4. IF the GSI query fails, THEN THE Scanner_Lambda SHALL log the error at ERROR level and exit without processing any predictions
5. THE Scanner_Lambda SHALL extract `prediction_id` from each GSI result item (from the projected attribute or by parsing the `PK` field)

### Requirement 3: Scanner Lambda — Verification Agent Invocation

**User Story:** As a pipeline operator, I want the scanner to invoke the verification agent for each due prediction, so that predictions are verified automatically.

#### Acceptance Criteria

1. FOR EACH due prediction returned by the GSI query, THE Scanner_Lambda SHALL invoke the Verification_Agent with payload `{"prediction_id": "<prediction_id>"}`
2. THE Scanner_Lambda SHALL process predictions sequentially, one at a time, to avoid overwhelming the Verification_Agent
3. THE Scanner_Lambda SHALL use `AgentCoreRuntimeClient` to invoke the deployed Verification_Agent in production
4. WHERE a development environment is configured, THE Scanner_Lambda SHALL use HTTP POST to `localhost:8080` to invoke the local `agentcore dev` server
5. WHEN the Verification_Agent returns a response, THE Scanner_Lambda SHALL parse the JSON response and record the `status` field (verified, inconclusive, or error)
6. IF a single Verification_Agent invocation fails or returns an error, THEN THE Scanner_Lambda SHALL log the error and continue processing the remaining predictions
7. IF the Verification_Agent is unavailable (connection refused, timeout, service error), THEN THE Scanner_Lambda SHALL log the error, skip the prediction, and continue to the next one

### Requirement 4: Scanner Lambda — Summary Logging

**User Story:** As a pipeline operator, I want a summary of each scanner run, so that I can monitor verification throughput and identify failures.

#### Acceptance Criteria

1. WHEN the Scanner_Lambda completes processing, THE Scanner_Lambda SHALL log an Invocation_Summary containing: total predictions found, total invoked, total succeeded, and total failed
2. THE Scanner_Lambda SHALL return a response dict with `statusCode` and the Invocation_Summary for CloudWatch visibility
3. IF zero predictions are found, THE Scanner_Lambda SHALL log a summary indicating zero predictions due and exit normally

### Requirement 5: Scanner Lambda — Infrastructure

**User Story:** As a developer, I want the scanner Lambda and GSI defined in infrastructure-as-code, so that the system is reproducible and deployable.

#### Acceptance Criteria

1. THE Scanner_Lambda SHALL be defined in a SAM/CloudFormation template as a standard Python 3.12 Lambda function with zip packaging (NOT Docker, NOT AgentCore)
2. THE Scanner_Lambda SHALL have a timeout of 900 seconds to accommodate sequential verification invocations that can each take 30-400+ seconds
3. THE Scanner_Lambda SHALL have IAM permissions to query the `calledit-db` DynamoDB table and its GSI
4. THE Scanner_Lambda SHALL have IAM permissions to invoke the Verification_Agent via AgentCore Runtime API
5. THE Scanner_Lambda SHALL be triggered by an EventBridge schedule rule with `rate(15 minutes)`
6. THE SAM/CloudFormation template SHALL define the Status_Verification_Date_GSI on the `calledit-db` table
