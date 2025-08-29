# Verification Lambda Deployment Implementation Plan

**Date**: August 28, 2025  
**Status**: 🚧 Ready to Implement  
**Goal**: Connect existing verification system code to deployed AWS Lambda infrastructure

## Current State Analysis

### ✅ Already Deployed in AWS (via SAM template)
- **`VerificationFunction`** - Lambda function configured
- **EventBridge Schedule** - Every 15 minutes trigger
- **S3 Bucket** - `VerificationLogsBucket` for audit logs
- **SNS Topic** - `VerificationNotificationTopic` for emails
- **IAM Permissions** - DynamoDB, S3, SNS, Bedrock access

### ❌ Missing Components
- **Handler Code** - `handlers/verification/app.py` doesn't exist
- **Code Bridge** - No connection between `/verification` folder and Lambda
- **Dependencies** - Verification requirements not in Lambda package

## Implementation Steps

### Step 1: Create Lambda Handler
**File**: `backend/calledit-backend/handlers/verification/app.py`
```python
#!/usr/bin/env python3
import sys
import os
sys.path.append('/opt/python')  # Lambda layer path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../verification'))

from verify_predictions import PredictionVerificationRunner

def lambda_handler(event, context):
    runner = PredictionVerificationRunner()
    stats = runner.run_verification_batch()
    return {
        'statusCode': 200,
        'body': stats
    }
```

### Step 2: Copy Verification Code to Handler
**Action**: Copy `/verification` folder contents to `handlers/verification/`
```bash
cp -r verification/* backend/calledit-backend/handlers/verification/
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
sam build
sam deploy --no-confirm-changeset
```

## Expected Results

### After Deployment
- **Automated Verification**: Every 15 minutes
- **S3 Audit Logs**: Verification results logged
- **Email Notifications**: TRUE predictions trigger emails
- **CloudWatch Logs**: Verification processing logs

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
- ✅ Verification processes pending predictions
- ✅ S3 logs contain verification results
- ✅ Email notifications sent for TRUE predictions
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
**Dependencies**: Strands agents library, AWS credentials