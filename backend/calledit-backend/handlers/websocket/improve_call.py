"""
WebSocket handler for call improvement interactions
"""
import json
import boto3
import os
from review_agent import ReviewAgent

def lambda_handler(event, context):
    """Handle improvement requests from users"""
    
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
    
    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')
        
        review_agent = ReviewAgent()
        
        if action == 'request_questions':
            # User clicked on a section to get improvement questions
            section = body.get('section')
            questions = body.get('questions', [])
            
            friendly_questions = review_agent.ask_improvement_questions(section, questions)
            
            api_gateway_management_api.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    "type": "improvement_questions",
                    "data": {
                        "section": section,
                        "questions": friendly_questions
                    }
                })
            )
            
        elif action == 'submit_improvements':
            # User provided answers to improve a section
            section = body.get('section')
            user_input = body.get('user_input')
            original_response = body.get('original_response')
            original_prediction = body.get('original_prediction')
            
            # Generate improved response
            improvement_result = review_agent.regenerate_with_improvements(
                original_response, section, user_input, original_prediction
            )
            
            # Send improved response
            api_gateway_management_api.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    "type": "improved_response",
                    "data": improvement_result
                })
            )
            
            # If significant change, re-review the improved response
            if improvement_result.get('change_type') == 'significant':
                try:
                    new_review = review_agent.review_call_response(
                        improvement_result['updated_response']
                    )
                    
                    api_gateway_management_api.post_to_connection(
                        ConnectionId=connection_id,
                        Data=json.dumps({
                            "type": "review_complete",
                            "data": new_review
                        })
                    )
                except Exception as e:
                    print(f"Re-review failed: {e}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'success'})
        }
        
    except Exception as e:
        print(f"Error in improve_call handler: {str(e)}")
        
        try:
            api_gateway_management_api.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    "type": "error",
                    "message": f"Improvement failed: {str(e)}"
                })
            )
        except:
            pass
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }