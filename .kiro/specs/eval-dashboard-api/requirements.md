# Requirements Document

## Introduction

The eval dashboard currently operates only in dev mode via a Vite dev server proxy that reads DynamoDB using local AWS credentials. For production deployment behind CloudFront, the dashboard needs API Gateway HTTP API endpoints backed by Lambda functions. This spec adds two new Lambda functions to the existing v4-frontend SAM template (following the established ListPredictions pattern), updates the React frontend to call API Gateway with Cognito JWT auth in production while preserving the Vite proxy for local development, and adds the eval reports DynamoDB table to the persistent resources stack.

## Glossary

- **V4_Frontend_Stack**: The existing SAM stack (`infrastructure/v4-frontend/template.yaml`) containing CloudFront, HTTP API Gateway, Cognito JWT authorizer, and Lambda functions
- **Persistent_Resources_Stack**: The SAM stack (`infrastructure/v4-persistent-resources/template.yaml`) containing long-lived resources (S3 bucket, DynamoDB tables) that survive stack rollbacks
- **Eval_Reports_Table**: DynamoDB table `calledit-v4-eval-reports` with PK=`AGENT#{agent_type}` (String) and SK=ISO 8601 timestamp (String), storing eval run reports
- **ListEvalReports_Lambda**: Lambda function that queries the Eval_Reports_Table for report summaries (metadata and aggregate scores, excluding case_results)
- **GetEvalReport_Lambda**: Lambda function that retrieves a full eval report from the Eval_Reports_Table, including reassembly of split case_results
- **HTTP_API**: The existing AWS API Gateway V2 HTTP API with Cognito JWT authorizer in the V4_Frontend_Stack
- **Report_Summary**: A report item containing only `run_metadata` and `aggregate_scores` fields (case_results excluded)
- **Full_Report**: A complete report item including `run_metadata`, `aggregate_scores`, and `case_results`
- **Split_Case_Results**: A storage pattern where case_results exceeding the DynamoDB 400KB item limit are stored in a separate item with SK=`{timestamp}#CASES`
- **Vite_Proxy**: The dev-mode server middleware (`server/eval-api.ts`) that proxies `/api/eval/*` requests to DynamoDB using local AWS credentials
- **Dashboard_Client**: The React frontend code (`useReportStore.ts`) that fetches eval reports

## Requirements

### Requirement 1: Eval Reports Table in Persistent Resources

**User Story:** As a platform operator, I want the eval reports DynamoDB table defined in the persistent resources stack, so that it survives stack rollbacks and is managed alongside other long-lived data stores.

#### Acceptance Criteria

1. THE Persistent_Resources_Stack SHALL define the Eval_Reports_Table as a DynamoDB table resource with TableName `calledit-v4-eval-reports`, partition key `PK` (String), sort key `SK` (String), and PAY_PER_REQUEST billing mode
2. THE Persistent_Resources_Stack SHALL set DeletionPolicy and UpdateReplacePolicy to Retain on the Eval_Reports_Table resource
3. THE Persistent_Resources_Stack SHALL export the Eval_Reports_Table name and ARN as stack outputs for consumption by the V4_Frontend_Stack

### Requirement 2: ListEvalReports Lambda Function

**User Story:** As a dashboard user, I want to retrieve a list of eval report summaries for a given agent type, so that I can browse run history without downloading full case_results data.

#### Acceptance Criteria

1. THE V4_Frontend_Stack SHALL define the ListEvalReports_Lambda as a SAM Function resource with Python 3.12 runtime, `handler.lambda_handler` entry point, 30-second timeout, 256MB memory, and SnapStart enabled (`SnapStart: ApplyOn: PublishedVersions`)
2. THE ListEvalReports_Lambda SHALL have a published version and a `live` alias, with the API Gateway integration targeting the alias ARN (not the function ARN)
3. THE ListEvalReports_Lambda SHALL receive the Eval_Reports_Table name via an environment variable
4. THE ListEvalReports_Lambda SHALL have an IAM policy granting `dynamodb:Query` on the Eval_Reports_Table ARN
5. WHEN the ListEvalReports_Lambda receives a GET request to `/eval/reports` with an `agent` query parameter, THE ListEvalReports_Lambda SHALL query the Eval_Reports_Table with PK=`AGENT#{agent}`, ProjectionExpression excluding `case_results`, and ScanIndexForward=false
6. WHEN the `agent` query parameter is missing, THE ListEvalReports_Lambda SHALL return HTTP 400 with a JSON error message
7. THE ListEvalReports_Lambda SHALL return a JSON array of Report_Summary objects with `run_metadata` and `aggregate_scores` fields
8. THE ListEvalReports_Lambda SHALL convert DynamoDB Decimal values to JSON-compatible float or int values in the response
9. IF the DynamoDB query fails, THEN THE ListEvalReports_Lambda SHALL return HTTP 500 with a JSON error message and log the error

### Requirement 3: GetEvalReport Lambda Function

**User Story:** As a dashboard user, I want to retrieve a full eval report including case-level results, so that I can inspect individual test case outcomes.

#### Acceptance Criteria

1. THE V4_Frontend_Stack SHALL define the GetEvalReport_Lambda as a SAM Function resource with Python 3.12 runtime, `handler.lambda_handler` entry point, 30-second timeout, 256MB memory, and SnapStart enabled (`SnapStart: ApplyOn: PublishedVersions`)
2. THE GetEvalReport_Lambda SHALL have a published version and a `live` alias, with the API Gateway integration targeting the alias ARN (not the function ARN)
3. THE GetEvalReport_Lambda SHALL receive the Eval_Reports_Table name via an environment variable
4. THE GetEvalReport_Lambda SHALL have an IAM policy granting `dynamodb:GetItem` on the Eval_Reports_Table ARN
4. WHEN the GetEvalReport_Lambda receives a GET request to `/eval/report` with `agent` and `ts` query parameters, THE GetEvalReport_Lambda SHALL get the item from the Eval_Reports_Table with PK=`AGENT#{agent}` and SK=`{ts}`
5. WHEN the retrieved item has `case_results_split` set to true, THE GetEvalReport_Lambda SHALL fetch the companion item with SK=`{ts}#CASES` and reassemble the `case_results` field into the response
6. WHEN either `agent` or `ts` query parameter is missing, THE GetEvalReport_Lambda SHALL return HTTP 400 with a JSON error message
7. WHEN no item is found for the given PK and SK, THE GetEvalReport_Lambda SHALL return HTTP 404 with a JSON error message
8. THE GetEvalReport_Lambda SHALL remove the `PK`, `SK`, and `case_results_split` fields from the response before returning
9. THE GetEvalReport_Lambda SHALL convert DynamoDB Decimal values to JSON-compatible float or int values in the response
10. IF the DynamoDB GetItem fails, THEN THE GetEvalReport_Lambda SHALL return HTTP 500 with a JSON error message and log the error

### Requirement 4: API Gateway Routes with JWT Authorization

**User Story:** As a platform operator, I want the eval API endpoints protected by the existing Cognito JWT authorizer, so that only authenticated users can access eval data.

#### Acceptance Criteria

1. THE V4_Frontend_Stack SHALL define an API Gateway V2 Route for `GET /eval/reports` with JWT authorization using the existing CognitoAuthorizer, targeting the ListEvalReports_Lambda via an AWS_PROXY integration with PayloadFormatVersion 2.0
2. THE V4_Frontend_Stack SHALL define an API Gateway V2 Route for `GET /eval/report` with JWT authorization using the existing CognitoAuthorizer, targeting the GetEvalReport_Lambda via an AWS_PROXY integration with PayloadFormatVersion 2.0
3. THE V4_Frontend_Stack SHALL define Lambda Permission resources allowing `apigateway.amazonaws.com` to invoke each Lambda function, scoped to the respective route ARN
4. THE V4_Frontend_Stack SHALL accept the Eval_Reports_Table name and ARN as parameters (sourced from the Persistent_Resources_Stack outputs)

### Requirement 5: Frontend API Client Switching

**User Story:** As a dashboard user, I want the eval dashboard to work both in local development (Vite proxy) and in production (API Gateway with auth), so that developers can iterate locally and the deployed dashboard works behind CloudFront.

#### Acceptance Criteria

1. WHILE running in development mode (`import.meta.env.DEV` is true), THE Dashboard_Client SHALL call `/api/eval/reports` and `/api/eval/report` without an Authorization header (using the Vite_Proxy)
2. WHILE running in production mode (`import.meta.env.DEV` is false), THE Dashboard_Client SHALL call `{VITE_V4_API_URL}/eval/reports` and `{VITE_V4_API_URL}/eval/report` with an `Authorization: Bearer {id_token}` header using the Cognito ID token from the AuthContext
3. THE Dashboard_Client SHALL preserve the existing `agent` and `ts` query parameter interface for both modes
4. THE Vite_Proxy SHALL remain unchanged and continue to serve dev-mode requests using local AWS credentials

### Requirement 6: Frontend Build and Deployment

**User Story:** As a platform operator, I want to build the frontend, sync it to S3, and invalidate the CloudFront cache, so that the production dashboard reflects the latest code.

#### Acceptance Criteria

1. WHEN the frontend is built with `npm run build`, THE Dashboard_Client SHALL embed the `VITE_V4_API_URL` environment variable into the production bundle
2. WHEN the built assets are synced to the S3 bucket via `aws s3 sync`, THE Persistent_Resources_Stack S3 bucket SHALL serve the assets through CloudFront with OAC (the existing private bucket + CloudFront pattern)
3. WHEN a CloudFront cache invalidation is issued for `/*`, THE CloudFront distribution SHALL serve the updated assets within the invalidation propagation time

### Requirement 7: SnapStart for All V4 Lambda Functions

**User Story:** As a platform operator, I want all v4 Lambda functions to use SnapStart for faster cold starts, so that the dashboard and other API endpoints respond quickly on first invocation.

#### Acceptance Criteria

1. THE V4_Frontend_Stack SHALL enable SnapStart (`SnapStart: ApplyOn: PublishedVersions`) on the existing PresignedUrlFunction and ListPredictionsFunction, in addition to the new ListEvalReports_Lambda and GetEvalReport_Lambda
2. EACH Lambda function with SnapStart enabled SHALL have a published version resource and a `live` alias resource
3. ALL API Gateway V2 Integration resources SHALL target the Lambda alias ARN (not the function ARN)
4. ALL Lambda Permission resources SHALL reference the alias ARN and include `DependsOn` for the alias resource to prevent CloudFormation race conditions (per Decision 17)
5. THE VerificationScannerFunction in the verification-scanner stack SHALL also have SnapStart enabled with a published version and `live` alias, with the EventBridge target updated to invoke the alias ARN
