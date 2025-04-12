import json
import logging
import boto3
import os
# import requests

logger = logging.getLogger()
def checkcreds():
        # Log environment variables
    logger.debug(f"AWS_PROFILE: {os.environ.get('AWS_PROFILE')}")
    logger.debug(f"AWS_DEFAULT_REGION: {os.environ.get('AWS_DEFAULT_REGION')}")
    logger.debug(f"AWS_ACCESS_KEY_ID: {os.environ.get('AWS_ACCESS_KEY_ID', 'Not set')[:5]}...")
    
    # Get the caller identity to verify credentials
    sts = boto3.client('sts')
    try:
        caller_identity = sts.get_caller_identity()
        logger.debug(f"Caller Identity: {caller_identity}")
    except Exception as e:
        logger.error(f"Error getting caller identity: {str(e)}")


def lambda_handler(event, context):
    # checkcreds()
 
    if isinstance(event, dict):
        # API Gateway request with queryStringParameters
        if event.get('queryStringParameters') and 'prompt' in event['queryStringParameters']:
            prompt = event['queryStringParameters']['prompt']
        # API Gateway request with multiValueQueryStringParameters    
        elif event.get('multiValueQueryStringParameters') and 'prompt' in event['multiValueQueryStringParameters']:
            prompt = event['multiValueQueryStringParameters']['prompt'][0]
        # Direct lambda invocation with prompt in body
        elif 'prompt' in event:
            prompt = event['prompt']
        # API Gateway request with prompt in body
        elif 'body' in event:
            try:
                body = json.loads(event['body'])
                prompt = body.get('prompt')
            except:
                prompt = None
        else:
            prompt = None
    else:
        prompt = None

    if not prompt:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'No prompt provided'})
        }

 
 
    print("hello world invoked")
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        "body": json.dumps({
            "message": "hello world " + prompt,
            # "location": ip.text.replace("\n", "")
        }),
    }
