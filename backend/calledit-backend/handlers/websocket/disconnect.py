import json

def lambda_handler(event, context):
    """
    Handle WebSocket disconnection events.
    """
    print("WebSocket disconnection event:", event)
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Disconnected'})
    }