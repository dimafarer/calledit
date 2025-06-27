# CalledIt Streaming Implementation: Actual Implementation Steps

This document reflects the exact steps we took to successfully implement WebSocket streaming in the CalledIt application.

## Phase 1: Backend Setup

### Step 1: Create WebSocket Handler Directory

Created directory structure for WebSocket handlers:

```bash
mkdir -p backend/calledit-backend/handlers/websocket
```

### Step 2: Create Basic WebSocket Handlers

Created simple connect and disconnect handlers:

**handlers/websocket/connect.py:**
```python
import json

def lambda_handler(event, context):
    """
    Handle WebSocket connection events.
    """
    print("WebSocket connection event:", event)
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Connected'})
    }
```

**handlers/websocket/disconnect.py:**
```python
import json

def lambda_handler(event, context):
    """
    Handle WebSocket disconnection events.
    """
    print("WebSocket disconnection event:", event)
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Disconnected'})
    }
```

**handlers/websocket/requirements.txt:**
```
boto3
```

### Step 3: Initial Streaming Handler (Simple Version)

First created a simple streaming handler to test WebSocket infrastructure:

**handlers/make_call/make_call_stream_simple.py:**
```python
import json
import boto3
from datetime import datetime

def lambda_handler(event, context):
    # Extract WebSocket connection info
    connection_id = event.get('requestContext', {}).get('connectionId')
    domain_name = event.get('requestContext', {}).get('domainName')
    stage = event.get('requestContext', {}).get('stage')
    
    # Set up API Gateway Management API client
    api_gateway_management_api = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f"https://{domain_name}/{stage}"
    )
    
    # Get prompt from request body
    body = json.loads(event.get('body', '{}'))
    prompt = body.get('prompt', '')
    
    # Simulate streaming with mock chunks
    chunks = [
        "Analyzing your prediction: ",
        prompt,
        "\n\nGenerating verification method...\n",
        "Creating structured format...\n",
        "Setting verification date...\n"
    ]
    
    for chunk in chunks:
        api_gateway_management_api.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                "type": "text",
                "content": chunk
            })
        )
    
    # Send mock final response
    mock_response = {
        "prediction_statement": prompt,
        "verification_date": "2025-12-31",
        "verification_method": {
            "source": ["Manual verification", "News sources"],
            "criteria": ["Check if prediction came true"],
            "steps": ["Wait until verification date", "Check relevant sources"]
        },
        "initial_status": "pending"
    }
    
    api_gateway_management_api.post_to_connection(
        ConnectionId=connection_id,
        Data=json.dumps({
            "type": "complete",
            "content": json.dumps(mock_response)
        })
    )
    
    return {'statusCode': 200, 'body': json.dumps({'status': 'Streaming completed'})}
```

### Step 4: Enhanced Strands Streaming Handler

After testing basic WebSocket functionality, created the full Strands-powered streaming handler in the existing strands_make_call directory:

**handlers/strands_make_call/strands_make_call_stream.py:**
- Full Strands Agent integration with streaming callbacks
- Timezone-aware date handling
- Tool integration (current_time, parse_relative_date)
- Comprehensive system and user prompts from existing strands handler
- Real-time streaming of AI responses via WebSocket

### Step 5: SAM Template Updates

Added WebSocket API resources to template.yaml:

```yaml
# WebSocket API
WebSocketApi:
  Type: AWS::ApiGatewayV2::Api
  Properties:
    Name: CalledItWebSocketAPI
    ProtocolType: WEBSOCKET
    RouteSelectionExpression: "$request.body.action"

# Routes
ConnectRoute:
  Type: AWS::ApiGatewayV2::Route
  Properties:
    ApiId: !Ref WebSocketApi
    RouteKey: $connect
    # ... integration details

MakeCallStreamRoute:
  Type: AWS::ApiGatewayV2::Route
  Properties:
    ApiId: !Ref WebSocketApi
    RouteKey: makecall
    # ... integration details

# Lambda Functions
MakeCallStreamFunction:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: handlers/strands_make_call/
    Handler: strands_make_call_stream.lambda_handler
    Runtime: python3.12
    Timeout: 300
    MemorySize: 512
    Policies:
      - DynamoDBCrudPolicy:
          TableName: calledit-db
      - Statement:
          - Effect: Allow
            Action:
              - 'bedrock:InvokeModel'
              - 'bedrock:InvokeModelWithResponseStream'
              - 'bedrock:ListFoundationModels'
            Resource: '*'
      - Statement:
          - Effect: Allow
            Action:
              - 'execute-api:ManageConnections'
            Resource: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${WebSocketApi}/*'
```

## Phase 2: Deploy and Test Backend

### Step 1: Build and Deploy

```bash
cd backend/calledit-backend
. ../../venv/bin/activate
sam build
sam deploy --stack-name calledit-backend --no-confirm-changeset
```

### Step 2: Test WebSocket API

Created test script to verify WebSocket functionality:

**test_websocket_strands.js:**
```javascript
const WebSocket = require('ws');

const ws = new WebSocket('wss://0yv5r2auh5.execute-api.us-west-2.amazonaws.com/prod');

ws.on('open', function open() {
  const testMessage = {
    action: 'makecall',
    prompt: 'The S&P 500 will reach 6000 points by March 2025',
    timezone: 'America/New_York'
  };
  ws.send(JSON.stringify(testMessage));
});

ws.on('message', function message(data) {
  const parsedData = JSON.parse(data.toString());
  console.log('Received:', parsedData);
});
```

## Phase 3: Frontend Implementation

### Step 1: Create WebSocket Service

**frontend/src/services/websocket.ts:**
```typescript
export class WebSocketService {
  private socket: WebSocket | null = null;
  private messageHandlers: Map<string, (data: any) => void> = new Map();
  
  constructor(private url: string) {}
  
  async connect(): Promise<void> {
    // WebSocket connection logic
  }
  
  async send(action: string, data: any): Promise<void> {
    // Send message logic
  }
  
  onMessage(type: string, handler: (data: any) => void): void {
    // Register message handlers
  }
}
```

### Step 2: Create Prediction Service

**frontend/src/services/predictionService.ts:**
```typescript
import { WebSocketService } from './websocket';

export class PredictionService {
  private webSocketService: WebSocketService;
  
  constructor(webSocketUrl: string) {
    this.webSocketService = new WebSocketService(webSocketUrl);
  }
  
  async makePredictionWithStreaming(
    prompt: string,
    onTextChunk: (text: string) => void,
    onToolUse: (toolName: string, input: any) => void,
    onComplete: (finalResponse: any) => void,
    onError: (error: string) => void
  ): Promise<void> {
    // Streaming prediction logic
  }
}
```

### Step 3: Create Streaming Component

**frontend/src/components/StreamingPrediction.tsx:**
- React component with real-time text display
- WebSocket connection management
- Streaming text accumulation
- Final prediction display

### Step 4: Update App.tsx

Added new navigation option for streaming predictions:
- Updated navigation controls to include "Streaming Call" option
- Added conditional rendering for StreamingPrediction component
- Updated type definitions to include 'streaming' view

### Step 5: Environment Configuration

Updated frontend/.env:
```
VITE_WEBSOCKET_URL=wss://0yv5r2auh5.execute-api.us-west-2.amazonaws.com/prod
```

## Key Implementation Decisions

### 1. Dependency Management
- Initially tried to add Strands to make_call handler but encountered build issues
- Solution: Used existing strands_make_call directory which already had working dependencies

### 2. WebSocket Handler Evolution
- Started with simple mock streaming handler to test infrastructure
- Evolved to full Strands integration once WebSocket functionality was verified

### 3. Permissions
- Added comprehensive Bedrock permissions including InvokeModelWithResponseStream
- Added execute-api:ManageConnections for WebSocket communication

### 4. Frontend Architecture
- Created separate WebSocket and Prediction services for modularity
- Used React hooks for state management and cleanup
- Implemented real-time text accumulation for streaming display

## Final Result

Successfully implemented real-time WebSocket streaming with:
- ✅ WebSocket API Gateway with proper routing
- ✅ Strands Agent integration with streaming callbacks
- ✅ Real-time text streaming to React frontend
- ✅ Tool usage visibility (current_time, date parsing)
- ✅ Rich prediction verification with comprehensive details
- ✅ Timezone-aware date handling
- ✅ Error handling and connection management

The implementation provides a much better user experience with immediate feedback and detailed AI-generated verification methods.