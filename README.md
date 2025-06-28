# CalledIt: A Serverless Prediction Verification Platform

CalledIt is a serverless web application that enables users to make predictions, track their accuracy, and verify outcomes through structured verification methods. Built on AWS serverless architecture, it provides a robust platform for creating, managing, and validating predictions with AI-powered verification guidance.

The application combines AWS Cognito for authentication, AWS Lambda for serverless compute, and DynamoDB for data persistence. The frontend is built with React and TypeScript, providing a responsive and intuitive user interface. The backend leverages **Strands agents** for AI orchestration, Amazon Bedrock for reasoning, and **real-time WebSocket streaming** for immediate user feedback during prediction processing.

## Repository Structure
```
.
├── backend/                      # Backend serverless application
│   └── calledit-backend/
│       ├── handlers/            # Lambda function handlers
│       │   ├── auth_token/      # Cognito token management
│       │   ├── strands_make_call/ # Strands agent with streaming
│       │   ├── websocket/       # WebSocket connection handlers
│       │   ├── list_predictions/# Retrieve user predictions
│       │   └── write_to_db/     # DynamoDB write operations
│       ├── template.yaml        # SAM template for AWS resources
│       └── tests/               # Backend unit tests
├── frontend/                    # React TypeScript frontend
│   ├── src/
│   │   ├── components/         # React components including streaming
│   │   ├── services/          # API, auth, and WebSocket services
│   │   └── utils/             # Utility functions
│   └── package.json           # Frontend dependencies
├── strands/                     # Strands agent development
│   └── my_agent/               # Custom agent implementation
└── docs/                       # Documentation and infrastructure diagrams
```

## Usage Instructions
### Prerequisites
- Node.js 16.x or later
- Python 3.12
- AWS CLI configured with appropriate credentials
- AWS SAM CLI installed
- Docker (for local development)
- **Strands agents library** (installed via pip)

### Installation

#### Backend Setup
```bash
# Navigate to backend directory
cd backend/calledit-backend

# Install Python dependencies (including Strands)
pip install -r requirements.txt

# Deploy to AWS
sam build
sam deploy --guided
```

#### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create .env file from example
cp .env.example .env

# Update environment variables with your AWS configuration
# Add both REST API and WebSocket URLs from the backend deployment
# VITE_API_URL=https://your-api-gateway-url
# VITE_WEBSOCKET_URL=wss://your-websocket-api-url
```

### Quick Start
1. Start the frontend development server:
```bash
cd frontend
npm run dev
```

2. Open your browser to `http://localhost:5173`

3. Log in using your Cognito credentials

4. Create a prediction using streaming:
   - Click "Streaming Call" tab
   - Enter your prediction in the input field
   - Click "Make Call" and watch real-time AI processing
   - Review the generated verification method
   - Click "Log Call" to save your prediction

### More Detailed Examples

#### Making a Streaming Prediction
The application now uses Strands agents for intelligent prediction processing:

```typescript
// Example streaming prediction flow
1. User enters: "Bitcoin will hit $100k before 3pm today"
2. Strands agent processes with tools:
   - current_time tool for date/time context
   - Reasoning model for verification method generation
3. Real-time streaming shows:
   - "Processing your prediction with AI agent..."
   - "[Using tool: current_time]"
   - Generated verification method with timezone handling
4. Final structured output:
{
  "prediction_statement": "Bitcoin will reach $100,000 before 15:00:00 on 2025-01-27",
  "verification_date": "2025-01-27T15:00:00Z",
  "verification_method": {
    "source": ["CoinGecko API", "CoinMarketCap"],
    "criteria": ["BTC/USD price exceeds $100,000 before 15:00 UTC"],
    "steps": ["Check BTC price at 15:00:00 on January 27, 2025"]
  },
  "date_reasoning": "Converted 3pm to 15:00 24-hour format for precision"
}
```

### Troubleshooting

#### Common Issues

1. **WebSocket Connection Issues**
```bash
# Check WebSocket API deployment
aws apigatewayv2 get-apis

# Verify WebSocket URL in frontend .env
# VITE_WEBSOCKET_URL=wss://your-websocket-id.execute-api.region.amazonaws.com/prod
```

2. **Strands Agent Errors**
```bash
# Check agent function logs
sam logs -n MakeCallStreamFunction --stack-name calledit-backend

# Verify Strands dependencies in requirements.txt
# strands-agents>=0.1.0
# strands-agents-tools>=0.1.0
```

3. **Streaming Issues**
- Ensure WebSocket permissions are configured
- Check connection timeout settings (5 minutes default)
- Verify Bedrock streaming permissions:
```bash
# Required permissions:
# bedrock:InvokeModel
# bedrock:InvokeModelWithResponseStream
# execute-api:ManageConnections
```

4. **Authentication Issues**
```bash
# Verify Cognito configuration
aws cognito-idp describe-user-pool --user-pool-id YOUR_POOL_ID

# Check user status
aws cognito-idp admin-get-user --user-pool-id YOUR_POOL_ID --username USER_EMAIL
```

## Data Flow
The application follows a serverless event-driven architecture with real-time streaming capabilities.

```ascii
User -> Cognito Auth -> WebSocket API -> Strands Agent -> Bedrock (Reasoning)
                    |                      |              |
                    |                      -> Tools -> Real-time Stream
                    |
                    -> REST API -> Lambda Functions -> DynamoDB
```

Key component interactions:
1. User authenticates through Cognito user pool
2. **WebSocket connection** established for real-time streaming
3. **Strands agent** orchestrates between reasoning model and tools
4. **Streaming responses** sent back to frontend via WebSocket
5. Bedrock provides AI reasoning with **InvokeModelWithResponseStream**
6. Tools (current_time, etc.) provide context to the agent
7. Final predictions stored in DynamoDB via REST API
8. Frontend receives real-time updates during processing

## Infrastructure

![Infrastructure diagram](./docs/infra.svg)
The application uses the following AWS resources:

### API Gateways
- **CallitAPI** (AWS::Serverless::Api): REST API for CRUD operations
  - Handles authentication and data persistence
  - Implements CORS and Cognito authorization
- **WebSocketApi** (AWS::ApiGatewayV2::Api): Real-time streaming
  - Handles WebSocket connections for streaming responses
  - Routes: $connect, $disconnect, makecall

### Lambda Functions
- **MakeCallStreamFunction**: Strands agent with streaming via WebSocket
- **ConnectFunction/DisconnectFunction**: WebSocket connection management
- **LogCall**: Writes predictions to DynamoDB
- **ListPredictions**: Retrieves user predictions
- **AuthTokenFunction**: Handles Cognito token exchange

### AI & Orchestration
- **Strands Agents**: Orchestrate between reasoning models and tools
- **Amazon Bedrock**: AI reasoning with streaming support
- **Custom Tools**: current_time, date parsing utilities

### Authentication
- **CognitoUserPool**: Manages user authentication
- **UserPoolClient**: Configures OAuth flows
- **UserPoolDomain**: Provides hosted UI for authentication

### Database
- **DynamoDB** table "calledit-db" for storing predictions and verification data

### Key Features
- **Real-time Streaming**: WebSocket-based streaming for immediate feedback
- **Agent Orchestration**: Strands agents coordinate AI reasoning and tool usage
- **Timezone Intelligence**: Automatic timezone handling and 12/24-hour conversion
- **Structured Verification**: AI-generated verification methods with reasoning