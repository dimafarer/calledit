# CalledIt Application Flow Documentation

**Version**: 1.6.0  
**Date**: January 19, 2026  
**Status**: Active

**Architecture**: 3-Agent Graph (Parser → Categorizer → Verification Builder)

## Table of Contents
1. [System Overview](#system-overview)
2. [Authentication Flow](#authentication-flow)
3. [Prediction Creation Flow](#prediction-creation-flow)
4. [VPSS Workflow](#vpss-workflow)
5. [Data Persistence Flow](#data-persistence-flow)
6. [Verification System Flow](#verification-system-flow)
7. [Component Interactions](#component-interactions)

---

## System Overview

CalledIt is a serverless application that transforms natural language predictions into structured, verifiable formats using AI agents. The system follows an event-driven architecture with real-time streaming capabilities.

### High-Level Architecture

```
┌─────────────┐
│   User      │
│  Browser    │
└──────┬──────┘
       │
       ├─── Authentication ──────► AWS Cognito
       │
       ├─── REST API ────────────► API Gateway ──► Lambda ──► DynamoDB
       │
       └─── WebSocket ───────────► WebSocket API ──► Lambda ──► 3-Agent Graph ──► Bedrock
                                                                    │
                                                                    ├──► Parser Agent
                                                                    ├──► Categorizer Agent
                                                                    ├──► Verification Builder
                                                                    │
                                                                    └──► Tools
```

### Core Technologies
- **Frontend**: React 18 + TypeScript + Vite
- **Backend**: Python 3.12 + AWS Lambda
- **AI**: Strands 3-Agent Graph + Amazon Bedrock
- **Database**: DynamoDB
- **Auth**: AWS Cognito
- **APIs**: API Gateway (REST + WebSocket)

---

## Authentication Flow

### User Login Process

```
User clicks "Login"
    │
    ├──► Frontend redirects to Cognito Hosted UI
    │
    ├──► User enters credentials
    │
    ├──► Cognito validates credentials
    │
    ├──► Cognito redirects back with authorization code
    │
    ├──► Frontend calls /auth/token endpoint
    │
    ├──► Lambda exchanges code for JWT tokens
    │
    └──► Frontend stores tokens in localStorage
```

### Key Components
- **Cognito User Pool**: Manages user accounts and authentication
- **Cognito Hosted UI**: Provides login/signup interface
- **AuthTokenFunction**: Lambda that exchanges auth codes for JWT tokens
- **AuthContext**: React context that manages auth state

### Token Management
```typescript
// Frontend: AuthContext.tsx
- Stores access_token, id_token, refresh_token
- Provides authentication state to all components
- Handles token refresh automatically
- Manages logout and session cleanup
```

---

## Prediction Creation Flow

This is the core workflow where users create predictions with real-time AI processing.

### Step-by-Step Flow

```
1. USER INPUT
   User enters prediction text
   Example: "Bitcoin will hit $100k tomorrow"
   │
   ├──► Frontend: StreamingCall.tsx
   │    - Captures user input
   │    - Validates input
   │    - Gets user timezone
   │
   └──► Sends WebSocket message

2. WEBSOCKET CONNECTION
   WebSocket API receives message
   │
   ├──► Action: "makecall"
   ├──► Payload: { prompt, timezone }
   │
   └──► Routes to MakeCallStreamFunction

3. LAMBDA PROCESSING
   strands_make_call_graph.py
   │
   ├──► Validates request
   ├──► Extracts connection_id for streaming
   ├──► Executes 3-agent graph
   │
   └──► Sends initial status: "processing"

4. 3-AGENT GRAPH EXECUTION
   Parser → Categorizer → Verification Builder
   │
   ├──► PARSER AGENT
   │    ├──► Extracts prediction statement (exact text)
   │    ├──► Parses dates/times (12h → 24h conversion)
   │    ├──► Uses current_time and parse_relative_date tools
   │    └──► Streams: { type: "tool", name: "current_time" }
   │
   ├──► CATEGORIZER AGENT
   │    ├──► Receives parser output
   │    ├──► Analyzes verifiability
   │    ├──► Classifies into 5 categories
   │    └──► Provides reasoning for classification
   │
   └──► VERIFICATION BUILDER AGENT
        ├──► Receives categorizer output
        ├──► Generates verification method
        ├──► Creates source list
        ├──► Defines criteria
        └──► Outlines verification steps

5. RESPONSE STREAMING
   Real-time updates sent to frontend
   │
   ├──► Text chunks displayed as they arrive
   ├──► Tool usage shown with icons
   ├──► Processing indicators updated
   │
   └──► Final response: { type: "call_response", content: {...} }

6. FUTURE: VPSS REVIEW (Task 10)
   ReviewAgent will analyze response
   │
   ├──► Identify improvable sections
   ├──► Generate questions for each section
   │
   └──► Send: { type: "review_complete", data: {...} }
   
   Note: VPSS is not yet integrated into the 3-agent graph

7. FRONTEND DISPLAY
   StreamingCall.tsx renders result
   │
   ├──► Shows prediction statement
   ├──► Displays verifiability category with badge
   ├──► Shows verification method (source, criteria, steps)
   │
   └──► Enables "Log Call" button
```

### Detailed Component Interactions

#### Frontend (StreamingCall.tsx)
```typescript
// 1. User submits prediction
handleSubmit() {
  callService.makeCallWithStreaming(
    prompt,
    onTextChunk,      // Handles streaming text
    onToolUse,        // Handles tool notifications
    onComplete,       // Handles final response
    onError,          // Handles errors
    onReviewStatus,   // Handles review status
    onReviewComplete, // Handles review results
    onImproved        // Handles improvements
  )
}

// 2. Streaming handlers update UI in real-time
onTextChunk: (text) => setStreamingText(prev => prev + text)
onToolUse: (tool) => setCurrentTool(tool)
onComplete: (response) => {
  setCall(JSON.parse(response))
  setIsLoading(false)
}
```

#### Backend (strands_make_call_graph.py)
```python
# 1. Execute 3-agent graph with streaming callback
def stream_callback_handler(**kwargs):
    if "data" in kwargs:
        # Stream text chunks
        api_gateway_management_api.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({"type": "text", "content": kwargs["data"]})
        )
    elif "current_tool_use" in kwargs:
        # Stream tool usage
        api_gateway_management_api.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({"type": "tool", "name": tool_name})
        )

# 2. Execute prediction graph (Parser → Categorizer → Verification Builder)
final_state = execute_prediction_graph(
    user_prompt=prompt,
    user_timezone=user_timezone,
    current_datetime_utc=formatted_datetime_utc,
    current_datetime_local=formatted_datetime_local,
    callback_handler=stream_callback_handler
)

# 3. Send final structured response
response_data = {
    "prediction_statement": final_state.get("prediction_statement"),
    "verification_date": final_state.get("verification_date"),
    "date_reasoning": final_state.get("date_reasoning"),
    "verifiable_category": final_state.get("verifiable_category"),
    "category_reasoning": final_state.get("category_reasoning"),
    "verification_method": final_state.get("verification_method"),
    "initial_status": "pending"
}
```

### Verifiability Categorization

The agent automatically classifies predictions into 5 categories:

1. **agent_verifiable** 🧠
   - Pure reasoning/knowledge
   - Example: "The sun will rise tomorrow"

2. **current_tool_verifiable** ⏰
   - Current time tool only
   - Example: "It's currently past 3pm"

3. **strands_tool_verifiable** 🔧
   - Strands library tools (calculator, python_repl)
   - Example: "15% compound interest on $1000 over 5 years"

4. **api_tool_verifiable** 🌐
   - External API calls required
   - Example: "Bitcoin will hit $100k tomorrow"

5. **human_verifiable_only** 👤
   - Human observation required
   - Example: "I will feel happy tomorrow"

---

## VPSS Workflow

**Verifiable Prediction Structuring System** - Transforms predictions into verification-ready JSON structures.

### VPSS Architecture Pattern

```
Server-Initiated Review
    │
    ├──► ReviewAgent analyzes prediction
    │    └──► Identifies improvable sections
    │
    ├──► Client-Facilitated LLM Interaction
    │    └──► WebSocket handles improvement requests
    │
    ├──► Human-in-the-Loop
    │    └──► User provides clarifications
    │
    └──► Multi-Step Workflow
         └──► Review → Questions → Answers → Regeneration
```

### Detailed VPSS Flow

```
1. AUTOMATIC REVIEW
   After prediction is created
   │
   ├──► ReviewAgent.review_prediction(response)
   │    │
   │    ├──► Analyzes each field
   │    ├──► Identifies improvable sections
   │    ├──► Generates specific questions
   │    │
   │    └──► Returns: {
   │         "reviewable_sections": [
   │           {
   │             "section": "prediction_statement",
   │             "improvable": true,
   │             "questions": [
   │               "What specific location?",
   │               "What exact time?"
   │             ],
   │             "reasoning": "More specificity improves verification"
   │           }
   │         ]
   │       }
   │
   └──► Frontend receives review results

2. USER INTERACTION
   User clicks reviewable section
   │
   ├──► ImprovementModal opens
   │    │
   │    ├──► Shows questions
   │    ├──► Shows reasoning
   │    │
   │    └──► User provides answers:
   │         - "New York City"
   │         - "tomorrow at 3pm"
   │
   └──► User clicks "Submit Improvements"

3. IMPROVEMENT REQUEST
   Frontend sends WebSocket message
   │
   ├──► Action: "improvement_answers"
   ├──► Payload: {
   │      section: "prediction_statement",
   │      answers: ["New York City", "tomorrow at 3pm"],
   │      original_value: "it will rain",
   │      full_context: { entire prediction object }
   │    }
   │
   └──► Backend receives request

4. REGENERATION
   ReviewAgent.regenerate_section()
   │
   ├──► For prediction_statement (special case):
   │    │
   │    ├──► Regenerates multiple fields:
   │    │    - prediction_statement
   │    │    - verification_date
   │    │    - verification_method
   │    │
   │    └──► Returns: {
   │         "prediction_statement": "It will rain in NYC tomorrow",
   │         "verification_date": "2025-08-05T23:59:59Z",
   │         "verification_method": {
   │           "source": ["NYC Weather API"],
   │           "criteria": ["Measurable precipitation"],
   │           "steps": ["Check NYC weather on Aug 5"]
   │         }
   │       }
   │
   └──► For other sections:
        └──► Returns single improved value

5. RESPONSE UPDATE
   Backend sends improved response
   │
   ├──► WebSocket message: {
   │      type: "improved_response",
   │      data: {
   │        section: "prediction_statement",
   │        multiple_updates: { ... }  // or improved_value
   │      }
   │    }
   │
   └──► Frontend receives update

6. UI UPDATE
   StreamingCall.tsx processes improvement
   │
   ├──► Updates call state with new values
   ├──► Re-renders affected sections
   ├──► Clears improvement indicators
   ├──► Updates improvement history
   │
   └──► User sees improved prediction
```

### VPSS State Management

The frontend uses 4 custom React hooks for enterprise-grade state management:

#### 1. useReviewState
```typescript
// Manages review workflow state
{
  reviewableSections: [],      // Sections that can be improved
  showImprovementModal: false, // Modal visibility
  improvingSection: null,      // Currently improving section
  currentQuestions: [],        // Questions for current section
  isImproving: false,          // Improvement in progress
  reviewStatus: ''             // Status message
}
```

#### 2. useErrorHandler
```typescript
// Centralized error handling
{
  error: { message, type, timestamp },
  hasError: boolean,
  setWebSocketError: (msg) => {},
  setImprovementError: (msg) => {},
  clearError: () => {}
}
```

#### 3. useWebSocketConnection
```typescript
// WebSocket connection management
{
  callService: WebSocketService,
  handleConnectionError: (error) => {},
  reconnectCount: number
}
```

#### 4. useImprovementHistory
```typescript
// Tracks improvement audit trail
{
  history: [
    {
      timestamp: Date,
      section: string,
      questions: string[],
      answers: string[],
      originalContent: string,
      improvedContent: string
    }
  ],
  addHistoryEntry: (entry) => {},
  updateHistoryEntry: (timestamp, improved) => {},
  clearHistory: () => {}
}
```

### Date Conflict Resolution

VPSS intelligently handles date conflicts:

```
User says: "it will rain"
Agent assumes: "today"

User clarifies: "tomorrow"

VPSS detects conflict:
- Original verification_date: 2025-08-04
- User specified: "tomorrow"
- VPSS updates: 2025-08-05

Result: Multiple fields updated consistently
```

---

## Data Persistence Flow

### Saving Predictions to DynamoDB

```
1. USER ACTION
   User clicks "Log Call" button
   │
   ├──► LogCallButton.tsx
   │    └──► Validates prediction data
   │
   └──► Calls apiService.logCall()

2. API REQUEST
   POST /log-call
   │
   ├──► Headers: {
   │      Authorization: Bearer {jwt_token},
   │      Content-Type: application/json
   │    }
   │
   └──► Body: {
        prediction: {
          prediction_statement: "...",
          verification_date: "2025-01-27T15:00:00Z",
          verifiable_category: "api_tool_verifiable",
          category_reasoning: "...",
          verification_method: {...},
          initial_status: "pending"
        }
      }

3. LAMBDA PROCESSING
   write_to_db.py
   │
   ├──► Validates JWT token (Cognito)
   ├──► Extracts user_id from token
   ├──► Generates timestamp for SK
   │
   └──► Prepares DynamoDB item

4. DYNAMODB WRITE
   Table: calledit-db
   │
   ├──► Partition Key (PK): USER#{user_id}
   ├──► Sort Key (SK): PREDICTION#{timestamp}
   │
   └──► Item: {
        PK: "USER#abc123",
        SK: "PREDICTION#2025-01-27T10:30:00.000Z",
        prediction_statement: "...",
        verification_date: "2025-01-27T15:00:00Z",
        verifiable_category: "api_tool_verifiable",
        category_reasoning: "...",
        verification_method: {...},
        initial_status: "pending",
        createdAt: "2025-01-27T10:30:00.000Z",
        updatedAt: "2025-01-27T10:30:00.000Z"
      }

5. RESPONSE
   Lambda returns success
   │
   └──► Frontend shows success message
        └──► Navigates to ListPredictions
```

### Retrieving Predictions

```
1. USER NAVIGATION
   User clicks "List Predictions" tab
   │
   └──► ListPredictions.tsx mounts

2. API REQUEST
   GET /list-predictions
   │
   ├──► Headers: {
   │      Authorization: Bearer {jwt_token}
   │    }
   │
   └──► Lambda: list_predictions.py

3. DYNAMODB QUERY
   Query by partition key
   │
   ├──► PK = USER#{user_id}
   ├──► Sort by SK descending (newest first)
   │
   └──► Returns all user's predictions

4. RESPONSE PROCESSING
   Lambda formats response
   │
   └──► Returns: {
        results: [
          {
            prediction_statement: "...",
            verification_date: "...",
            verifiable_category: "...",
            verification_status: "pending",
            verification_confidence: null,
            ...
          }
        ]
      }

5. FRONTEND DISPLAY
   ListPredictions.tsx renders
   │
   ├──► Shows predictions in cards
   ├──► Displays verifiability badges
   ├──► Shows verification status
   │
   └──► Allows filtering/sorting
```

### DynamoDB Schema

```
Table: calledit-db

Primary Key:
- PK (Partition Key): USER#{user_id}
- SK (Sort Key): PREDICTION#{timestamp}

Attributes:
- prediction_statement: string
- verification_date: string (ISO 8601 UTC)
- prediction_date: string (ISO 8601 UTC)
- verifiable_category: string (enum)
- category_reasoning: string
- verification_method: map {
    source: list<string>
    criteria: list<string>
    steps: list<string>
  }
- initial_status: string
- verification_status: string (updated by verification system)
- verification_confidence: number (0.0-1.0)
- verification_reasoning: string
- createdAt: string (ISO 8601 UTC)
- updatedAt: string (ISO 8601 UTC)

Indexes:
- None (single-table design with PK/SK)

Access Patterns:
1. Get all predictions for user: Query by PK
2. Get specific prediction: Get by PK + SK
3. Update verification status: Update by PK + SK
```

---

## Verification System Flow

Automated verification system that processes ALL predictions every 15 minutes.

### EventBridge Scheduled Execution

```
1. EVENTBRIDGE TRIGGER
   Every 15 minutes
   │
   ├──► Rule: VerificationScheduleRule
   ├──► Schedule: rate(15 minutes)
   │
   └──► Invokes: VerificationFunction Lambda

2. LAMBDA INITIALIZATION
   verification/app.py
   │
   ├──► Imports verification components
   ├──► Initializes DynamoDB scanner
   ├──► Creates verification agent
   │
   └──► Starts verification process

3. SCAN DYNAMODB
   ddb_scanner.py
   │
   ├──► Scans entire calledit-db table
   ├──► Filters for pending predictions
   ├──► Checks verification_date <= now
   │
   └──► Returns: [
        {PK, SK, prediction_statement, verifiable_category, ...}
      ]

4. VERIFICATION LOOP
   For each pending prediction
   │
   ├──► verification_agent.py
   │    │
   │    ├──► Routes by verifiable_category:
   │    │    │
   │    │    ├──► agent_verifiable
   │    │    │    └──► Pure reasoning verification
   │    │    │
   │    │    ├──► current_tool_verifiable
   │    │    │    └──► Time-based verification
   │    │    │
   │    │    ├──► strands_tool_verifiable
   │    │    │    └──► Mathematical verification
   │    │    │
   │    │    ├──► api_tool_verifiable
   │    │    │    └──► Tool gap detection
   │    │    │
   │    │    └──► human_verifiable_only
   │    │         └──► Mark as inconclusive
   │    │
   │    └──► Returns: VerificationResult {
   │         status: TRUE | FALSE | INCONCLUSIVE | TOOL_GAP
   │         confidence: 0.0 - 1.0
   │         reasoning: "..."
   │         tools_used: [...]
   │         mcp_suggestions: {...}
   │       }
   │
   └──► Process result

5. UPDATE DYNAMODB
   status_updater.py
   │
   ├──► Updates prediction item:
   │    - verification_status: "true" | "false" | "inconclusive"
   │    - verification_confidence: 0.85
   │    - verification_reasoning: "..."
   │    - verification_date_actual: "2025-01-27T15:05:00Z"
   │    - updatedAt: "2025-01-27T15:05:00Z"
   │
   └──► DynamoDB UpdateItem

6. LOG TO S3
   s3_logger.py
   │
   ├──► Creates structured log entry
   ├──► Bucket: calledit-verification-logs
   ├──► Key: logs/YYYY/MM/DD/HH-MM-SS-{prediction_id}.json
   │
   └──► Stores: {
        prediction_id: "...",
        verification_result: {...},
        timestamp: "...",
        processing_time_ms: 1234
      }

7. SEND NOTIFICATIONS
   email_notifier.py
   │
   ├──► If verification_status == "true":
   │    │
   │    ├──► Get user email from Cognito
   │    ├──► Check SNS subscription status
   │    │
   │    └──► Send SNS notification:
   │         Subject: "🎉 Your prediction came true!"
   │         Body: "Your prediction '{statement}' was verified as TRUE!"
   │
   └──► User receives email

8. FRONTEND UPDATE
   User refreshes ListPredictions
   │
   ├──► Fetches updated predictions
   ├──► Shows verification status badges
   ├──► Displays confidence scores
   │
   └──► Shows verification reasoning
```

### Verification Agent Logic

#### Agent Verifiable
```python
def _verify_with_reasoning(prediction):
    """Pure reasoning for natural laws"""
    prompt = f"""
    Verify: "{prediction}"
    Use established knowledge and logic.
    """
    
    response = agent.run(prompt)
    
    # Parse response for TRUE/FALSE
    if 'true' in response.lower():
        return VerificationResult(
            status=TRUE,
            confidence=0.9,
            reasoning="Verified through reasoning"
        )
```

#### Current Tool Verifiable
```python
def _verify_with_time_tool(prediction):
    """Time-based verification"""
    prompt = f"""
    Verify: "{prediction}"
    Use current_time tool to check.
    """
    
    response = agent.run(prompt)
    tools_used = ['current_time']
    
    return VerificationResult(
        status=TRUE/FALSE,
        confidence=0.85,
        tools_used=tools_used
    )
```

#### API Tool Verifiable (Tool Gap Detection)
```python
def _verify_with_api_gap_detection(prediction):
    """Detect missing tools"""
    
    if 'bitcoin' in prediction.lower():
        return create_tool_gap_result(
            reasoning="Bitcoin price verification requires crypto API",
            mcp_suggestions={
                "suggested_tool": "cryptocurrency_price_checker",
                "mcp_server": "crypto-data-mcp",
                "implementation_guide": "..."
            }
        )
```

### Verification Result Structure

```python
class VerificationResult:
    prediction_id: str
    status: VerificationStatus  # TRUE, FALSE, INCONCLUSIVE, TOOL_GAP, ERROR
    confidence: float           # 0.0 - 1.0
    reasoning: str
    verification_date: datetime
    tools_used: List[str]
    agent_thoughts: str
    verification_method: str
    processing_time_ms: int
    
    # Tool gap detection
    tool_gap: Optional[ToolGap] = None
    mcp_suggestions: Optional[MCPToolSuggestions] = None
```

### "Crying" Notification System

When a prediction is verified as TRUE:

```
1. Verification completes with status=TRUE
   │
2. email_notifier.py checks SNS subscriptions
   │
3. Sends email via SNS:
   │
   ├──► Subject: "🎉 Your prediction came true!"
   │
   └──► Body:
        "Congratulations! Your prediction was verified as TRUE:
        
        Prediction: '{statement}'
        Verification Date: {date}
        Confidence: {confidence}%
        
        Share your success:
        - Twitter: [Share link]
        - LinkedIn: [Share link]
        - Facebook: [Share link]"

4. User receives email notification
   │
5. User can share on social media
```

---

## Component Interactions

### Frontend Component Hierarchy

```
App.tsx
│
├── AuthContext (provides authentication state)
│
├── ErrorBoundary (catches React errors)
│
└── Main Content
    │
    ├── LoginButton (if not authenticated)
    │
    └── Authenticated Content
        │
        ├── Navigation Tabs
        │   ├── StreamingCall
        │   └── ListPredictions
        │
        ├── StreamingCall.tsx
        │   │
        │   ├── Custom Hooks:
        │   │   ├── useReviewState
        │   │   ├── useErrorHandler
        │   │   ├── useWebSocketConnection
        │   │   └── useImprovementHistory
        │   │
        │   ├── Components:
        │   │   ├── AnimatedText (streaming display)
        │   │   ├── ReviewableSection (improvable fields)
        │   │   ├── ImprovementModal (VPSS questions)
        │   │   └── LogCallButton (save prediction)
        │   │
        │   └── Services:
        │       ├── callService (WebSocket)
        │       └── apiService (REST)
        │
        └── ListPredictions.tsx
            │
            ├── PredictionDisplay (individual cards)
            ├── NavigationControls (pagination)
            └── ReviewStatus (verification badges)
```

### Service Layer Architecture

```
Frontend Services
│
├── authService.ts
│   ├── login()
│   ├── logout()
│   ├── getToken()
│   └── refreshToken()
│
├── apiService.ts
│   ├── logCall(prediction)
│   ├── listPredictions()
│   ├── subscribeNotifications(email)
│   └── unsubscribeNotifications()
│
├── callService.ts
│   ├── makeCallWithStreaming()
│   ├── handleStreamingResponse()
│   └── parseResponse()
│
└── websocket.ts
    ├── connect()
    ├── send(action, data)
    ├── onMessage(handler)
    ├── onError(handler)
    └── disconnect()
```

### Backend Lambda Functions

```
API Gateway (REST)
│
├── /auth/token
│   └── AuthTokenFunction
│       └── handlers/auth_token/auth_token.py
│
├── /log-call
│   └── WriteToDBFunction
│       └── handlers/write_to_db/write_to_db.py
│
├── /list-predictions
│   └── ListPredictionsFunction
│       └── handlers/list_predictions/list_predictions.py
│
├── /subscribe-notifications
│   └── NotificationManagementFunction
│       └── handlers/notification_management/app.py
│
└── /unsubscribe-notifications
    └── NotificationManagementFunction

WebSocket API
│
├── $connect
│   └── ConnectFunction
│       └── handlers/websocket/connect.py
│
├── $disconnect
│   └── DisconnectFunction
│       └── handlers/websocket/disconnect.py
│
└── makecall
    └── MakeCallStreamFunction
        └── handlers/strands_make_call/strands_make_call_graph.py
            │
            ├── prediction_graph.py (Graph orchestration)
            ├── parser_agent.py (Parser Agent)
            ├── categorizer_agent.py (Categorizer Agent)
            ├── verification_builder_agent.py (Verification Builder)
            ├── graph_state.py (State TypedDict)
            └── utils.py (Utilities)
            
            Future (Task 10):
            └── review_agent.py (VPSS - not yet integrated)

EventBridge
│
└── VerificationScheduleRule (every 15 minutes)
    └── VerificationFunction
        └── handlers/verification/app.py
            │
            ├── ddb_scanner.py
            ├── verification_agent.py
            ├── status_updater.py
            ├── s3_logger.py
            └── email_notifier.py
```

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        USER BROWSER                          │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ StreamingCall│    │ListPredictions│   │ LoginButton  │ │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘ │
│         │                   │                    │          │
└─────────┼───────────────────┼────────────────────┼──────────┘
          │                   │                    │
          │                   │                    │
    ┌─────▼─────┐       ┌─────▼─────┐      ┌─────▼─────┐
    │ WebSocket │       │  REST API │      │  Cognito  │
    │    API    │       │  Gateway  │      │  Hosted   │
    └─────┬─────┘       └─────┬─────┘      │    UI     │
          │                   │             └───────────┘
          │                   │
    ┌─────▼─────┐       ┌─────▼─────┐
    │  Lambda   │       │  Lambda   │
    │ Streaming │       │   CRUD    │
    └─────┬─────┘       └─────┬─────┘
          │                   │
    ┌─────▼─────┐             │
    │  Strands  │             │
    │   Agent   │             │
    └─────┬─────┘             │
          │                   │
    ┌─────▼─────┐       ┌─────▼─────┐
    │  Bedrock  │       │ DynamoDB  │
    │  (Claude) │       │           │
    └───────────┘       └─────┬─────┘
                              │
                        ┌─────▼─────┐
                        │EventBridge│
                        │ (15 min)  │
                        └─────┬─────┘
                              │
                        ┌─────▼─────┐
                        │Verification│
                        │  Lambda   │
                        └─────┬─────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
              ┌─────▼───┐ ┌───▼────┐ ┌─▼────┐
              │   S3    │ │  SNS   │ │ DDB  │
              │  Logs   │ │ Email  │ │Update│
              └─────────┘ └────────┘ └──────┘
```

---

## Complete User Journey Examples

### Example 1: Creating a Simple Prediction

```
USER ACTION: "Bitcoin will hit $100k tomorrow"

1. User types prediction in StreamingCall
2. User clicks "Make Call"
3. WebSocket connects to backend
4. Lambda receives message
5. Strands agent starts processing
   
   STREAMING OUTPUT:
   "I'll analyze this prediction..."
   [Using tool: current_time]
   "Current time is 2025-01-27 10:30 AM..."
   "This prediction requires external Bitcoin price data..."
   
6. Agent generates structured response:
   {
     "prediction_statement": "Bitcoin will hit $100k tomorrow",
     "verification_date": "2025-01-28T23:59:59Z",
     "verifiable_category": "api_tool_verifiable",
     "category_reasoning": "Requires real-time cryptocurrency price API",
     "verification_method": {
       "source": ["CoinGecko API", "CoinMarketCap"],
       "criteria": ["BTC/USD price >= $100,000"],
       "steps": ["Check BTC price at end of day tomorrow"]
     }
   }

7. ReviewAgent analyzes response
   - Identifies: prediction_statement could be more specific
   - Questions: "What exact time tomorrow?", "Which exchange?"

8. Frontend displays:
   - Prediction with 🌐 API Verifiable badge
   - Reviewable sections highlighted
   - "Log Call" button enabled

9. User clicks "Log Call"
10. Prediction saved to DynamoDB
11. User navigates to ListPredictions
12. Sees prediction with "pending" status
```

### Example 2: Using VPSS to Improve Prediction

```
USER ACTION: "it will rain"

1. Initial prediction created (assumes "today")
2. ReviewAgent identifies improvements needed:
   - prediction_statement: too vague
   - Questions: ["What location?", "What timeframe?", "How much rain?"]

3. User clicks prediction_statement section
4. ImprovementModal opens with questions
5. User provides answers:
   - "New York City"
   - "tomorrow"
   - "measurable precipitation"

6. Frontend sends improvement_answers via WebSocket
7. ReviewAgent regenerates with user input:
   
   MULTIPLE FIELD UPDATE:
   {
     "prediction_statement": "It will rain in NYC tomorrow with measurable precipitation",
     "verification_date": "2025-08-05T23:59:59Z",  // Updated from today to tomorrow
     "verification_method": {
       "source": ["NYC Weather API", "NOAA"],
       "criteria": ["Precipitation >= 0.01 inches in NYC"],
       "steps": ["Check NYC weather data for Aug 5, 2025"]
     }
   }

8. Frontend updates all affected fields
9. User sees improved prediction
10. User clicks "Log Call"
11. Improved prediction saved to DynamoDB
```

### Example 3: Automated Verification

```
SCHEDULED: EventBridge triggers every 15 minutes

1. VerificationFunction Lambda starts
2. DDB Scanner finds pending predictions:
   - "Bitcoin will hit $100k tomorrow" (verification_date: 2025-01-28)
   - Current date: 2025-01-28 15:00

3. Verification Agent processes:
   - Category: api_tool_verifiable
   - Detects tool gap (no crypto API available)
   - Returns: TOOL_GAP status with MCP suggestions

4. Status Updater writes to DynamoDB:
   {
     "verification_status": "tool_gap",
     "verification_confidence": 0.0,
     "verification_reasoning": "Bitcoin price verification requires crypto API",
     "mcp_suggestions": {
       "suggested_tool": "cryptocurrency_price_checker",
       "mcp_server": "crypto-data-mcp"
     }
   }

5. S3 Logger saves verification log
6. No email sent (not TRUE status)

7. User refreshes ListPredictions
8. Sees "Tool Gap" badge with MCP suggestions
```

### Example 4: Successful Prediction Notification

```
PREDICTION: "The sun will rise tomorrow"

1. EventBridge triggers verification
2. Verification Agent processes:
   - Category: agent_verifiable
   - Uses pure reasoning
   - Determines: TRUE (confidence: 0.95)

3. Status Updater writes to DynamoDB:
   {
     "verification_status": "true",
     "verification_confidence": 0.95,
     "verification_reasoning": "Natural law - sun rises daily"
   }

4. Email Notifier checks SNS subscriptions
5. Sends email to user:
   
   Subject: "🎉 Your prediction came true!"
   
   Body:
   "Congratulations! Your prediction was verified as TRUE:
   
   Prediction: 'The sun will rise tomorrow'
   Confidence: 95%
   Reasoning: Natural law - sun rises daily
   
   Share your success on social media!"

6. User receives email
7. User clicks share links
8. Prediction shared on Twitter/LinkedIn/Facebook
```

---

## Key Architectural Patterns

### 1. Server-Initiated, Client-Facilitated Pattern (VPSS)
- Server (ReviewAgent) identifies what needs improvement
- Client (WebSocket) facilitates the LLM interaction
- Human provides the missing information
- Server regenerates with complete context

### 2. Real-Time Streaming Pattern
- WebSocket maintains persistent connection
- Backend streams responses as they're generated
- Frontend updates UI incrementally
- User sees progress in real-time

### 3. Event-Driven Verification Pattern
- EventBridge schedules regular verification runs
- Lambda processes predictions asynchronously
- Results written back to DynamoDB
- Notifications sent via SNS

### 4. Single-Table DynamoDB Design
- PK: USER#{user_id} (partition key)
- SK: PREDICTION#{timestamp} (sort key)
- All user data in one table
- Efficient queries by user

### 5. Serverless Architecture
- No servers to manage
- Auto-scaling based on demand
- Pay only for what you use
- High availability built-in

---

## Performance Characteristics

### Latency Targets
- WebSocket connection: < 1 second
- Prediction processing: < 60 seconds
- REST API calls: < 5 seconds
- Verification run: < 5 minutes (for all predictions)

### Scalability
- Concurrent WebSocket connections: 1000+
- Concurrent users: Unlimited (Lambda auto-scales)
- DynamoDB throughput: Auto-scales with demand
- Bedrock API: Rate limited by AWS quotas

### Cost Optimization
- Lambda: Pay per invocation
- DynamoDB: On-demand pricing
- Bedrock: Pay per token
- S3: Pay per storage + requests
- EventBridge: Free tier covers most usage

---

## Security Considerations

### Authentication & Authorization
- Cognito manages all user authentication
- JWT tokens required for all authenticated endpoints
- Tokens validated on every request
- User data isolated by partition key

### Data Protection
- TLS 1.2+ for all data in transit
- DynamoDB encryption at rest
- S3 encryption at rest
- No sensitive data in logs

### Input Validation
- All user inputs sanitized
- JSON schema validation
- SQL injection prevention (NoSQL)
- XSS prevention in frontend

---

## Monitoring & Observability

### CloudWatch Logs
- All Lambda functions log to CloudWatch
- Structured logging with context
- Error tracking with stack traces
- Performance metrics captured

### CloudWatch Metrics
- Lambda invocations, duration, errors
- API Gateway request count, latency
- DynamoDB read/write capacity
- WebSocket connection count

### Alarms
- High error rates
- Slow response times
- DynamoDB throttling
- Lambda timeout errors

---

## Related Documentation

- **[API.md](./API.md)** - Complete API reference
- **[TRD.md](./TRD.md)** - Technical requirements
- **[VPSS_COMPLETE.md](./VPSS_COMPLETE.md)** - VPSS implementation details
- **[VERIFICATION_SYSTEM.md](./VERIFICATION_SYSTEM.md)** - Verification system guide
- **[TESTING.md](./TESTING.md)** - Testing strategy
- **[README.md](../../README.md)** - Project overview

---

**Document Version**: 1.0  
**Last Updated**: January 16, 2026  
**Maintained By**: Development Team
