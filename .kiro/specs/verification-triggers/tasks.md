# Implementation Plan: Verification Triggers & Storage (Spec B2)

## Overview

Create the DynamoDB storage utility (`verification_store.py`), the EventBridge-triggered scanner Lambda (`verification_scanner.py`), update the SAM template with the new `VerificationScannerFunction` resource, and write tests. All code is Python, tests use Hypothesis for property-based testing and pytest for unit tests. Per Decision 78, tests hit real DynamoDB and real Bedrock — no mocks. Test records use `USER:TEST-{uuid}` PK prefixes and clean up after themselves.

## Tasks

- [x] 1. Create `verification_store.py` — DynamoDB storage utility
  - [x] 1.1 Create `backend/calledit-backend/handlers/strands_make_call/verification_store.py`
    - Implement `store_verification_result(user_id: str, sort_key: str, outcome: dict) -> bool`
    - Construct `PK=USER:{user_id}` from the `user_id` argument
    - Use `UpdateExpression` with `SET verification_result = :vr, #s = :status, updatedAt = :ts`
    - Use `ExpressionAttributeNames` to alias `#s` → `status` (DynamoDB reserved word)
    - Set `:status` from `outcome.get('status', 'inconclusive')`
    - Set `:ts` to `datetime.now(timezone.utc).isoformat()`
    - Wrap entire body in `try/except Exception` — log at ERROR level, return `False` on failure
    - Never raise — always return `True` or `False`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

- [x] 2. Create `verification_scanner.py` — Scanner Lambda handler
  - [x] 2.1 Create `backend/calledit-backend/handlers/strands_make_call/verification_scanner.py` with scan logic
    - Implement `lambda_handler(event, context)` as the EventBridge entry point
    - Scan `calledit-db` with `FilterExpression`: `status=PENDING` AND `verifiable_category=auto_verifiable`
    - Handle pagination via `LastEvaluatedKey` loop
    - Filter results in code: `verification_date <= now` (string comparison, `YYYY-MM-DD HH:MM:SS` format)
    - Extract `user_id` by stripping `USER:` prefix from `PK`
    - If DynamoDB scan raises, log at ERROR level and return immediately (no partial processing)
    - _Requirements: 2.1, 2.2, 2.3, 2.7_

  - [x] 2.2 Implement per-prediction verification loop with timeout
    - Process eligible predictions sequentially (no concurrency — MCP singleton constraint)
    - Call `run_verification(prediction_record)` from Spec B1 for each eligible prediction
    - Use `threading.Thread` + `thread.join(timeout=60)` for 60-second per-prediction timeout
    - On timeout: build `inconclusive` outcome with `"reasoning": "Verification timed out after 60 seconds"`
    - Call `store_verification_result(user_id, sort_key, outcome)` with the result
    - If `run_verification()` raises, catch exception, log, and continue to next prediction
    - If `store_verification_result()` returns `False`, increment failed counter and continue
    - Track counts: total_scanned, eligible, verified, failed, outcomes by status
    - Log summary dict at end of invocation
    - Return `dict` with `statusCode` and summary
    - _Requirements: 2.3, 2.4, 2.5, 2.6, 2.8, 2.10_

- [x] 3. Checkpoint — Storage and scanner modules verified
  - Ensure both modules import cleanly, ask the user if questions arise.

- [x] 4. Update SAM template with VerificationScannerFunction
  - [x] 4.1 Add `VerificationScannerFunction` resource to `backend/calledit-backend/template.yaml`
    - `PackageType: Image` (Docker Lambda, same image as MakeCallStreamFunction)
    - `ImageConfig.Command: [verification_scanner.lambda_handler]` (CMD override)
    - `Timeout: 900`, `MemorySize: 512`
    - Same env vars: `PROMPT_VERSION_PARSER`, `PROMPT_VERSION_CATEGORIZER`, `PROMPT_VERSION_VB`, `PROMPT_VERSION_REVIEW`, `BRAVE_API_KEY`
    - Policies: `DynamoDBCrudPolicy` on `calledit-db`, Bedrock invoke/stream/list, Bedrock Prompt Management (`bedrock-agent:GetPrompt`)
    - NO WebSocket `execute-api:ManageConnections` permission (scanner doesn't send WS messages)
    - NO `calledit-eval-reasoning` DynamoDB policy (scanner doesn't write eval data)
    - Add `Events.ScheduledScan` with `Type: Schedule`, `Schedule: rate(15 minutes)`, `Enabled: true`
    - Use same `Metadata` block (DockerTag, DockerContext, Dockerfile) as MakeCallStreamFunction
    - _Requirements: 2.1, 2.9_

- [x] 5. Checkpoint — SAM template validates
  - Ensure SAM template is syntactically valid, ask the user if questions arise.

- [x] 6. Write tests for verification triggers
  - [x] 6.1 Create `backend/calledit-backend/tests/test_verification_triggers.py` with unit tests
    - Test `store_verification_result()` with a real DynamoDB item — seed a test item, call store, read back, verify `verification_result`, `status`, and `updatedAt` are set correctly and all original fields preserved
    - Test `store_verification_result()` with invalid key — verify returns `False` without raising
    - Test `store_verification_result()` with malformed outcome (None, empty dict, string) — verify returns `False` without raising
    - Test scanner with real DynamoDB items — seed items with various `status`/`verifiable_category`/`verification_date` combinations, run scanner, verify only eligible items were processed
    - Test scanner with empty table (no matching items) — verify completes with zero processed
    - Test scanner summary logging — verify log contains expected counts
    - All tests use `USER:TEST-{uuid}` PK prefix and clean up after themselves
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.2, 2.3, 2.4, 2.7, 2.10_

  - [ ]* 6.2 Write property test: store_verification_result never raises (Property 1)
    - **Property 1: store_verification_result never raises**
    - Generate random `user_id` strings, `sort_key` strings, and adversarial `outcome` dicts (including None, empty, non-dict values)
    - Verify function never raises and always returns a boolean (`True` or `False`)
    - Uses real DynamoDB — test PK prefix `USER:TEST-{uuid}`, cleanup after
    - Test file: `backend/calledit-backend/tests/test_verification_triggers.py`
    - **Validates: Requirements 1.1, 1.5**

  - [ ]* 6.3 Write property test: Store round-trip preserves existing fields (Property 2)
    - **Property 2: Round-trip preserves existing fields and writes verification fields**
    - Seed a real DynamoDB item with random extra fields, call `store_verification_result` with a random valid outcome, read item back
    - Verify: (a) `verification_result` equals the outcome dict, (b) `status` equals `outcome['status']`, (c) `updatedAt` is valid ISO 8601, (d) all pre-existing fields unchanged
    - Uses real DynamoDB — test PK prefix `USER:TEST-{uuid}`, cleanup after
    - Test file: `backend/calledit-backend/tests/test_verification_triggers.py`
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.6**

  - [ ]* 6.4 Write property test: Scanner processes exactly eligible predictions (Property 3)
    - **Property 3: Scanner processes exactly the eligible predictions**
    - Extract the scanner's eligibility filtering logic as a pure function
    - Generate random prediction records with varying `status`, `verifiable_category`, and `verification_date`
    - Verify the filter selects exactly records where `status=PENDING` AND `verifiable_category=auto_verifiable` AND `verification_date <= now`
    - Pure function test — no DynamoDB needed for this property
    - Test file: `backend/calledit-backend/tests/test_verification_triggers.py`
    - **Validates: Requirements 2.2, 2.3, 2.4**

- [x] 7. Final checkpoint — All tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate the 3 correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All tests go in `backend/calledit-backend/tests/test_verification_triggers.py`
- All Python commands must use `/home/wsluser/projects/calledit/venv/bin/python`
- Per Decision 78: NO MOCKS — tests hit real DynamoDB and real Bedrock
- Test records use `USER:TEST-{uuid}` PK prefixes and clean up after themselves
- Scanner shares same Docker image as MakeCallStreamFunction (CMD override in SAM)
