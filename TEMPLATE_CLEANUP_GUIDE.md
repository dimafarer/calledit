# SAM Template Cleanup Guide

After running `cleanup_unused_handlers.sh`, you need to remove the corresponding function definitions from `template.yaml`.

## Functions to Remove from template.yaml

### 1. HelloWorldFunction

**Location**: Lines ~35-60

```yaml
  HelloWorldFunction:
    Type: AWS::Serverless::Function 
    Properties:
      CodeUri: handlers/hello_world/
      # ... rest of definition
```

**Action**: Delete entire function definition

---

### 2. PromptBedrockFunction

**Location**: Lines ~62-90

```yaml
  PromptBedrockFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: handlers/prompt_bedrock/
      # ... rest of definition
```

**Action**: Delete entire function definition

---

### 3. PromptAgentFunction

**Location**: Lines ~91-108

```yaml
  PromptAgentFunction:
    Type: AWS::Serverless::Function 
    Properties:
      CodeUri: handlers/prompt_agent/
      # ... rest of definition
```

**Action**: Delete entire function definition

---

### 4. MakeCallFunction

**Location**: Lines ~142-159

```yaml
  MakeCallFunction:
    Type: AWS::Serverless::Function 
    Properties:
      CodeUri: handlers/make_call/
      # ... rest of definition
```

**Action**: Delete entire function definition

---

### 5. StrandsMakeCallFunction (OLD - not streaming)

**Location**: Lines ~108-141

```yaml
  StrandsMakeCallFunction:
    Type: AWS::Serverless::Function 
    Properties:
      CodeUri: handlers/strands_make_call/
      Handler: strands_make_call.lambda_handler  # OLD non-streaming handler
      # ... rest of definition
```

**Action**: Delete entire function definition (keep MakeCallStreamFunction which uses strands_make_call_stream.lambda_handler)

---

## Verification Steps

After editing template.yaml:

```bash
# 1. Validate template
sam validate

# 2. Check for syntax errors
grep -n "CodeUri: handlers/" template.yaml

# Expected remaining handlers:
# - handlers/auth_token/
# - handlers/list_predictions/
# - handlers/write_to_db/
# - handlers/strands_make_call/ (only MakeCallStreamFunction)
# - handlers/websocket/
# - handlers/verification/
# - handlers/notification_management/

# 3. Build to verify
sam build

# 4. Check build output
ls -la .aws-sam/build/
```

## Expected Remaining Functions

After cleanup, template.yaml should have these Lambda functions:

1. ✅ **AuthTokenFunction** - `handlers/auth_token/`
2. ✅ **WriteToDBFunction** - `handlers/write_to_db/`
3. ✅ **ListPredictionsFunction** - `handlers/list_predictions/`
4. ✅ **ConnectFunction** - `handlers/websocket/`
5. ✅ **DisconnectFunction** - `handlers/websocket/`
6. ✅ **MakeCallStreamFunction** - `handlers/strands_make_call/` (streaming handler)
7. ✅ **VerificationFunction** - `handlers/verification/`
8. ✅ **NotificationManagementFunction** - `handlers/notification_management/`

**Total**: 8 Lambda functions (down from 13)

## Quick Search Commands

```bash
# Find all function definitions
grep -n "Type: AWS::Serverless::Function" template.yaml

# Find all CodeUri references
grep -n "CodeUri: handlers/" template.yaml

# Count remaining functions
grep -c "Type: AWS::Serverless::Function" template.yaml
```

---

**Note**: Be careful to delete the entire function definition including all nested properties, policies, and events. Use proper YAML indentation awareness.
