import json
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    """
    Handle prediction requests and stream responses back to the client.
    Simple version without Strands for testing WebSocket infrastructure.
    """
    print("WebSocket message event:", event)
    
    # Extract connection ID for WebSocket
    connection_id = event.get('requestContext', {}).get('connectionId')
    domain_name = event.get('requestContext', {}).get('domainName')
    stage = event.get('requestContext', {}).get('stage')
    
    if not connection_id or not domain_name or not stage:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing WebSocket connection information'})
        }
    
    # Set up API Gateway Management API client
    api_gateway_management_api = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f"https://{domain_name}/{stage}"
    )
    
    # Get the prompt from the event body
    try:
        body = json.loads(event.get('body', '{}'))
        prompt = body.get('prompt', '')
        
        if not prompt:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No prompt provided'})
            }
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Invalid request body: {str(e)}'})
        }
    
    # Get current date and time
    current_datetime = datetime.now()
    formatted_date = current_datetime.strftime("%Y-%m-%d")
    formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # Send initial message
        api_gateway_management_api.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                "type": "status",
                "status": "processing",
                "message": "Processing your prediction..."
            })
        )
        
        # Simulate streaming by sending multiple text chunks
        chunks = [
            "Analyzing your prediction: ",
            prompt,
            "\n\nGenerating verification method...\n",
            "Creating structured format...\n",
            "Setting verification date...\n"
        ]
        
        for chunk in chunks:
            api_gateway_management_api.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    "type": "text",
                    "content": chunk
                })
            )
        
        # Create a simple mock response
        mock_response = {
            "prediction_statement": prompt,
            "verification_date": "2025-12-31",
            "verification_method": {
                "source": ["Manual verification", "News sources"],
                "criteria": ["Check if prediction came true"],
                "steps": ["Wait until verification date", "Check relevant sources"]
            },
            "initial_status": "pending",
            "creation_date": formatted_datetime
        }
        
        # Send the complete response
        api_gateway_management_api.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                "type": "complete",
                "content": json.dumps(mock_response)
            })
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'Streaming completed'})
        }
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        try:
            # Notify client of error
            api_gateway_management_api.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    "type": "error",
                    "message": str(e)
                })
            )
        except:
            pass
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }