# Implementing Real-Time Streaming for CalledIt Predictions

This guide provides a step-by-step approach to implementing real-time streaming responses from AWS Lambda to your React frontend using WebSockets. By the end of this implementation, users will see AI-generated prediction verification details as they're being created, rather than waiting for the complete response.

## Table of Contents

1. [Understanding the Architecture](#understanding-the-architecture)
2. [Setting Up WebSocket API Gateway](#setting-up-websocket-api-gateway)
3. [Creating the Streaming Lambda Function](#creating-the-streaming-lambda-function)
4. [Updating the SAM Template](#updating-the-sam-template)
5. [Implementing the React Frontend](#implementing-the-react-frontend)
6. [Testing and Troubleshooting](#testing-and-troubleshooting)
7. [Production Considerations](#production-considerations)

## Understanding the Architecture

### Current Architecture

Currently, the CalledIt application follows this flow for prediction creation:

1. User enters a prediction in the React frontend
2. Frontend makes a REST API call to API Gateway
3. API Gateway triggers the `make_call` Lambda function
4. Lambda calls Amazon Bedrock to generate verification details
5. Lambda returns the complete response to the frontend
6. Frontend displays the results

The main issue with this approach is that users must wait for the entire process to complete before seeing any feedback, which can take several seconds or more.

### Streaming Architecture

With WebSockets, we'll modify the flow to:

1. User enters a prediction in the React frontend
2. Frontend establishes a WebSocket connection with API Gateway
3. Frontend sends the prediction through the WebSocket
4. WebSocket API Gateway triggers the streaming Lambda function
5. Lambda begins processing with Amazon Bedrock using Strands SDK
6. **As the AI generates content, Lambda streams chunks back through the WebSocket**
7. **Frontend displays these chunks in real-time**
8. When complete, Lambda sends a final message and the frontend updates accordingly

This approach provides immediate feedback to users and improves the perceived performance of the application.

## Setting Up WebSocket API Gateway

### Step 1: Create WebSocket API in SAM Template

First, we need to define a WebSocket API in our SAM template. This API will handle the WebSocket connections and route messages to our Lambda function.

```yaml
WebSocketApi:
  Type: AWS::ApiGatewayV2::Api
  Properties:
    Name: CalledItWebSocketAPI
    ProtocolType: WEBSOCKET
    RouteSelectionExpression: "$request.body.action"
```

The `RouteSelectionExpression` determines how API Gateway routes incoming messages. In this case, it will use the "action" field in the message body.

### Step 2: Define WebSocket Routes

We need to define three essential routes for our WebSocket API:

1. `$connect` - Handles new connections
2. `$disconnect` - Handles disconnections
3. `makecall` - Handles prediction requests

```yaml
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
```

### Step 3: Create Route Integrations

Each route needs an integration that connects it to a Lambda function:

```yaml
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
```

### Step 4: Create a Deployment and Stage

To make our WebSocket API available, we need to create a deployment and stage:

```yaml
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
```

## Creating the Streaming Lambda Function

### Step 1: Define Lambda Functions in SAM Template

We need to create three Lambda functions for our WebSocket API:

```yaml
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
```

### Step 2: Create Lambda Function Permissions

We need to grant API Gateway permission to invoke our Lambda functions:

```yaml
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
```

### Step 3: Implement the Connect Lambda Function

Create a file at `handlers/websocket/connect.py`:

```python
import json

def lambda_handler(event, context):
    """
    Handle WebSocket connection events.
    
    This function is triggered when a client connects to the WebSocket API.
    It simply acknowledges the connection with a 200 status code.
    """
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Connected'})
    }
```

### Step 4: Implement the Disconnect Lambda Function

Create a file at `handlers/websocket/disconnect.py`:

```python
import json

def lambda_handler(event, context):
    """
    Handle WebSocket disconnection events.
    
    This function is triggered when a client disconnects from the WebSocket API.
    It simply acknowledges the disconnection with a 200 status code.
    """
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Disconnected'})
    }
```

### Step 5: Implement the Streaming Lambda Function

Create a file at `handlers/make_call/make_call_stream.py`:

```python
import json
import boto3
import os
from datetime import datetime
from strands import Agent

def lambda_handler(event, context):
    """
    Handle prediction requests and stream responses back to the client.
    
    This function:
    1. Extracts the connection ID and prompt from the event
    2. Sets up the API Gateway Management API client
    3. Creates a callback handler to stream responses
    4. Processes the prompt with the Strands Agent
    5. Streams the results back to the client
    """
    # Extract connection ID for WebSocket
    connection_id = event.get('requestContext', {}).get('connectionId')
    domain_name = event.get('requestContext', {}).get('domainName')
    stage = event.get('requestContext', {}).get('stage')
    
    # Set up API Gateway Management API client
    api_gateway_management_api = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f"https://{domain_name}/{stage}"
    )
    
    # Get the prompt from the event body
    body = json.loads(event.get('body', '{}'))
    prompt = body.get('prompt', '')
    
    # Get current date and time
    current_datetime = datetime.now()
    formatted_date = current_datetime.strftime("%Y-%m-%d")
    formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    
    # Define callback handler for streaming
    def stream_callback_handler(**kwargs):
        """
        Callback handler that streams responses back to the client.
        
        This function is called by the Strands Agent as it generates content.
        It sends different types of events to the client based on the content.
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
```

### Step 6: Update Requirements

Make sure to update your `requirements.txt` file to include the necessary dependencies:

```
boto3>=1.28.0
strands>=0.1.0
```

## Updating the SAM Template

Now, let's put everything together in the SAM template. Here's a complete example that you can add to your existing `template.yaml`:

```yaml
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
  Outputs:
    WebSocketApiEndpoint:
      Description: "WebSocket API endpoint URL"
      Value: !Sub "wss://${WebSocketApi}.execute-api.${AWS::Region}.amazonaws.com/${WebSocketStage}"
```

## Implementing the React Frontend

### Step 1: Create a WebSocket Service

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

### Step 2: Create a Prediction Service

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

### Step 3: Update Environment Configuration

Update your `.env` file to include the WebSocket URL:

```
REACT_APP_API_URL=https://your-api-id.execute-api.region.amazonaws.com/prod
REACT_APP_WEBSOCKET_URL=wss://your-websocket-api-id.execute-api.region.amazonaws.com/prod
```

### Step 4: Create a Streaming Prediction Component

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

### Step 5: Update Your App Component

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

## Testing and Troubleshooting

### Local Testing

1. Deploy your backend:
```bash
cd backend/calledit-backend
sam build
sam deploy --guided
```

2. Note the WebSocket URL from the CloudFormation outputs.

3. Update your frontend `.env` file with the WebSocket URL.

4. Start your frontend:
```bash
cd frontend
npm run dev
```

5. Open your browser and test the prediction form.

### Common Issues and Solutions

1. **WebSocket Connection Errors**
   - Check that your WebSocket URL is correct
   - Verify that CORS is properly configured
   - Check CloudWatch logs for the Connect Lambda function

2. **Lambda Execution Errors**
   - Check CloudWatch logs for the MakeCallStream Lambda function
   - Verify that the Lambda has the correct permissions
   - Check that the Strands SDK is properly installed

3. **Frontend Issues**
   - Check browser console for errors
   - Verify that the WebSocket URL is correctly set in the environment variables
   - Test the WebSocket connection using a tool like wscat

## Production Considerations

### Security

1. **Authentication**: Add Cognito authentication to your WebSocket API:
```yaml
ConnectRoute:
  Type: AWS::ApiGatewayV2::Route
  Properties:
    ApiId: !Ref WebSocketApi
    RouteKey: $connect
    AuthorizationType: CUSTOM
    AuthorizerId: !Ref WebSocketAuthorizer
    OperationName: ConnectRoute
    Target: !Join
      - '/'
      - - 'integrations'
        - !Ref ConnectIntegration

WebSocketAuthorizer:
  Type: AWS::ApiGatewayV2::Authorizer
  Properties:
    ApiId: !Ref WebSocketApi
    AuthorizerType: REQUEST
    IdentitySource:
      - route.request.querystring.token
    Name: CognitoAuthorizer
    AuthorizerUri: !Sub arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${AuthorizerFunction.Arn}/invocations
```

2. **Rate Limiting**: Add usage plans to prevent abuse.

3. **Input Validation**: Validate all inputs in your Lambda functions.

### Scalability

1. **Connection Management**: Store connection IDs in DynamoDB to handle multiple users.

2. **Lambda Concurrency**: Set appropriate concurrency limits for your Lambda functions.

3. **Error Handling**: Implement robust error handling and retry mechanisms.

### Monitoring

1. **CloudWatch Metrics**: Set up CloudWatch metrics for API Gateway and Lambda.

2. **Alarms**: Create alarms for error rates and latency.

3. **Logging**: Implement structured logging for easier troubleshooting.

## Conclusion

You've now implemented real-time streaming for your CalledIt prediction verification platform! Users will see AI-generated content as it's being created, providing a much more engaging and responsive experience.

This implementation leverages AWS WebSockets, Lambda, and the Strands SDK to create a scalable, serverless solution for streaming AI responses. The modular architecture allows for easy extension and maintenance as your application grows.

Next steps could include:
1. Adding authentication to your WebSocket API
2. Implementing connection management for multiple users
3. Enhancing the frontend UI with animations and better formatting
4. Adding analytics to track user engagement with the streaming feature