# Requirements Document — Spec B2: Verification Triggers & Storage

## Introduction

Wire the Verification Executor agent (built in Spec B1) into production with DynamoDB result storage and a scheduled scanner that verifies predictions when their verification date arrives.

In production, prediction creation is completely separated from verification. The prediction pipeline runs (possibly multiple HITL rounds), the user logs the prediction to DynamoDB, and that's it. Verification happens asynchronously via an EventBridge-triggered scanner that runs every 15 minutes, finds `auto_verifiable` predictions whose `verification_date` has passed, and verifies them using `run_verification()` from Spec B1.

For local evaluation, the eval runner (Spec B3) calls `run_verification()` directly after the prediction pipeline — no production trigger needed.

This spec depends on Spec B1 (`verification-execution-agent`) which provides the `run_verification()` entry point and the Verification_Executor agent.

This is the second of three specs split from the original Spec B:
- **Spec B1** (`verification-execution-agent`): Verification Executor agent — COMPLETE
- **Spec B2** (this spec): DynamoDB storage, scheduled scanner
- **Spec B3** (`verification-eval-integration`): Eval framework extension

This spec does NOT cover: the Verification Executor agent itself (Spec B1), eval framework integration (Spec B3), immediate verification triggers (dropped — Decision 81), AgentCore migration (Decision 68, 73), cold start optimization, or frontend display.

## Glossary

- **Verification_Outcome**: The output of the Verification_Executor — a dict with `status` (confirmed/refuted/inconclusive), `confidence` (0.0-1.0), `evidence` (list of evidence items gathered), `reasoning` (explanation of the verdict), `verified_at` (ISO 8601 UTC timestamp), and `tools_used` (list of tool name strings)
- **Prediction_Record**: An existing DynamoDB item in `calledit-db` with `PK=USER:{userId}` and `SK=PREDICTION#{timestamp}`, containing the prediction statement, verification method, and other pipeline outputs. Status is `PENDING` when first logged.
- **DynamoDB_Client**: A boto3 DynamoDB resource client used to read prediction records and write verification outcomes back to `calledit-db`
- **Verification_Date**: The `verification_date` field extracted by the parser in `YYYY-MM-DD HH:MM:SS` format, indicating the earliest point in time at which a prediction's truth value can be determined
- **Verification_Scanner**: A Lambda function on an EventBridge schedule (every 15 minutes) that queries DynamoDB for `auto_verifiable` predictions with `status=PENDING` and `verification_date <= now`, then invokes `run_verification` for each match
- **store_verification_result**: A utility function that writes a Verification_Outcome back to the Prediction_Record in DynamoDB

## Requirements

### Requirement 1: DynamoDB Result Storage

**User Story:** As a data consumer, I want verification outcomes stored alongside the original prediction in DynamoDB, so that results are queryable and available for future display and evaluation.

#### Acceptance Criteria

1. A `store_verification_result(user_id: str, sort_key: str, outcome: dict)` utility function SHALL be implemented that updates the existing Prediction_Record in `calledit-db`
2. THE function SHALL add a `verification_result` attribute containing the full Verification_Outcome dict
3. THE function SHALL update the Prediction_Record's `status` attribute to the Verification_Outcome's `status` value (e.g., `confirmed`, `refuted`, `inconclusive`)
4. THE function SHALL update the Prediction_Record's `updatedAt` attribute to the current ISO 8601 UTC timestamp
5. IF the DynamoDB update fails, THEN the function SHALL log the error at ERROR level and return False without raising an exception
6. THE DynamoDB update SHALL use an `UpdateExpression` to modify only the verification-related attributes, preserving all existing Prediction_Record fields
7. THE function SHALL be importable independently so both the Verification_Scanner and the eval runner (Spec B3) can use it

### Requirement 2: Scheduled Verification Scanner

**User Story:** As a pipeline operator, I want a periodic process that finds predictions whose verification date has arrived and triggers verification for them, so that future-dated predictions are verified at the right time without per-prediction scheduling.

#### Acceptance Criteria

1. THE Verification_Scanner SHALL be implemented as a Lambda function triggered by an EventBridge scheduled rule running at a fixed interval (every 15 minutes)
2. WHEN the Verification_Scanner runs, it SHALL scan `calledit-db` for Prediction_Records where `verifiable_category` equals `auto_verifiable` and `status` equals `PENDING`
3. FOR EACH matching Prediction_Record, THE Verification_Scanner SHALL check if `verification_date` is less than or equal to the current UTC time before invoking verification
4. FOR EACH eligible Prediction_Record, THE Verification_Scanner SHALL call `run_verification` with the Prediction_Record, then call `store_verification_result` with the outcome
5. IF a single verification execution exceeds a 60-second timeout, THEN THE Verification_Scanner SHALL store an `inconclusive` outcome with timeout reasoning and continue processing remaining predictions
6. THE Verification_Scanner SHALL process predictions sequentially within a single invocation to avoid concurrent MCP server connection issues
7. IF the Verification_Scanner encounters a DynamoDB scan/query error, THEN it SHALL log the error at ERROR level and exit without processing any predictions
8. THE Verification_Scanner Lambda SHALL reuse the same `run_verification` entry point from Spec B1 — no separate verification logic
9. THE Verification_Scanner SHALL be a Docker Lambda (same image as MakeCallStreamFunction) so it has access to MCP tools and Strands
10. THE Verification_Scanner SHALL log a summary at the end of each invocation: total predictions scanned, verified, and failed
