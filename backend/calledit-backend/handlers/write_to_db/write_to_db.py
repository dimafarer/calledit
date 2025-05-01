# write a lambda handler to write to a ddb table named calledit-db with a primary key caled PK and a sort key name SK
import boto3
import json
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from datetime import datetime

headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}


def get_post_body_property(event, prop_name):
    """
    Extract property from POST request body, handling both direct Lambda invocation
    and API Gateway integration cases.
    
    Args:
        event: Lambda event object
        prop_name: Name of property to extract
    
    Returns:
        Value if found, or error response if not found/invalid
    """
    try:
        # Handle direct Lambda invocation where event might be the body itself
        if isinstance(event, dict):
            # Case 1: Direct lambda invocation with property in event
            if prop_name in event:
                return event[prop_name]
            
            # Case 2: API Gateway request with stringified JSON body
            if 'body' in event:
                # Parse body if it's a string
                body = (
                    json.loads(event['body']) 
                    if isinstance(event['body'], str) 
                    else event['body']
                )
                
                # Look for property in parsed body
                if prop_name in body:
                    return body[prop_name]
                
                # Handle nested JSON structures
                for key, value in body.items():
                    if isinstance(value, dict) and prop_name in value:
                        return value[prop_name]
        
        # If we get here, property wasn't found
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({
                'error': f'Required property "{prop_name}" not found in request body'
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({
                'error': 'Invalid JSON in request body'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': f'Error processing request: {str(e)}'
            })
        }


def get_user_from_cognito_context(event):
    """
    Extract user information from the Cognito authorizer context.
    
    Args:
        event: Lambda event object
    
    Returns:
        User ID if found, or default value if not found
    """
    try:
        # Check if the event contains the requestContext with authorizer information
        if ('requestContext' in event and 
            'authorizer' in event['requestContext'] and 
            'claims' in event['requestContext']['authorizer']):
            
            claims = event['requestContext']['authorizer']['claims']
            
            # Try to get the user's sub (unique identifier) from claims
            if 'sub' in claims:
                return claims['sub']
            
            # Alternatively, try to get the user's email
            if 'email' in claims:
                return claims['email']
        
        # If we can't find user info, return a default value
        return "USER-01"  # Default user ID if not authenticated
    except Exception as e:
        print(f"Error extracting user from Cognito context: {str(e)}")
        return "USER-01"  # Default user ID if there's an error


# Call the function
def lambda_handler(event, context):
    try:
        # Get user ID from Cognito context
        user_id = get_user_from_cognito_context(event)
        
        # Use your robust function to get the prediction
        prediction = get_post_body_property(event, 'prediction')
        # If get_post_body_property returned an error response, return it
        if isinstance(prediction, dict) and 'statusCode' in prediction:
            return prediction
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('calledit-db')
        # Get current timestamp for SK
        timestamp = datetime.now().isoformat()
        # Create item to store in DynamoDB
        # item = {
        #     'PK': str(f'USER:{user_id}:Call:{timestamp}'),
        #     'SK': str(timestamp),
        #     'userId': user_id,  # Store the user ID separately for easier querying
        #     **prediction  # Include all fields from prediction
        # }
        
        item = {
            'PK': f'USER:{user_id}',  # Clear entity type prefix
            'SK': f'PREDICTION#{timestamp}',  # Organized hierarchy
            'userId': user_id,  # Keep for GSI if needed
            'status': 'PENDING',  # Add status field
            'createdAt': timestamp,
            'updatedAt': timestamp,
            **prediction  # Include all fields from prediction
        }

        
        
        
        
        # Write to DynamoDB
        response = table.put_item(Item=item)
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'response': 'Prediction logged successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,  # Include headers in error response
            'body': json.dumps({'error': str(e)})
        }