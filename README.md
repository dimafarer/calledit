# CalledIt: A Serverless Prediction Verification Platform

CalledIt is a serverless web application that enables users to make predictions, track their accuracy, and verify outcomes through structured verification methods. Built on AWS serverless architecture, it provides a robust platform for creating, managing, and validating predictions with automated verification guidance.

The application combines AWS Cognito for authentication, AWS Lambda for serverless compute, and DynamoDB for data persistence. The frontend is built with React and TypeScript, providing a responsive and intuitive user interface. The backend leverages Amazon Bedrock for AI-powered verification method generation and implements a structured approach to prediction tracking and validation.

## Repository Structure
```
.
├── backend/                      # Backend serverless application
│   └── calledit-backend/
│       ├── handlers/            # Lambda function handlers
│       │   ├── auth_token/      # Cognito token management
│       │   ├── make_call/       # Prediction creation with Bedrock
│       │   ├── list_predictions/# Retrieve user predictions
│       │   └── write_to_db/     # DynamoDB write operations
│       ├── template.yaml        # SAM template for AWS resources
│       └── tests/               # Backend unit tests
├── frontend/                    # React TypeScript frontend
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── services/          # API and auth services
│   │   └── utils/             # Utility functions
│   └── package.json           # Frontend dependencies
└── docs/                      # Documentation and infrastructure diagrams
```

## Usage Instructions
### Prerequisites
- Node.js 16.x or later
- Python 3.12
- AWS CLI configured with appropriate credentials
- AWS SAM CLI installed
- Docker (for local development)

### Installation

#### Backend Setup
```bash
# Navigate to backend directory
cd backend/calledit-backend

# Install Python dependencies
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
# Edit .env with your AWS details from the backend deployment
```

### Quick Start
1. Start the frontend development server:
```bash
cd frontend
npm run dev
```

2. Open your browser to `http://localhost:5173`

3. Log in using your Cognito credentials

4. Create a prediction:
   - Enter your prediction in the input field
   - Click "Make Prediction"
   - Review the generated verification method
   - Click "Log Call" to save your prediction

### More Detailed Examples

#### Making a Prediction
```typescript
// Example prediction format
{
  "prediction": "Bitcoin will reach $100,000 by the end of 2025",
  "verification_method": {
    "source": ["CoinGecko API", "Bloomberg Terminal"],
    "criteria": ["BTC/USD price exceeds $100,000"],
    "steps": ["Check BTC price on December 31, 2025"]
  }
}
```

### Troubleshooting

#### Common Issues

1. CORS Errors
```bash
# Check CORS configuration in template.yaml
# Ensure your frontend origin is listed in the CORS configuration
```

2. Authentication Issues
```bash
# Verify Cognito configuration
aws cognito-idp describe-user-pool --user-pool-id YOUR_POOL_ID

# Check user status
aws cognito-idp admin-get-user --user-pool-id YOUR_POOL_ID --username USER_EMAIL
```

3. API Gateway Errors
- Enable CloudWatch logs for API Gateway
- Check Lambda function logs:
```bash
sam logs -n FunctionName --stack-name calledit-backend
```

## Data Flow
The application follows a serverless event-driven architecture for handling predictions and verifications.

```ascii
User -> Cognito Auth -> API Gateway -> Lambda Functions -> DynamoDB
                                   |
                                   -> Bedrock (AI) -> Verification Format
```

Key component interactions:
1. User authenticates through Cognito user pool
2. Frontend makes authenticated API calls through API Gateway
3. Lambda functions process requests and interact with DynamoDB
4. Bedrock AI generates structured verification methods
5. DynamoDB stores predictions and verification data
6. API Gateway returns responses to frontend
7. Frontend updates UI based on response data

## Infrastructure

![Infrastructure diagram](./docs/infra.svg)
The application uses the following AWS resources:

### API Gateway
- CallitAPI (AWS::Serverless::Api)
  - Handles all HTTP endpoints
  - Implements CORS
  - Uses Cognito authorizer

### Lambda Functions
- MakeCall: Generates predictions using Bedrock
- LogCall: Writes predictions to DynamoDB
- ListPredictions: Retrieves user predictions
- AuthTokenFunction: Handles Cognito token exchange

### Authentication
- CognitoUserPool: Manages user authentication
- UserPoolClient: Configures OAuth flows
- UserPoolDomain: Provides hosted UI for authentication

### Database
- DynamoDB table "calledit-db" for storing predictions and verification data