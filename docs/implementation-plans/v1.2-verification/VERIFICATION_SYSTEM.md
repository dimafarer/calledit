# Prediction Verification System
## CalledIt: Automated Verification with Strands Agents

**Document Version:** 1.0  
**Date:** January 27, 2025  
**Status:** Phase 1 Implementation

---

## 1. System Overview

The Prediction Verification System automatically validates predictions stored in DynamoDB using Strands agents, providing intelligent verification across all 5 verifiability categories.

### 1.1 Architecture Goals
- **Automated Verification**: Reduce manual prediction checking
- **Intelligent Routing**: Use appropriate tools per category
- **Audit Trail**: Complete logging of verification reasoning
- **User Notification**: Email alerts for verified predictions
- **Scalable Design**: Ready for production automation

---

## 2. Tech Stack

### 2.1 Phase 1: Manual Script
```
DynamoDB → Python Script → Strands Agent → Email → S3 Logs
```

### 2.2 Phase 2: Automated Pipeline  
```
EventBridge (cron) → Lambda → DynamoDB → Strands Agent → SNS → S3 Logs
```

### 2.3 Components
- **DynamoDB**: Prediction storage and status tracking
- **Strands Agents**: AI-powered verification logic
- **S3**: Structured logging and audit trails
- **SES/SMTP**: Email notifications for verified predictions
- **EventBridge**: Scheduled automation (Phase 2)
- **Lambda**: Serverless execution (Phase 2)
- **SNS**: Reliable notification delivery (Phase 2)

---

## 3. Phase 1 Implementation

### 3.1 Manual Verification Script
**File**: `verification/verify_predictions.py`

#### Core Components:
1. **DynamoDB Scanner**: Query pending predictions
2. **Strands Verification Agent**: Intelligent verification
3. **S3 Logger**: Audit trail and reasoning logs
4. **Email Notifier**: Success notifications
5. **Status Updater**: Update prediction verification status

#### Execution Flow:
```python
# 1. Query DynamoDB for PENDING predictions
predictions = query_pending_predictions()

# 2. For each prediction:
for prediction in predictions:
    # 3. Route to appropriate verification method
    result = verify_with_strands_agent(prediction)
    
    # 4. Log verification reasoning to S3
    log_verification_attempt(prediction, result)
    
    # 5. Update DynamoDB status
    update_prediction_status(prediction, result.status)
    
    # 6. Send email if verified TRUE
    if result.status == "TRUE":
        send_verification_email(prediction, result)
```

### 3.2 Verification Categories

#### Agent Verifiable
- **Method**: Pure reasoning and knowledge
- **Example**: "The sun will rise tomorrow"
- **Tools**: Strands reasoning model only

#### Current Tool Verifiable  
- **Method**: Time/date checking
- **Example**: "It's past 11 PM"
- **Tools**: Current time tool + reasoning

#### Strands Tool Verifiable
- **Method**: Mathematical computation
- **Example**: "15% compound interest calculation"
- **Tools**: Calculator + mathematical reasoning

#### API Tool Verifiable
- **Method**: External data sources
- **Example**: "Bitcoin price prediction"
- **Tools**: Financial APIs + market data
- **Phase 1**: Limited API integration
- **Phase 2**: Full external API suite

#### Human Verifiable Only
- **Method**: Mark as inconclusive
- **Example**: "I will feel happy"
- **Action**: Skip verification, log reasoning

### 3.3 Data Structures

#### Verification Result
```python
@dataclass
class VerificationResult:
    prediction_id: str
    status: str  # "TRUE", "FALSE", "INCONCLUSIVE", "ERROR", "TOOL_GAP"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    verification_date: datetime
    tools_used: List[str]
    agent_thoughts: str
    error_message: Optional[str] = None
    # Tool gap analysis
    missing_tool: Optional[str] = None
    suggested_mcp_tool: Optional[str] = None
    tool_specification: Optional[str] = None
```

#### S3 Log Structure
```json
{
  "timestamp": "2025-01-27T15:30:00Z",
  "prediction_id": "pred_123",
  "original_statement": "Bitcoin will hit $100k by Jan 28",
  "verification_category": "api_tool_verifiable",
  "agent_reasoning": "Checking current Bitcoin price...",
  "tools_used": ["bitcoin_price_api"],
  "verification_result": "FALSE",
  "confidence": 0.95,
  "verification_date": "2025-01-28T00:00:00Z",
  "actual_outcome": "Bitcoin price: $97,500",
  "processing_time_ms": 3500,
  "tool_gaps": {
    "missing_tool": null,
    "suggested_mcp_tool": null,
    "tool_specification": null
  }
}
```

#### Tool Gap Log Example
```json
{
  "timestamp": "2025-01-27T15:30:00Z",
  "prediction_id": "pred_456",
  "original_statement": "It will be sunny in Tokyo tomorrow",
  "verification_category": "api_tool_verifiable",
  "agent_reasoning": "Need weather data for Tokyo, but no weather API available",
  "tools_used": [],
  "verification_result": "TOOL_GAP",
  "confidence": 0.0,
  "tool_gaps": {
    "missing_tool": "weather_api",
    "suggested_mcp_tool": "mcp-weather",
    "tool_specification": "Need MCP tool for weather data: get_weather(location, date) -> {temperature, conditions, precipitation}"
  }
}
```

---

## 4. Implementation Steps

### 4.1 Step 1: DynamoDB Query Logic
**File**: `verification/ddb_scanner.py`

```python
def query_pending_predictions():
    """Query all predictions with status='PENDING'"""
    # Implementation details below
```

### 4.2 Step 2: Strands Verification Agent
**File**: `verification/verification_agent.py`

```python
class PredictionVerificationAgent:
    """Strands agent for intelligent prediction verification"""
    
    def verify_prediction(self, prediction) -> VerificationResult:
        # Route based on verifiability category
        # Use appropriate tools and reasoning
        # Return structured result
```

### 4.3 Step 3: S3 Logging System
**File**: `verification/s3_logger.py`

```python
def log_verification_attempt(prediction, result):
    """Log verification reasoning and results to S3"""
    # Structured JSON logging
    # Organized by date and prediction ID
```

### 4.4 Step 4: Email Notification
**File**: `verification/email_notifier.py`

```python
def send_verification_email(prediction, result):
    """Send email notification for verified predictions"""
    # Email template with prediction details
    # Include verification reasoning
```

### 4.5 Step 5: Status Updates
**File**: `verification/status_updater.py`

```python
def update_prediction_status(prediction_id, status, result):
    """Update DynamoDB with verification results"""
    # Add verification_status field
    # Store verification_date and confidence
```

---

## 5. Configuration

### 5.1 Environment Variables
```bash
# AWS Configuration
AWS_REGION=us-west-2
DYNAMODB_TABLE_NAME=calledit-db

# S3 Configuration  
S3_BUCKET_NAME=calledit-verification-logs
S3_LOG_PREFIX=verification-logs/

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
NOTIFICATION_EMAIL=your-email@example.com

# Strands Configuration
STRANDS_MODEL=claude-3-sonnet
VERIFICATION_TIMEOUT=30
```

### 5.2 Required Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/calledit-db"
    },
    {
      "Effect": "Allow", 
      "Action": [
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::calledit-verification-logs/*"
    }
  ]
}
```

---

## 6. Testing Strategy

### 6.1 Test Data Preparation
- Create sample predictions across all 5 categories
- Include edge cases and boundary conditions
- Test with both verifiable and unverifiable predictions

### 6.2 Verification Tests
```python
# Test each verification category
test_agent_verifiable()      # Natural laws
test_current_tool_verifiable()  # Time-based
test_strands_tool_verifiable()  # Mathematical  
test_api_tool_verifiable()      # External data
test_human_verifiable_only()    # Subjective
```

### 6.3 Integration Tests
- End-to-end verification workflow
- S3 logging verification
- Email notification testing
- DynamoDB status updates

---

## 7. Phase 2 Automation Plan

### 7.1 Lambda Function
- Convert script to AWS Lambda
- Add error handling and retries
- Implement batch processing

### 7.2 EventBridge Scheduling
- Daily verification runs
- Configurable cron expressions
- Event-driven triggers

### 7.3 SNS Integration
- Replace SMTP with SNS
- Multiple notification channels
- Delivery confirmations

### 7.4 Enhanced Tools
- Weather API integration
- Stock market data
- News and event verification
- Social media sentiment

---

## 8. Tool Gap Analysis & MCP Integration

### 8.1 Tool Gap Detection
When Strands encounters a prediction it cannot verify with current tools, it will:

1. **Identify the missing capability**
2. **Suggest known MCP tools** that could provide the functionality
3. **Specify requirements** for building custom tools if none exist
4. **Log detailed analysis** for future tool development

### 8.2 Common Tool Gaps & MCP Solutions

#### Weather Data
- **Gap**: Weather predictions ("It will rain tomorrow")
- **MCP Tool**: `mcp-weather` or `mcp-openweathermap`
- **Specification**: `get_weather(location, date) -> {temperature, conditions, precipitation}`

#### Financial Data
- **Gap**: Stock prices, crypto beyond Bitcoin
- **MCP Tool**: `mcp-finance` or `mcp-yahoo-finance`
- **Specification**: `get_stock_price(symbol, date) -> {price, volume, change}`

#### Sports Data
- **Gap**: Game results, team statistics
- **MCP Tool**: `mcp-sports` or `mcp-espn`
- **Specification**: `get_game_result(team1, team2, date) -> {winner, score, status}`

#### News & Events
- **Gap**: Real-world event verification
- **MCP Tool**: `mcp-news` or `mcp-wikipedia`
- **Specification**: `search_events(query, date_range) -> {events, sources, relevance}`

#### Social Media
- **Gap**: Public sentiment, viral content
- **MCP Tool**: `mcp-twitter` or `mcp-social`
- **Specification**: `get_sentiment(topic, date) -> {sentiment, mentions, engagement}`

### 8.3 Tool Development Roadmap

#### Phase 2 Priority Tools
1. **Weather API Integration** - High impact for weather predictions
2. **Sports Data API** - Many sports-related predictions
3. **Enhanced Financial APIs** - Beyond Bitcoin price checking
4. **News Event Verification** - Real-world event validation

#### Phase 3 Advanced Tools
1. **Social Media Monitoring** - Sentiment and viral content
2. **Government Data APIs** - Policy and regulatory predictions
3. **Scientific Data APIs** - Research and discovery predictions
4. **Custom Domain APIs** - Industry-specific verification

### 8.4 Tool Gap Logging

#### S3 Tool Gap Reports
- **Location**: `s3://calledit-verification-logs/tool-gaps/`
- **Format**: JSON with detailed specifications
- **Aggregation**: Daily reports on most needed tools
- **Priority Scoring**: Based on prediction frequency and user impact

#### Tool Gap Analytics
```python
# Example tool gap analysis
{
  "date": "2025-01-27",
  "total_predictions": 50,
  "tool_gaps": {
    "weather_api": {
      "count": 12,
      "examples": ["It will rain tomorrow", "Sunny weekend ahead"],
      "priority": "HIGH",
      "suggested_mcp": "mcp-weather"
    },
    "sports_api": {
      "count": 8,
      "examples": ["Lakers will win tonight", "Super Bowl prediction"],
      "priority": "MEDIUM",
      "suggested_mcp": "mcp-espn"
    }
  }
}
```

---

## 9. Monitoring & Observability

### 8.1 Metrics
- Verification success rate by category
- Processing time per prediction
- Agent confidence scores
- Error rates and types

### 8.2 Logging
- Structured JSON logs in S3
- Agent reasoning chains
- Tool usage statistics
- Performance metrics

### 8.3 Alerting
- Failed verification attempts
- High error rates
- Processing timeouts
- S3 logging failures

---

## 9. Security Considerations

### 9.1 Data Protection
- Encrypt S3 logs at rest
- Secure email credentials
- IAM least privilege access

### 9.2 API Security
- Rate limiting for external APIs
- API key rotation
- Secure credential storage

### 9.3 Audit Trail
- Complete verification history
- Agent decision logging
- User notification tracking

---

## 10. Success Metrics

### 10.1 Phase 1 Goals
- Successfully verify 80%+ of agent_verifiable predictions
- Complete S3 logging for all attempts
- Email notifications for verified predictions
- Zero data loss or corruption

### 10.2 Performance Targets
- <30 seconds per prediction verification
- 95%+ uptime for manual script execution
- Complete audit trail in S3

---

**Document Control:**
- **Author**: Development Team
- **Last Review**: January 27, 2025
- **Next Review**: February 15, 2025
- **Implementation Status**: Phase 1 - In Progress