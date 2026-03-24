# Requirements Document — V4-8a: Production Cutover

## Introduction

Deploy both v4 AgentCore agents to production, build new v4 frontend infrastructure, and connect the React PWA to the v4 agents. This is the production cutover step that replaces the v3 Lambda-based backend with AgentCore Runtime.

The v3 system (API Gateway WebSocket + REST, Docker Lambda, SnapStart Lambdas) stays running untouched until v4 is validated (Decision 111). Cognito user pool and Prompt Management stack `calledit-prompts` are reused. A new v4 DynamoDB table `calledit-v4` replaces the shared `calledit-db` table — clean break from v3 key format, no scanning, GSIs from day one (Decision 113).

V4-8a delivers eight things:
1. AgentCore agent deployment — `agentcore launch` for both creation and verification agents, validated via `agentcore invoke`
2. V4 DynamoDB table — new `calledit-v4` table with v4 key format (`PK=PRED#{id}`, `SK=BUNDLE`) and two GSIs: `user_id` + `created_at` for listing, `status` + `verification_date` for the scanner (Decision 113)
3. S3 bucket for v4 frontend — private bucket in a persistent resources CloudFormation template (Decision 112), all public access blocked, AES256 encryption
4. CloudFront distribution with OAC — serves the React PWA from the private S3 bucket, HTTPS only, SPA error page routing
5. Presigned URL Lambda — receives Cognito JWT, validates it, calls `AgentCoreRuntimeClient.generate_presigned_url()`, returns a `wss://` URL for direct frontend-to-agent WebSocket (Decision 110)
6. API Gateway HTTP API — two routes (`POST /presigned-url`, `GET /predictions`) with Cognito JWT authorizer and CORS
7. Frontend updates — React PWA calls the presigned URL endpoint, opens WebSocket directly to AgentCore Runtime, parses SSE stream events, keeps existing Cognito auth
8. ListPredictions Lambda — queries v4 DDB GSI for user's predictions, returns JSON list

V4-8a does NOT deliver: v3 teardown, Memory integration (V4-6), eval framework updates (V4-7a), or custom domain.

## Glossary

- **Creation_Agent**: The AgentCore runtime deployed from `calleditv4/`. Handles prediction creation via streaming WebSocket. Invoked by users through presigned WebSocket URLs.
- **Verification_Agent**: The AgentCore runtime deployed from `calleditv4-verification/`. Handles batch prediction verification. Invoked by the Scanner_Lambda via EventBridge schedule.
- **Scanner_Lambda**: The existing Lambda at `infrastructure/verification-scanner/` that queries DDB for due predictions and invokes the Verification_Agent. Deployed in V4-5b.
- **Presigned_URL_Lambda**: A Python 3.12 Lambda that validates a Cognito JWT from the Authorization header, calls `AgentCoreRuntimeClient.generate_presigned_url(runtime_arn)` for the Creation_Agent, and returns the presigned `wss://` URL to the frontend.
- **ListPredictions_Lambda**: A Python 3.12 Lambda that queries the `calledit-v4` DynamoDB table's `user_id-created_at-index` GSI for a user's predictions and returns a JSON list with status, verdict, and metadata.
- **V4_DynamoDB_Table**: A new DynamoDB table `calledit-v4` with key format `PK=PRED#{prediction_id}`, `SK=BUNDLE`. Includes two GSIs: `user_id-created_at-index` (for listing by user) and `status-verification_date-index` (for the scanner). CloudFormation-managed, defined in the persistent resources template alongside the S3 bucket (Decision 113, 114).
- **V4_HTTP_API**: An API Gateway HTTP API (not REST API, not WebSocket API) with two routes and a Cognito JWT authorizer. Serves as the v4 API surface for the React PWA.
- **V4_Frontend_Bucket**: A private S3 bucket for the v4 React PWA build artifacts. All public access blocked, AES256 encryption. Defined in its own CloudFormation template at `infrastructure/v4-frontend-bucket/template.yaml` (Decision 112).
- **V4_CloudFront_Distribution**: A CloudFront distribution that serves the React PWA from the V4_Frontend_Bucket using Origin Access Control (OAC). HTTPS only.
- **OAC**: Origin Access Control — the AWS-recommended mechanism for CloudFront to access private S3 buckets. Replaces the older OAI pattern. Uses SigV4 signing.
- **React_PWA**: The existing React Progressive Web App in `frontend/`. Currently connects to v3 via API Gateway WebSocket and REST API. Will be updated to use presigned WebSocket URLs and the V4_HTTP_API.
- **Cognito_User_Pool**: The existing Cognito user pool from the `calledit-backend` CloudFormation stack. Reused by v4 — not recreated.
- **AgentCore_Runtime**: The AWS Bedrock AgentCore Runtime service that hosts deployed agents. Supports `generate_presigned_url()` for WebSocket access and `invoke()` for synchronous invocation.

## Requirements

### Requirement 1: AgentCore Agent Deployment

**User Story:** As a developer, I want both v4 agents deployed to AgentCore Runtime, so that the frontend and scanner can invoke production agents instead of local dev servers.

#### Acceptance Criteria

1. THE Creation_Agent SHALL be deployed to AgentCore_Runtime via `agentcore launch` from the `calleditv4/` directory
2. THE Verification_Agent SHALL be deployed to AgentCore_Runtime via `agentcore launch` from the `calleditv4-verification/` directory
3. WHEN the Creation_Agent is deployed, THE Creation_Agent SHALL respond to `agentcore invoke` with a valid streaming response
4. WHEN the Verification_Agent is deployed, THE Verification_Agent SHALL respond to `agentcore invoke` with a valid JSON response containing `prediction_id`, `verdict`, `confidence`, and `status` fields
5. WHEN both agents are deployed, THE Scanner_Lambda SHALL be updated with the `VERIFICATION_AGENT_ID` environment variable set to the Verification_Agent runtime ID
6. WHEN the Scanner_Lambda is updated with the agent ID, THE Scanner_Lambda EventBridge schedule SHALL be enabled

### Requirement 2: V4 DynamoDB Table

**User Story:** As a developer, I want a dedicated v4 DynamoDB table with proper key format and GSIs, so that predictions are stored cleanly without v3 key format baggage and can be queried efficiently without table scans.

#### Acceptance Criteria

1. THE V4_DynamoDB_Table SHALL be named `calledit-v4` and defined in the persistent resources CloudFormation template alongside the V4_Frontend_Bucket (Decision 114)
2. THE V4_DynamoDB_Table SHALL use `PK` (String) as partition key and `SK` (String) as sort key, with items stored as `PK=PRED#{prediction_id}`, `SK=BUNDLE`
3. THE V4_DynamoDB_Table SHALL include a GSI named `user_id-created_at-index` with `user_id` (String) as partition key and `created_at` (String) as sort key, for efficient per-user prediction listing
4. THE V4_DynamoDB_Table SHALL include a GSI named `status-verification_date-index` with `status` (String) as partition key and `verification_date` (String) as sort key, for efficient scanner queries
5. THE V4_DynamoDB_Table SHALL use PAY_PER_REQUEST billing mode
6. THE V4_DynamoDB_Table SHALL export its table name and ARN as CloudFormation outputs for cross-stack reference
7. WHEN the v4 agents are deployed, THE agents SHALL be configured with `DYNAMODB_TABLE_NAME=calledit-v4` to use the new table instead of `calledit-db`

### Requirement 3: V4 Frontend S3 Bucket

**User Story:** As a developer, I want a private S3 bucket for the v4 frontend build, so that the React PWA can be served securely through CloudFront.

#### Acceptance Criteria

1. THE V4_Frontend_Bucket SHALL be defined in a standalone CloudFormation template at `infrastructure/v4-frontend-bucket/template.yaml` (Decision 112)
2. THE V4_Frontend_Bucket SHALL have `AccessControl` set to `Private`
3. THE V4_Frontend_Bucket SHALL have `PublicAccessBlockConfiguration` with `BlockPublicAcls`, `BlockPublicPolicy`, `IgnorePublicAcls`, and `RestrictPublicBuckets` all set to `true`
4. THE V4_Frontend_Bucket SHALL have server-side encryption enabled with `SSEAlgorithm` set to `AES256`
5. THE V4_Frontend_Bucket CloudFormation template SHALL be independent of the main v4 frontend stack, so that the bucket can be created once and referenced without risk of rollback deleting a non-empty bucket
6. THE V4_Frontend_Bucket SHALL export its bucket name and ARN as CloudFormation outputs for cross-stack reference

### Requirement 4: CloudFront Distribution with OAC

**User Story:** As a user, I want the v4 frontend served over HTTPS through CloudFront, so that I can access the app securely with low latency.

#### Acceptance Criteria

1. THE V4_CloudFront_Distribution SHALL be defined in the main v4 frontend CloudFormation template at `infrastructure/v4-frontend/template.yaml`
2. THE V4_CloudFront_Distribution SHALL use Origin Access Control (OAC) to access the V4_Frontend_Bucket (not OAI)
3. THE V4_CloudFront_Distribution SHALL set `ViewerProtocolPolicy` to `redirect-to-https` so that all HTTP requests redirect to HTTPS
4. THE V4_CloudFront_Distribution SHALL set `DefaultRootObject` to `index.html`
5. WHEN CloudFront receives a 403 or 404 error from S3, THE V4_CloudFront_Distribution SHALL return `/index.html` with HTTP status 200 to support SPA client-side routing
6. THE V4_Frontend_Bucket SHALL have a bucket policy that allows `s3:GetObject` only from the `cloudfront.amazonaws.com` service principal, conditioned on the V4_CloudFront_Distribution ARN
7. THE V4_CloudFront_Distribution SHALL export its domain name as a CloudFormation output

### Requirement 5: Presigned URL Lambda

**User Story:** As a user, I want to get a presigned WebSocket URL for the creation agent, so that my browser can connect directly to AgentCore Runtime without a streaming proxy.

#### Acceptance Criteria

1. THE Presigned_URL_Lambda SHALL be defined in the main v4 frontend CloudFormation template at `infrastructure/v4-frontend/template.yaml`
2. THE Presigned_URL_Lambda SHALL be a Python 3.12 Lambda function with zip packaging
3. WHEN the Presigned_URL_Lambda receives a request, THE Presigned_URL_Lambda SHALL extract the JWT from the `Authorization` header
4. WHEN the Presigned_URL_Lambda receives a valid Cognito JWT, THE Presigned_URL_Lambda SHALL call `AgentCoreRuntimeClient.generate_presigned_url()` with the Creation_Agent runtime ARN
5. WHEN the presigned URL is generated, THE Presigned_URL_Lambda SHALL return a JSON response with the `wss://` URL in the response body
6. IF the Authorization header is missing or the JWT is invalid, THEN THE Presigned_URL_Lambda SHALL return HTTP 401 with an error message
7. IF the `generate_presigned_url()` call fails, THEN THE Presigned_URL_Lambda SHALL return HTTP 502 with an error message describing the failure
8. THE Presigned_URL_Lambda SHALL have IAM permissions to call `generate_presigned_url()` on the Creation_Agent runtime

### Requirement 6: API Gateway HTTP API

**User Story:** As a developer, I want an API Gateway HTTP API with Cognito authorization, so that the frontend has a secure API surface for presigned URLs and prediction listing.

#### Acceptance Criteria

1. THE V4_HTTP_API SHALL be defined in the main v4 frontend CloudFormation template as an API Gateway HTTP API (not REST API, not WebSocket API)
2. THE V4_HTTP_API SHALL have a `POST /presigned-url` route integrated with the Presigned_URL_Lambda
3. THE V4_HTTP_API SHALL have a `GET /predictions` route integrated with the ListPredictions_Lambda
4. THE V4_HTTP_API SHALL use a Cognito JWT authorizer on both routes, configured with the existing Cognito_User_Pool
5. THE V4_HTTP_API SHALL configure CORS to allow requests from the V4_CloudFront_Distribution domain, with `Authorization` and `Content-Type` in allowed headers
6. THE V4_HTTP_API SHALL export its invoke URL as a CloudFormation output

### Requirement 7: ListPredictions Lambda

**User Story:** As a user, I want to see my past predictions with their status and verdicts, so that I can track which predictions have been verified.

#### Acceptance Criteria

1. THE ListPredictions_Lambda SHALL be defined in the main v4 frontend CloudFormation template at `infrastructure/v4-frontend/template.yaml`
2. THE ListPredictions_Lambda SHALL be a Python 3.12 Lambda function with zip packaging
3. WHEN the ListPredictions_Lambda receives a request, THE ListPredictions_Lambda SHALL extract the `user_id` from the Cognito JWT claims
4. WHEN the ListPredictions_Lambda has a valid `user_id`, THE ListPredictions_Lambda SHALL query the V4_DynamoDB_Table's `user_id-created_at-index` GSI for prediction items belonging to that user, sorted by creation date descending
5. THE ListPredictions_Lambda SHALL return a JSON response containing a list of predictions, each with `prediction_id`, `raw_prediction`, `status`, `verification_date`, `verifiability_score`, and `verification_result` fields when available
6. IF the DynamoDB query fails, THEN THE ListPredictions_Lambda SHALL return HTTP 500 with an error message
7. IF no predictions are found for the user, THE ListPredictions_Lambda SHALL return HTTP 200 with an empty list
8. THE ListPredictions_Lambda SHALL have IAM read permissions on the V4_DynamoDB_Table and its GSIs

### Requirement 8: Frontend WebSocket Integration

**User Story:** As a user, I want to make predictions through the v4 frontend, so that my predictions are processed by the v4 creation agent via direct WebSocket.

#### Acceptance Criteria

1. WHEN the user submits a prediction, THE React_PWA SHALL call `POST /presigned-url` on the V4_HTTP_API with the Cognito JWT in the Authorization header
2. WHEN the React_PWA receives a presigned `wss://` URL, THE React_PWA SHALL open a WebSocket connection directly to that URL
3. WHEN the React_PWA receives stream events from AgentCore_Runtime over the WebSocket, THE React_PWA SHALL parse SSE-formatted events (`data: {...}\n\n`) and update the UI progressively
4. WHEN the WebSocket connection closes, THE React_PWA SHALL display the final prediction result to the user
5. IF the presigned URL request fails, THEN THE React_PWA SHALL display an error message to the user
6. IF the WebSocket connection fails or drops, THEN THE React_PWA SHALL display a connection error and allow the user to retry
7. THE React_PWA SHALL continue to use the existing Cognito auth flow (login, token exchange, token refresh) from the AuthContext

### Requirement 9: Frontend API Migration

**User Story:** As a developer, I want the frontend to use the new v4 API endpoints, so that prediction listing and API calls go through the v4 infrastructure.

#### Acceptance Criteria

1. THE React_PWA SHALL update its API base URL configuration to point to the V4_HTTP_API invoke URL
2. THE React_PWA SHALL call `GET /predictions` on the V4_HTTP_API to fetch the user's prediction list (replacing the v3 `/list-predictions` endpoint)
3. THE React_PWA SHALL update the Cognito redirect URIs to include the V4_CloudFront_Distribution domain
4. THE React_PWA SHALL be built and deployed to the V4_Frontend_Bucket
5. WHEN the frontend is deployed, THE V4_CloudFront_Distribution cache SHALL be invalidated to serve the latest build

### Requirement 10: Scanner Lambda Agent Integration

**User Story:** As a pipeline operator, I want the verification scanner to invoke the deployed v4 verification agent, so that predictions are verified automatically in production.

#### Acceptance Criteria

1. WHEN the Scanner_Lambda `VERIFICATION_AGENT_ID` environment variable is set, THE Scanner_Lambda SHALL use `AgentCoreRuntimeClient` to invoke the deployed Verification_Agent
2. WHEN the Scanner_Lambda EventBridge schedule is enabled, THE Scanner_Lambda SHALL run every 15 minutes and process due predictions
3. IF the Verification_Agent invocation fails, THEN THE Scanner_Lambda SHALL log the error and continue processing remaining predictions

### Requirement 11: Infrastructure Separation

**User Story:** As a developer, I want v4 infrastructure to be independent of v3, so that v3 stays running until v4 is validated and can be torn down separately.

#### Acceptance Criteria

1. THE v4 frontend infrastructure SHALL be defined in new CloudFormation templates under `infrastructure/v4-frontend-bucket/` and `infrastructure/v4-frontend/`, separate from the v3 `backend/calledit-backend/template.yaml`
2. THE v4 infrastructure SHALL reference the existing Cognito_User_Pool by importing its User Pool ID as a parameter (not by creating a new user pool)
3. THE v4 infrastructure SHALL use the new V4_DynamoDB_Table (`calledit-v4`) for all prediction data — not the v3 `calledit-db` table (Decision 113)
4. THE v3 infrastructure (API Gateway WebSocket + REST, Docker Lambda, SnapStart Lambdas) SHALL remain running and unmodified until v4 is validated
