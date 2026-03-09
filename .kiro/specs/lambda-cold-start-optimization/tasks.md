# Implementation Plan: Lambda Cold Start Optimization

## Overview

Enable AWS Lambda SnapStart for Python across CalledIt Lambda functions in two phases. Phase 1 targets MakeCallStreamFunction (low risk, already has AutoPublishAlias). Phase 2 targets secondary functions (higher risk, some need AutoPublishAlias added). ConnectFunction and DisconnectFunction are excluded. Implementation includes runtime hooks for snapshot restore, graph validation logic, and property-based tests for correctness properties.

## Tasks

- [x] 1. Measure baseline cold start times
  - Ask the user to invoke MakeCallStreamFunction after a period of inactivity and run the CloudWatch Insights query to capture `Init Duration` from REPORT log lines
  - Record baseline INIT duration values for MakeCallStreamFunction before any changes
  - Query: `filter @type = "REPORT" | stats avg(@initDuration) as avgInit, max(@initDuration) as maxInit, count(*) as coldStarts | filter ispresent(@initDuration)`
  - _Requirements: 5.1_

- [x] 2. Create runtime hooks module and graph validation for MakeCallStreamFunction
  - [x] 2.1 Create `snapstart_hooks.py` in `backend/calledit-backend/handlers/strands_make_call/`
    - Import `register_before_snapshot` and `register_after_restore` from `snapshot_restore_py`
    - Implement `before_snapshot()` hook with `@register_before_snapshot` decorator that logs at INFO level
    - Implement `after_restore()` hook with `@register_after_restore` decorator that logs at INFO level
    - Wrap hook internals in try/except so exceptions never propagate to the Lambda runtime
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.6_

  - [x] 2.2 Add `validate_graph_after_restore()` function to `snapstart_hooks.py`
    - Check that the 4 expected agent nodes (parser, categorizer, verification_builder, review) exist in the `prediction_graph` singleton
    - If nodes are missing or graph is corrupted, call `create_prediction_graph()` to rebuild and log a WARNING
    - If rebuild fails, log ERROR and return False
    - Call `validate_graph_after_restore()` from within the `after_restore()` hook
    - _Requirements: 4.1, 4.3, 4.4_

  - [x] 2.3 Import `snapstart_hooks` in `strands_make_call_graph.py`
    - Add `import snapstart_hooks` to the handler module so hooks register at module load time
    - This import must be at module level (not inside handler) so hooks register during INIT/snapshot
    - _Requirements: 2.1, 2.2_

  - [ ]* 2.4 Write property test: Restore hook resilience (Property 1)
    - **Property 1: Restore hook resilience**
    - Generate random exception types and messages using Hypothesis
    - Inject exceptions into the restore hook's internal logic (mock graph validation to raise)
    - Verify the `after_restore()` hook never propagates exceptions to the caller
    - Test file: `tests/lambda_cold_start/test_property_restore_hook.py`
    - **Validates: Requirements 2.1, 2.6**

  - [ ]* 2.5 Write property test: Graph validation correctness (Property 3)
    - **Property 3: Graph validation correctness**
    - Generate mock graph objects with random subsets of the 4 expected node names (parser, categorizer, verification_builder, review)
    - Verify `validate_graph_after_restore()` returns True for valid graphs (all 4 nodes present)
    - Verify it attempts re-creation for invalid graphs and returns True if re-creation succeeds
    - Verify it returns False only when re-creation itself fails
    - Test file: `tests/lambda_cold_start/test_property_graph_validation.py`
    - **Validates: Requirements 4.3, 4.4**

  - [ ]* 2.6 Write unit tests for hooks and graph validation
    - Test `before_snapshot()` produces INFO log message
    - Test `after_restore()` produces INFO log message
    - Test `validate_graph_after_restore()` returns True when all 4 nodes present
    - Test `validate_graph_after_restore()` re-creates graph when nodes missing
    - Test `after_restore()` does not raise even when internal logic fails
    - Test file: `tests/lambda_cold_start/test_hooks_unit.py`
    - _Requirements: 2.4, 2.5, 2.6, 4.3, 4.4_

- [x] 3. Phase 1 — Enable SnapStart on MakeCallStreamFunction (SAM template)
  - [x] 3.1 Add SnapStart property to MakeCallStreamFunction in `backend/calledit-backend/template.yaml`
    - Add `SnapStart: { ApplyOn: PublishedVersions }` to the MakeCallStreamFunction resource
    - Verify existing `AutoPublishAlias: live` is preserved (already present)
    - Verify Runtime is `python3.12` (already present)
    - Do NOT modify any other properties (MemorySize, Timeout, Policies, Environment, Handler)
    - _Requirements: 1.1, 1.2, 1.3, 7.1, 7.3_

  - [ ]* 3.2 Write property test: Existing properties preserved (Property 4)
    - **Property 4: Existing properties preserved after SnapStart addition**
    - Generate random sets of Lambda function properties using Hypothesis
    - Apply the "add SnapStart" transformation
    - Verify all original properties remain present and unchanged after adding SnapStart
    - Test file: `tests/lambda_cold_start/test_property_preserved.py`
    - **Validates: Requirements 7.3**

  - [ ]* 3.3 Write unit test for SAM template structure
    - Parse `template.yaml` and verify MakeCallStreamFunction has `SnapStart: { ApplyOn: PublishedVersions }`
    - Verify MakeCallStreamFunction has `AutoPublishAlias: live`
    - Verify MakeCallStreamFunction has `Runtime: python3.12`
    - Test file: `tests/lambda_cold_start/test_sam_template.py`
    - _Requirements: 1.1, 1.2, 1.3_

- [x] 4. Checkpoint — Phase 1 validation
  - Ensure all tests pass, ask the user if questions arise.
  - Ask the user to deploy Phase 1 (`sam build && sam deploy`) and invoke MakeCallStreamFunction after a cold start
  - Ask the user to run the CloudWatch Insights query for Restore Duration: `filter @type = "REPORT" | stats avg(@restoreDuration) as avgRestore, max(@restoreDuration) as maxRestore, count(*) as snapRestores | filter ispresent(@restoreDuration)`
  - Compare Restore Duration to baseline Init Duration from task 1
  - _Requirements: 5.2, 5.3, 5.4_

- [x] 5. Phase 2 — Enable SnapStart on secondary functions
  - [x] 5.1 Create `snapstart_hooks.py` in `backend/calledit-backend/handlers/notification_management/`
    - Implement `after_restore()` hook that refreshes the module-level `sns_client` in `app.py`
    - Import `app` module inside the hook to access and replace `app.sns_client` with a fresh `boto3.client('sns')`
    - Log at INFO level after refresh
    - Wrap in try/except so exceptions never propagate
    - _Requirements: 2.1, 2.3, 2.6, 3.5_

  - [x] 5.2 Import `snapstart_hooks` in `backend/calledit-backend/handlers/notification_management/app.py`
    - Add `import snapstart_hooks` at module level so hooks register during INIT
    - _Requirements: 3.5_

  - [x] 5.3 Add SnapStart and AutoPublishAlias to secondary functions in `template.yaml`
    - Add `SnapStart: { ApplyOn: PublishedVersions }` to LogCall (already has AutoPublishAlias)
    - Add `SnapStart: { ApplyOn: PublishedVersions }` to ListPredictions (already has AutoPublishAlias)
    - Add `AutoPublishAlias: live` AND `SnapStart: { ApplyOn: PublishedVersions }` to VerificationFunction (does NOT have AutoPublishAlias)
    - Add `AutoPublishAlias: live` AND `SnapStart: { ApplyOn: PublishedVersions }` to NotificationManagementFunction (does NOT have AutoPublishAlias)
    - Do NOT modify ConnectFunction or DisconnectFunction (excluded — trivial imports, WebSocket routing risk)
    - Do NOT modify any other existing properties on these functions
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 7.1, 7.3_

  - [ ]* 5.4 Write property test: SnapStart requires AutoPublishAlias (Property 2)
    - **Property 2: SnapStart requires AutoPublishAlias**
    - Generate random SAM template structures with varying combinations of SnapStart and AutoPublishAlias using Hypothesis
    - Implement a validation function that checks all functions with SnapStart also have AutoPublishAlias
    - Verify the validator correctly identifies templates where SnapStart is present without AutoPublishAlias
    - Test file: `tests/lambda_cold_start/test_property_autopublish.py`
    - **Validates: Requirements 3.4**

  - [ ]* 5.5 Write unit tests for Phase 2 SAM template and NotificationManagement hooks
    - Verify SnapStart on LogCall, ListPredictions, VerificationFunction, NotificationManagementFunction in template.yaml
    - Verify AutoPublishAlias on VerificationFunction and NotificationManagementFunction
    - Verify ConnectFunction and DisconnectFunction do NOT have SnapStart
    - Test NotificationManagement `after_restore()` refreshes `app.sns_client`
    - Test file: `tests/lambda_cold_start/test_phase2.py`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 6. Checkpoint — Phase 2 validation
  - Ensure all tests pass, ask the user if questions arise.
  - Phase 2 should be deployed SEPARATELY from Phase 1 to isolate any AutoPublishAlias issues
  - Ask the user to deploy Phase 2 and verify all secondary functions still operate correctly
  - If deployment fails due to AutoPublishAlias on VerificationFunction or NotificationManagementFunction, roll back Phase 2 only — Phase 1 SnapStart remains active
  - _Requirements: 3.6, 7.2, 7.4_

- [x] 7. Document Provisioned Concurrency as fallback
  - Create `docs/provisioned-concurrency.md` in the project root
  - Include SAM configuration syntax for ProvisionedConcurrencyConfig on AutoPublishAlias
  - State estimated monthly cost (~$39/month for 1 instance at 512MB)
  - Explain it's recommended only if SnapStart restore times exceed acceptable thresholds
  - Note the user's previous deployment failure and provide correct SAM syntax to avoid it
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 8. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Run full test suite: `/home/wsluser/projects/calledit/venv/bin/python -m pytest tests/lambda_cold_start/ -v`

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Phase 1 (task 3) and Phase 2 (task 5) must be deployed separately to isolate risk
- ConnectFunction and DisconnectFunction are intentionally excluded from SnapStart
- All Python commands use the venv at `/home/wsluser/projects/calledit/venv/bin/python`
- Property tests validate universal correctness properties from the design document
- `snapshot_restore_py` is included in the Python 3.12 managed runtime — no pip install needed
