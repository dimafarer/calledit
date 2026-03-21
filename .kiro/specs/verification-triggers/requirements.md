# Requirements Document — Spec B2: Verification Triggers & Storage

## Introduction

Wire the Verification Executor agent (built in Spec B1) into the production pipeline with DynamoDB result storage, immediate verification for currently-decidable predictions, and a scheduled scanner for future-dated predictions.

This spec depends on Spec B1 (`verification-execution-agent`) which provides the `run_verification()` entry point and the Verification_Executor agent. This spec adds the infrastructure and integration code that makes verification actually happen in production.

This is the second of three specs split from the original Spec B:
- **Spec B1** (`verification-execution-agent`): Verification Executor agent — PREREQUISITE
- **Spec B2** (this spec): DynamoDB storage, immediate trigger, scheduled scanner
- **Spec B3** (`verification-eval-integration`): Eval framework extension

This spec does NOT cover: the Verification Executor agent itself (Spec B1), eval framework integration (Spec B3), AgentCore migration (Decision 68, 73), cold start optimization, or frontend display.

## Glossary

- **Verification_Outcome**: The output of the Verification_Executor — a dict with `status` (confirmed/refuted/inconclusive), `confidence` (0.0-1.0), `evidence` (list of evidence items gathered), and `reasoning` (explanation of the verdict)
- **Prediction_Record**: An existing DynamoDB item in `calledit-db` with `PK=USER:{userId}` and `SK=PREDICTION#{timestamp}`, containing the prediction statement, verification method, and other pipeline outputs
- **DynamoDB_Client**: A boto3 DynamoDB resource client used to read prediction records and write verification outcomes back to `calledit-db`
- **Verification_Date**: The `verification_date` field extracted by the parser in `YYYY-MM-DD HH:MM:SS` format, indicating the earliest point in time at which a prediction's truth value can be determined
- **Immediate_Verification**: Verification triggered inline after the prediction pipeline completes, used when the Verification_Date is in the past or within a short tolerance window (5 minutes) of the current time
- **Scheduled_Verification**: Verification triggered by a periodic scan process that finds predictions whose Verification_Date has arrived but whose status is still `pending`
- **Verification_Scanner**: A periodic process (Lambda on an EventBridge schedule) that queries DynamoDB for `auto_verifiable` predictions with `status=pending` and `verification_date <= now`, then invokes `run_verification` for each match

## Requirements

### Requirement 1: DynamoDB Result Storage

**User Story:** As a data consumer, I want verification outcomes stored alongside the original prediction in DynamoDB, so that results are queryable and available for future display and evaluation.

#### Acceptance Criteria

1. WHEN verification completes, THE DynamoDB_Client SHALL update the existing Prediction_Record in `calledit-db` by adding a `verification_result` attribute containing the full Verification_Outcome
2. WHEN verification completes, THE DynamoDB_Client SHALL update the Prediction_Record's `status` attribute from `pending` to the Verification_Outcome's `status` value
3. WHEN verification completes, THE DynamoDB_Client SHALL update the Prediction_Record's `updatedAt` attribute to the current ISO 8601 UTC timestamp
4. IF the DynamoDB update fails, THEN THE DynamoDB_Client SHALL log the error at ERROR level and return the Verification_Outcome to the caller without raising an exception
5. THE DynamoDB update SHALL use an `UpdateExpression` to modify only the verification-related attributes, preserving all existing Prediction_Record fields

### Requirement 2: Immediate Verification Trigger

**User Story:** As a pipeline developer, I want predictions whose verification date has already passed to be verified immediately after the user logs the prediction, so that currently-decidable facts are resolved without delay.

#### Acceptance Criteria

1. WHEN a prediction is logged to DynamoDB via the "Log Call" action with `verifiable_category` equal to `auto_verifiable`, THE handler SHALL compare the prediction's `verification_date` against the current UTC time
2. WHEN the `verification_date` is in the past or within 5 minutes of the current UTC time, THE handler SHALL trigger Immediate_Verification by calling `run_verification` with the logged prediction data
3. WHEN the `verification_date` is more than 5 minutes in the future, THE handler SHALL skip Immediate_Verification and leave the prediction in `pending` status for the Verification_Scanner to pick up later
4. WHEN Immediate_Verification completes, THE handler SHALL send a `verification_ready` WebSocket message to the client containing the Verification_Outcome
5. IF Immediate_Verification exceeds a 60-second timeout, THEN THE handler SHALL cancel the verification, return an `inconclusive` outcome with timeout reasoning, and send the partial result to the client
6. THE Immediate_Verification SHALL run after the prediction is logged and the `prediction_ready` message is sent, so the user sees the prediction immediately and verification results arrive asynchronously
7. THE trigger SHALL only fire after the user has completed the HITL review loop and explicitly logged the prediction — verification SHALL NOT be triggered by the prediction pipeline completing or the Verification Builder producing a plan

### Requirement 3: Scheduled Verification Scanner

**User Story:** As a pipeline operator, I want a periodic process that finds predictions whose verification date has arrived and triggers verification for them, so that future-dated predictions are verified at the right time without per-prediction scheduling.

#### Acceptance Criteria

1. THE Verification_Scanner SHALL be implemented as a Lambda function triggered by an EventBridge scheduled rule running at a fixed interval (every 15 minutes)
2. WHEN the Verification_Scanner runs, THE Verification_Scanner SHALL query `calledit-db` for Prediction_Records where `verifiable_category` equals `auto_verifiable`, `status` equals `pending`, and `verification_date` is less than or equal to the current UTC time
3. FOR EACH matching Prediction_Record, THE Verification_Scanner SHALL call `run_verification` with the Prediction_Record
4. IF a single verification execution exceeds a 60-second timeout, THEN THE Verification_Scanner SHALL cancel that execution, store an `inconclusive` outcome with timeout reasoning, and continue processing remaining predictions
5. THE Verification_Scanner SHALL process predictions sequentially within a single invocation to avoid concurrent MCP server connection issues
6. IF the Verification_Scanner encounters a DynamoDB query error, THEN THE Verification_Scanner SHALL log the error at ERROR level and exit without processing any predictions
7. THE Verification_Scanner Lambda SHALL reuse the same `run_verification` entry point and Verification_Executor agent as the Immediate_Verification path — no separate verification logic
