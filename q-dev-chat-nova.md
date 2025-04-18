I want to do some research I want to use a relativly new model in amazon bedrock. its so new you might not be familiaure with it, so lets start with that. Are you familure with the new awmazon model called nova?

---

Yes, I'm familiar with Amazon Nova, which was recently announced as a new generation of foundation models available through Amazon Bedrock. Amazon Nova includes several different models designed for different purposes: [[1]](https://aws.amazon.com/blogs/machine-learning/aws-reinvent-2024-highlights-top-takeaways-from-swami-sivasubramanian-to-help-customers-manage-generative-ai-at-scale/)

1. Understanding Models:
- Amazon Nova Micro: A text-only model focused on low latency and cost [[2]](https://aws.amazon.com/about-aws/whats-new/2024/12/amazon-nova-foundation-models-bedrock/)
- Amazon Nova Lite: A multimodal model that handles image, video, and text at low cost
- Amazon Nova Pro: A highly capable multimodal model balancing accuracy, speed, and cost

2. Creative Generation Models:
- Amazon Nova Canvas: For generating professional-grade images [[3]](https://aws.amazon.com/blogs/aws/introducing-amazon-nova-frontier-intelligence-and-industry-leading-price-performance/)
- Amazon Nova Reel: For video generation

Looking at your code, I notice you're currently using the Titan model (`amazon.titan-text-express-v1`). If you're interested in switching to Nova, you'll need to choose which Nova model best fits your use case. Each model has different strengths and capabilities.

Would you like to know more about a specific Nova model or would you like help implementing one of them in your code?

---

ok I need a very good model. its task is to help me make a prediction and then help me decide how to judge if the prediction comes true or not, including a date to make the judegement. The the model with place the prediction and the cirtiria to judge it into a json object and then post that to dunamodb.  For example if I say it will rain next tuesday the model will take the prediction and sugest to check the national weather service on next tuesday to judge the prediction.   \n\n Question: which nova model (with prompt endineering) would mostly likely work for this task?

---

For this specific task, I would recommend Amazon Nova Pro for several reasons:

1. Complex Reasoning: Your task requires:
   - Understanding natural language predictions
   - Creating structured judgment criteria
   - Temporal reasoning (understanding dates)
   - Generating structured JSON output
   - Suggesting verification sources

2. Why Nova Pro:
   - It's the most capable model in the Nova family
   - Better at complex structured outputs
   - Strong reasoning capabilities
   - Good at following multi-step instructions
   - Excellent at maintaining context and format consistency

Here's a suggested prompt engineering structure for Nova Pro:

```python
prompt_template = """
Task: Convert a prediction into a structured verification format.

Prediction: {user_prediction}

Please create a JSON object with the following structure:
{
    "prediction": {
        "statement": "&lt;original prediction&gt;",
        "date_made": "&lt;current_date&gt;",
        "verification_date": "&lt;when to verify&gt;",
        "verification_method": {
            "source": "&lt;specific source to check&gt;",
            "criteria": "&lt;specific measurable criteria&gt;",
            "steps": ["&lt;step by step verification process&gt;"]
        }
    }
}

Requirements:
1. The verification_date must be specific and appropriate for the prediction
2. The verification_method must be objective and measurable
3. Include specific, authoritative sources
4. Break down verification steps clearly
"""
```

To implement this:

```python
import boto3
import json
from datetime import datetime

bedrock = boto3.client('bedrock-runtime')

def generate_prediction_verification(user_prediction):
    response = bedrock.invoke_model(
        modelId='us.amazon.nova-pro-v1:0',
        body=json.dumps({
            "prompt": prompt_template.format(user_prediction=user_prediction),
            "temperature": 0.2,  # Lower temperature for more consistent structured output
            "topP": 0.9,
            "maxTokens": 1000
        })
    )
    
    # Parse and validate the response
    result = json.loads(response['body'].read())
    
    # Add to DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('PredictionsTable')
    
    # Add timestamp and prediction ID
    result['prediction']['id'] = str(uuid.uuid4())
    result['prediction']['timestamp'] = datetime.utcnow().isoformat()
    
    table.put_item(Item=result['prediction'])
    
    return result
```

The lower temperature (0.2) helps ensure consistent JSON formatting, while maintaining enough creativity to generate appropriate verification methods.

Would you like me to provide an example of how this would work with a specific prediction, or would you like to know more about fine-tuning the prompt for specific types of predictions?

---

Thanks, that was a super helpfull response. The next step of this project is to use Amamzon nova act agents to read the prediction and varification json and to take apropriet action to judege the prediction. Are you familare witth nova act agents? If yes would you make an changes to the your above recommended json strcuture or do you recommend keeping as is?

---

Yes, I'm familiar with Amazon Bedrock Agents (which can use Nova as their foundation model). For integration with Bedrock Agents, we should modify the JSON structure slightly to make it more agent-friendly and actionable. Here's the recommended modified structure: [[1]](https://docs.aws.amazon.com/nova/latest/userguide/agents-use-nova.html)

```python
prompt_template = """
Task: Convert a prediction into a structured verification format.

Prediction: {user_prediction}

Please create a JSON object with the following structure:
{
    "prediction": {
        "id": "&lt;uuid&gt;",
        "statement": "&lt;original prediction&gt;",
        "date_made": "&lt;current_date&gt;",
        "status": "pending",
        "verification": {
            "due_date": "&lt;when to verify&gt;",
            "method": {
                "source": "&lt;specific source to check&gt;",
                "source_type": "&lt;api|web|human_check&gt;",
                "endpoint": "&lt;api_endpoint or url if applicable&gt;",
                "criteria": {
                    "success_condition": "&lt;specific measurable criteria&gt;",
                    "failure_condition": "&lt;specific measurable criteria&gt;",
                    "uncertain_condition": "&lt;criteria for unclear results&gt;"
                },
                "verification_steps": ["&lt;step by step verification process&gt;"]
            }
        },
        "result": {
            "verified_at": null,
            "outcome": null,
            "evidence": null
        }
    }
}

Requirements:
1. The verification_date must be specific and appropriate for the prediction
2. Include source_type to help the agent determine how to verify
3. Break down success/failure criteria explicitly
4. Include specific, actionable endpoints where applicable
"""
```

Key changes made to support Bedrock Agents:

1. Added `status` field for tracking
2. Added `source_type` to help agents determine verification method
3. Structured `criteria` into explicit success/failure conditions
4. Added `endpoint` for API-based verifications
5. Added `result` section for the agent to fill in
6. Separated verification method from results

The implementation would be similar:

```python
import boto3
import json
import uuid
from datetime import datetime

def generate_prediction_verification(user_prediction):
    bedrock = boto3.client('bedrock-runtime')
    
    response = bedrock.invoke_model(
        modelId='us.amazon.nova-pro-v1:0',
        body=json.dumps({
            "prompt": prompt_template.format(user_prediction=user_prediction),
            "temperature": 0.2,
            "topP": 0.9,
            "maxTokens": 1000
        })
    )
    
    # Parse and validate the response
    result = json.loads(response['body'].read())
    
    # Add to DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('PredictionsTable')
    
    # Add timestamp and prediction ID if not already present
    prediction = result['prediction']
    prediction['id'] = prediction.get('id', str(uuid.uuid4()))
    prediction['date_made'] = prediction.get('date_made', datetime.utcnow().isoformat())
    prediction['status'] = prediction.get('status', 'pending')
    
    table.put_item(Item=prediction)
    
    return result
```

This structure provides several advantages for Bedrock Agents:

1. Clear action paths based on source_type
2. Explicit success/failure criteria for automated judgment
3. Structured fields for storing verification results
4. Status tracking for workflow management
5. Separate sections for prediction, verification method, and results

The agent can now:
- Automatically determine how to verify (API call, web scraping, human check)
- Have clear criteria for making judgments
- Store evidence and results in a structured way
- Track the status of verifications
- Handle different types of predictions consistently

Would you like me to provide an example of how a Bedrock Agent would interact with this structure, or would you like to know more about specific verification methods we could add?

---

yes please provide an example of how a Bedrock Agent would interact with this structure

---

I'll demonstrate how a Bedrock Agent would interact with this structure using a weather prediction example. Here's how we can set it up: [[1]](https://repost.aws/questions/QUgBSR-m5LQwy6dB912xYVeg/bedrock-agent-with-real-time-data)

```python
# First, define the agent's action group schema
weather_verification_schema = {
    "openapi": "3.0.0",
    "info": {"title": "Prediction Verification", "version": "1.0.0"},
    "paths": {
        "/verify-weather": {
            "post": {
                "operationId": "verifyWeatherPrediction",
                "parameters": [
                    {
                        "name": "prediction_id",
                        "in": "query",
                        "required": true,
                        "schema": {"type": "string"}
                    }
                ]
            }
        }
    }
}

# Lambda function that the agent will call to verify weather predictions
def verify_weather_prediction(prediction_id):
    # Get prediction from DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('PredictionsTable')
    
    prediction = table.get_item(
        Key={'id': prediction_id}
    )['Item']
    
    if prediction['verification']['method']['source_type'] == 'api':
        # Make API call to weather service
        weather_data = requests.get(
            prediction['verification']['method']['endpoint'],
            params={'date': prediction['verification']['due_date']}
        ).json()
        
        # Compare against success criteria
        actual_condition = weather_data['condition']
        if actual_condition == prediction['verification']['method']['criteria']['success_condition']:
            outcome = 'success'
        elif actual_condition == prediction['verification']['method']['criteria']['failure_condition']:
            outcome = 'failure'
        else:
            outcome = 'uncertain'
            
        # Update prediction result
        table.update_item(
            Key={'id': prediction_id},
            UpdateExpression="SET #result = :r, #status = :s",
            ExpressionAttributeNames={
                '#result': 'result',
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':r': {
                    'verified_at': datetime.utcnow().isoformat(),
                    'outcome': outcome,
                    'evidence': weather_data
                },
                ':s': 'verified'
            }
        )
```

Here's an example interaction:

1. User makes a prediction:
```python
prediction = "It will rain next Tuesday in Seattle"

# This uses our earlier code to generate the structured prediction
result = generate_prediction_verification(prediction)

# The generated JSON might look like:
{
    "prediction": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "statement": "It will rain next Tuesday in Seattle",
        "date_made": "2024-01-24T10:00:00Z",
        "status": "pending",
        "verification": {
            "due_date": "2024-01-30T12:00:00Z",
            "method": {
                "source": "National Weather Service API",
                "source_type": "api",
                "endpoint": "https://api.weather.gov/points/47.6062,-122.3321/forecast",
                "criteria": {
                    "success_condition": "rain",
                    "failure_condition": "clear",
                    "uncertain_condition": "cloudy"
                },
                "verification_steps": [
                    "Query NWS API for Seattle forecast on 2024-01-30",
                    "Check weather condition at 12:00 PM local time",
                    "Compare actual condition against criteria"
                ]
            }
        },
        "result": {
            "verified_at": null,
            "outcome": null,
            "evidence": null
        }
    }
}
```

2. Agent Instruction Example:
```yaml
instructions: |
    You are a prediction verification agent. Your task is to:
    1. Monitor predictions in DynamoDB
    2. When a prediction's verification due_date arrives:
        - Check the source_type
        - Follow verification_steps
        - Update the result based on criteria
    3. Handle different source_types appropriately:
        - 'api': Make direct API calls
        - 'web': Extract data from websites
        - 'human_check': Create a human task
```

3. Agent Execution:
```python
# When the agent runs (triggered by EventBridge on schedule)
def agent_handler(event, context):
    # Find predictions due for verification
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('PredictionsTable')
    
    now = datetime.utcnow().isoformat()
    response = table.scan(
        FilterExpression='verification.due_date &lt;= :now AND #status = :pending',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':now': now, ':pending': 'pending'}
    )
    
    for prediction in response['Items']:
        if prediction['verification']['method']['source_type'] == 'api':
            # Call the verification Lambda
            lambda_client = boto3.client('lambda')
            lambda_client.invoke(
                FunctionName='verify_weather_prediction',
                InvocationType='Event',
                Payload=json.dumps({'prediction_id': prediction['id']})
            )
```

4. Final Result Example:
```json
{
    "prediction": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "verified",
        "result": {
            "verified_at": "2024-01-30T12:00:00Z",
            "outcome": "success",
            "evidence": {
                "location": "Seattle, WA",
                "timestamp": "2024-01-30T12:00:00Z",
                "condition": "rain",
                "temperature": 52,
                "precipitation_probability": 90
            }
        }
    }
}
```

The agent can handle different types of verifications based on the source_type:
- `api`: Makes direct API calls (like weather APIs)
- `web`: Could use web scraping for sources without APIs
- `human_check`: Could create tasks in systems like Amazon Mechanical Turk

This structure allows the agent to:
1. Understand how to verify each prediction
2. Follow specific steps for verification
3. Make clear judgments based on criteria
4. Store evidence and results
5. Update the prediction status

Would you like me to elaborate on any particular aspect of this interaction or explain how to handle different types of predictions?

---

Error: 
Object { stack: "AxiosError@http://localhost:5173/node_modules/.vite/deps/axios.js?v=a8c410f6:380:18\nsettle@http://localhost:5173/node_modules/.vite/deps/axios.js?v=a8c410f6:1218:12\nonloadend@http://localhost:5173/node_modules/.vite/deps/axios.js?v=a8c410f6:1550:13\n", message: "Request failed with status code 500", name: "AxiosError", code: "ERR_BAD_RESPONSE", config: {…}, request: XMLHttpRequest, response: {…}, status: 500 }
<anonymous code>:1:145535
Source map error: Error: JSON.parse: unexpected character at line 1 column 1 of the JSON data
Resource URL: http://localhost:5173/%3Canonymous%20code%3E
Source Map URL: installHook.js.map

---

Looking at your error and the code from the file, I notice that the `generate_structured_prediction` function isn't returning the response properly. Here's the fix:

```python
def generate_structured_prediction(user_prediction):
    response = bedrock.invoke_model(
        modelId='us.amazon.nova-pro-v1:0',
        body=json.dumps({
            "prompt": prompt_template.format(user_prediction=user_prediction),
            "temperature": 0.2,  # Lower temperature for more consistent structured output
            "topP": 0.9,
            "maxTokens": 1000
        })
    )
    
    # Parse the response body
    response_body = json.loads(response.get('body').read().decode('utf-8'))
    return response_body['output']  # Nova returns output in this format

def lambda_handler(event, context):
    print(f"event!!!!!!!!!!!!!!!!!!!! {event}")
    prompt = get_event_property(event, 'prompt')
    if isinstance(prompt, dict):  # This means we got an error response
        return prompt  # Return the error response directly
        
    try:
        print('prompting model start')
        response = generate_structured_prediction(prompt)
        
        if response is None:
            print('response is None from model')
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Error invoking model'})
            }
            
        print('returning response!!!')
        print(f'response {response}')
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response)
        }
    except Exception as e:
        print(f'error!!! {e}')
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
```

The key changes made:
1. Properly decode and parse the response from Bedrock
2. Extract the actual output from the response
3. Ensure proper error handling and response formatting

The 500 error you're seeing is likely because the response wasn't being properly processed before being returned to the client. This should resolve the axios error you're seeing on the frontend.

Would you like me to explain any part of these changes in more detail?

---

XHRGET
https://zvdf8sswt3.execute-api.us-west-2.amazonaws.com/Prod/make-call?prompt=The+Denver+Nuggets+will+win+their+game+today
[HTTP/2 500  1240ms]

Error: 
Object { stack: "AxiosError@http://localhost:5173/node_modules/.vite/deps/axios.js?v=a8c410f6:380:18\nsettle@http://localhost:5173/node_modules/.vite/deps/axios.js?v=a8c410f6:1218:12\nonloadend@http://localhost:5173/node_modules/.vite/deps/axios.js?v=a8c410f6:1550:13\nEventHandlerNonNull*dispatchXhrRequest@http://localhost:5173/node_modules/.vite/deps/axios.js?v=a8c410f6:1560:7\nxhr_default<@http://localhost:5173/node_modules/.vite/deps/axios.js?v=a8c410f6:1517:10\ndispatchRequest@http://localhost:5173/node_modules/.vite/deps/axios.js?v=a8c410f6:1992:10\n_request@http://localhost:5173/node_modules/.vite/deps/axios.js?v=a8c410f6:2213:33\nrequest@http://localhost:5173/node_modules/.vite/deps/axios.js?v=a8c410f6:2104:25\nforEachMethodNoData/Axios.prototype[method]@http://localhost:5173/node_modules/.vite/deps/axios.js?v=a8c410f6:2232:17\nwrap@http://localhost:5173/node_modules/.vite/deps/axios.js?v=a8c410f6:8:15\nhandleSubmit@http://localhost:5173/src/App.tsx:30:34\nexecuteDispatch@http://localhost:5173/node_modules/.vite/deps/react-dom_client.js?v=a8c410f6:11736:19\nrunWithFiberInDEV@http://localhost:5173/node_modules/.vite/deps/react-dom_client.js?v=a8c410f6:1487:15\nprocessDispatchQueue@http://localhost:5173/node_modules/.vite/deps/react-dom_client.js?v=a8c410f6:11772:37\nnode_modules/react-dom/cjs/react-dom-client.development.js/dispatchEventForPluginEventSystem/<@http://localhost:5173/node_modules/.vite/deps/react-dom_client.js?v=a8c410f6:12182:31\nbatchedUpdates$1@http://localhost:5173/node_modules/.vite/deps/react-dom_client.js?v=a8c410f6:2628:44\ndispatchEventForPluginEventSystem@http://localhost:5173/node_modules/.vite/deps/react-dom_client.js?v=a8c410f6:11877:25\ndispatchEvent@http://localhost:5173/node_modules/.vite/deps/react-dom_client.js?v=a8c410f6:14792:46\ndispatchDiscreteEvent@http://localhost:5173/node_modules/.vite/deps/react-dom_client.js?v=a8c410f6:14773:62\n", message: "Request failed with status code 500", name: "AxiosError", code: "ERR_BAD_RESPONSE", config: {…}, request: XMLHttpRequest, response: {…}, status: 500 }

---

Let's debug this error. Looking at the Lambda logs would be helpful, but I can see a few potential issues in the code that might be causing the 500 error.

Here's the corrected version:

```python
import boto3
import json
from botocore.exceptions import ClientError
from datetime import datetime

headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

bedrock = boto3.client('bedrock-runtime')

def generate_structured_prediction(user_prediction):
    try:
        response = bedrock.invoke_model(
            modelId='anthropic.claude-v2',  # or 'us.amazon.nova-pro-v1:0'
            body=json.dumps({
                "prompt": prompt_template.format(user_prediction=user_prediction),
                "temperature": 0.2,
                "topP": 0.9,
                "maxTokens": 1000
            })
        )
        
        # Properly handle the response stream
        response_body = json.loads(response['body'].read().decode('utf-8'))
        
        # Log the response for debugging
        print(f"Model response: {response_body}")
        
        # Extract the completion from the response
        if 'output' in response_body:  # Nova format
            return response_body['output']
        elif 'completion' in response_body:  # Claude format
            return response_body['completion']
        else:
            raise ValueError("Unexpected response format from model")
            
    except ClientError as e:
        print(f"AWS service error: {str(e)}")
        raise
    except Exception as e:
        print(f"Unexpected error in generate_structured_prediction: {str(e)}")
        raise

def get_event_property(event, prop_name):
    try:
        if isinstance(event, dict):
            # Check query parameters first
            if event.get('queryStringParameters') and prop_name in event['queryStringParameters']:
                return event['queryStringParameters'][prop_name]
            
            # Check body if it exists
            if 'body' in event:
                try:
                    body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
                    if prop_name in body:
                        return body[prop_name]
                except json.JSONDecodeError:
                    print("Failed to parse body as JSON")
            
            # Direct access
            if prop_name in event:
                return event[prop_name]
        
        print(f"Property {prop_name} not found in event: {event}")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': f'No {prop_name} provided'})
        }
    except Exception as e:
        print(f"Error in get_event_property: {str(e)}")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': f'Error processing {prop_name}'})
        }

def lambda_handler(event, context):
    try:
        print(f"Received event: {json.dumps(event)}")
        
        # Get the prompt
        prompt = get_event_property(event, 'prompt')
        if isinstance(prompt, dict):  # This means we got an error response
            return prompt
            
        if not prompt:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'No prompt provided'})
            }
            
        # Generate the prediction
        print('Generating prediction...')
        response = generate_structured_prediction(prompt)
        
        if not response:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'No response from model'})
            }
            
        # Return successful response
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response)
        }
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }
```

Key changes made:
1. Added more robust error handling
2. Improved logging for debugging
3. Better handling of the Bedrock response
4. Proper handling of query parameters
5. Added support for both Nova and Claude response formats
6. Improved input validation

To test this, you can try:
```bash
curl "https://zvdf8sswt3.execute-api.us-west-2.amazonaws.com/Prod/make-call?prompt=The+Denver+Nuggets+will+win+their+game+today"
```

Also, please check:
1. That your Lambda has the correct IAM permissions for Bedrock
2. That Bedrock is available in your region
3. That the model ID is correct for your region

Can you try this updated version and let me know if you still get the 500 error? If you do, could you share the Lambda logs to help debug further?

---

you have been generate incorrect prompt templates which have been generating most of the above errors. below i&#39;m posting the contents of the nova getting started ipynb file. please use it to fix my prompt structure &lt;ipynb&gt;
01_Getting Started with Amazon Nova Models

Amazon Nova is a new generation of multimodal understanding and creative content generation models that offer state-of-the-art quality, unparalleled customization, and the best price-performance. Amazon Nova models incorporate the same secure-by-design approach as all AWS services, with built-in controls for the safe and responsible use of AI.

Amazon Nova has two categories of models:

    Understanding models —These models are capable of reasoning over several input modalities, including text, video, and image, and output text.
    Creative Content Generation models —These models generate images or videos based on a text or image prompt.

Amazon Nova Models at Glance

media/model_intro.png

Multimodal Understanding Models

    Amazon Nova Micro: Lightening fast, cost-effective text-only model
    Amazon Nova Lite: Fastest, most affordable multimodal FM in the industry for its intelligence tier
    Amazon Nova Pro: The fastest, most cost-effective, state-of-the-art multimodal model in the industry

Creative Content Generation Models

    Amazon Nova Canvas:State-of-the-art image generation model
    Amazon Nova Reel:State-of-the-art video generation model

The following notebooks will be focused primarily on Amazon Nova Understanding Models.

Amazon Nova Multimodal understanding foundation models (FMs) are a family of models that are capable of reasoning over several input modalities, including text, video, documents and/or images, and output text. You can access these models through the Bedrock Converse API and InvokeModel API.
1. Setup

Step 1: Gain Access to the Model: If you have not yet requested for model access in Bedrock, you do so request access following these instructions.

media/model_access.png
2 When to Use What?
2.1 When to Use Amazon Nova Micro Model

Amazon Nova Micro (Text Input Only) is the fastest and most affordable option, optimized for large-scale, latency-sensitive deployments like conversational interfaces, chats, and high-volume tasks, such as classification, routing, entity extraction, and document summarization.
2.2 When to Use Amazon Nova Lite Model

Amazon Nova Lite balances intelligence, latency, and cost-effectiveness. It’s optimized for complex scenarios where low latency (minimal delay) is crucial, such as interactive agents that need to orchestrate multiple tool calls simultaneously. Amazon Nova Lite supports image, video, and text inputs and outputs text.
2.3 When to Use Amazon Nova Pro Model

Amazon Nova Pro is designed for highly complex use cases requiring advanced reasoning, creativity, and code generation. Amazon Nova pro supports image, video, and text inputs and outputs text.
Prerequisites

Run the cells in this section to install the packages needed by the notebooks in this workshop. ⚠️ You will see pip dependency errors, you can safely ignore these errors. ⚠️

IGNORE ERROR: pip&#39;s dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.

%pip install --no-build-isolation --force-reinstall \
    &quot;boto3&gt;=1.28.57&quot; \
    &quot;awscli&gt;=1.29.57&quot; \
    &quot;botocore&gt;=1.31.57&quot;

# restart kernel
from IPython.core.display import HTML
HTML(&quot;&lt;script&gt;Jupyter.notebook.kernel.restart()&lt;/script&gt;&quot;)

2. Text Understanding [Applicable for Amazon Nova Micro, Amazon Nova Lite, Amazon Nova Pro]

The example below demonstrates how to use a text-based prompt, including a simple system prompt and message list.

Note: Below examples are using Nova Lite for Illustrative Purposes but you can make use of Micro Models for Text Understanidng Usecases as well.

import boto3
import json
import base64
from datetime import datetime

PRO_MODEL_ID = &quot;us.amazon.nova-pro-v1:0&quot;
LITE_MODEL_ID = &quot;us.amazon.nova-lite-v1:0&quot;
MICRO_MODEL_ID = &quot;us.amazon.nova-micro-v1:0&quot;

# Create a Bedrock Runtime client in the AWS Region of your choice.
client = boto3.client(&quot;bedrock-runtime&quot;, region_name=&quot;us-east-1&quot;)

InvokeModel body and output

The invoke_model() method of the Amazon Bedrock runtime client (InvokeModel API) will be the primary method we use for most of our Text Generation and Processing tasks

Although the method is shared, the format of input and output varies depending on the foundation model used - as described below:

{
  &quot;system&quot;: [
    {
      &quot;text&quot;: string
    }
  ],
  &quot;messages&quot;: [
    {
      &quot;role&quot;: &quot;user&quot;,# first turn should always be the user turn
      &quot;content&quot;: [
        {
          &quot;text&quot;: string
        },
        {
          &quot;image&quot;: {
            &quot;format&quot;: &quot;jpeg&quot;| &quot;png&quot; | &quot;gif&quot; | &quot;webp&quot;,
            &quot;source&quot;: {
              &quot;bytes&quot;: &quot;base64EncodedImageDataHere...&quot;#  base64-encoded binary
            }
          }
        },
        {
          &quot;video&quot;: {
            &quot;format&quot;: &quot;mkv&quot; | &quot;mov&quot; | &quot;mp4&quot; | &quot;webm&quot; | &quot;three_gp&quot; | &quot;flv&quot; | &quot;mpeg&quot; | &quot;mpg&quot; | &quot;wmv&quot;,
            &quot;source&quot;: {
            # source can be s3 location of base64 bytes based on size of input file. 
               &quot;s3Location&quot;: {
                &quot;uri&quot;: string, #  example: s3://my-bucket/object-key
                &quot;bucketOwner&quot;: string #  (Optional) example: 123456789012)
               }
              &quot;bytes&quot;: &quot;base64EncodedImageDataHere...&quot; #  base64-encoded binary
            }
          }
        },
      ]
    },
    {
      &quot;role&quot;: &quot;assistant&quot;,
      &quot;content&quot;: [
        {
          &quot;text&quot;: string # prefilling assistant turn
        }
      ]
    }
  ],
 &quot;inferenceConfig&quot;:{ # all Optional
    &quot;max_new_tokens&quot;: int, #  greater than 0, equal or less than 5k (default: dynamic*)
    &quot;temperature&quot;: float, # greater then 0 and less than 1.0 (default: 0.7)
    &quot;top_p&quot;: float, #  greater than 0, equal or less than 1.0 (default: 0.9)
    &quot;top_k&quot;: int #  0 or greater (default: 50)
    &quot;stopSequences&quot;: [string]
  },
  &quot;toolConfig&quot;: { #  all Optional
        &quot;tools&quot;: [
                {
                    &quot;toolSpec&quot;: {
                        &quot;name&quot;: string # menaingful tool name (Max char: 64)
                        &quot;description&quot;: string # meaningful description of the tool
                        &quot;inputSchema&quot;: {
                            &quot;json&quot;: { # The JSON schema for the tool. For more information, see JSON Schema Reference
                                &quot;type&quot;: &quot;object&quot;,
                                &quot;properties&quot;: {
                                    &lt;args&gt;: { # arguments 
                                        &quot;type&quot;: string, # argument data type
                                        &quot;description&quot;: string # meaningful description
                                    }
                                },
                                &quot;required&quot;: [
                                    string # args
                                ]
                            }
                        }
                    }
                }
            ],
   &quot;toolChoice&quot;: &quot;auto&quot; //Amazon Nova models currently ONLY support tool choice of &quot;auto&quot;
        }
    }
}

The following are required parameters.

    system – (Optional) The system prompt for the request. A system prompt is a way of providing context and instructions to Amazon Nova, such as specifying a particular goal or role.
    messages – (Required) The input messages.
        role – The role of the conversation turn. Valid values are user and assistant.
        content – (required) The content of the conversation turn.
            type – (required) The type of the content. Valid values are image, text. , video
                if chosen text (text content)
                    text - The content of the conversation turn.
                If chosen Image (image content)
                    source – (required) The base64 encoded image bytes for the image.
                    format – (required) The type of the image. You can specify the following image formats.
                        jpeg
                        png
                        webp
                        gif
                If chosen video: (video content)
                    source – (required) The base64 encoded image bytes for the video or S3 URI and bucket owner as shown in the above schema
                    format – (required) The type of the video. You can specify the following video formats.
                        mkv
                        mov
                        mp4
                        webm
                        three_gp
                        flv
                        mpeg
                        mpg
                        wmv
    inferenceConfig: These are inference config values that can be passed in inference.
        max_new_tokens – (Optional) The maximum number of tokens to generate before stopping. Note that Amazon Nova models might stop generating tokens before reaching the value of max_tokens. Maximum New Tokens value allowed is 5K.
        temperature – (Optional) The amount of randomness injected into the response.
        top_p – (Optional) Use nucleus sampling. Amazon Nova computes the cumulative distribution over all the options for each subsequent token in decreasing probability order and cuts it off once it reaches a particular probability specified by top_p. You should alter either temperature or top_p, but not both.
        top_k – (Optional) Only sample from the top K options for each subsequent token. Use top_k to remove long tail low probability responses.
        stopSequences – (Optional) Array of strings containing step sequences. If the model generates any of those strings, generation will stop and response is returned up until that point.
        toolConfig – (Optional) JSON object following ToolConfig schema, containing the tool specification and tool choice. This schema is the same followed by the Converse API

2.1 Synchronous API Call

# Define your system prompt(s).
system_list = [
    { &quot;text&quot;: &quot;You should respond to all messages in french&quot; }
]

# Define one or more messages using the &quot;user&quot; and &quot;assistant&quot; roles.
message_list = [
    {&quot;role&quot;: &quot;user&quot;, &quot;content&quot;: [{&quot;text&quot;: &quot;tell me a joke&quot;}]},
]

# Configure the inference parameters.
inf_params = {&quot;max_new_tokens&quot;: 300, &quot;top_p&quot;: 0.9, &quot;top_k&quot;: 20, &quot;temperature&quot;: 0.7}

native_request = {
    &quot;messages&quot;: message_list,
    &quot;system&quot;: system_list,
    &quot;inferenceConfig&quot;: inf_params,
}

# Invoke the model and extract the response body.
response = client.invoke_model(modelId=LITE_MODEL_ID, body=json.dumps(native_request))
request_id = response[&quot;ResponseMetadata&quot;][&quot;RequestId&quot;]
print(f&quot;Request ID: {request_id}&quot;)
model_response = json.loads(response[&quot;body&quot;].read())

# Pretty print the response JSON.
print(&quot;\n[Full Response]&quot;)
print(json.dumps(model_response, indent=2))

# Print the text content for easy readability.
content_text = model_response[&quot;output&quot;][&quot;message&quot;][&quot;content&quot;][0][&quot;text&quot;]
print(&quot;\n[Response Content Text]&quot;)
print(content_text)

2.2 Streaming API Call

The example below demonstrates how to use a text-based prompt with the streaming API.

# Define your system prompt(s).
system_list = [
    { &quot;text&quot;: &quot;Act as a creative writing assistant. When the user provides you with a topic, write a short story about that topic.&quot; }
]

# Define one or more messages using the &quot;user&quot; and &quot;assistant&quot; roles.
message_list = [{&quot;role&quot;: &quot;user&quot;, &quot;content&quot;: [{&quot;text&quot;: &quot;A camping trip&quot;}]}]

# Configure the inference parameters.
inf_params = {&quot;max_new_tokens&quot;: 500, &quot;top_p&quot;: 0.9, &quot;top_k&quot;: 20, &quot;temperature&quot;: 0.7}

request_body = {
    &quot;messages&quot;: message_list,
    &quot;system&quot;: system_list,
    &quot;inferenceConfig&quot;: inf_params,
}

start_time = datetime.now()

# Invoke the model with the response stream
response = client.invoke_model_with_response_stream(
    modelId=LITE_MODEL_ID, body=json.dumps(request_body)
)

request_id = response.get(&quot;ResponseMetadata&quot;).get(&quot;RequestId&quot;)
print(f&quot;Request ID: {request_id}&quot;)
print(&quot;Awaiting first token...&quot;)

chunk_count = 0
time_to_first_token = None

# Process the response stream
stream = response.get(&quot;body&quot;)
if stream:
    for event in stream:
        chunk = event.get(&quot;chunk&quot;)
        if chunk:
            # Print the response chunk
            chunk_json = json.loads(chunk.get(&quot;bytes&quot;).decode())
            # Pretty print JSON
            # print(json.dumps(chunk_json, indent=2, ensure_ascii=False))
            content_block_delta = chunk_json.get(&quot;contentBlockDelta&quot;)
            if content_block_delta:
                if time_to_first_token is None:
                    time_to_first_token = datetime.now() - start_time
                    print(f&quot;Time to first token: {time_to_first_token}&quot;)

                chunk_count += 1
                current_time = datetime.now().strftime(&quot;%Y-%m-%d %H:%M:%S:%f&quot;)
                # print(f&quot;{current_time} - &quot;, end=&quot;&quot;)
                print(content_block_delta.get(&quot;delta&quot;).get(&quot;text&quot;), end=&quot;&quot;)
    print(f&quot;Total chunks: {chunk_count}&quot;)
else:
    print(&quot;No response stream received.&quot;)

3. Multimodal Understanding [Applicable only for Amazon Nova lite/Amazon Nova Pro Model]

The following examples show how to pass various media types to the model. (reminder - this is only supported with the Lite model)
3.1 Image Understanding

Lets see how Nova model does on Image Understanding Usecase.

Here we will pass an Image of a Sunset and ask model to try to create 3 art titles for this image.

A Sunset Image

# Open the image you&#39;d like to use and encode it as a Base64 string.
with open(&quot;media/sunset.png&quot;, &quot;rb&quot;) as image_file:
    binary_data = image_file.read()
    base_64_encoded_data = base64.b64encode(binary_data)
    base64_string = base_64_encoded_data.decode(&quot;utf-8&quot;)

# Define your system prompt(s).
system_list = [
    { &quot;text&quot;: &quot;You are an expert artist. When the user provides you with an image, provide 3 potential art titles&quot; }
]

# Define a &quot;user&quot; message including both the image and a text prompt.
message_list = [
    {
        &quot;role&quot;: &quot;user&quot;,
        &quot;content&quot;: [
            {
                &quot;image&quot;: {
                    &quot;format&quot;: &quot;png&quot;,
                    &quot;source&quot;: {&quot;bytes&quot;: base64_string},
                }
            },
            {&quot;text&quot;: &quot;Provide art titles for this image.&quot;},
        ],
    }
]

# Configure the inference parameters.
inf_params = {&quot;max_new_tokens&quot;: 300, &quot;top_p&quot;: 0.1, &quot;top_k&quot;: 20, &quot;temperature&quot;: 0.3}

native_request = {
    &quot;messages&quot;: message_list,
    &quot;system&quot;: system_list,
    &quot;inferenceConfig&quot;: inf_params,
}

# Invoke the model and extract the response body.
response = client.invoke_model(modelId=LITE_MODEL_ID, body=json.dumps(native_request))
model_response = json.loads(response[&quot;body&quot;].read())

# Pretty print the response JSON.
print(&quot;[Full Response]&quot;)
print(json.dumps(model_response, indent=2))

# Print the text content for easy readability.
content_text = model_response[&quot;output&quot;][&quot;message&quot;][&quot;content&quot;][0][&quot;text&quot;]
print(&quot;\n[Response Content Text]&quot;)
print(content_text)

There can be multiple image contents. In this example we ask the model to find what two images have in common:

# Open the image you&#39;d like to use and encode it as a Base64 string.
with open(&quot;media/dog.jpeg&quot;, &quot;rb&quot;) as image_file:
    binary_data = image_file.read()
    base_64_encoded_data = base64.b64encode(binary_data)
    dog_base64_string = base_64_encoded_data.decode(&quot;utf-8&quot;)

with open(&quot;media/cat.jpeg&quot;, &quot;rb&quot;) as image_file:
    binary_data = image_file.read()
    base_64_encoded_data = base64.b64encode(binary_data)
    cat_base64_string = base_64_encoded_data.decode(&quot;utf-8&quot;)

# Define a &quot;user&quot; message including both the image and a text prompt.
message_list = [
    {
        &quot;role&quot;: &quot;user&quot;,
        &quot;content&quot;: [
            {
                &quot;image&quot;: {
                    &quot;format&quot;: &quot;jpeg&quot;,
                    &quot;source&quot;: {&quot;bytes&quot;: dog_base64_string},
                }
            },
            {
                &quot;image&quot;: {
                    &quot;format&quot;: &quot;jpeg&quot;,
                    &quot;source&quot;: {&quot;bytes&quot;: cat_base64_string},
                }
            },
            {&quot;text&quot;: &quot;What do these two images have in common?&quot;},
        ],
    }
]

# Configure the inference parameters.
inf_params = {&quot;max_new_tokens&quot;: 300, &quot;top_p&quot;: 0.1, &quot;top_k&quot;: 20, &quot;temperature&quot;: 0.3}

native_request = {
    &quot;messages&quot;: message_list,
    &quot;inferenceConfig&quot;: inf_params,
}

# Invoke the model and extract the response body.
response = client.invoke_model(modelId=LITE_MODEL_ID, body=json.dumps(native_request))
model_response = json.loads(response[&quot;body&quot;].read())

# Pretty print the response JSON.
print(&quot;[Full Response]&quot;)
print(json.dumps(model_response, indent=2))

# Print the text content for easy readability.
content_text = model_response[&quot;output&quot;][&quot;message&quot;][&quot;content&quot;][0][&quot;text&quot;]
print(&quot;\n[Response Content Text]&quot;)
print(content_text)

3.2 Video Understanding

Lets now, try to see how Nova does on Video understanding use case

Here we are going to pass in a video with Quesdilla making instructions.

from IPython.display import Video

Video(&quot;media/the-sea.mp4&quot;)

# Open the image you&#39;d like to use and encode it as a Base64 string.
with open(&quot;media/the-sea.mp4&quot;, &quot;rb&quot;) as video_file:
    binary_data = video_file.read()
    base_64_encoded_data = base64.b64encode(binary_data)
    base64_string = base_64_encoded_data.decode(&quot;utf-8&quot;)

# Define your system prompt(s).
system_list = [
    { &quot;text&quot;: &quot;You are an expert media analyst. When the user provides you with a video, provide 3 potential video titles&quot; }
]

# Define a &quot;user&quot; message including both the image and a text prompt.
message_list = [
    {
        &quot;role&quot;: &quot;user&quot;,
        &quot;content&quot;: [
            {
                &quot;video&quot;: {
                    &quot;format&quot;: &quot;mp4&quot;,
                    &quot;source&quot;: {&quot;bytes&quot;: base64_string},
                }
            },
            {&quot;text&quot;: &quot;Provide video titles for this clip.&quot;},
        ],
    }
]

# Configure the inference parameters.
inf_params = {&quot;max_new_tokens&quot;: 300, &quot;top_p&quot;: 0.1, &quot;top_k&quot;: 20, &quot;temperature&quot;: 0.3}

native_request = {
    &quot;messages&quot;: message_list,
    &quot;system&quot;: system_list,
    &quot;inferenceConfig&quot;: inf_params,
}

# Invoke the model and extract the response body.
response = client.invoke_model(modelId=LITE_MODEL_ID, body=json.dumps(native_request))
model_response = json.loads(response[&quot;body&quot;].read())

# Pretty print the response JSON.
print(&quot;[Full Response]&quot;)
print(json.dumps(model_response, indent=2))

# Print the text content for easy readability.
content_text = model_response[&quot;output&quot;][&quot;message&quot;][&quot;content&quot;][0][&quot;text&quot;]
print(&quot;\n[Response Content Text]&quot;)
print(content_text)

Video Understanding using S3 Path
Replace the S3 URI below with the S3 URI where your video is located

# Define your system prompt(s).
system_list = [
    { &quot;text&quot;: &quot;You are an expert media analyst. When the user provides you with a video, provide 3 potential video titles&quot; }
]

# Define a &quot;user&quot; message including both the image and a text prompt.
message_list = [
    {
        &quot;role&quot;: &quot;user&quot;,
        &quot;content&quot;: [
            {
                &quot;video&quot;: {
                    &quot;format&quot;: &quot;mp4&quot;,
                    &quot;source&quot;: {
                        &quot;s3Location&quot;: {
                            # Replace the S3 URI
                            &quot;uri&quot;: &quot;s3://demo-bucket/the-sea.mp4&quot;
                        }
                    },
                }
            },
            {&quot;text&quot;: &quot;Provide video titles for this clip.&quot;},
        ],
    }
]

# Configure the inference parameters.
inf_params = {&quot;max_new_tokens&quot;: 300, &quot;top_p&quot;: 0.1, &quot;top_k&quot;: 20, &quot;temperature&quot;: 0.3}

native_request = {
    &quot;schemaVersion&quot;: &quot;messages-v1&quot;,
    &quot;messages&quot;: message_list,
    &quot;system&quot;: system_list,
    &quot;inferenceConfig&quot;: inf_params,
}

# Invoke the model and extract the response body.
response = client.invoke_model(modelId=LITE_MODEL_ID, body=json.dumps(native_request))
model_response = json.loads(response[&quot;body&quot;].read())

# Pretty print the response JSON.
print(&quot;[Full Response]&quot;)
print(json.dumps(model_response, indent=2))

# Print the text content for easy readability.
content_text = model_response[&quot;output&quot;][&quot;message&quot;][&quot;content&quot;][0][&quot;text&quot;]
print(&quot;\n[Response Content Text]&quot;)
print(content_text)

&lt;/ipynb&gt;

---

Thank you for providing the Nova documentation. Let me help correct the prompt structure. Based on the documentation, here's the correct implementation:

```python
def generate_structured_prediction(user_prediction):
    try:
        # Define system prompt
        system_list = [
            {
                "text": """You are a prediction verification expert. Your task is to:
                1. Analyze predictions
                2. Create structured verification criteria
                3. Specify how to verify the prediction"""
            }
        ]

        # Define the message list
        message_list = [
            {
                "role": "user",
                "content": [
                    {
                        "text": f"""Create a structured verification format for this prediction: {user_prediction}
                        
                        Format the response as a JSON object with:
                        - prediction statement
                        - verification date
                        - verification method (source, criteria, steps)
                        - initial status (pending)"""
                    }
                ]
            }
        ]

        # Configure inference parameters
        inf_params = {
            "max_new_tokens": 1000,
            "temperature": 0.2,
            "top_p": 0.9,
            "top_k": 50
        }

        # Create the request body
        request_body = {
            "messages": message_list,
            "system": system_list,
            "inferenceConfig": inf_params
        }

        # Invoke the model
        response = bedrock.invoke_model(
            modelId='us.amazon.nova-pro-v1:0',
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        
        # Extract the completion text
        if 'output' in response_body:
            return response_body['output']
        else:
            print(f"Unexpected response format: {response_body}")
            raise ValueError("Unexpected response format from model")
            
    except Exception as e:
        print(f"Error in generate_structured_prediction: {str(e)}")
        raise

```

Key changes made:
1. Properly structured system and message format according to Nova's schema
2. Correct inference configuration parameters
3. Proper response handling for Nova's output format
4. Better error handling and logging

The main differences from the previous version:
1. Uses the correct message structure with `role` and `content`
2. Properly formatted system prompt
3. Correct inference parameter structure
4. Handles Nova's specific response format

Would you like me to provide an example of how this would work with a specific prediction, or would you like to see any other aspects of the implementation?

---

nice! we got a response with that update, but it did not post to the second text box in  **@App.tsx** , instead the text box content was &quot;unable to show results&quot; the response object from the browser console is:   \n\n API Response: 
Object { message: {…} }
​
message: Object { content: (1) […], role: &quot;assistant&quot; }
​​
content: Array [ {…} ]
​​​
0: Object { text: &#39;```json\n{\n  &quot;prediction_statement&quot;: &quot;The Denver Nuggets will win the NBA finals&quot;,\n  &quot;verification_date&quot;: &quot;To be determined after the NBA finals conclude&quot;,\n  &quot;verification_method&quot;: {\n    &quot;source&quot;: [\n      &quot;Official NBA website&quot;,\n      &quot;Reputable sports news websites (e.g., ESPN, Bleacher Report)&quot;,\n      &quot;NBA mobile app&quot;\n    ],\n    &quot;criteria&quot;: [\n      &quot;Confirmation of the NBA finals winner&quot;,\n      &quot;Cross-verification from multiple reliable sources&quot;\n    ],\n    &quot;steps&quot;: [\n      &quot;Wait for the conclusion of the NBA finals&quot;,\n      &quot;Check the official NBA website for the announced winner&quot;,\n      &quot;Verify the winner information on at least two reputable sports news websites&quot;,\n      &quot;Confirm the winner through the NBA mobile app if available&quot;,\n      &quot;Cross-check all gathered information to ensure consistency and accuracy&quot;\n    ]\n  },\n  &quot;initial_status&quot;: &quot;pending&quot;\n}\n```&#39; }
​​​
length: 1
​​​
&lt;prototype&gt;: Array []
​​
role: &quot;assistant&quot;
​​
&lt;prototype&gt;: Object { … }

---

I see the issue. The response structure from Nova needs to be properly handled in both the backend and frontend. Let's fix both parts:

1. First, let's modify the backend response to extract just the JSON content from the text:

```python
def generate_structured_prediction(user_prediction):
    # ... (previous code remains the same until response handling)
    
    try:
        response_body = json.loads(response['body'].read().decode('utf-8'))
        
        # Extract the text content from the Nova response
        text_content = response_body['output']['message']['content'][0]['text']
        
        # The text content includes ```json and ``` markers, let's clean it up
        json_str = text_content.replace('```json\n', '').replace('\n```', '')
        
        # Parse the cleaned JSON string
        prediction_json = json.loads(json_str)
        
        return {
            "results": [{
                "outputText": json.dumps(prediction_json, indent=2),
                "tokenCount": len(text_content.split()),
                "completionReason": "COMPLETE"
            }]
        }
            
    except Exception as e:
        print(f"Error in generate_structured_prediction: {str(e)}")
        raise
```

2. Then, let's update the frontend App.tsx to properly handle the response:

```typescript
// Update the interfaces in App.tsx
interface BedrockResult {
  tokenCount: number;
  outputText: string;
  completionReason: string;
}

interface BedrockResponse {
  results: BedrockResult[];
}

// In your App component, update the response handling:
&lt;textarea
  value={
    typeof response === 'string' 
      ? response 
      : response.results?.[0]?.outputText || 'Unable to show results'
  }
  readOnly
  placeholder="Response will appear here..."
  rows={4}
  className="text-box"
/&gt;
```

The key changes are:

1. Backend:
   - Extracts the JSON content from the code block
   - Parses and reformats it to match the expected BedrockResponse structure
   - Returns a consistent format that matches the frontend interface

2. Frontend:
   - Properly types the response
   - Correctly accesses the outputText from the results array

This should now properly display the structured prediction in the second text box. The response will be formatted JSON that includes:
- The prediction statement
- Verification date
- Verification method
- Initial status

Would you like me to explain any part of these changes in more detail?