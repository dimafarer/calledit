# CalledIt Streaming Implementation: Step-by-Step Guide

This document provides a practical, step-by-step approach to implementing WebSocket streaming in your CalledIt application. We'll break down the process into manageable chunks that you can implement one at a time.

## Phase 1: Backend Setup

### Step 1: Create WebSocket Handler Directory

First, let's create a directory structure for our WebSocket handlers:

```bash
mkdir -p backend/calledit-backend/handlers/websocket
```

### Step 2: Create Basic WebSocket Handlers

Create the connect handler:

```bash
# Create connect.py
cat > backend/calledit-backend/handlers/websocket/connect.py << 'EOF'
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
EOF
```

Create the disconnect handler:

```bash
# Create disconnect.py
cat > backend/calledit-backend/handlers/websocket/disconnect.py << 'EOF'
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
EOF
```

### Step 3: Create the Streaming Lambda Function

Create the streaming prediction handler:

```bash
# Create make_call_stream.py
cat > backend/calledit-backend/handlers/make_call/make_call_stream.py << 'EOF'
import json
import boto3
import os
from datetime import datetime
from strands import Agent

def lambda_handler(event, context):
    """
    Handle prediction requests and stream responses back to the client.
    """
    print("WebSocket message event:", event)
    
    # Extract connection ID for WebSocket
    connection_id = event.get('requestContext', {}).get('connectionId')
    domain_name = event.get('requestContext', {}).get('domainName')
    stage = event.get('requestContext', {}).get('stage')
    
    if not connection_id or not domain_name or not stage:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing WebSocket connection information'})
        }
    
    # Set up API Gateway Management API client
    api_gateway_management_api = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f"https://{domain_name}/{stage}"
    )
    
    # Get the prompt from the event body
    try:
        body = json.loads(event.get('body', '{}'))
        prompt = body.get('prompt', '')
        
        if not prompt:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No prompt provided'})
            }
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Invalid request body: {str(e)}'})
        }
    
    # Get current date and time
    current_datetime = datetime.now()
    formatted_date = current_datetime.strftime("%Y-%m-%d")
    formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    
    # Define callback handler for streaming
    def stream_callback_handler(**kwargs):
        """
        Callback handler that streams responses back to the client.
        """
        try:
            if "data" in kwargs:
                # Send text chunks to the client
                api_gateway_management_api.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        "type": "text",
                        "content": kwargs["data"]
                    })
                )
            elif "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
                # Send tool usage info
                api_gateway_management_api.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        "type": "tool",
                        "name": kwargs["current_tool_use"]["name"],
                        "input": kwargs["current_tool_use"].get("input", {})
                    })
                )
            elif kwargs.get("complete", False):
                # Send completion notification
                api_gateway_management_api.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        "type": "status",
                        "status": "complete"
                    })
                )
        except Exception as e:
            print(f"Error sending to WebSocket: {str(e)}")
    
    # Create agent with streaming callback
    agent = Agent(
        callback_handler=stream_callback_handler,
        system_prompt="""You are a prediction verification expert. Your task is to:
            1. Analyze predictions
            2. Create structured verification criteria
            3. Specify how to verify the prediction"""
    )
    
    # Process the prompt with streaming
    user_prompt = f"""Create a structured verification format for this prediction: {prompt}
        
        Today's date is {formatted_date} and the current time is {formatted_datetime}.
        
        Format the response as a JSON object with:
        - prediction_statement
        - verification_date (use a realistic future date based on the prediction and today's date)
        - verification_method (source, criteria, steps)
        - initial_status (pending)"""
    
    try:
        # Send initial message
        api_gateway_management_api.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                "type": "status",
                "status": "processing",
                "message": "Processing your prediction..."
            })
        )
        
        # This will stream responses via the callback handler
        full_response = agent(user_prompt)
        
        # Send the complete response
        api_gateway_management_api.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                "type": "complete",
                "content": full_response
            })
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'Streaming completed'})
        }
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        try:
            # Notify client of error
            api_gateway_management_api.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    "type": "error",
                    "message": str(e)
                })
            )
        except:
            pass
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
EOF
```

### Step 4: Update Requirements

Make sure your `requirements.txt` includes the necessary dependencies:

```bash
# Update requirements.txt
cat >> backend/calledit-backend/requirements.txt << 'EOF'
strands>=0.1.0
EOF
```

### Step 5: Update SAM Template

Create a new file with just the WebSocket additions to your SAM template:

```bash
# Create websocket_additions.yaml
cat > backend/calledit-backend/websocket_additions.yaml << 'EOF'
# WebSocket API resources
  WebSocketApi:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: CalledItWebSocketAPI
      ProtocolType: WEBSOCKET
      RouteSelectionExpression: "$request.body.action"

  ConnectRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref WebSocketApi
      RouteKey: $connect
      AuthorizationType: NONE
      OperationName: ConnectRoute
      Target: !Join
        - '/'
        - - 'integrations'
          - !Ref ConnectIntegration

  DisconnectRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref WebSocketApi
      RouteKey: $disconnect
      AuthorizationType: NONE
      OperationName: DisconnectRoute
      Target: !Join
        - '/'
        - - 'integrations'
          - !Ref DisconnectIntegration

  MakeCallStreamRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref WebSocketApi
      RouteKey: makecall
      AuthorizationType: NONE
      OperationName: MakeCallStreamRoute
      Target: !Join
        - '/'
        - - 'integrations'
          - !Ref MakeCallStreamIntegration

  ConnectIntegration:
    Type: AWS::ApiGatewayV2::Integration
    Properties:
      ApiId: !Ref WebSocketApi
      IntegrationType: AWS_PROXY
      IntegrationUri: !Sub arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${ConnectFunction.Arn}/invocations

  DisconnectIntegration:
    Type: AWS::ApiGatewayV2::Integration
    Properties:
      ApiId: !Ref WebSocketApi
      IntegrationType: AWS_PROXY
      IntegrationUri: !Sub arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${DisconnectFunction.Arn}/invocations

  MakeCallStreamIntegration:
    Type: AWS::ApiGatewayV2::Integration
    Properties:
      ApiId: !Ref WebSocketApi
      IntegrationType: AWS_PROXY
      IntegrationUri: !Sub arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${MakeCallStreamFunction.Arn}/invocations

  WebSocketDeployment:
    Type: AWS::ApiGatewayV2::Deployment
    DependsOn:
      - ConnectRoute
      - DisconnectRoute
      - MakeCallStreamRoute
    Properties:
      ApiId: !Ref WebSocketApi

  WebSocketStage:
    Type: AWS::ApiGatewayV2::Stage
    Properties:
      ApiId: !Ref WebSocketApi
      DeploymentId: !Ref WebSocketDeployment
      StageName: prod
      AutoDeploy: true

  # Lambda functions for WebSocket API
  ConnectFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: handlers/websocket/
      Handler: connect.lambda_handler
      Runtime: python3.12
      Policies:
        - Statement:
            - Effect: Allow
              Action:
                - 'execute-api:ManageConnections'
              Resource: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${WebSocketApi}/*'

  DisconnectFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: handlers/websocket/
      Handler: disconnect.lambda_handler
      Runtime: python3.12
      Policies:
        - Statement:
            - Effect: Allow
              Action:
                - 'execute-api:ManageConnections'
              Resource: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${WebSocketApi}/*'

  MakeCallStreamFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: handlers/make_call/
      Handler: make_call_stream.lambda_handler
      Runtime: python3.12
      Timeout: 300  # 5 minutes
      MemorySize: 512
      Policies:
        - AmazonDynamoDBFullAccess
        - Statement:
            - Effect: Allow
              Action:
                - 'bedrock:InvokeModel'
              Resource: '*'
        - Statement:
            - Effect: Allow
              Action:
                - 'execute-api:ManageConnections'
              Resource: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${WebSocketApi}/*'

  # Lambda permissions
  ConnectFunctionPermission:
    Type: AWS::Lambda::Permission
    Properties:
      Action: lambda:InvokeFunction
      FunctionName: !Ref ConnectFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${WebSocketApi}/*/$connect'

  DisconnectFunctionPermission:
    Type: AWS::Lambda::Permission
    Properties:
      Action: lambda:InvokeFunction
      FunctionName: !Ref DisconnectFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${WebSocketApi}/*/$disconnect'

  MakeCallStreamFunctionPermission:
    Type: AWS::Lambda::Permission
    Properties:
      Action: lambda:InvokeFunction
      FunctionName: !Ref MakeCallStreamFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${WebSocketApi}/*/makecall'

  # Outputs
  WebSocketApiEndpoint:
    Description: "WebSocket API endpoint URL"
    Value: !Sub "wss://${WebSocketApi}.execute-api.${AWS::Region}.amazonaws.com/${WebSocketStage}"
EOF
```

Now you'll need to manually merge these additions into your main `template.yaml` file.

## Phase 2: Deploy and Test Backend

### Step 1: Build and Deploy

```bash
cd backend/calledit-backend
sam build
sam deploy --guided
```

During the guided deployment, make sure to:
1. Enter a unique stack name (e.g., `calledit-backend-streaming`)
2. Choose your AWS region
3. Accept the default parameter values
4. Confirm changes before deploying

### Step 2: Note the WebSocket URL

After deployment, note the WebSocket URL from the CloudFormation outputs:

```bash
aws cloudformation describe-stacks --stack-name calledit-backend-streaming --query "Stacks[0].Outputs[?OutputKey=='WebSocketApiEndpoint'].OutputValue" --output text
```

This URL will be used in your frontend application.

### Step 3: Test the WebSocket API

You can use a tool like `wscat` to test your WebSocket API:

```bash
# Install wscat if you don't have it
npm install -g wscat

# Connect to your WebSocket API
wscat -c wss://your-websocket-api-id.execute-api.region.amazonaws.com/prod

# Send a test message
{"action":"makecall","prompt":"Bitcoin will reach $100,000 by the end of 2025"}
```

You should see streaming responses coming back from your Lambda function.

## Phase 3: Frontend Implementation

### Step 1: Create WebSocket Service

Create a new file at `frontend/src/services/websocket.ts`:

```typescript
// WebSocket service for handling streaming predictions
export class WebSocketService {
  private socket: WebSocket | null = null;
  private messageHandlers: Map<string, (data: any) => void> = new Map();
  private connectionPromise: Promise<void> | null = null;
  private resolveConnection: (() => void) | null = null;
  private rejectConnection: ((error: Error) => void) | null = null;

  constructor(private url: string) {}

  // Connect to the WebSocket server
  connect(): Promise<void> {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      return Promise.resolve();
    }

    this.connectionPromise = new Promise((resolve, reject) => {
      this.resolveConnection = resolve;
      this.rejectConnection = reject;

      try {
        this.socket = new WebSocket(this.url);

        this.socket.onopen = () => {
          console.log('WebSocket connection established');
          if (this.resolveConnection) {
            this.resolveConnection();
          }
        };

        this.socket.onclose = () => {
          console.log('WebSocket connection closed');
        };

        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          if (this.rejectConnection) {
            this.rejectConnection(new Error('Failed to connect to WebSocket server'));
          }
        };

        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            const type = data.type;

            if (this.messageHandlers.has(type)) {
              this.messageHandlers.get(type)!(data);
            } else {
              console.log(`No handler for message type: ${type}`, data);
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };
      } catch (error) {
        if (this.rejectConnection) {
          this.rejectConnection(error as Error);
        }
      }
    });

    return this.connectionPromise;
  }

  // Disconnect from the WebSocket server
  disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  // Send a message to the WebSocket server
  async send(action: string, data: any): Promise<void> {
    await this.connect();

    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const message = JSON.stringify({
        action,
        ...data,
      });
      this.socket.send(message);
    } else {
      throw new Error('WebSocket is not connected');
    }
  }

  // Register a handler for a specific message type
  onMessage(type: string, handler: (data: any) => void): void {
    this.messageHandlers.set(type, handler);
  }

  // Remove a handler for a specific message type
  offMessage(type: string): void {
    this.messageHandlers.delete(type);
  }
}
```

### Step 2: Create Prediction Service

Create a new file at `frontend/src/services/prediction.ts`:

```typescript
import { WebSocketService } from './websocket';

export class PredictionService {
  private webSocketService: WebSocketService;

  constructor(webSocketUrl: string) {
    this.webSocketService = new WebSocketService(webSocketUrl);
  }

  // Make a prediction with streaming response
  async makePredictionWithStreaming(
    prompt: string,
    onTextChunk: (text: string) => void,
    onToolUse: (toolName: string, input: any) => void,
    onComplete: (finalResponse: any) => void,
    onError: (error: string) => void
  ): Promise<void> {
    try {
      // Register handlers for different message types
      this.webSocketService.onMessage('text', (data) => {
        onTextChunk(data.content);
      });

      this.webSocketService.onMessage('tool', (data) => {
        onToolUse(data.name, data.input);
      });

      this.webSocketService.onMessage('complete', (data) => {
        onComplete(data.content);
      });

      this.webSocketService.onMessage('error', (data) => {
        onError(data.message);
      });

      // Connect and send the prediction request
      await this.webSocketService.connect();
      await this.webSocketService.send('makecall', { prompt });
    } catch (error) {
      onError((error as Error).message);
    }
  }

  // Clean up resources
  cleanup(): void {
    this.webSocketService.disconnect();
  }
}
```

### Step 3: Create Streaming Prediction Component

Create a new file at `frontend/src/components/StreamingPrediction.tsx`:

```tsx
import React, { useState, useEffect, useRef } from 'react';
import { PredictionService } from '../services/prediction';

interface StreamingPredictionProps {
  webSocketUrl: string;
}

const StreamingPrediction: React.FC<StreamingPredictionProps> = ({ webSocketUrl }) => {
  const [prompt, setPrompt] = useState('');
  const [streamingText, setStreamingText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [prediction, setPrediction] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const predictionServiceRef = useRef<PredictionService | null>(null);

  useEffect(() => {
    // Initialize the prediction service
    predictionServiceRef.current = new PredictionService(webSocketUrl);

    // Clean up on unmount
    return () => {
      if (predictionServiceRef.current) {
        predictionServiceRef.current.cleanup();
      }
    };
  }, [webSocketUrl]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!prompt.trim() || !predictionServiceRef.current) {
      return;
    }

    setIsLoading(true);
    setStreamingText('');
    setPrediction(null);
    setError(null);

    try {
      await predictionServiceRef.current.makePredictionWithStreaming(
        prompt,
        // Text chunk handler
        (text) => {
          setStreamingText((prev) => prev + text);
        },
        // Tool use handler
        (toolName, input) => {
          setStreamingText((prev) => 
            prev + `\n[Using tool: ${toolName}]\n`
          );
        },
        // Complete handler
        (finalResponse) => {
          setPrediction(finalResponse);
          setIsLoading(false);
        },
        // Error handler
        (errorMessage) => {
          setError(errorMessage);
          setIsLoading(false);
        }
      );
    } catch (err) {
      setError((err as Error).message);
      setIsLoading(false);
    }
  };

  const handleSavePrediction = () => {
    // Implement logic to save the prediction to your backend
    console.log('Saving prediction:', prediction);
  };

  return (
    <div className="streaming-prediction">
      <h2>Make a Prediction</h2>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="prediction-input">Your Prediction:</label>
          <textarea
            id="prediction-input"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter your prediction..."
            rows={4}
            disabled={isLoading}
            className="form-control"
          />
        </div>
        
        <button 
          type="submit" 
          disabled={isLoading || !prompt.trim()} 
          className="btn btn-primary"
        >
          {isLoading ? 'Processing...' : 'Make Prediction'}
        </button>
      </form>
      
      {error && (
        <div className="error-message">
          <p>Error: {error}</p>
        </div>
      )}
      
      {streamingText && (
        <div className="streaming-response">
          <h3>Processing your prediction...</h3>
          <div className="streaming-text">
            {streamingText}
          </div>
        </div>
      )}
      
      {prediction && (
        <div className="prediction-result">
          <h3>Prediction Details</h3>
          <div className="prediction-json">
            <pre>{JSON.stringify(prediction, null, 2)}</pre>
          </div>
          <button 
            onClick={handleSavePrediction}
            className="btn btn-success"
          >
            Log Call
          </button>
        </div>
      )}
    </div>
  );
};

export default StreamingPrediction;
```

### Step 4: Update Environment Configuration

Create or update your `.env` file to include the WebSocket URL:

```
REACT_APP_API_URL=https://your-api-id.execute-api.region.amazonaws.com/prod
REACT_APP_WEBSOCKET_URL=wss://your-websocket-api-id.execute-api.region.amazonaws.com/prod
```

### Step 5: Update App Component

Update your main App component to use the new StreamingPrediction component:

```tsx
import React from 'react';
import StreamingPrediction from './components/StreamingPrediction';
import './App.css';

function App() {
  const webSocketUrl = process.env.REACT_APP_WEBSOCKET_URL || '';
  
  return (
    <div className="App">
      <header className="App-header">
        <h1>CalledIt: Prediction Verification Platform</h1>
      </header>
      <main>
        <StreamingPrediction webSocketUrl={webSocketUrl} />
      </main>
    </div>
  );
}

export default App;
```

## Phase 4: Testing and Refinement

### Step 1: Start Frontend Development Server

```bash
cd frontend
npm run dev
```

### Step 2: Test the Streaming Functionality

1. Open your browser to `http://localhost:5173`
2. Enter a prediction in the form
3. Submit the form and observe the streaming response
4. Verify that the final prediction is displayed correctly

### Step 3: Debug Common Issues

If you encounter issues:

1. Check browser console for errors
2. Verify WebSocket URL is correct
3. Check CloudWatch logs for Lambda errors
4. Test WebSocket connection with wscat

### Step 4: Refine the UI

Enhance the streaming experience:
- Add loading indicators
- Improve text formatting
- Add animations for incoming text
- Style the streaming text area

## Next Steps

After implementing the basic streaming functionality, consider these enhancements:

1. **Authentication**: Add Cognito authentication to your WebSocket API
2. **Connection Management**: Store connection IDs in DynamoDB
3. **Error Handling**: Implement robust error handling and retry mechanisms
4. **Analytics**: Track user engagement with the streaming feature
5. **UI Improvements**: Add animations and better formatting for streaming text

## Conclusion

You've now implemented real-time streaming for your CalledIt prediction verification platform! This implementation provides a much more engaging and responsive user experience by showing AI-generated content as it's being created.

The modular architecture allows for easy extension and maintenance as your application grows. Continue to refine and enhance the implementation based on user feedback and your specific requirements.