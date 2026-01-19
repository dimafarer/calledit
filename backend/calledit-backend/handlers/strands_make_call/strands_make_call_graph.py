"""
Lambda Handler for Prediction Verification using 3-Agent Graph

This handler integrates the new 3-agent graph workflow:
Parser → Categorizer → Verification Builder

Following Strands best practices:
- Uses prediction_graph for orchestration
- Comprehensive callback handler for streaming
- Simple error handling with fallbacks
- Backward compatible with existing API
"""

import json
import boto3
import logging
from datetime import datetime, timezone
import pytz

from prediction_graph import execute_prediction_graph
from utils import get_current_datetime_in_timezones, convert_local_to_utc

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create_streaming_callback(connection_id, api_gateway_client):
    """
    Create comprehensive callback handler for graph streaming.
    
    Handles all Strands lifecycle events:
    - Text generation (data field)
    - Tool usage (current_tool_use field)
    - Lifecycle events (init_event_loop, start_event_loop, complete, force_stop)
    - Message events (message field)
    
    Following Strands best practices:
    - Graceful error handling (catch and log, don't re-raise)
    - Never crash agent execution
    
    Args:
        connection_id: WebSocket connection ID
        api_gateway_client: API Gateway Management API client
        
    Returns:
        Callback handler function
    """
    def callback_handler(**kwargs):
        try:
            # Text generation events
            if "data" in kwargs:
                api_gateway_client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        "type": "text",
                        "content": kwargs["data"]
                    })
                )
            
            # Tool usage events
            elif "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
                api_gateway_client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        "type": "tool",
                        "name": kwargs["current_tool_use"]["name"],
                        "input": kwargs["current_tool_use"].get("input", {})
                    })
                )
            
            # Lifecycle events
            elif kwargs.get("init_event_loop"):
                logger.info("Event loop initialized")
                
            elif kwargs.get("start_event_loop"):
                logger.info("Event loop cycle starting")
                
            elif kwargs.get("complete"):
                api_gateway_client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        "type": "status",
                        "status": "complete"
                    })
                )
                
            elif kwargs.get("force_stop"):
                reason = kwargs.get("force_stop_reason", "unknown")
                logger.warning(f"Agent force-stopped: {reason}")
                
            # Message events
            elif "message" in kwargs:
                logger.debug(f"Message created: {kwargs['message'].get('role')}")
                
        except Exception as e:
            # Graceful error handling - don't crash agent
            logger.error(f"Callback error: {str(e)}", exc_info=True)
            # Don't re-raise - callback errors shouldn't stop execution
    
    return callback_handler


def lambda_handler(event, context):
    """
    Lambda handler for prediction verification using 3-agent graph.
    
    Processes WebSocket messages and streams responses back to client.
    Uses the new graph workflow: Parser → Categorizer → Verification Builder
    
    Args:
        event: Lambda event from API Gateway WebSocket
        context: Lambda context
        
    Returns:
        Lambda response with statusCode and body
    """
    try:
        logger.info("WebSocket message event received")
        
        # Extract connection information
        connection_id = event.get('requestContext', {}).get('connectionId')
        domain_name = event.get('requestContext', {}).get('domainName')
        stage = event.get('requestContext', {}).get('stage')
        
        if not connection_id or not domain_name or not stage:
            logger.error("Missing WebSocket connection information")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing WebSocket connection information'})
            }
        
        # Create API Gateway Management API client
        api_gateway_client = boto3.client(
            'apigatewaymanagementapi',
            endpoint_url=f"https://{domain_name}/{stage}"
        )
        
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
            action = body.get('action', 'makecall')
            prompt = body.get('prompt', '')
            user_timezone = body.get('timezone', 'UTC')
            
            if not prompt:
                logger.warning("No prompt provided in request")
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'No prompt provided'})
                }
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request body: {str(e)}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid JSON format'})
            }
        
        # Get current datetime in both UTC and user's timezone
        (formatted_date_utc, formatted_datetime_utc, 
         formatted_date_local, formatted_datetime_local) = get_current_datetime_in_timezones(user_timezone)
        
        # Create streaming callback
        callback_handler = create_streaming_callback(connection_id, api_gateway_client)
        
        # Send initial processing message
        api_gateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                "type": "status",
                "status": "processing",
                "message": "Processing your prediction with 3-agent graph..."
            })
        )
        
        # Execute the 3-agent graph
        logger.info(f"Executing graph for prediction: {prompt[:50]}...")
        
        final_state = execute_prediction_graph(
            user_prompt=prompt,
            user_timezone=user_timezone,
            current_datetime_utc=formatted_datetime_utc,
            current_datetime_local=formatted_datetime_local,
            callback_handler=callback_handler
        )
        
        # Convert verification_date from local to UTC if needed
        verification_date_utc = final_state.get("verification_date", "")
        if verification_date_utc and not verification_date_utc.endswith("Z"):
            # Convert local time to UTC
            converted = convert_local_to_utc(verification_date_utc, user_timezone)
            if converted:
                verification_date_utc = converted
        
        # Build response in expected format (backward compatible)
        response_data = {
            "prediction_statement": final_state.get("prediction_statement", prompt),
            "verification_date": verification_date_utc,
            "prediction_date": formatted_datetime_utc,
            "timezone": "UTC",
            "user_timezone": user_timezone,
            "local_prediction_date": formatted_datetime_local,
            "verifiable_category": final_state.get("verifiable_category", "human_verifiable_only"),
            "category_reasoning": final_state.get("category_reasoning", "No reasoning provided"),
            "verification_method": final_state.get("verification_method", {
                "source": ["Manual verification"],
                "criteria": ["Human judgment required"],
                "steps": ["Manual review needed"]
            }),
            "initial_status": "pending",
            "date_reasoning": final_state.get("date_reasoning", "No reasoning provided")
        }
        
        # Check for errors in graph execution
        if "error" in final_state:
            logger.warning(f"Graph execution had error: {final_state['error']}")
            response_data["error"] = final_state["error"]
        
        # Send the complete response
        api_gateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                "type": "call_response",
                "content": json.dumps(response_data)
            })
        )
        
        # Send final completion status
        api_gateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                "type": "complete",
                "status": "ready"
            })
        )
        
        logger.info(f"Graph execution completed successfully. Category: {response_data['verifiable_category']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'Streaming completed'})
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}", exc_info=True)
        
        # Try to notify client of error
        try:
            api_gateway_client.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    "type": "error",
                    "message": f"Processing failed: {str(e)}"
                })
            )
        except:
            pass
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
