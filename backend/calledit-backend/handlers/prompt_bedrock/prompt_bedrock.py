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


def get_event_property(event, prop_name):
    if isinstance(event, dict):
        if event.get('queryStringParameters') and prop_name in event['queryStringParameters']:
            value = event['queryStringParameters'][prop_name]
        elif event.get('multiValueQueryStringParameters') and prop_name in event['multiValueQueryStringParameters']:
            value = event['multiValueQueryStringParameters'][prop_name][0]
        # Direct lambda invocation with prop_name in body
        elif prop_name in event:
            value = event[prop_name]
        # API Gateway request with prop_name in body
        elif 'body' in event:
            try:
                body = json.loads(event['body'])
                value = body.get(prop_name)
            except:
                value = None
        else:
            value = None
    else:
        value = None
    if not value:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': f'No {prop_name} provided'})
        }
    else:
        return value


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
