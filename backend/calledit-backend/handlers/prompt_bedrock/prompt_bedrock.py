import boto3
import json
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError


bedrock_client = boto3.client("bedrock-runtime")

def bedrock_text_prompt(textGenerationConfig, prompt, modelId):
    native_request = {
        "inputText": prompt,
        "textGenerationConfig": textGenerationConfig
    }
    
    try:
        request = json.dumps(native_request)
        modelResponse = bedrock_client.invoke_model(modelId=modelId, body=request)
        model_response = json.loads(modelResponse["body"].read())
        return model_response
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{modelId}'. Reason: {e}")
        return None

textGenerationConfig = {
    "maxTokenCount": 512,
    "temperature": 0.5,
    "topP": 0.9
}

modelId = "amazon.titan-text-express-v1"
prompt = "Tell me an interesting fact."

# Call the function
def lambda_handler(event, context):
    prompt = "what is the captial of colorado"
    try:
        response = bedrock_text_prompt(textGenerationConfig, prompt, modelId)
        # Define CORS headers once
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        }
        # Only process response if it exists
        if response is None:
            return {
                'statusCode': 500,
                'headers': headers,  # Include headers in error response
                'body': json.dumps({'error': 'Error invoking model'})
            }
        
        # Add headers to successful response
        response['headers'] = headers
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,  # Include headers in error response
            'body': json.dumps({'error': str(e)})
        }
