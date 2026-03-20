# Requirements Document

## Introduction

Remove the old verification system infrastructure and code from the CalledIt prediction pipeline, and switch the MakeCallStreamFunction Lambda from a zip-based Python 3.12 runtime to a Docker-based Lambda image containing both Python 3.12 and Node.js. This is Spec A1 of a split from the combined "mcp-verification-foundation" spec — it covers pure infrastructure changes with zero application logic modifications. The prediction pipeline must work identically after deployment.

The old verification system (`handlers/verification/`) was a primitive attempt at automated prediction verification: an EventBridge rule triggered a Lambda every 15 minutes to scan DynamoDB for pending predictions and verify them using a Strands agent with a datetime tool and reasoning. It used a DynamoDB tool registry (`TOOL#{tool_id}` records) with only `web_search` registered, and a custom `@tool` DuckDuckGo wrapper. The system never worked well and is being replaced by MCP-based tool discovery (Spec A2). The Docker Lambda is needed because MCP servers are npm packages invoked via `npx`, which requires Node.js — not available in the standard `python3.12` Lambda runtime.

## Glossary

- **Old_Verification_System**: The `handlers/verification/` directory containing `app.py`, `verification_agent.py`, `verify_predictions.py`, `ddb_scanner.py`, `status_updater.py`, `s3_logger.py`, `email_notifier.py`, `verification_result.py`, `web_search_tool.py`, `seed_web_search_tool.py`, `error_handling.py`, `cleanup_predictions.py`, `inspect_data.py`, `mock_strands.py`, `modernize_data.py`, `recategorize.py`, `test_scanner.py`, `test_verification_result.py`, and `requirements.txt`, plus the SAM template resources VerificationFunction, VerificationLogsBucket, VerificationNotificationTopic, and the EventBridge schedule
- **SAM_Template**: The `backend/calledit-backend/template.yaml` that defines all Lambda functions and infrastructure resources
- **MakeCallStreamFunction**: The Lambda function running the prediction pipeline (Parser → Categorizer → VB → Review graph), currently using `Runtime: python3.12`
- **NotificationManagementFunction**: The Lambda function for SNS email subscription management, which depends on the VerificationNotificationTopic being removed
- **Docker_Lambda_Image**: A container image based on AWS Lambda Python 3.12 base image, extended with Node.js runtime to support `npx` subprocess execution for MCP servers (Spec A2)
- **Tool_Registry**: The `tool_registry.py` module in `handlers/strands_make_call/` that reads `TOOL#` records from DynamoDB — being archived as part of the old verification system cleanup
- **SnapStart**: AWS Lambda SnapStart for Java/Python that caches the Lambda INIT phase, reducing cold start latency. Must continue working with the Docker-based Lambda image

## Requirements

### Requirement 1: Remove Old Verification Resources from SAM Template

**User Story:** As a DevOps engineer, I want the old verification infrastructure removed from the SAM template, so that there are no orphaned resources running in production.

#### Acceptance Criteria

1. THE SAM_Template SHALL remove the `VerificationFunction` Lambda resource including its EventBridge schedule event (`ScheduledVerification`)
2. THE SAM_Template SHALL remove the `VerificationLogsBucket` S3 bucket resource
3. THE SAM_Template SHALL remove the `VerificationNotificationTopic` SNS topic resource
4. THE SAM_Template SHALL remove the `NotificationManagementFunction` Lambda resource, since the NotificationManagementFunction references the removed VerificationNotificationTopic via `!Ref` and `!GetAtt`
5. THE SAM_Template SHALL remove the `VerificationFunctionArn`, `VerificationLogsBucket`, and `VerificationNotificationTopic` entries from the Outputs section
6. THE SAM_Template SHALL contain zero `!Ref` or `!GetAtt` references to VerificationFunction, VerificationLogsBucket, VerificationNotificationTopic, or NotificationManagementFunction after the removal
7. THE SAM_Template SHALL retain all non-verification resources unchanged: CallitAPI, LogCall, ListPredictions, AuthTokenFunction, CognitoUserPool, UserPoolClient, UserPoolDomain, WebSocketApi, all WebSocket routes and integrations, ConnectFunction, DisconnectFunction, MakeCallStreamFunction, EvalReasoningTable, and all associated permissions


### Requirement 2: Archive Old Verification Handler Code

**User Story:** As a developer, I want the old verification handler code archived with documentation explaining what it was and why it was replaced, so that the project history is preserved.

#### Acceptance Criteria

1. THE old verification handler directory (`handlers/verification/`) SHALL be moved to `docs/historical/verification-v1/`
2. THE archive SHALL include all 19 files from the old verification handler: `app.py`, `verification_agent.py`, `verify_predictions.py`, `ddb_scanner.py`, `status_updater.py`, `s3_logger.py`, `email_notifier.py`, `verification_result.py`, `web_search_tool.py`, `seed_web_search_tool.py`, `error_handling.py`, `cleanup_predictions.py`, `inspect_data.py`, `mock_strands.py`, `modernize_data.py`, `recategorize.py`, `test_scanner.py`, `test_verification_result.py`, and `requirements.txt`
3. THE `tool_registry.py` module from `handlers/strands_make_call/` SHALL be archived to `docs/historical/verification-v1/tool_registry.py` with a header comment explaining it was replaced by MCP-native discovery
4. THE archive SHALL include a `README.md` documenting what the old verification system did, what files it contained, why it was replaced, and what replaced it
5. THE archive README SHALL reference Decision 18 (3 verifiability categories), Decision 19 (DDB tool registry), Decision 20 (web search as first tool), and Backlog item 7 (verification pipeline via MCP tools) as context for the replacement
6. WHEN the archive is complete, THE `handlers/verification/` directory SHALL no longer exist in the source tree
7. WHEN the archive is complete, THE `handlers/strands_make_call/tool_registry.py` file SHALL no longer exist in the source tree

### Requirement 3: Docker Lambda Image for MakeCallStreamFunction

**User Story:** As a DevOps engineer, I want the MakeCallStreamFunction switched from a zip-based Python runtime to a Docker-based Lambda image containing both Python 3.12 and Node.js, so that MCP servers (npm packages) can be invoked via `npx` subprocess in Spec A2.

#### Acceptance Criteria

1. THE project SHALL include a `Dockerfile` at `backend/calledit-backend/Dockerfile` that builds a Lambda container image based on the AWS Lambda Python 3.12 base image
2. THE Docker_Lambda_Image SHALL include Node.js runtime (LTS version) and npm, so that `npx` commands can execute MCP server packages
3. THE Docker_Lambda_Image SHALL copy the `handlers/strands_make_call/` source code and install Python dependencies from `handlers/strands_make_call/requirements.txt`
4. THE Docker_Lambda_Image SHALL set the CMD to the existing handler entry point: `strands_make_call_graph.lambda_handler`
5. THE SAM_Template SHALL change the MakeCallStreamFunction from `Runtime: python3.12` and `Handler:` and `CodeUri:` properties to `PackageType: Image` with a `Metadata` section specifying the Dockerfile path
6. THE SAM_Template SHALL retain the existing MakeCallStreamFunction configuration: `Timeout: 300`, `MemorySize: 512`, `AutoPublishAlias: live`, `SnapStart`, environment variables (`PROMPT_VERSION_PARSER`, `PROMPT_VERSION_CATEGORIZER`, `PROMPT_VERSION_VB`, `PROMPT_VERSION_REVIEW`), and all IAM policies
7. WHEN the Docker-based MakeCallStreamFunction is deployed, THE prediction pipeline SHALL produce identical results to the zip-based deployment for the same input

### Requirement 4: SnapStart Compatibility with Docker Lambda

**User Story:** As a DevOps engineer, I want to confirm that SnapStart continues to work with the Docker-based Lambda image, so that cold start performance is not degraded.

#### Acceptance Criteria

1. THE SAM_Template SHALL retain the `SnapStart: ApplyOn: PublishedVersions` configuration on the MakeCallStreamFunction after switching to `PackageType: Image`
2. IF SnapStart is not supported for container image Lambdas in the target region, THEN THE SAM_Template SHALL document this limitation as a comment and remove the SnapStart configuration rather than causing a deployment failure
3. WHEN the Docker-based Lambda cold-starts, THE MakeCallStreamFunction SHALL complete initialization (module imports, singleton creation) within the existing 300-second timeout

### Requirement 5: Pipeline Validation After Infrastructure Change

**User Story:** As a developer, I want to confirm the prediction pipeline works identically after the infrastructure changes, so that there are no regressions from removing old resources or switching to Docker.

#### Acceptance Criteria

1. WHEN the updated SAM template is deployed, THE deployment SHALL succeed without errors from missing resource references or invalid configurations
2. WHEN a WebSocket `makecall` message is sent after deployment, THE MakeCallStreamFunction SHALL execute the prediction graph (Parser → Categorizer → VB → Review) and return results via WebSocket
3. WHEN a WebSocket `clarify` message is sent after deployment, THE MakeCallStreamFunction SHALL execute the clarification flow and return results via WebSocket
4. THE removal of VerificationFunction, VerificationLogsBucket, VerificationNotificationTopic, and NotificationManagementFunction SHALL have zero impact on the prediction pipeline execution path
5. THE Docker-based Lambda SHALL successfully import all existing Python dependencies: `strands`, `boto3`, and all handler modules in `handlers/strands_make_call/`
