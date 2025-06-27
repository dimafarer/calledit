import json

def lambda_handler(event, context):
    """
    Handle WebSocket connection events.
    """
    print("WebSocket connection event:", event)
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Connected'})
    }