import boto3
import json
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

prompt_template = """
Task: Convert a prediction into a structured verification format.

Prediction: {user_prediction}

Please create a JSON object with the following structure:
{{
    "prediction": {{
        "id": "<uuid>",
        "statement": "<original prediction>",
        "date_made": "<current_date>",
        "status": "pending",
        "verification": {{
            "due_date": "<when to verify>",
            "method": {{
                "source": "<specific source to check>",
                "source_type": "<api|web|human_check>",
                "endpoint": "<api_endpoint or url if applicable>",
                "criteria": {{
                    "success_condition": "<specific measurable criteria>",
                    "failure_condition": "<specific measurable criteria>",
                    "uncertain_condition": "<criteria for unclear results>"
                }},
                "verification_steps": ["<step by step verification process>"]
            }}
        }},
        "result": {{
            "verified_at": null,
            "outcome": null,
            "evidence": null
        }}
    }}
}}

Requirements:
1. The verification_date must be specific and appropriate for the prediction
2. Include source_type to help the agent determine how to verify
3. Break down success/failure criteria explicitly
4. Include specific, actionable endpoints where applicable
"""

headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

bedrock = boto3.client('bedrock-runtime')


# def generate_structured_prediction(user_prediction):
#     try:
#         response = bedrock.invoke_model(
#             modelId='us.amazon.nova-pro-v1:0',
#             body=json.dumps({
#                 "inputText": prompt_template.format(user_prediction=user_prediction),
#                 "textGenerationConfig": {
#                     "maxTokenCount": 1000,
#                     "temperature": 0.2,
#                     "topP": 0.9,
#                     "stopSequences": []
#                 }
#             })
#         )
#         # Log raw response for debugging
#         print(f"Raw response from bedrock: {response}")
        
#         # Properly handle the response stream
#         response_body = json.loads(response['body'].read().decode('utf-8'))
        
#         # Log parsed response for debugging
#         print(f"Parsed response body: {response_body}")
        
#         # Extract the completion from the response
#         if 'results' in response_body:  # Nova/Titan format
#             return response_body
#         else:
#             print(f"Unexpected response format: {response_body}")
#             raise ValueError("Unexpected response format from model")
            
#     except ClientError as e:
#         print(f"AWS service error: {str(e)}")
#         raise
#     except json.JSONDecodeError as e:
#         print(f"JSON parsing error: {str(e)}")
#         print(f"Response content: {response['body'].read().decode('utf-8')}")
#         raise
#     except Exception as e:
#         print(f"Unexpected error in generate_structured_prediction: {str(e)}")
#         print(f"Error type: {type(e)}")
#         import traceback
#         print(f"Traceback: {traceback.format_exc()}")
#         raise
    
    
    
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


        
# # Parse and validate the response
# result = json.loads(response['body'].read())

# # Add to DynamoDB
# dynamodb = boto3.resource('dynamodb')
# table = dynamodb.Table('PredictionsTable')

# # Add timestamp and prediction ID
# result['prediction']['id'] = str(uuid.uuid4())
# result['prediction']['timestamp'] = datetime.utcnow().isoformat()

# table.put_item(Item=result['prediction'])        