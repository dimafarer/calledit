import boto3
import json
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError


headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

bedrock = boto3.client('bedrock-runtime')

    
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
        # Extract the text content from the Nova response
        text_content = response_body['output']['message']['content'][0]['text']
        # The text content includes ```json and ``` markers, let's clean it up
        json_str = text_content.replace('```json\n', '').replace('\n```', '')
        # Parse the cleaned JSON string
        prediction_json = json.loads(json_str)
        
        return {
            "results": [prediction_json]
        }
            
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
