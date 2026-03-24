# Implementation Plan: V4-8a Production Cutover

## Overview

Deploy both v4 AgentCore agents, build new v4 frontend infrastructure (S3 + DDB + CloudFront + HTTP API + Lambdas), connect the React PWA to v4 agents via presigned WebSocket URLs, and update the scanner Lambda. Each task builds incrementally — persistent resources first, then agents, then frontend infra, then Lambda code, then frontend updates, then scanner, then validation.

## Tasks

- [ ] 1. Create persistent resources CloudFormation template
  - [ ] 1.1 Create `infrastructure/v4-persistent-resources/template.yaml` with S3 bucket and DynamoDB table
    - Define `V4FrontendBucket`: private S3 bucket, all `PublicAccessBlockConfiguration` flags `true`, `SSEAlgorithm: AES256`
    - Define `V4PredictionsTable`: table name `calledit-v4`, `PK` (String) partition key, `SK` (String) sort key, `PAY_PER_REQUEST` billing
    - Add GSI `user_id-created_at-index`: partition key `user_id` (String), sort key `created_at` (String)
    - Add GSI `status-verification_date-index`: partition key `status` (String), sort key `verification_date` (String)
    - Export outputs: `V4FrontendBucketName`, `V4FrontendBucketArn`, `V4FrontendBucketRegionalDomainName`, `V4PredictionsTableName`, `V4PredictionsTableArn`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 11.1_
  - [ ]* 1.2 Write property test for S3 bucket security configuration
    - **Property 1: S3 Bucket Security Configuration**
    - Parse the CloudFormation template YAML and verify: `AccessControl: Private`, all four `PublicAccessBlockConfiguration` flags `true`, `SSEAlgorithm: AES256`
    - **Validates: Requirements 3.2, 3.3, 3.4**

- [ ] 2. Deploy persistent resources and launch AgentCore agents
  - [ ] 2.1 Deploy the `calledit-v4-persistent-resources` CloudFormation stack
    - Run `aws cloudformation deploy --template-file infrastructure/v4-persistent-resources/template.yaml --stack-name calledit-v4-persistent-resources`
    - Verify stack outputs: bucket name, bucket ARN, table name, table ARN
    - _Requirements: 2.1, 2.6, 3.1, 3.5, 3.6_
  - [ ] 2.2 Launch Creation Agent via `agentcore launch`
    - Run `agentcore launch` from `calleditv4/` directory (requires TTY — ask user to run)
    - Ensure `DYNAMODB_TABLE_NAME=calledit-v4` is set in agent environment
    - Capture the Creation Agent runtime ARN from launch output
    - Validate with `agentcore invoke` — expect valid streaming response
    - _Requirements: 1.1, 1.3, 2.7_
  - [ ] 2.3 Launch Verification Agent via `agentcore launch`
    - Run `agentcore launch` from `calleditv4-verification/` directory (requires TTY — ask user to run)
    - Ensure `DYNAMODB_TABLE_NAME=calledit-v4` is set in agent environment
    - Capture the Verification Agent runtime ARN from launch output
    - Validate with `agentcore invoke` — expect JSON response with `prediction_id`, `verdict`, `confidence`, `status`
    - _Requirements: 1.2, 1.4, 2.7_

- [ ] 3. Checkpoint — Persistent resources deployed, both agents running
  - Ensure persistent resources stack is deployed and both agents respond to `agentcore invoke`. Ask the user if questions arise.

- [ ] 4. Create Presigned URL Lambda
  - [ ] 4.1 Create `infrastructure/v4-frontend/presigned_url/handler.py`
    - Extract `sub` (user_id) from `event.requestContext.authorizer.jwt.claims`
    - Call `AgentCoreRuntimeClient.generate_presigned_url(runtime_arn=CREATION_AGENT_RUNTIME_ARN)` using `bedrock-agentcore` SDK
    - Return `{"url": "wss://...", "session_id": "<uuid>"}` with HTTP 200
    - On `generate_presigned_url()` failure, return HTTP 502 with `{"error": "..."}`
    - On unexpected exception, return HTTP 500 with generic error
    - Environment variable: `CREATION_AGENT_RUNTIME_ARN`
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_
  - [ ] 4.2 Create `infrastructure/v4-frontend/presigned_url/requirements.txt`
    - Add `bedrock-agentcore` dependency for `AgentCoreRuntimeClient`
    - _Requirements: 5.2_
  - [ ]* 4.3 Write property test for JWT claim extraction (Presigned URL Lambda)
    - **Property 2: JWT Claim Extraction**
    - For any API Gateway HTTP API event with valid Cognito JWT authorizer claims containing a `sub` field, verify the Lambda extracts `user_id` as the `sub` value from `event.requestContext.authorizer.jwt.claims`
    - **Validates: Requirements 5.3**
  - [ ]* 4.4 Write property test for presigned URL response format
    - **Property 3: Presigned URL Response Format**
    - For any successful `generate_presigned_url()` call, verify the Lambda returns HTTP 200 with JSON body containing `url` starting with `wss://` and `session_id` as a valid UUID
    - **Validates: Requirements 5.5**

- [ ] 5. Create ListPredictions Lambda
  - [ ] 5.1 Create `infrastructure/v4-frontend/list_predictions/handler.py`
    - Extract `sub` from `event.requestContext.authorizer.jwt.claims`
    - Query `calledit-v4` table's `user_id-created_at-index` GSI with `user_id = sub`, `ScanIndexForward=False` for descending sort
    - Return `{"results": [...]}` with fields: `prediction_id`, `raw_prediction`, `status`, `verification_date`, `verifiability_score`, `verification_result`, `created_at`
    - Return `{"results": []}` with HTTP 200 if no predictions found
    - On DynamoDB `ClientError`, return HTTP 500 with `{"error": "Database error: ..."}`
    - On unexpected exception, return HTTP 500 with `{"error": "Unexpected error: ..."}`
    - Environment variable: `DYNAMODB_TABLE_NAME` (default `calledit-v4`)
    - _Requirements: 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_
  - [ ] 5.2 Create `infrastructure/v4-frontend/list_predictions/requirements.txt`
    - Add `boto3` dependency
    - _Requirements: 7.2_
  - [ ]* 5.3 Write property test for JWT claim extraction (ListPredictions Lambda)
    - **Property 2: JWT Claim Extraction**
    - Same property as 4.3 but for the ListPredictions Lambda handler
    - **Validates: Requirements 7.3**
  - [ ]* 5.4 Write property test for prediction list formatting
    - **Property 4: Prediction List Formatting**
    - For any set of DynamoDB prediction items, verify the Lambda returns JSON where each prediction in `results` contains `prediction_id`, `status`, `verification_date`, and optionally `verification_result`
    - **Validates: Requirements 7.5**

- [ ] 6. Create main frontend CloudFormation template
  - [ ] 6.1 Create `infrastructure/v4-frontend/template.yaml` with CloudFront, OAC, HTTP API, and Lambda resources
    - Define parameters: `CognitoUserPoolId`, `CognitoUserPoolClientId`, `DynamoDBTableName`, `CreationAgentRuntimeArn`, `FrontendBucketName`, `FrontendBucketArn`, `FrontendBucketDomainName`
    - Define `CloudFrontOAC`: Origin Access Control with SigV4, always sign, S3 origin type
    - Define `CloudFrontDistribution`: `ViewerProtocolPolicy: redirect-to-https`, `DefaultRootObject: index.html`, custom error responses for 403/404 → `/index.html` with 200
    - Define `FrontendBucketPolicy`: `s3:GetObject` for `cloudfront.amazonaws.com` principal, conditioned on distribution ARN
    - Define `V4HttpApi`: API Gateway HTTP API with Cognito JWT authorizer (issuer + audience from parameters)
    - Define `POST /presigned-url` route → `PresignedUrlFunction`
    - Define `GET /predictions` route → `ListPredictionsFunction`
    - Define `PresignedUrlFunction`: Python 3.12, zip packaging, `CREATION_AGENT_RUNTIME_ARN` env var, IAM `bedrock:InvokeAgent` permission
    - Define `ListPredictionsFunction`: Python 3.12, zip packaging, `DYNAMODB_TABLE_NAME` env var, IAM `dynamodb:Query` on table + GSIs
    - Configure CORS: allow CloudFront domain + `http://localhost:5173`, headers `Authorization` + `Content-Type`, methods `GET`, `POST`, `OPTIONS`
    - Export outputs: `CloudFrontDomainName`, `CloudFrontDistributionId`, `HttpApiUrl`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.1, 5.8, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.8, 11.1, 11.2_

- [ ] 7. Deploy main frontend stack
  - [ ] 7.1 Deploy the `calledit-v4-frontend` CloudFormation stack
    - Run `aws cloudformation deploy` with parameters: Cognito user pool ID/client ID from `calledit-backend` stack, DynamoDB table name `calledit-v4`, Creation Agent runtime ARN, frontend bucket name/ARN/domain from persistent resources stack
    - Verify stack outputs: CloudFront domain, distribution ID, HTTP API URL
    - _Requirements: 4.1, 5.1, 6.1, 6.6, 11.1_

- [ ] 8. Checkpoint — Frontend infrastructure deployed
  - Ensure CloudFront distribution is deployed, HTTP API is accessible, both Lambdas are created. Ask the user if questions arise.

- [ ] 9. Update frontend React code for v4
  - [ ] 9.1 Create `frontend/src/services/agentCoreWebSocket.ts` — new WebSocket service for AgentCore
    - Implement `getPresignedUrl(apiUrl, token)`: calls `POST /presigned-url` with Cognito JWT, returns `{url, session_id}`
    - Implement `connectAndStream(wssUrl, predictionPayload, callbacks)`: opens native WebSocket to presigned URL, sends prediction payload, parses SSE-formatted events (`data: {...}\n\n`), emits typed events (`flow_started`, `text`, `turn_complete`, `flow_complete`)
    - Handle connection errors with retry callback
    - Handle WebSocket drop mid-stream with partial results + error callback
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_
  - [ ] 9.2 Update `frontend/src/components/PredictionInput.tsx` for v4 WebSocket flow
    - Replace direct `axios.get` to `/strands-make-call` with presigned URL → WebSocket flow using `agentCoreWebSocket.ts`
    - Call `POST /presigned-url` on v4 HTTP API, then open WebSocket to returned URL
    - Parse SSE stream events and update UI progressively
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [ ] 9.3 Update `frontend/src/components/ListPredictions.tsx` for v4 API
    - Change endpoint from `VITE_APIGATEWAY + '/list-predictions'` to `VITE_V4_API_URL + '/predictions'`
    - Update response field mapping to match v4 schema (`raw_prediction`, `verifiability_score`, etc.)
    - _Requirements: 9.2_
  - [ ] 9.4 Update `frontend/src/services/apiService.ts` for v4 API base URL
    - Add v4 API instance using `VITE_V4_API_URL` environment variable
    - Keep existing v3 API instance for backward compatibility during transition
    - _Requirements: 9.1_
  - [ ] 9.5 Update `frontend/.env` with v4 environment variables
    - Add `VITE_V4_API_URL` with the HTTP API invoke URL from stack output
    - Update `VITE_COGNITO_PROD_REDIRECT_URI` to the v4 CloudFront domain
    - _Requirements: 9.1, 9.3_
  - [ ]* 9.6 Write property test for SSE stream event parsing
    - **Property 5: SSE Stream Event Parsing**
    - For any valid SSE-formatted string matching `data: {json}\n\n`, verify the parser extracts a valid JSON object with a `type` field
    - Use fast-check library (TypeScript)
    - **Validates: Requirements 8.3**

- [ ] 10. Build and deploy frontend
  - [ ] 10.1 Build React PWA and deploy to S3
    - Run `npm run build` in `frontend/` directory
    - Run `aws s3 sync frontend/dist/ s3://{bucket-name} --delete` to deploy build artifacts
    - _Requirements: 9.4_
  - [ ] 10.2 Invalidate CloudFront cache
    - Run `aws cloudfront create-invalidation --distribution-id {dist-id} --paths "/*"`
    - _Requirements: 9.5_

- [ ] 11. Update scanner Lambda for v4
  - [ ] 11.1 Update `infrastructure/verification-scanner/template.yaml` for v4 table
    - Change `DynamoDBTableName` default from `calledit-db` to `calledit-v4`
    - Verify `VerificationAgentId` parameter is passed during deployment
    - _Requirements: 1.5, 10.1_
  - [ ] 11.2 Redeploy scanner Lambda with v4 configuration
    - Deploy with `VERIFICATION_AGENT_ID` set to the Verification Agent runtime ID from step 2.3
    - Deploy with `DYNAMODB_TABLE_NAME=calledit-v4`
    - Enable the EventBridge schedule (`Enabled: true`)
    - _Requirements: 1.5, 1.6, 10.1, 10.2_

- [ ] 12. Final checkpoint — End-to-end validation
  - Validate the full flow: CloudFront serves React PWA, login via Cognito, make a prediction via presigned WebSocket, check prediction list via GET /predictions, verify scanner runs on schedule. Ensure all tests pass, ask the user if questions arise.
  - _Requirements: 1.3, 1.4, 8.1, 8.2, 8.3, 8.4, 9.2, 9.4, 9.5, 10.2, 11.3, 11.4_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- `agentcore launch` requires TTY — ask the user to run these commands manually and provide the output
- Property tests use Hypothesis (Python) and fast-check (TypeScript)
- Decision 96: No mocks — property tests validate real code paths
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- v3 infrastructure stays running and unmodified (Decision 111)
