# Automated Verification System

**Status**: ✅ Production Operational  
**Version**: v1.2.0+  
**Last Updated**: August 28, 2025

## Overview

The CalledIt Automated Verification System processes pending predictions every 15 minutes using Strands agents to intelligently verify predictions across all 5 verifiability categories.

## Architecture

```
EventBridge (15min) → Lambda → DynamoDB Scanner → Strands Agent → Verification Results
                                     ↓
S3 Audit Logs ← SNS Email Alerts ← Status Updates ← Tool Gap Detection
```

## Core Components

### `/verification/` Folder Structure
```
verification/
├── verify_predictions.py      # Main verification runner
├── verification_agent.py      # Strands agent for verification
├── ddb_scanner.py             # DynamoDB pending prediction scanner
├── verification_result.py     # Result structures and tool gap analysis
├── email_notifier.py          # SNS email notifications
├── s3_logger.py              # S3 audit logging
├── status_updater.py         # DynamoDB status updates
└── mock_strands.py           # Mock for testing without Strands
```

## Verification Categories & Routing

### 1. Agent Verifiable
- **Method**: Pure reasoning and established knowledge
- **Examples**: "The sun will rise tomorrow", "Water boils at 100°C"
- **Tools**: Reasoning only
- **Confidence**: High (0.9)

### 2. Current Tool Verifiable  
- **Method**: Current time tool verification
- **Examples**: "It's past 11 PM", "Today is Friday"
- **Tools**: `current_time`
- **Confidence**: High (0.85)

### 3. Strands Tool Verifiable
- **Method**: Mathematical/computational verification
- **Examples**: "15% compound interest on $1000 over 5 years exceeds $2000"
- **Tools**: `calculator`, `python_repl`
- **Confidence**: Very High (0.95)

### 4. API Tool Verifiable
- **Method**: Tool gap detection with MCP suggestions
- **Examples**: "Bitcoin will hit $100k", "It will rain tomorrow"
- **Status**: `TOOL_GAP` with MCP tool recommendations
- **Tools Suggested**: `mcp-weather`, `mcp-espn`, `mcp-yahoo-finance`

### 5. Human Verifiable Only
- **Method**: Mark as inconclusive
- **Examples**: "I will feel happy tomorrow"
- **Status**: `INCONCLUSIVE`
- **Reasoning**: Subjective assessment required

## Verification Results

### Status Types
- **`TRUE`**: Prediction verified as correct
- **`FALSE`**: Prediction verified as incorrect  
- **`INCONCLUSIVE`**: Cannot be determined objectively
- **`TOOL_GAP`**: Requires external API/tool not available
- **`ERROR`**: Verification process failed

### Data Structure
```json
{
  "prediction_id": "USER#123#PREDICTION#456",
  "status": "TRUE",
  "confidence": 0.95,
  "reasoning": "Verified through astronomical calculations",
  "verification_date": "2025-08-28T20:00:00Z",
  "tools_used": ["reasoning", "current_time"],
  "agent_thoughts": "Detailed agent analysis...",
  "processing_time_ms": 1250,
  "tool_gap": null
}
```

## Tool Gap Detection

### MCP Tool Suggestions
When predictions require external APIs, the system suggests specific MCP tools:

#### Weather Predictions
- **Missing Tool**: `weather_api`
- **MCP Suggestion**: `mcp-weather`
- **Priority**: HIGH
- **Specification**: `get_weather(location, date) -> weather_data`

#### Sports Predictions  
- **Missing Tool**: `sports_api`
- **MCP Suggestion**: `mcp-espn`
- **Priority**: MEDIUM
- **Specification**: `get_game_result(team1, team2, date) -> result`

#### Financial Predictions
- **Missing Tool**: `financial_api` 
- **MCP Suggestion**: `mcp-yahoo-finance`
- **Priority**: HIGH
- **Specification**: `get_stock_price(symbol, date) -> price_data`

## Operational Workflow

### 1. Scheduled Execution
- **Trigger**: EventBridge rule every 15 minutes
- **Lambda**: `VerificationFunction`
- **Timeout**: 5 minutes
- **Memory**: 512MB

### 2. Processing Pipeline
1. **Scan**: Query DynamoDB for `status=pending` predictions past verification date
2. **Route**: Determine verification method based on `verifiable_category`
3. **Verify**: Execute appropriate verification logic
4. **Update**: Store results in DynamoDB with confidence scores
5. **Notify**: Send email for `TRUE` verifications
6. **Log**: Audit trail to S3 with tool gap analysis

### 3. Email Notifications
- **Trigger**: Verification status = `TRUE`
- **Service**: SNS with HTML email templates
- **Content**: Prediction details, verification reasoning, confidence score
- **Subscription**: User-controlled via "Crying" system

## Monitoring & Metrics

### CloudWatch Metrics
- **Predictions Processed**: Count per batch
- **Verification Success Rate**: TRUE/FALSE ratio
- **Tool Gaps Identified**: Count by tool type
- **Processing Time**: Average verification duration
- **Error Rate**: Failed verifications

### S3 Audit Logs
```json
{
  "batch_id": "2025-08-28-20-00",
  "timestamp": "2025-08-28T20:00:00Z",
  "predictions_processed": 15,
  "results": {
    "verified_true": 3,
    "verified_false": 8,
    "inconclusive": 2,
    "tool_gaps": 2
  },
  "tool_gap_summary": {
    "weather_api": 1,
    "financial_api": 1
  }
}
```

## Configuration

### Environment Variables
- **`DYNAMODB_TABLE`**: `calledit-db`
- **`SNS_TOPIC_ARN`**: Email notification topic
- **`S3_BUCKET`**: Audit log storage
- **`BEDROCK_MODEL`**: `claude-3-sonnet-20241022`

### IAM Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Scan",
        "dynamodb:UpdateItem",
        "bedrock:InvokeModel",
        "sns:Publish",
        "s3:PutObject"
      ],
      "Resource": "*"
    }
  ]
}
```

## Testing

### Unit Tests
- **Location**: `verification/test_*.py`
- **Coverage**: Scanner, verification results, tool gap analysis
- **Mock Support**: `mock_strands.py` for testing without Strands

### Integration Tests  
- **Location**: `testing/integration/test_verification_pipeline.py`
- **Scope**: End-to-end verification workflow
- **Validation**: All 5 categories, tool gap detection, notifications

## Troubleshooting

### Common Issues

#### High Tool Gap Rate
- **Symptom**: Many predictions marked as `TOOL_GAP`
- **Solution**: Implement suggested MCP tools
- **Priority**: Weather and financial APIs first

#### Low Confidence Scores
- **Symptom**: Verification confidence < 0.7
- **Solution**: Review agent prompts and reasoning logic
- **Investigation**: Check agent thoughts in verification results

#### Email Delivery Issues
- **Symptom**: TRUE predictions not sending emails
- **Solution**: Check SNS topic subscriptions and email confirmations
- **Debug**: Review CloudWatch logs for SNS publish errors

### Performance Optimization
- **Batch Size**: Process 50 predictions per run (configurable)
- **Parallel Processing**: Consider concurrent verification for large batches
- **Caching**: Cache verification results for identical predictions

## Future Enhancements

### Phase 3 Roadmap
1. **MCP Tool Integration**: Implement weather, sports, financial APIs
2. **Smart Retry Logic**: Automatic re-verification for failed predictions
3. **Confidence Tuning**: Machine learning for confidence score optimization
4. **Real-time Verification**: WebSocket-based immediate verification option

---

**Operational Status**: ✅ Fully functional automated verification system processing predictions every 15 minutes with intelligent tool gap detection and email notifications.