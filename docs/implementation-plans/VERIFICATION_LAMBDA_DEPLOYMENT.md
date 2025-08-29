# Verification System Lambda Deployment Implementation Plan

**Date**: August 28, 2025  
**Status**: ✅ Successfully Deployed  
**Goal**: Deploy the automated verification system (core app functionality #2) to AWS Lambda

## Application Context

CalledIt has **2 core functionalities**:
1. **Prediction Creation**: Convert natural language → structured verifiable predictions with 5-category classification
2. **Verification System**: Automated verification of predictions to determine TRUE/FALSE status ← **THIS PLAN**

The verification system is already built in `/verification` folder but needs deployment to AWS Lambda infrastructure.

## Current State Analysis

### ✅ Already Deployed in AWS (via SAM template)
- **`VerificationFunction`** - Lambda function configured
- **EventBridge Schedule** - Every 15 minutes trigger
- **S3 Bucket** - `VerificationLogsBucket` for audit logs
- **SNS Topic** - `VerificationNotificationTopic` for emails
- **IAM Permissions** - DynamoDB, S3, SNS, Bedrock access

### ✅ Deployed Components
- **Handler Code** - `handlers/verification/app.py` created and deployed
- **Code Bridge** - Verification code copied to Lambda handler
- **Dependencies** - Strands agents and boto3 installed in Lambda package
- **Function ARN** - `arn:aws:lambda:REGION:ACCOUNT:function:called-it-verification`

## Implementation Steps

### Step 1: Copy Verification Code to Handler
**Action**: Copy `/verification` folder contents to `handlers/verification/`
```bash
cp -r verification/* backend/calledit-backend/handlers/verification/
```

### Step 2: Create Lambda Handler
**File**: `backend/calledit-backend/handlers/verification/app.py`
```python
#!/usr/bin/env python3
from verify_predictions import PredictionVerificationRunner

def lambda_handler(event, context):
    runner = PredictionVerificationRunner()
    stats = runner.run_verification_batch()
    return {
        'statusCode': 200,
        'body': stats
    }
```

### Step 3: Update Requirements
**File**: `backend/calledit-backend/handlers/verification/requirements.txt`
```
strands-agents>=0.1.0
strands-agents-tools>=0.1.0
boto3>=1.34.0
```

### Step 4: Verify SAM Template (Already Correct)
**File**: `backend/calledit-backend/template.yaml`
- ✅ `VerificationFunction` points to `handlers/verification/`
- ✅ EventBridge schedule: `rate(15 minutes)`
- ✅ All required permissions configured

### Step 5: Deploy
```bash
cd backend/calledit-backend
source ../../venv/bin/activate  # Use project virtual environment
sam build
sam deploy --no-confirm-changeset
```

## Expected Results

### After Deployment
- **Automated Verification**: Every 15 minutes processes ALL pending predictions
- **5-Category Routing**: Handles agent_verifiable, current_tool_verifiable, strands_tool_verifiable, api_tool_verifiable, human_verifiable_only
- **S3 Audit Logs**: Verification results logged with structured JSON
- **Email Notifications**: TRUE predictions trigger SNS emails
- **Frontend Integration**: Real-time verification status updates with confidence scores
- **Tool Gap Detection**: Automatic MCP tool suggestions for missing capabilities

### Validation Commands
```bash
# Check function exists
aws lambda get-function --function-name called-it-verification

# Check EventBridge rule
aws events list-rules --name-prefix called-it

# Test manual invocation
aws lambda invoke --function-name called-it-verification output.json
```

## File Structure After Implementation
```
backend/calledit-backend/handlers/verification/
├── app.py                    # Lambda handler entry point
├── requirements.txt          # Dependencies
├── verify_predictions.py     # Main verification runner
├── verification_agent.py     # Strands verification agent
├── ddb_scanner.py           # DynamoDB scanner
├── verification_result.py   # Result structures
├── email_notifier.py        # SNS email notifications
├── s3_logger.py             # S3 audit logging
├── status_updater.py        # DynamoDB status updates
└── mock_strands.py          # Mock for testing
```

## Success Criteria
- ✅ Lambda function deploys successfully
- ✅ EventBridge triggers every 15 minutes
- ✅ Verification processes pending predictions across all 5 categories
- ✅ S3 logs contain verification results with tool gap analysis
- ✅ Email notifications sent for TRUE predictions ("crying" system)
- ✅ Frontend displays real-time verification status updates
- ✅ CloudWatch shows successful executions

## Rollback Plan
If deployment fails:
1. Revert SAM template changes
2. Redeploy previous version
3. Check CloudWatch logs for errors
4. Fix issues and retry

---

**Implementation Time**: ~30 minutes  
**Risk Level**: Low (infrastructure already deployed)  
**Dependencies**: Strands agents library, AWS credentials, project virtual environment