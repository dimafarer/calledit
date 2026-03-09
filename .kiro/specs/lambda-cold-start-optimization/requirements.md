# Requirements Document

## Introduction

The CalledIt prediction verification app suffers from slow Lambda cold starts, particularly on the MakeCallStreamFunction which imports heavy dependencies (strands-agents, dateparser, pytz) and compiles a 4-agent graph at module level. This feature enables AWS Lambda SnapStart for Python to snapshot the initialized execution environment, eliminating the cold start penalty for module-level imports and graph compilation. SnapStart is free (no additional cost beyond normal Lambda pricing), making it the ideal solution for a demo/educational project with intermittent usage.

## Glossary

- **SnapStart**: An AWS Lambda feature that snapshots the initialized execution environment (after module-level code runs) and restores from that snapshot on cold starts, reducing initialization time to near zero. Enabled via `SnapStart: { ApplyOn: PublishedVersions }` in CloudFormation/SAM.
- **Cold_Start**: The initialization phase when Lambda creates a new execution environment — includes downloading code, starting the runtime, and executing module-level code (imports, singleton creation). For MakeCallStreamFunction, this includes importing strands-agents and compiling the 4-agent graph.
- **Warm_Start**: A Lambda invocation that reuses an existing execution environment — skips all initialization. The module-level singleton graph is already in memory.
- **SAM_Template**: The AWS SAM (Serverless Application Model) CloudFormation template at `backend/calledit-backend/template.yaml` that defines all Lambda functions and infrastructure.
- **MakeCallStreamFunction**: The primary Lambda function that runs the 4-agent prediction verification graph. It has the heaviest cold start due to strands-agents imports and graph compilation at module level.
- **Runtime_Hooks**: Python functions decorated with `@register_before_snapshot` or `@register_after_restore` from the `snapshot_restore_py` library (included in Python managed runtimes). These run before snapshot creation and after snapshot restoration respectively.
- **AutoPublishAlias**: A SAM property that automatically publishes a new Lambda version on each deployment and updates the specified alias. Required for SnapStart. MakeCallStreamFunction already has `AutoPublishAlias: live`.
- **Provisioned_Concurrency**: An alternative Lambda feature that keeps execution environments pre-initialized and warm. Eliminates cold starts but costs money even when idle (~$39/month for 1 instance at 512MB).
- **Singleton_Graph**: The module-level `prediction_graph` object in `prediction_graph.py` — compiled once at import time and reused across warm invocations. SnapStart snapshots this initialized state.

## Requirements

### Requirement 1: Enable SnapStart on MakeCallStreamFunction

**User Story:** As a developer, I want to enable SnapStart on the MakeCallStreamFunction, so that cold start latency is reduced without incurring additional cost.

#### Acceptance Criteria

1. WHEN the SAM template is deployed, THE SAM_Template SHALL include `SnapStart: { ApplyOn: PublishedVersions }` on the MakeCallStreamFunction resource.
2. THE MakeCallStreamFunction SHALL use Python 3.12 or later runtime (SnapStart requirement for Python support).
3. THE MakeCallStreamFunction SHALL retain the existing `AutoPublishAlias: live` property (required for SnapStart to function).
4. WHEN SnapStart is enabled, THE MakeCallStreamFunction SHALL snapshot the initialized execution environment including all module-level imports (strands-agents, dateparser, pytz, boto3) and the compiled Singleton_Graph.
5. IF the SAM deployment fails due to SnapStart configuration, THEN THE SAM_Template SHALL provide a clear error in the deployment output.

### Requirement 2: Implement Runtime Hooks for Stale Connection Handling

**User Story:** As a developer, I want runtime hooks to refresh stale connections after snapshot restore, so that the Lambda function operates correctly after resuming from a SnapStart snapshot.

#### Acceptance Criteria

1. WHEN the Lambda execution environment is restored from a SnapStart snapshot, THE MakeCallStreamFunction SHALL execute an `@register_after_restore` hook to refresh any stale boto3 client connections.
2. THE Runtime_Hooks module SHALL import `register_before_snapshot` and `register_after_restore` from the `snapshot_restore_py` library (included in Python managed runtimes, no pip install required).
3. WHEN the `@register_after_restore` hook executes, THE MakeCallStreamFunction SHALL re-initialize the API Gateway Management API client used for WebSocket message delivery.
4. THE `@register_after_restore` hook SHALL log a message at INFO level indicating that snapshot restoration completed and connections were refreshed.
5. THE `@register_before_snapshot` hook SHALL log a message at INFO level indicating that the snapshot is being created, for debugging and observability.
6. IF the `@register_after_restore` hook fails, THEN THE MakeCallStreamFunction SHALL log the error at ERROR level and allow the Lambda invocation to proceed (the handler creates a fresh boto3 client per invocation anyway).

### Requirement 3: Enable SnapStart on Secondary Lambda Functions

**User Story:** As a developer, I want to enable SnapStart on other Lambda functions in the stack, so that all functions benefit from reduced cold start times.

#### Acceptance Criteria

1. THE SAM_Template SHALL include `SnapStart: { ApplyOn: PublishedVersions }` on the LogCall function.
2. THE SAM_Template SHALL include `SnapStart: { ApplyOn: PublishedVersions }` on the ListPredictions function.
3. THE SAM_Template SHALL include `SnapStart: { ApplyOn: PublishedVersions }` on the VerificationFunction.
4. THE SAM_Template SHALL include `AutoPublishAlias: live` on each function that enables SnapStart (required dependency).
5. THE SAM_Template SHALL include `SnapStart: { ApplyOn: PublishedVersions }` on the NotificationManagementFunction.
6. WHEN SnapStart is enabled on secondary functions, THE secondary functions SHALL continue to operate with identical behavior to pre-SnapStart deployments.

**Risk Note — Versions and Aliases:**
Req 1 (MakeCallStreamFunction) is low-risk because `AutoPublishAlias: live` is already configured. Req 3 (secondary functions) carries higher risk: LogCall, ConnectFunction, DisconnectFunction, VerificationFunction, and NotificationManagementFunction do NOT currently have `AutoPublishAlias`. Adding it changes how API Gateway routes to the function (alias ARN instead of `$LATEST`). This is likely what caused the user's previous Provisioned Concurrency deployment failure. ListPredictions and AuthTokenFunction already have `AutoPublishAlias: live` so they are low-risk. Req 3 should be deployed separately from Req 1 so that any alias-related issues are isolated.

### Requirement 4: Validate SnapStart Compatibility with Singleton Pattern

**User Story:** As a developer, I want to verify that the module-level singleton graph pattern is compatible with SnapStart, so that the snapshotted graph works correctly after restore.

#### Acceptance Criteria

1. WHEN the MakeCallStreamFunction is restored from a SnapStart snapshot, THE Singleton_Graph SHALL be available in memory without re-compilation (the graph was compiled at module level before the snapshot was taken).
2. WHEN the MakeCallStreamFunction is restored from a SnapStart snapshot, THE Singleton_Graph SHALL produce identical prediction results to a non-SnapStart cold start for the same input.
3. THE MakeCallStreamFunction SHALL verify that the 4 agent nodes (parser, categorizer, verification_builder, review) are present in the restored Singleton_Graph.
4. IF the Singleton_Graph is corrupted or unavailable after snapshot restore, THEN THE MakeCallStreamFunction SHALL re-create the graph by calling `create_prediction_graph()` and log a warning.

### Requirement 5: Measure and Validate Cold Start Improvement

**User Story:** As a developer, I want to measure cold start times before and after enabling SnapStart, so that I can validate the improvement and document results.

#### Acceptance Criteria

1. WHEN measuring cold start performance, THE developer SHALL record the INIT duration from CloudWatch Logs for MakeCallStreamFunction before enabling SnapStart (baseline measurement).
2. WHEN measuring cold start performance after SnapStart, THE developer SHALL record the Restore duration from CloudWatch Logs for MakeCallStreamFunction (SnapStart replaces INIT with Restore).
3. THE SnapStart Restore duration for MakeCallStreamFunction SHALL be less than the pre-SnapStart INIT duration.
4. WHEN a SnapStart-enabled function is invoked after a period of inactivity, THE MakeCallStreamFunction SHALL complete the restore phase and begin handler execution within 2 seconds (compared to the current multi-second cold start from heavy imports).

### Requirement 6: Document Provisioned Concurrency as Alternative

**User Story:** As a developer, I want Provisioned Concurrency documented as a fallback option, so that I have a path forward if SnapStart proves insufficient for the use case.

#### Acceptance Criteria

1. THE documentation SHALL describe the SAM configuration for Provisioned Concurrency on MakeCallStreamFunction, including the `ProvisionedConcurrencyConfig` property on the `AutoPublishAlias`.
2. THE documentation SHALL state the estimated monthly cost of Provisioned Concurrency for 1 instance at 512MB memory (~$39/month).
3. THE documentation SHALL explain that Provisioned Concurrency is recommended only if SnapStart restore times exceed acceptable thresholds for the user experience.
4. THE documentation SHALL note that the user previously attempted Provisioned Concurrency and encountered a deployment failure, and provide the correct SAM syntax to avoid that issue.

### Requirement 7: Ensure Deployment Rollback Safety

**User Story:** As a developer, I want the SnapStart deployment to be safely reversible, so that I can roll back if SnapStart causes unexpected issues.

#### Acceptance Criteria

1. THE SAM_Template change to enable SnapStart SHALL be limited to adding the `SnapStart` property — no other resource modifications in the same deployment.
2. WHEN rolling back SnapStart, THE developer SHALL remove the `SnapStart` property from the SAM_Template and redeploy, restoring the function to standard cold start behavior.
3. THE SnapStart configuration SHALL preserve all existing MakeCallStreamFunction properties (MemorySize, Timeout, Policies, Environment, Handler, Runtime) without modification.
4. IF a SnapStart-enabled deployment fails, THEN THE CloudFormation stack SHALL roll back to the previous working version automatically (standard CloudFormation behavior).
