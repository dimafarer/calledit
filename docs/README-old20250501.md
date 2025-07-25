# Call It!! - AI-Powered Prediction Verification Platform

Call It!! is a web application that helps users make and verify predictions using AI technology. The platform enables users to create predictions, get AI-generated verification methods, and track the outcomes of their predictions over time.

The application combines a React-based frontend with a serverless AWS backend powered by AWS Lambda and Amazon Bedrock. Users can authenticate using Amazon Cognito, make predictions that are analyzed by AI to generate structured verification methods, and maintain a personal history of their predictions. The system provides a comprehensive verification framework that includes specific criteria, steps, and sources for validating each prediction.

## Repository Structure
```
.
├── backend/                      # Backend serverless application
│   └── calledit-backend/        
│       ├── handlers/            # Lambda function handlers for different endpoints
│       │   ├── auth_token/      # Cognito token management
│       │   ├── make_call/       # AI prediction generation using Bedrock
│       │   ├── list_predictions/# Retrieval of user predictions
│       │   └── write_to_db/     # Database operations for predictions
│       ├── template.yaml        # AWS SAM template for infrastructure
│       └── tests/               # Backend unit and integration tests
├── frontend/                    # React frontend application
│   ├── src/
│   │   ├── components/         # React components (predictions, auth, etc.)
│   │   ├── contexts/          # React contexts for state management
│   │   ├── services/         # API and authentication services
│   │   └── utils/           # Utility functions and helpers
│   └── package.json         # Frontend dependencies and scripts
```

## Usage Instructions
### Prerequisites
- Node.js 16.x or later
- Python 3.12
- AWS CLI configured with appropriate credentials
- AWS SAM CLI installed
- Docker (for local development)

### Installation

#### Backend
```bash
# Navigate to backend directory
cd backend/calledit-backend

# Install Python dependencies
pip install -r requirements.txt

# Deploy using SAM
sam build
sam deploy --guided
```

#### Frontend
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create .env file from example
cp .env.example .env

# Update environment variables with your AWS configuration
# Start development server
npm run dev
```

### Quick Start
1. Sign up for an account using the Cognito authentication system
2. Navigate to the "Make a Call" section
3. Enter your prediction in the input field
4. Review the AI-generated verification method
5. Save your prediction to track its outcome

### More Detailed Examples

Making a Prediction:
```typescript
// Example prediction input
const prediction = {
  statement: "Company X will release a new product in Q3 2024",
  verificationDate: "2024-09-30",
  verificationMethod: {
    sources: ["Official company announcements", "Press releases"],
    criteria: ["Product announcement", "Release date confirmation"],
    steps: ["Monitor company's official channels", "Track press releases"]
  }
};
```

### Troubleshooting

Common Issues:
1. Authentication Errors
   - Error: "User is not authenticated"
   - Solution: Ensure you're logged in and your tokens haven't expired
   - Check browser console for specific error messages

2. API Connection Issues
   - Error: "Failed to fetch predictions"
   - Solution: Verify API endpoint configuration in .env file
   - Check network tab for specific HTTP errors

3. Prediction Submission Failures
   - Error: "Failed to save prediction"
   - Solution: 
     - Verify DynamoDB permissions
     - Check prediction format matches expected schema
     - Enable debug logging: `localStorage.setItem('debug', 'true')`

## Data Flow
The application follows a structured flow for handling predictions and verification:

```ascii
User Input -> Frontend -> API Gateway -> Lambda Functions -> Bedrock (AI) -> DynamoDB
     ^                                                           |
     |                                                          v
     +---------------------------- Response --------------------->
```

Key Component Interactions:
1. Frontend React components collect user input and manage state
2. Authentication service handles Cognito integration
3. API Gateway routes requests to appropriate Lambda functions
4. Bedrock service generates structured verification methods
5. DynamoDB stores prediction data and user history
6. Lambda functions coordinate between services and handle business logic

## Infrastructure

![Infrastructure diagram](./docs/infra.svg)
The application uses the following AWS resources:

Lambda Functions:
- HelloWorldFunction: Basic health check endpoint
- PromptBedrockFunction: Handles AI prompt generation
- MakeCall: Processes prediction requests
- LogCall: Stores predictions in DynamoDB
- ListPredictions: Retrieves user predictions
- AuthTokenFunction: Manages Cognito authentication

API Gateway:
- CallitAPI: Main API endpoint with Cognito authorizer

Authentication:
- CognitoUserPool: User management and authentication
- UserPoolClient: Client application configuration
- UserPoolDomain: Hosted UI domain for authentication

Database:
- DynamoDB table: Stores user predictions and verification data