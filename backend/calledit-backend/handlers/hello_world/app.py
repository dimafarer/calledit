import json
import logging
import boto3
import os
# import requests

headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        }

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



def lambda_handler(event, context):
    print("hello world invoked")
    # checkcreds()
    prompt_result = get_event_property(event, 'prompt')
    # Check if prompt_result is an error response
    if isinstance(prompt_result, dict) and 'statusCode' in prompt_result:
        return prompt_result  # Return the error response directly so call resource can see the error
    
    return {
        "statusCode": 200,
        # "headers": {
        #     "Access-Control-Allow-Origin": "*",
        #     "Access-Control-Allow-Headers": "Content-Type",
        #     "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        # },
        "headers" : headers,
        "body": json.dumps({
            "message": "hello world " + prompt_result,
        }),
    }
