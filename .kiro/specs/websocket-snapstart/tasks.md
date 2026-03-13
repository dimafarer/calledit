# Tasks

## Task 1: Add SnapStart and AutoPublishAlias to ConnectFunction and DisconnectFunction

- [x] 1.1 Add `AutoPublishAlias: live` and `SnapStart: { ApplyOn: PublishedVersions }` to ConnectFunction in `backend/calledit-backend/template.yaml`
- [x] 1.2 Add `AutoPublishAlias: live` and `SnapStart: { ApplyOn: PublishedVersions }` to DisconnectFunction in `backend/calledit-backend/template.yaml`

## Task 2: Update Integration URIs to alias ARNs

- [x] 2.1 Update ConnectIntegration IntegrationUri from `${ConnectFunction.Arn}/invocations` to `${ConnectFunction.Arn}:live/invocations`
- [x] 2.2 Update DisconnectIntegration IntegrationUri from `${DisconnectFunction.Arn}/invocations` to `${DisconnectFunction.Arn}:live/invocations`

## Task 3: Add alias Lambda permissions

- [x] 3.1 Add ConnectFunctionAliasPermission resource with FunctionName `${ConnectFunction}:live`, scoped to `$connect` route
- [x] 3.2 Add DisconnectFunctionAliasPermission resource with FunctionName `${DisconnectFunction}:live`, scoped to `$disconnect` route

## Task 4: Write template validation tests

- [x] 4.1 Write pytest tests that parse template.yaml and verify SnapStart + AutoPublishAlias on both functions, alias URIs on both integrations, alias permissions exist with correct scoping, existing permissions preserved, and IAM policies unchanged
- [x] 4.2 Write handler unit tests confirming connect and disconnect handlers return expected responses

## Task 5: Build and deploy

- [x] 5.1 Run `sam build` and verify no build errors
- [x] 5.2 Run `sam deploy` and verify CloudFormation stack update succeeds
- [x] 5.3 Validate WebSocket connectivity (connect, send makecall, disconnect) and confirm SnapStart is active via CloudWatch restoreDurationMs logs
