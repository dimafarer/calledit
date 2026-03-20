# Implementation Plan: Verification Teardown & Docker Lambda

## Overview

Pure infrastructure spec — remove old verification system resources from SAM template, archive old handler code, and switch MakeCallStreamFunction to a Docker-based Lambda image with Python 3.12 + Node.js. No application logic changes. The prediction pipeline must produce identical results after deployment.

## Tasks

- [x] 1. Remove old verification resources from SAM template
  - [x] 1.1 Remove VerificationFunction, VerificationLogsBucket, VerificationNotificationTopic, and NotificationManagementFunction resource blocks from `backend/calledit-backend/template.yaml`
    - Remove the 4 resource definitions and all their sub-properties (Events, Policies, Environment, etc.)
    - Remove the 3 verification-related Outputs: `VerificationFunctionArn`, `VerificationLogsBucket`, `VerificationNotificationTopic`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 1.2 Remove MakeCallStreamFunctionAliasPermission and update MakeCallStreamIntegration
    - Remove the `MakeCallStreamFunctionAliasPermission` resource (no more `:live` alias for MakeCallStreamFunction)
    - Remove `DependsOn: MakeCallStreamFunctionAliaslive` from `MakeCallStreamIntegration`
    - Update `MakeCallStreamIntegration` IntegrationUri to use unqualified function ARN: remove `:live` suffix from the `!Sub` expression
    - Remove the old comment about alias ARN and SnapStart on the IntegrationUri
    - _Requirements: 1.6, 1.7_

  - [x] 1.3 Remove SnapStart and AutoPublishAlias from MakeCallStreamFunction
    - Remove `AutoPublishAlias: live` from MakeCallStreamFunction Properties
    - Remove `SnapStart: ApplyOn: PublishedVersions` from MakeCallStreamFunction Properties
    - Add a comment explaining SnapStart is not supported for container image Lambdas
    - _Requirements: 4.1, 4.2_

- [ ] 2. Archive old verification handler code
  - [ ] 2.1 Move verification handler files to archive
    - Copy all 19 files from `backend/calledit-backend/handlers/verification/` to `docs/historical/verification-v1/`
    - Copy `backend/calledit-backend/handlers/notification_management/app.py` and `snapstart_hooks.py` to `docs/historical/verification-v1/notification_management/`
    - Copy `backend/calledit-backend/handlers/strands_make_call/tool_registry.py` to `docs/historical/verification-v1/tool_registry.py`
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 2.2 Create archive README
    - Create `docs/historical/verification-v1/README.md` documenting what the old verification system did, what files it contained, why it was replaced, and what replaced it
    - Reference Decision 18 (3 verifiability categories), Decision 19 (DDB tool registry), Decision 20 (web search as first tool), and Backlog item 7 (verification pipeline via MCP tools)
    - _Requirements: 2.4, 2.5_

  - [ ] 2.3 Remove original source files
    - Delete `backend/calledit-backend/handlers/verification/` directory
    - Delete `backend/calledit-backend/handlers/notification_management/` directory
    - Delete `backend/calledit-backend/handlers/strands_make_call/tool_registry.py`
    - _Requirements: 2.6, 2.7_

- [ ] 3. Checkpoint — Verify teardown is clean
  - Ensure the SAM template has no dangling `!Ref` or `!GetAtt` references to removed resources
  - Ensure all non-verification resources are retained unchanged
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Create Dockerfile and switch MakeCallStreamFunction to Docker Lambda
  - [ ] 4.1 Create Dockerfile
    - Create `backend/calledit-backend/Dockerfile` based on `public.ecr.aws/lambda/python:3.12`
    - Install Node.js LTS (v20.x) via pre-built binary tarball
    - Copy `handlers/strands_make_call/requirements.txt` and install Python deps
    - Copy `handlers/strands_make_call/` source code to `LAMBDA_TASK_ROOT`
    - Set CMD to `strands_make_call_graph.lambda_handler`
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ] 4.2 Update MakeCallStreamFunction to PackageType: Image
    - Replace `CodeUri`, `Handler`, `Runtime` with `PackageType: Image`
    - Add `Metadata` section with `DockerTag: python3.12-nodejs-v1`, `DockerContext: .`, `Dockerfile: Dockerfile`
    - Retain `Timeout: 300`, `MemorySize: 512`, all `PROMPT_VERSION_*` env vars, and all IAM policies
    - _Requirements: 3.5, 3.6_

- [ ] 5. Checkpoint — Verify Docker infrastructure
  - Ensure SAM template is valid YAML with correct resource references
  - Ensure Dockerfile exists at the correct path with expected content
  - Ensure all tests pass, ask the user if questions arise.

- [ ]* 6. Write tests for verification teardown and Docker switch
  - [ ]* 6.1 Write property test for SAM template reference consistency
    - **Property 1: SAM template reference consistency** — For any `!Ref` or `!GetAtt` target in the template, the referenced logical resource name must exist in the Resources section
    - **Validates: Requirements 1.6**
    - Test file: `tests/strands_make_call/test_verification_teardown_docker.py`

  - [ ]* 6.2 Write property test for no hard import dependencies on removed modules
    - **Property 2: Pipeline code has no import dependencies on removed modules** — For any Python source file in `handlers/strands_make_call/`, all import statements must not hard-depend on `verification`, `notification_management`, or `tool_registry`
    - **Validates: Requirements 5.4**
    - Test file: `tests/strands_make_call/test_verification_teardown_docker.py`

  - [ ]* 6.3 Write unit tests for resource removal and Docker configuration
    - Verify removed resources (VerificationFunction, VerificationLogsBucket, VerificationNotificationTopic, NotificationManagementFunction) are not in template Resources
    - Verify removed outputs are not in template Outputs
    - Verify MakeCallStreamFunction has `PackageType: Image`, no `Runtime`/`Handler`/`CodeUri`, no `SnapStart`, no `AutoPublishAlias`
    - Verify MakeCallStreamFunction retains `Timeout: 300`, `MemorySize: 512`, env vars, policies
    - Verify Metadata section has `DockerTag`, `DockerContext`, `Dockerfile`
    - Verify MakeCallStreamIntegration uses unqualified function ARN (no `:live`)
    - Verify MakeCallStreamFunctionAliasPermission is removed
    - Verify Dockerfile exists with correct base image, Node.js install, and CMD
    - Verify archive files exist at `docs/historical/verification-v1/`
    - Verify source directories are removed
    - _Requirements: 1.1–1.7, 2.1–2.7, 3.1–3.6, 4.1–4.2, 5.1, 5.4_

- [ ] 7. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- This is a pure infrastructure spec — no application logic changes
- `prediction_graph.py` already has a try/except fallback for `tool_registry` import — no code change needed
- Manual validation (sam build, sam deploy, WebSocket testing) is handled by the user post-implementation
- ConnectFunction and DisconnectFunction retain their SnapStart + alias configuration unchanged
