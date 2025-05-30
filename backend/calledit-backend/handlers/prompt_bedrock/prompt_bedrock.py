import boto3
import json
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError


bedrock_client = boto3.client("bedrock-runtime")

headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

def bedrock_text_prompt(textGenerationConfig, prompt, modelId):
    native_request = {
        "inputText": prompt,
        "textGenerationConfig": textGenerationConfig
    }
    try:
        request = json.dumps(native_request)
        modelResponse = bedrock_client.invoke_model(modelId=modelId, body=request)
        model_response = json.loads(modelResponse["body"].read())
        print('successfully prompt model')
        return model_response
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{modelId}'. Reason: {e}")
        return None


def get_event_property(event, prop_name, max_depth=10):
    """
    Recursively search for prop_name in the event dictionary, no matter how deeply nested.
    Returns the first occurrence found.
    
    Args:
        event: The event dictionary to search in
        prop_name: The property name to search for
        max_depth: Maximum recursion depth to prevent stack overflow (default: 10)
    """
    # First check common API Gateway patterns
    if isinstance(event, dict):
        # Check query parameters first
        if event.get('queryStringParameters') and prop_name in event['queryStringParameters']:
            return event['queryStringParameters'][prop_name]
        
        if event.get('multiValueQueryStringParameters') and prop_name in event['multiValueQueryStringParameters']:
            return event['multiValueQueryStringParameters'][prop_name][0]
        
        # Check if prop_name is directly in the event
        if prop_name in event:
            return event[prop_name]
        
        # Check if body is a string that needs to be parsed
        if 'body' in event and isinstance(event['body'], str):
            try:
                body = json.loads(event['body'])
                if isinstance(body, dict):
                    # Recursively search in the parsed body
                    result = search_dict(body, prop_name, max_depth)
                    if result is not None:
                        return result
            except json.JSONDecodeError:
                pass
        
        # Recursively search in all dictionary values
        result = search_dict(event, prop_name, max_depth)
        if result is not None:
            return result
    
    # If we get here, we couldn't find the property
    return {
        'statusCode': 400,
        'headers': headers,
        'body': json.dumps({'error': f'No {prop_name} provided'})
    }

def search_dict(d, key, max_depth=10, current_depth=0):
    """
    Helper function to recursively search for a key in nested dictionaries.
    
    Args:
        d: The dictionary to search in
        key: The key to search for
        max_depth: Maximum recursion depth to prevent stack overflow
        current_depth: Current recursion depth
    """
    # Stop recursion if we've reached the maximum depth
    if current_depth >= max_depth:
        return None
    
    if not isinstance(d, dict):
        return None
    
    # Direct match
    if key in d:
        return d[key]
    
    # Search in nested dictionaries
    for k, v in d.items():
        if isinstance(v, dict):
            result = search_dict(v, key, max_depth, current_depth + 1)
            if result is not None:
                return result
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    result = search_dict(item, key, max_depth, current_depth + 1)
                    if result is not None:
                        return result
    
    return None


textGenerationConfig = {
    "maxTokenCount": 512,
    "temperature": 0.5,
    "topP": 0.9
}

modelId = "amazon.titan-text-express-v1"

# Call the function
def lambda_handler(event, context):
    print(f"event!!!!!!!!!!!!!!!!!!!! {event}")
    # headers = {
    #     'Access-Control-Allow-Origin': '*',
    #     'Access-Control-Allow-Headers': 'Content-Type',
    #     'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    # }
    prompt = get_event_property(event, 'prompt')
    try:
        print('prompting model start')
        response = bedrock_text_prompt(textGenerationConfig, prompt, modelId)
        # Only process response if it exists
        if response is None:
            print('response is None from model')
            return {
                'statusCode': 500,
                'headers': headers,  # Include headers in error response
                'body': json.dumps({'error': 'Error invoking model'})
            }
        
        # Add headers to successful response
        # response['headers'] = headers
        print('returning response!!!')
        print(f'response {response}')
        return {
            'statusCode': 200,
            'headers': headers,  # Include headers in successful response
            'body': json.dumps(response)
        }
    except Exception as e:
        print(f'error!!! {e}')
        return {
            'statusCode': 500,
            'headers': headers,  # Include headers in error response
            'body': json.dumps({'error': str(e)})
        }
        
