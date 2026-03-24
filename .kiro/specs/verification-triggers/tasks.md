# Implementation Plan — V4-5b: Verification Triggers

## Overview

Implement the scheduling layer that finds due predictions in DynamoDB and invokes the V4-5a verification agent. Tasks are ordered: prerequisite DDB changes → GSI setup script → scanner Lambda code → invocation clients → SAM template → tests → checkpoints. All code is Python 3.12 with boto3 only (no Strands, no AgentCore SDK in the scanner Lambda itself).

## Tasks

- [ ] 1. Promote `verification_date` to top-level DDB attribute
  - [ ] 1.1 Update `build_bundle()` in `calleditv4/src/bundle.py`
    - Extract `parsed_claim["verification_date"]` and write it as a top-level `verification_date` field in the returned bundle dict
    - Must be set before `format_ddb_item()` is called so it becomes a top-level DDB attribute the GSI can index
    - _Requirements: 1.1, 1.3_
  - [ ] 1.2 Update `format_ddb_update()` in `calleditv4/src/bundle.py`
    - Add `verification_date` to the SET expression so clarification rounds also update the top-level field from `parsed_claim["verification_date"]`
    - _Requirements: 1.1, 1.3_
  - [ ]* 1.3 Update property tests in `calleditv4/tests/test_bundle.py`
    - Add assertions to `TestBundleAssemblyInvariants` verifying `verification_date` is present as a top-level field
    - Add assertions to `TestDdbItemFormat` verifying the top-level `verification_date` survives `format_ddb_item()`
    - _Requirements: 1.1_

- [ ] 2. Create GSI setup script
  - [ ] 2.1 Create `infrastructure/verification-scanner/setup_gsi.sh`
    - Write the `aws dynamodb update-table` command to add `status-verification_date-index` GSI to `calledit-db`
    - GSI partition key: `status` (String), sort key: `verification_date` (String)
    - Projection: INCLUDE with `prediction_id` as non-key attribute
    - Make the script executable and include a wait command for GSI to become ACTIVE
    - _Requirements: 1.1, 1.2, 1.3_

- [ ] 3. Implement scanner Lambda core
  - [ ] 3.1 Create `infrastructure/verification-scanner/scanner.py` with `extract_prediction_id()`
    - Implement `extract_prediction_id(item: dict) -> str | None` that extracts prediction_id from the `prediction_id` projected attribute or parses `PK` (`PRED#pred-xxx` → `pred-xxx`)
    - Returns `None` if PK doesn't start with `PRED#` and no `prediction_id` attribute exists
    - _Requirements: 2.5_
  - [ ] 3.2 Implement `query_due_predictions()` in `scanner.py`
    - Query the GSI with `status = "pending"` and `verification_date <= now_iso` as KeyConditionExpression
    - Handle pagination by following `LastEvaluatedKey` until all results are collected
    - Return list of all matching items
    - _Requirements: 1.5, 2.2, 2.3_
  - [ ] 3.3 Implement `lambda_handler()` in `scanner.py`
    - Entry point: `lambda_handler(event, context) -> dict`
    - Validate env vars (`VERIFICATION_AGENT_ID` or `VERIFICATION_AGENT_ENDPOINT` must be set)
    - Call `query_due_predictions()`, iterate results sequentially
    - For each prediction: extract ID, invoke verification agent, parse response, track success/failure
    - Log error and continue on individual prediction failures (fail-forward)
    - Log and return invocation summary with `total_found`, `total_invoked`, `total_succeeded`, `total_failed`, `failures` list
    - If GSI query fails, log ERROR and exit immediately
    - If zero predictions found, log INFO and return summary with all zeros
    - _Requirements: 2.1, 2.2, 2.4, 3.1, 3.2, 3.5, 3.6, 3.7, 4.1, 4.2, 4.3_

- [ ] 4. Implement invocation client abstraction
  - [ ] 4.1 Implement `AgentCoreInvoker` and `HttpInvoker` classes in `scanner.py`
    - `AgentCoreInvoker`: uses `AgentCoreRuntimeClient` (boto3) to invoke the deployed verification agent with `{"prediction_id": "<id>"}` payload
    - `HttpInvoker`: uses `urllib.request` to HTTP POST to the dev endpoint (e.g., `http://localhost:8080`) with the same payload
    - Both expose an `invoke(prediction_id: str) -> dict` method returning parsed JSON response
    - _Requirements: 3.1, 3.3, 3.4_
  - [ ] 4.2 Implement `build_invocation_client()` factory in `scanner.py`
    - If `VERIFICATION_AGENT_ENDPOINT` env var is set → return `HttpInvoker`
    - Else if `VERIFICATION_AGENT_ID` env var is set → return `AgentCoreInvoker`
    - Else → raise configuration error
    - _Requirements: 3.3, 3.4_

- [ ] 5. Checkpoint — Verify core scanner logic
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Create SAM template and requirements
  - [ ] 6.1 Create `infrastructure/verification-scanner/template.yaml`
    - Define `VerificationScannerFunction` as `AWS::Serverless::Function` with Python 3.12, zip packaging, 900s timeout, 256MB memory
    - Define `ScannerScheduleRule` as EventBridge rule with `rate(15 minutes)`
    - Define IAM policies: DynamoDB Query on `calledit-db` table and `status-verification_date-index` GSI, plus AgentCore Runtime invoke
    - Set environment variables: `DYNAMODB_TABLE_NAME`, `GSI_NAME`, `VERIFICATION_AGENT_ID`, `VERIFICATION_AGENT_ENDPOINT`
    - Include commented instructions for GSI creation (reference `setup_gsi.sh`)
    - _Requirements: 1.4, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
  - [ ] 6.2 Create `infrastructure/verification-scanner/requirements.txt`
    - Add `boto3` as the only runtime dependency
    - _Requirements: 5.1_

- [ ] 7. Write property-based and unit tests
  - [ ]* 7.1 Write property test for prediction ID extraction
    - **Property 1: Prediction ID Extraction**
    - Test in `infrastructure/verification-scanner/tests/test_scanner_properties.py`
    - For any PK in format `PRED#<id>`, `extract_prediction_id` returns `<id>`. For PK not starting with `PRED#` and no `prediction_id` attr, returns `None`.
    - **Validates: Requirements 2.5**
  - [ ]* 7.2 Write property test for GSI query construction
    - **Property 2: GSI Query Filters Correctly**
    - Test in `infrastructure/verification-scanner/tests/test_scanner_properties.py`
    - For any ISO 8601 timestamp, the query uses `status = "pending"` as partition key and `verification_date <= now` as sort key condition.
    - **Validates: Requirements 1.5, 2.2**
  - [ ]* 7.3 Write property test for pagination
    - **Property 3: Pagination Collects All Results**
    - Test in `infrastructure/verification-scanner/tests/test_scanner_properties.py`
    - For any sequence of paginated responses, `query_due_predictions` returns concatenation of all items with no items lost or duplicated.
    - **Validates: Requirements 2.3**
  - [ ]* 7.4 Write property test for invocation payload format
    - **Property 4: Invocation Payload Format**
    - Test in `infrastructure/verification-scanner/tests/test_scanner_properties.py`
    - For any prediction ID string, the payload is exactly `{"prediction_id": "<id>"}` with no extra fields.
    - **Validates: Requirements 3.1**
  - [ ]* 7.5 Write property test for response parsing
    - **Property 5: Response Parsing Extracts Status**
    - Test in `infrastructure/verification-scanner/tests/test_scanner_properties.py`
    - For any valid JSON with a `status` field, the scanner parses it correctly. For invalid JSON, treats as error.
    - **Validates: Requirements 3.5**
  - [ ]* 7.6 Write property test for error resilience
    - **Property 6: Error Resilience**
    - Test in `infrastructure/verification-scanner/tests/test_scanner_properties.py`
    - For N predictions with K failures, scanner attempts all N and summary reports (N-K) succeeded and K failed.
    - **Validates: Requirements 3.6**
  - [ ]* 7.7 Write property test for summary count consistency
    - **Property 7: Summary Count Consistency**
    - Test in `infrastructure/verification-scanner/tests/test_scanner_properties.py`
    - For any run: `total_succeeded + total_failed == total_invoked` and `total_invoked <= total_found`.
    - **Validates: Requirements 4.1, 4.2**
  - [ ]* 7.8 Write unit tests in `infrastructure/verification-scanner/tests/test_scanner_unit.py`
    - `extract_prediction_id` with `PK="PRED#pred-abc123"` returns `"pred-abc123"`
    - `extract_prediction_id` with missing PK returns `None`
    - Client selection: `VERIFICATION_AGENT_ENDPOINT` set → `HttpInvoker`
    - Client selection: only `VERIFICATION_AGENT_ID` set → `AgentCoreInvoker`
    - Client selection: neither set → raises configuration error
    - Empty GSI response → summary with all zeros
    - Verification agent returns `{"status": "error"}` → counted as failure
    - _Requirements: 2.5, 3.3, 3.4, 3.5, 4.3_

- [ ] 8. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Run: `/home/wsluser/projects/calledit/venv/bin/python -m pytest infrastructure/verification-scanner/tests/ -v`
  - Run: `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/test_bundle.py -v`

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Decision 96: No mocks. Property tests exercise pure logic. Integration tests hit real DDB.
- The scanner Lambda uses boto3 only — no Strands, no AgentCore SDK
- Each property test maps to a correctness property from the design document
- Checkpoints ensure incremental validation
