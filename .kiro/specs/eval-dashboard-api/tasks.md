# Implementation Plan: Eval Dashboard API

## Overview

Add production API endpoints for the eval dashboard by extending the existing v4-frontend SAM stack with two new Lambda functions, a new DynamoDB table in persistent resources, SnapStart across all v4 Lambdas, and a dual-mode frontend API client. Build order follows deployment dependencies: persistent resources first, then Lambda handlers, SAM template updates, frontend client, and finally deployments.

## Tasks

- [x] 1. Add Eval Reports Table to Persistent Resources Stack
  - [x] 1.1 Define V4EvalReportsTable DynamoDB resource in `infrastructure/v4-persistent-resources/template.yaml`
    - TableName: `calledit-v4-eval-reports`, PK (String) + SK (String), PAY_PER_REQUEST
    - DeletionPolicy: Retain, UpdateReplacePolicy: Retain
    - Add stack outputs: `V4EvalReportsTableName` and `V4EvalReportsTableArn` with exports
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.2 Checkpoint — Deploy persistent resources stack
    - Ask the user to run `cd infrastructure/v4-persistent-resources && sam build && sam deploy` to create the table before the v4-frontend stack can reference it.
    - Ensure deployment succeeds and outputs are visible.

- [x] 2. Implement ListEvalReports Lambda handler
  - [x] 2.1 Create `infrastructure/v4-frontend/list_eval_reports/handler.py`
    - Follow the `ListPredictions` handler pattern: `DecimalEncoder`, `_response()` helper, API Gateway V2 payload format 2.0
    - Extract `agent` from `event["queryStringParameters"]`; return 400 if missing
    - Query DDB with `PK=AGENT#{agent}`, `ScanIndexForward=False`, ProjectionExpression excluding `case_results`
    - Strip `PK` and `SK` from each item, return JSON array of `{run_metadata, aggregate_scores}`
    - Handle `ClientError` → 500, unexpected exceptions → 500 with logging
    - _Requirements: 2.5, 2.6, 2.7, 2.8, 2.9_

  - [ ]* 2.2 Write property test: Decimal conversion round-trip
    - **Property 1: Decimal conversion round-trip**
    - Create `infrastructure/v4-frontend/tests/test_handler_properties.py`
    - Use Hypothesis with `@settings(max_examples=100)` to generate nested dicts/lists with Decimal values
    - Assert `DecimalEncoder` produces JSON-serializable output with no remaining Decimal instances
    - **Validates: Requirements 2.8, 3.10**

  - [ ]* 2.3 Write property test: ListEvalReports query construction
    - **Property 2: ListEvalReports query construction**
    - Use Hypothesis to generate agent type strings; mock `boto3.resource`
    - Assert DDB Query uses `PK=AGENT#{agent}`, `ScanIndexForward=False`, ProjectionExpression excludes `case_results`
    - **Validates: Requirements 2.5**

  - [ ]* 2.4 Write property test: ListEvalReports response shape
    - **Property 3: ListEvalReports response shape**
    - Use Hypothesis to generate lists of DDB items with `run_metadata` and `aggregate_scores` maps
    - Assert response is 200 with JSON array where each element has exactly `run_metadata` and `aggregate_scores` (no `PK`, `SK`, `case_results`)
    - **Validates: Requirements 2.7**

  - [ ]* 2.5 Write unit tests for ListEvalReports error cases
    - Test missing `agent` query param → 400
    - Test DynamoDB `ClientError` → 500
    - Test empty results → 200 with empty array
    - Create `infrastructure/v4-frontend/tests/test_handler_unit.py`
    - _Requirements: 2.6, 2.9_

- [x] 3. Implement GetEvalReport Lambda handler
  - [x] 3.1 Create `infrastructure/v4-frontend/get_eval_report/handler.py`
    - Follow same handler pattern as ListEvalReports
    - Extract `agent` and `ts` from `event["queryStringParameters"]`; return 400 if either missing
    - GetItem with `PK=AGENT#{agent}`, `SK={ts}`; return 404 if not found
    - If `case_results_split` is true, fetch companion item at `SK={ts}#CASES` and merge `case_results`
    - If companion item missing, set `case_results=[]` and log warning
    - Remove `PK`, `SK`, `case_results_split` from response
    - Convert Decimals via `DecimalEncoder`, return full report JSON
    - _Requirements: 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11_

  - [ ]* 3.2 Write property test: GetEvalReport key construction
    - **Property 4: GetEvalReport key construction**
    - Use Hypothesis to generate agent and timestamp strings; mock `boto3.resource`
    - Assert GetItem uses `PK=AGENT#{agent}` and `SK={ts}`
    - **Validates: Requirements 3.5**

  - [ ]* 3.3 Write property test: Split case_results reassembly
    - **Property 5: Split case_results reassembly**
    - Use Hypothesis to generate DDB items with `case_results_split=True` and companion items
    - Assert response `case_results` equals companion item's `case_results`, and `case_results_split` is absent
    - **Validates: Requirements 3.6, 3.9**

  - [ ]* 3.4 Write property test: GetEvalReport response sanitization
    - **Property 6: GetEvalReport response sanitization**
    - Use Hypothesis to generate DDB items with `PK`, `SK`, `case_results_split`, `run_metadata`, `aggregate_scores`, `case_results`
    - Assert response contains `run_metadata`, `aggregate_scores`, `case_results` but never `PK`, `SK`, or `case_results_split`
    - **Validates: Requirements 3.9**

  - [ ]* 3.5 Write unit tests for GetEvalReport error cases
    - Test missing `agent` or `ts` → 400
    - Test item not found → 404
    - Test DynamoDB `ClientError` → 500
    - Test split item with missing companion → `case_results: []`
    - Add to `infrastructure/v4-frontend/tests/test_handler_unit.py`
    - _Requirements: 3.7, 3.8, 3.11_

- [ ] 4. Checkpoint — Run all property and unit tests
  - Ensure all tests pass, ask the user if questions arise.
  - Run: `/home/wsluser/projects/calledit/venv/bin/python -m pytest infrastructure/v4-frontend/tests/ -v`

- [x] 5. Update v4-frontend SAM template with new Lambdas, SnapStart, and API routes
  - [x] 5.1 Add `EvalReportsTableName` and `EvalReportsTableArn` parameters to `infrastructure/v4-frontend/template.yaml`
    - _Requirements: 4.4_

  - [x] 5.2 Add ListEvalReports Lambda resources to the template
    - `ListEvalReportsFunction` with SnapStart, Python 3.12, 30s timeout, 256MB, env var for table name
    - IAM policy: `dynamodb:Query` on eval reports table ARN
    - `ListEvalReportsVersion` (AWS::Lambda::Version)
    - `ListEvalReportsAlias` (AWS::Lambda::Alias, Name: live)
    - `ListEvalReportsIntegration` targeting alias ARN, AWS_PROXY, PayloadFormatVersion 2.0
    - `ListEvalReportsRoute` for `GET /eval/reports` with JWT auth via CognitoAuthorizer
    - `ListEvalReportsPermission` with `DependsOn: ListEvalReportsAlias`, scoped to route ARN
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 4.1, 4.3_

  - [x] 5.3 Add GetEvalReport Lambda resources to the template
    - Same SnapStart pattern as ListEvalReports
    - `GetEvalReportFunction` with `dynamodb:GetItem` policy on eval reports table ARN
    - Version, Alias, Integration, Route (`GET /eval/report`), Permission
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.2, 4.3_

  - [x] 5.4 Retrofit SnapStart on existing PresignedUrlFunction
    - Add `SnapStart: ApplyOn: PublishedVersions` to function properties
    - Add `PresignedUrlVersion` and `PresignedUrlAlias` (live) resources
    - Update `PresignedUrlIntegration` to target alias ARN
    - Update `PresignedUrlPermission` to reference alias ARN with `DependsOn: PresignedUrlAlias`
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 5.5 Retrofit SnapStart on existing ListPredictionsFunction
    - Same pattern as PresignedUrl: add SnapStart, Version, Alias
    - Update `ListPredictionsIntegration` and `ListPredictionsPermission` to use alias ARN
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 6. Update verification-scanner template with SnapStart
  - [x] 6.1 Add SnapStart to VerificationScannerFunction in `infrastructure/verification-scanner/template.yaml`
    - Add `SnapStart: ApplyOn: PublishedVersions`
    - Add `VerificationScannerVersion` and `VerificationScannerAlias` (live) resources
    - Update EventBridge `ScheduledScan` target to invoke alias ARN
    - Update outputs to reference alias ARN
    - _Requirements: 7.5_

- [x] 7. Update frontend API client for dual-mode operation
  - [x] 7.1 Update `frontend-v4/src/pages/EvalDashboard/hooks/useReportStore.ts`
    - Import `useAuth` from AuthContext
    - Add base URL logic: `import.meta.env.DEV ? '/api' : import.meta.env.VITE_V4_API_URL`
    - Add auth header logic: dev mode omits header, prod mode includes `Authorization: Bearer {id_token}`
    - Update `useReportList` and `getFullReport` to use base URL + auth headers
    - Preserve existing `agent` and `ts` query parameter interface
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ]* 7.2 Write property test: Frontend API client mode switching
    - **Property 7: Frontend API client mode switching**
    - Create `frontend-v4/src/pages/EvalDashboard/hooks/__tests__/useReportStore.test.ts`
    - Use vitest to test URL construction and header logic for dev vs prod modes
    - Assert dev mode: URL starts with `/api/eval/`, no Authorization header
    - Assert prod mode: URL starts with `{VITE_V4_API_URL}/eval/`, includes Bearer token
    - Assert query params identical in both modes
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 8. Checkpoint — Deploy and verify
  - [x] 8.1 Deploy v4-frontend stack
    - Ask the user to run `cd infrastructure/v4-frontend && sam build && sam deploy` with the new `EvalReportsTableName` and `EvalReportsTableArn` parameter values from the persistent resources stack outputs.
    - Verify all 4 Lambdas have SnapStart aliases.

  - [x] 8.2 Deploy verification-scanner stack
    - Ask the user to run `cd infrastructure/verification-scanner && sam build && sam deploy`.
    - _Requirements: 7.5_

  - [x] 8.3 Build frontend, sync to S3, and invalidate CloudFront
    - Ask the user to run:
      - `cd frontend-v4 && npm run build`
      - `aws s3 sync dist/ s3://calledit-v4-persistent-resources-v4frontendbucket-tjqdqan1gbuy --delete`
      - `aws cloudfront create-invalidation --distribution-id E1V0EF85NP9DXQ --paths "/*"`
    - _Requirements: 6.1, 6.2, 6.3_

- [x] 9. Final checkpoint — Verify end-to-end
  - Ensure all tests pass, ask the user if questions arise.
  - Verify the deployed dashboard loads and fetches eval data through API Gateway with JWT auth.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Deployment commands require TTY — ask the user to run `sam build && sam deploy` commands manually
- Property tests use Hypothesis with `@settings(max_examples=100)`
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Frontend build: `cd frontend-v4 && npm run build`
- The existing v4-frontend stack is already deployed — tasks 5.4 and 5.5 are stack UPDATEs, not new stacks
- SnapStart retrofit on existing Lambdas may need careful ordering per Decision 17 (DependsOn for alias resources)
