import json
import boto3
import os
from datetime import datetime
from strands import Agent

def lambda_handler(event, context):
    """
    Handle prediction requests and stream responses back to the client.
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
    
    # Define callback handler for streaming
    def stream_callback_handler(**kwargs):
        """
        Callback handler that streams responses back to the client.
        """
        try:
            if "data" in kwargs:
                # Send text chunks to the client
                api_gateway_management_api.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        "type": "text",
                        "content": kwargs["data"]
                    })
                )
            elif "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
                # Send tool usage info
                api_gateway_management_api.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        "type": "tool",
                        "name": kwargs["current_tool_use"]["name"],
                        "input": kwargs["current_tool_use"].get("input", {})
                    })
                )
            elif kwargs.get("complete", False):
                # Send completion notification
                api_gateway_management_api.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        "type": "status",
                        "status": "complete"
                    })
                )
        except Exception as e:
            print(f"Error sending to WebSocket: {str(e)}")
    
    # Create agent with streaming callback
    agent = Agent(
        callback_handler=stream_callback_handler,
        system_prompt="""You are a prediction verification expert. Your task is to:
            1. Analyze predictions
            2. Create structured verification criteria
            3. Specify how to verify the prediction"""
    )
    
    # Process the prompt with streaming
    user_prompt = f"""Create a structured verification format for this prediction: {prompt}
        
        Today's date is {formatted_date} and the current time is {formatted_datetime}.
        
        Format the response as a JSON object with:
        - prediction_statement
        - verification_date (use a realistic future date based on the prediction and today's date)
        - verification_method (source, criteria, steps)
        - initial_status (pending)"""
    
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
        
        # This will stream responses via the callback handler
        full_response = agent(user_prompt)
        
        # Send the complete response
        api_gateway_management_api.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                "type": "complete",
                "content": full_response
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