# Requirements Document

## Introduction

The CalledIt backend has SnapStart enabled on 6 Lambda functions (MakeCallStreamFunction, LogCall, ListPredictions, AuthTokenFunction, VerificationFunction, NotificationManagementFunction) via Spec 4 (lambda-cold-start-optimization). Two WebSocket lifecycle functions — ConnectFunction and DisconnectFunction — were excluded from Spec 4 due to risk concerns around adding `AutoPublishAlias` to WebSocket lifecycle handlers. The alias integration pattern is now proven on MakeCallStreamFunction (alias ARN in IntegrationUri + separate alias Lambda permission), and a reference implementation from the DontSpin project confirms SnapStart works with WebSocket connect/disconnect functions. This feature adds SnapStart to ConnectFunction and DisconnectFunction for consistency across the stack.

## Glossary

- **SnapStart**: An AWS Lambda feature that snapshots the initialized execution environment after module-level code runs and restores from that snapshot on cold starts, reducing initialization time. Enabled via `SnapStart: { ApplyOn: PublishedVersions }` in SAM.
- **AutoPublishAlias**: A SAM property that automatically publishes a new Lambda version on each deployment and updates the specified alias (e.g., `live`). Required for SnapStart to function.
- **ConnectFunction**: The Lambda function that handles WebSocket `$connect` events. Located at `backend/calledit-backend/handlers/websocket/connect.py`. Imports only `json` (8 lines of code).
- **DisconnectFunction**: The Lambda function that handles WebSocket `$disconnect` events. Located at `backend/calledit-backend/handlers/websocket/disconnect.py`. Imports only `json` (8 lines of code).
- **ConnectIntegration**: The API Gateway V2 integration resource that routes `$connect` events to ConnectFunction. Currently references the unqualified function ARN (`${ConnectFunction.Arn}`).
- **DisconnectIntegration**: The API Gateway V2 integration resource that routes `$disconnect` events to DisconnectFunction. Currently references the unqualified function ARN (`${DisconnectFunction.Arn}`).
- **SAM_Template**: The AWS SAM CloudFormation template at `backend/calledit-backend/template.yaml` that defines all Lambda functions and infrastructure.
- **Alias_ARN**: The qualified function ARN that includes the alias suffix (e.g., `${ConnectFunction.Arn}:live`). Required in IntegrationUri so that API Gateway invokes the published version with SnapStart enabled, not `$LATEST`.
- **Alias_Permission**: A separate `AWS::Lambda::Permission` resource that grants API Gateway permission to invoke the alias-qualified function. Required because the existing unqualified permission does not cover alias invocations.

## Requirements

### Requirement 1: Enable SnapStart on ConnectFunction

**User Story:** As a developer, I want to enable SnapStart on the ConnectFunction, so that the WebSocket `$connect` handler is consistent with the rest of the SnapStart-enabled stack.

#### Acceptance Criteria

1. WHEN the SAM template is deployed, THE SAM_Template SHALL include `SnapStart: { ApplyOn: PublishedVersions }` on the ConnectFunction resource.
2. THE SAM_Template SHALL include `AutoPublishAlias: live` on the ConnectFunction resource (required for SnapStart to function).
3. WHEN SnapStart is enabled, THE ConnectFunction SHALL continue to return a 200 status code with a JSON body containing `{"message": "Connected"}` for valid `$connect` events.
4. THE ConnectFunction SHALL retain the existing `execute-api:ManageConnections` IAM policy without modification.

### Requirement 2: Enable SnapStart on DisconnectFunction

**User Story:** As a developer, I want to enable SnapStart on the DisconnectFunction, so that the WebSocket `$disconnect` handler is consistent with the rest of the SnapStart-enabled stack.

#### Acceptance Criteria

1. WHEN the SAM template is deployed, THE SAM_Template SHALL include `SnapStart: { ApplyOn: PublishedVersions }` on the DisconnectFunction resource.
2. THE SAM_Template SHALL include `AutoPublishAlias: live` on the DisconnectFunction resource (required for SnapStart to function).
3. WHEN SnapStart is enabled, THE DisconnectFunction SHALL continue to return a 200 status code with a JSON body containing `{"message": "Disconnected"}` for valid `$disconnect` events.
4. THE DisconnectFunction SHALL retain the existing `execute-api:ManageConnections` IAM policy without modification.

### Requirement 3: Update WebSocket Integration URIs to Use Alias ARNs

**User Story:** As a developer, I want the WebSocket integrations to invoke the alias-qualified function ARNs, so that API Gateway routes requests through the published version with SnapStart enabled instead of `$LATEST`.

#### Acceptance Criteria

1. THE ConnectIntegration IntegrationUri SHALL reference the alias ARN using `${ConnectFunction.Arn}:live` instead of the unqualified `${ConnectFunction.Arn}`.
2. THE DisconnectIntegration IntegrationUri SHALL reference the alias ARN using `${DisconnectFunction.Arn}:live` instead of the unqualified `${DisconnectFunction.Arn}`.
3. WHEN the alias-qualified IntegrationUri is deployed, THE WebSocket API SHALL successfully route `$connect` events to the ConnectFunction published version.
4. WHEN the alias-qualified IntegrationUri is deployed, THE WebSocket API SHALL successfully route `$disconnect` events to the DisconnectFunction published version.

### Requirement 4: Add Alias Lambda Permissions

**User Story:** As a developer, I want alias-specific Lambda permissions for ConnectFunction and DisconnectFunction, so that API Gateway is authorized to invoke the alias-qualified function ARNs.

#### Acceptance Criteria

1. THE SAM_Template SHALL include a new `AWS::Lambda::Permission` resource for ConnectFunction that grants `lambda:InvokeFunction` to `apigateway.amazonaws.com` on the alias-qualified FunctionName `${ConnectFunction}:live`.
2. THE SAM_Template SHALL include a new `AWS::Lambda::Permission` resource for DisconnectFunction that grants `lambda:InvokeFunction` to `apigateway.amazonaws.com` on the alias-qualified FunctionName `${DisconnectFunction}:live`.
3. THE ConnectFunction alias permission SourceArn SHALL scope to the `$connect` route: `arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${WebSocketApi}/*/$connect`.
4. THE DisconnectFunction alias permission SourceArn SHALL scope to the `$disconnect` route: `arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${WebSocketApi}/*/$disconnect`.
5. THE existing unqualified ConnectFunctionPermission and DisconnectFunctionPermission resources SHALL remain unchanged (they cover `$LATEST` invocations as a fallback).

### Requirement 5: Validate WebSocket Connectivity After Deployment

**User Story:** As a developer, I want to verify that WebSocket connections work correctly after enabling SnapStart, so that I can confirm the changes did not break the WebSocket lifecycle.

#### Acceptance Criteria

1. WHEN the SnapStart-enabled stack is deployed, THE WebSocket API SHALL accept new `$connect` requests and return a successful connection response.
2. WHEN a connected WebSocket client disconnects, THE WebSocket API SHALL process the `$disconnect` event and return a successful response.
3. WHEN a connected WebSocket client sends a `makecall` action, THE WebSocket API SHALL route the message to MakeCallStreamFunction and stream results back to the client (end-to-end validation).
4. IF the deployment fails due to SnapStart or alias configuration, THEN THE CloudFormation stack SHALL roll back to the previous working version automatically.

### Requirement 6: Ensure Deployment Rollback Safety

**User Story:** As a developer, I want the SnapStart changes to be safely reversible, so that I can roll back if WebSocket connectivity breaks.

#### Acceptance Criteria

1. THE SAM_Template changes SHALL be limited to SnapStart-related additions (SnapStart property, AutoPublishAlias, alias IntegrationUri, alias permissions) with no unrelated resource modifications.
2. WHEN rolling back, THE developer SHALL revert the SAM_Template to the previous version (remove SnapStart, AutoPublishAlias, revert IntegrationUri to unqualified ARN, remove alias permissions) and redeploy.
3. THE rollback procedure SHALL restore WebSocket functionality to the pre-change state within a single `sam deploy` operation.
4. THE ConnectFunction and DisconnectFunction handler code SHALL require zero modifications for SnapStart enablement (no runtime hooks needed because the functions import only `json` and hold no perishable resources).
