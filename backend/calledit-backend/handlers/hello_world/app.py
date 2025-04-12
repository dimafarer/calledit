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
    checkcreds()
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    # try:
    #     ip = requests.get("http://checkip.amazonaws.com/")
    # except requests.RequestException as e:
    #     # Send some context about this error to Lambda Logs
    #     print(e)

    #     raise e
    print("hello world invoked")
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        "body": json.dumps({
            "message": "hello world",
            # "location": ip.text.replace("\n", "")
        }),
    }
