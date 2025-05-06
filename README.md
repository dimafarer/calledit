# Called It - AI-Powered Prediction Verification Platform

Called It is a serverless web application that helps users make and track predictions with AI-powered verification methods. The platform enables users to create predictions, automatically generates structured verification criteria, and allows tracking of prediction outcomes over time.

The application combines AWS serverless technologies with AI capabilities from Amazon Bedrock to provide an intuitive prediction management system. Key features include:
- AI-assisted verification method generation using Amazon Bedrock
- Secure user authentication via Amazon Cognito
- Persistent storage of predictions in DynamoDB
- Real-time prediction status tracking
- Responsive React-based frontend with TypeScript

## Repository Structure
```
.
├── backend/                      # Serverless backend application
│   └── calledit-backend/
│       ├── handlers/            # Lambda function handlers
│       │   ├── auth_token/      # Cognito token management
│       │   ├── hello_world/     # Health check endpoint
│       │   ├── list_predictions/# Prediction retrieval
│       │   ├── make_call/       # Prediction creation with Bedrock
│       │   ├── prompt_bedrock/  # Bedrock integration
│       │   └── write_to_db/     # DynamoDB write operations
│       ├── template.yaml        # AWS SAM infrastructure template
│       └── tests/              # Backend test suites
├── frontend/                    # React TypeScript frontend
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── contexts/          # React contexts (auth)
│   │   ├── services/          # API and auth services
│   │   └── utils/             # Utility functions
│   └── package.json           # Frontend dependencies
└── docs/                       # Infrastructure documentation
```

## Usage Instructions
### Prerequisites
- Node.js 16+ for frontend development
- Python 3.12 for backend development
- AWS CLI configured with appropriate credentials
- AWS SAM CLI for local development and deployment
- Docker for local development (optional)

### Installation

#### Backend Setup
```bash
# Install backend dependencies
cd backend/calledit-backend
pip install -r requirements.txt

# Deploy using SAM
sam build
sam deploy --guided
```

#### Frontend Setup
```bash
# Install frontend dependencies
cd frontend
npm install

# Start development server
npm run dev
```

### Quick Start
1. Configure AWS credentials and environment variables:
```bash
# Create .env file from template
cp frontend/.env.example frontend/.env
# Update with your AWS configuration
```

2. Deploy the backend:
```bash
cd backend/calledit-backend
sam deploy --guided
```

3. Start the frontend development server:
```bash
cd frontend
npm run dev
```

4. Navigate to http://localhost:5173 in your browser

### More Detailed Examples

#### Making a Prediction
```typescript
// Using the API service
const response = await apiService.makeCall({
  prompt: "Tesla stock will reach $300 by end of 2024",
});

// Response includes verification method
console.log(response.verification_method);
```

#### Listing User Predictions
```typescript
// Fetch authenticated user's predictions
const predictions = await apiService.listPredictions();
```

### Troubleshooting

#### Common Issues

1. Authentication Errors
- Error: "User not authenticated"
- Solution: Ensure Cognito user pool is properly configured and user is signed in
- Check browser console for token expiration

2. API Gateway Issues
- Error: CORS errors in browser console
- Solution: Verify CORS settings in `template.yaml`
- Ensure API Gateway endpoints are properly configured

3. Bedrock Integration
- Error: "Cannot invoke Bedrock model"
- Solution: Check IAM permissions for Lambda functions
- Verify Bedrock service availability in your region

#### Debugging
- Enable debug mode in SAM template:
```yaml
Metadata:
  Debug: true
```
- Check CloudWatch logs for Lambda functions
- Frontend debug logs: `localStorage.debug = 'calledit:*'`

## Data Flow
The application follows a serverless event-driven architecture where predictions are processed through AI verification and stored for tracking.

```ascii
[Frontend] -> [API Gateway] -> [Lambda Functions] -> [Bedrock/DynamoDB]
     ^                               |                      |
     |                               |                      |
     +-------------------------------+----------------------+
```

Key component interactions:
1. Frontend authenticates via Cognito
2. Authenticated requests route through API Gateway
3. Lambda functions process requests and interact with services
4. Bedrock generates verification methods for predictions
5. DynamoDB stores prediction data and user associations
6. API Gateway returns responses to frontend
7. Frontend updates UI based on response data

## Infrastructure

![Infrastructure diagram](./docs/infra.svg)
The application uses AWS SAM to define and deploy the following resources:

### API Gateway
- CallitAPI: Main REST API with Cognito authorizer

### Lambda Functions
- HelloWorldFunction: Health check endpoint
- PromptBedrockFunction: Bedrock integration
- MakeCall: Prediction creation
- LogCall: DynamoDB write operations
- ListPredictions: Prediction retrieval
- AuthTokenFunction: Token management

### Authentication
- CognitoUserPool: User management
- UserPoolClient: Application client
- UserPoolDomain: Hosted UI domain

### Storage
- DynamoDB table (calledit-db): Prediction storage

## Deployment
1. Prerequisites:
- AWS CLI configured
- SAM CLI installed
- Node.js and Python installed

2. Backend Deployment:
```bash
cd backend/calledit-backend
sam build
sam deploy --guided
```

3. Frontend Deployment:
```bash
cd frontend
npm run build
# Deploy build output to hosting service (e.g., S3/CloudFront)
```

4. Environment Configuration:
- Update frontend environment variables with deployed backend URLs
- Configure Cognito user pool settings
- Set up CloudFront distribution (optional)