import json
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    try:
        # Setup CORS headers
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        }
        
        # Get the prompt from query parameters
        if not event.get('queryStringParameters') or 'prompt' not in event['queryStringParameters']:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'No prompt provided'
                })
            }
            
        prompt = event['queryStringParameters']['prompt']
        
        # Get current date and time
        current_datetime = datetime.now()
        formatted_date = current_datetime.strftime("%Y-%m-%d")
        formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
        
        # Initialize Bedrock client
        bedrock = boto3.client('bedrock-runtime')
        
        # Prepare the request for Nova
        system_prompt = [{"text": """You are a prediction verification expert. Your task is to:
            1. Analyze predictions
            2. Create structured verification criteria
            3. Specify how to verify the prediction"""}]
            
        message_list = [{
            "role": "user",
            "content": [{
                "text": f"""Create a structured verification format for this prediction: {prompt}
                
                Today's date is {formatted_date} and the current time is {formatted_datetime}.
                
                Format the response as a JSON object with:
                - prediction_statement
                - verification_date (use a realistic future date based on the prediction and today's date)
                - verification_method (source, criteria, steps)
                - initial_status (pending)"""
            }]
        }]
        
        request_body = {
            "messages": message_list,
            "system": system_prompt,
            "inferenceConfig": {
                "temperature": 0.2,
                "top_p": 0.9,
                "top_k": 50,
                "max_new_tokens": 1000
            }
        }
        
        # Call Bedrock
        response = bedrock.invoke_model(
            modelId='us.amazon.nova-pro-v1:0',
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        
        # Extract the text content from Nova's response
        if 'output' not in response_body or 'message' not in response_body['output']:
            raise ValueError("Unexpected response format from Nova")
            
        text_content = response_body['output']['message']['content'][0]['text']
        
        # Clean up the response text by removing markdown code blocks
        json_str = text_content.replace('```json\n', '').replace('\n```', '').strip()
        
        try:
            # Parse the JSON content
            prediction_json = json.loads(json_str)
            
            # Ensure the prediction_json has the expected structure
            sanitized_response = {
                "prediction_statement": str(prediction_json.get("prediction_statement", "")),
                "verification_date": str(prediction_json.get("verification_date", "")),
                "creation_date": formatted_datetime,
                "verification_method": {
                    "source": ensure_list(prediction_json.get("verification_method", {}).get("source", [])),
                    "criteria": ensure_list(prediction_json.get("verification_method", {}).get("criteria", [])),
                    "steps": ensure_list(prediction_json.get("verification_method", {}).get("steps", []))
                },
                "initial_status": str(prediction_json.get("initial_status", "pending"))
            }
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'results': [sanitized_response]
                })
            }
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from model response: {e}")
            print(f"Raw text content: {text_content}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Invalid response format from model',
                    'details': str(e)
                })
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

def ensure_list(value):
    """Helper function to ensure value is always a list of strings"""
    if isinstance(value, str):
        return [value]
    elif isinstance(value, list):
        return [str(item) if not isinstance(item, dict) else json.dumps(item) for item in value]
    elif value is None:
        return []
    else:
        return [str(value)]
