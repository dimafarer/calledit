# Handler Cleanup Analysis

**Date**: January 16, 2026  
**Purpose**: Identify and remove unused Lambda handlers before Strands refactoring

## Current Handlers in `/backend/calledit-backend/handlers/`

### ✅ ACTIVE HANDLERS (Keep - Currently Deployed)

1. **auth_token/** - `AuthTokenFunction`
   - Handler: `auth_token.lambda_handler`
   - Purpose: Cognito token exchange
   - Status: ✅ ACTIVE

2. **list_predictions/** - `ListPredictionsFunction`
   - Handler: `list_predictions.lambda_handler`
   - Purpose: Retrieve user predictions from DynamoDB
   - Status: ✅ ACTIVE

3. **write_to_db/** - `WriteToDBFunction` (LogCall)
   - Handler: `write_to_db.lambda_handler`
   - Purpose: Save predictions to DynamoDB
   - Status: ✅ ACTIVE

4. **strands_make_call/** - `MakeCallStreamFunction`
   - Handler: `strands_make_call_stream.lambda_handler`
   - Purpose: Main prediction processing with Strands + VPSS
   - Status: ✅ ACTIVE (Primary handler for refactoring)

5. **websocket/** - `ConnectFunction` & `DisconnectFunction`
   - Handlers: `connect.lambda_handler`, `disconnect.lambda_handler`
   - Purpose: WebSocket connection management
   - Status: ✅ ACTIVE

6. **verification/** - `VerificationFunction`
   - Handler: `app.lambda_handler`
   - Purpose: Automated verification system (EventBridge scheduled)
   - Status: ✅ ACTIVE

7. **notification_management/** - `NotificationManagementFunction`
   - Handler: `app.lambda_handler`
   - Purpose: SNS email subscription management ("crying" system)
   - Status: ✅ ACTIVE

### ❌ UNUSED HANDLERS (Delete - Not Deployed)

1. **hello_world/** - `HelloWorldFunction`
   - Handler: `app.lambda_handler`
   - Purpose: Demo/test function
   - Status: ❌ UNUSED (appears in template but not used in production)
   - **Action**: DELETE

2. **make_call/** - `MakeCallFunction`
   - Handler: `make_call.lambda_handler`
   - Purpose: Old non-streaming prediction handler (superseded by strands_make_call)
   - Status: ❌ UNUSED (replaced by MakeCallStreamFunction)
   - **Action**: DELETE

3. **prompt_bedrock/** - `PromptBedrockFunction`
   - Handler: `prompt_bedrock.lambda_handler`
   - Purpose: Direct Bedrock prompting (superseded by Strands)
   - Status: ❌ UNUSED (old implementation)
   - **Action**: DELETE

4. **prompt_agent/** - `PromptAgentFunction`
   - Handler: `agent.lambda_handler`
   - Purpose: Early agent implementation (superseded by Strands)
   - Status: ❌ UNUSED (old implementation)
   - **Action**: DELETE

5. **shared/** - Shared utilities folder
   - Contents: `error_handling.py`, `__init__.py`
   - Purpose: Shared error handling (duplicated in strands_make_call)
   - Status: ❌ UNUSED (not imported by active handlers)
   - **Action**: DELETE (error handling is in strands_make_call/error_handling.py)

## Dependency Check Results

✅ **Verification Complete**

**Active Code**: No active handlers import from unused handlers  
**Tests**: Only `tests/hello_world/` and `tests/make_call/` reference them  
**Documentation**: No critical docs reference them

## Cleanup Plan

### Phase 1: Remove from SAM Template

Remove function definitions from `template.yaml`:
- HelloWorldFunction
- MakeCallFunction
- PromptBedrockFunction
- PromptAgentFunction

### Phase 2: Delete Handler Directories

```bash
cd /home/wsluser/projects/calledit/backend/calledit-backend/handlers

# Delete unused handlers
rm -rf hello_world/
rm -rf make_call/
rm -rf prompt_bedrock/
rm -rf prompt_agent/
rm -rf shared/
```

### Phase 3: Delete Test Directories

```bash
cd /home/wsluser/projects/calledit/backend/calledit-backend/tests

# Delete tests for unused handlers
rm -rf hello_world/
rm -rf make_call/
```

### Phase 4: Update Documentation

Update any documentation that references deleted handlers.

## Risk Assessment

**Risk Level**: LOW

**Reasoning**:
- All deleted handlers are superseded by newer implementations
- No active production code references them
- They appear in template.yaml but are not critical to current functionality
- Easy to restore from git if needed

**Mitigation**:
- Commit changes before deletion
- Test deployment after cleanup
- Keep git history for reference

## Expected Benefits

1. **Cleaner Codebase**: Remove ~5 unused handler directories
2. **Faster Deployments**: Fewer functions to package and deploy
3. **Reduced Confusion**: Clear which handlers are active
4. **Easier Refactoring**: Focus only on active handlers for Strands improvements

## Verification Steps

After cleanup:
1. ✅ Run `sam validate` to check template
2. ✅ Run `sam build` to verify build succeeds
3. ✅ Deploy to AWS and test all active endpoints
4. ✅ Verify frontend still works correctly

## Timeline

- **Analysis**: Complete ✅
- **Cleanup**: 15 minutes
- **Testing**: 30 minutes
- **Total**: ~45 minutes

---

**Recommendation**: Proceed with cleanup. This is a straightforward task that will make the Strands refactoring cleaner and easier.
