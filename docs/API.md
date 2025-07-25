# CalledIt API Documentation

This document describes the REST and WebSocket APIs for the CalledIt prediction verification platform.

## Base URLs

- **REST API**: `https://{api-id}.execute-api.{region}.amazonaws.com/Prod`
- **WebSocket API**: `wss://{websocket-id}.execute-api.{region}.amazonaws.com/prod`

## Authentication

All authenticated endpoints require AWS Cognito JWT tokens in the Authorization header:

```
Authorization: Bearer {jwt-token}
```

## REST API Endpoints

### Authentication

#### POST /auth/token
Exchange authorization code for JWT tokens.

**Request Body:**
```json
{
  "code": "string",
  "redirect_uri": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "id_token": "string",
  "refresh_token": "string",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Predictions/Calls

#### POST /log-call
Save a prediction/call to the database.

**Authentication:** Required

**Request Body:**
```json
{
  "prediction": {
    "prediction_statement": "string",
    "verification_date": "2025-01-27T15:00:00Z",
    "prediction_date": "2025-01-27T10:30:00Z",
    "verifiable_category": "api_tool_verifiable",
    "category_reasoning": "string",
    "verification_method": {
      "source": ["string"],
      "criteria": ["string"],
      "steps": ["string"]
    },
    "initial_status": "pending",
    "timezone": "UTC",
    "user_timezone": "America/New_York",
    "date_reasoning": "string"
  }
}
```

**Response:**
```json
{
  "response": "Prediction logged successfully"
}
```

#### GET /list-predictions
Retrieve user's predictions/calls.

**Authentication:** Required

**Response:**
```json
{
  "results": [
    {
      "prediction_statement": "string",
      "verification_date": "2025-01-27T15:00:00Z",
      "prediction_date": "2025-01-27T10:30:00Z",
      "verifiable_category": "api_tool_verifiable",
      "category_reasoning": "string",
      "verification_method": {
        "source": ["string"],
        "criteria": ["string"],
        "steps": ["string"]
      },
      "initial_status": "pending"
    }
  ]
}
```

## WebSocket API

### Connection

Connect to the WebSocket API using the WebSocket URL. No authentication required for connection, but user context is needed for prediction processing.

### Events

#### Client → Server Events

##### makecall
Process a prediction with real-time streaming.

**Message Format:**
```json
{
  "action": "makecall",
  "prompt": "Bitcoin will hit $100k tomorrow",
  "timezone": "America/New_York"
}
```

#### Server → Client Events

##### status
Processing status updates.

**Message Format:**
```json
{
  "type": "status",
  "status": "processing",
  "message": "Processing your prediction with AI agent..."
}
```

##### text
Streaming text chunks from AI processing.

**Message Format:**
```json
{
  "type": "text",
  "content": "I'll analyze this prediction..."
}
```

##### tool
Tool usage notifications.

**Message Format:**
```json
{
  "type": "tool",
  "name": "current_time",
  "input": {}
}
```

##### complete
Final processed prediction result.

**Message Format:**
```json
{
  "type": "complete",
  "content": "{\"prediction_statement\":\"...\",\"verification_date\":\"...\",\"verifiable_category\":\"...\"}"
}
```

##### error
Error notifications.

**Message Format:**
```json
{
  "type": "error",
  "message": "Error description"
}
```

## Data Models

### Prediction/Call Object

```typescript
interface CallResponse {
  prediction_statement: string;
  verification_date: string;          // ISO 8601 UTC
  prediction_date?: string;           // ISO 8601 UTC
  verifiable_category?: string;       // One of 5 categories
  category_reasoning?: string;        // AI reasoning for category
  verification_method: {
    source: string[];                 // Verification sources
    criteria: string[];               // Verification criteria
    steps: string[];                  // Verification steps
  };
  initial_status: string;             // "pending", "verified", etc.
  timezone?: string;                  // Default: "UTC"
  user_timezone?: string;             // User's local timezone
  date_reasoning?: string;            // AI reasoning for dates
}
```

### Verifiability Categories

The system classifies predictions into 5 categories:

1. **`agent_verifiable`** - Can be verified using pure reasoning/knowledge
   - Example: "The sun will rise tomorrow"

2. **`current_tool_verifiable`** - Can be verified using only the current_time tool
   - Example: "It's currently past 11:00 PM"

3. **`strands_tool_verifiable`** - Requires Strands library tools (calculator, python_repl)
   - Example: "15% compound interest on $1000 over 5 years will exceed $2000"

4. **`api_tool_verifiable`** - Requires external API calls
   - Example: "Bitcoin will hit $100k tomorrow"

5. **`human_verifiable_only`** - Requires human observation/judgment
   - Example: "I will feel happy tomorrow"

## Error Handling

### HTTP Status Codes

- **200**: Success
- **400**: Bad Request - Invalid input data
- **401**: Unauthorized - Missing or invalid authentication
- **403**: Forbidden - Insufficient permissions
- **500**: Internal Server Error

### WebSocket Error Handling

WebSocket errors are sent as `error` type messages with descriptive error messages. The connection remains open unless there's a critical failure.

## Rate Limiting

- **REST API**: No explicit rate limiting (AWS API Gateway defaults apply)
- **WebSocket API**: Connection timeout of 5 minutes for idle connections
- **Prediction Processing**: Single prediction per WebSocket connection at a time

## CORS Configuration

The REST API supports CORS for the following origins:
- `http://localhost:5173` (development)
- `https://d2k653cdpjxjdu.cloudfront.net` (production)

## Examples

### Making a Streaming Prediction

```javascript
// Connect to WebSocket
const ws = new WebSocket('wss://your-websocket-url/prod');

// Send prediction
ws.send(JSON.stringify({
  action: 'makecall',
  prompt: 'Bitcoin will hit $100k tomorrow',
  timezone: 'America/New_York'
}));

// Handle responses
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'text':
      console.log('Streaming:', data.content);
      break;
    case 'tool':
      console.log('Using tool:', data.name);
      break;
    case 'complete':
      const prediction = JSON.parse(data.content);
      console.log('Final result:', prediction);
      break;
    case 'error':
      console.error('Error:', data.message);
      break;
  }
};
```

### Saving a Prediction

```javascript
// After getting prediction from WebSocket, save it
const response = await fetch('/log-call', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    prediction: predictionObject
  })
});
```

## Changelog

- **v1.0.0**: Added verifiability categorization to all endpoints
- **v0.9.0**: Added WebSocket streaming API
- **v0.8.0**: Initial REST API with basic prediction CRUD operations