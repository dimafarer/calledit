import boto3
import json
from decimal import Decimal
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

# Custom JSON encoder to handle Decimal types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

print("Starting lambda function execution")

# List of allowed origins
ALLOWED_ORIGINS = [
    'http://localhost:5173',  # Local development
    'https://d2k653cdpjxjdu.cloudfront.net',  # Production CloudFront
]

def get_cors_headers(event):
    """
    Generate CORS headers based on the origin of the request.
    When credentials are enabled, Access-Control-Allow-Origin must be a specific origin, not '*'.
    
    Args:
        event: Lambda event object containing request details
        
    Returns:
        Dictionary of CORS headers
    """
    # Default headers with no specific origin
    cors_headers = {
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,GET',
        'Access-Control-Allow-Credentials': 'true'
    }
    
    # Extract origin from request headers
    origin = None
    if 'headers' in event and event['headers'] is not None:
        origin_header = event['headers'].get('origin') or event['headers'].get('Origin')
        if origin_header and origin_header in ALLOWED_ORIGINS:
            origin = origin_header
    
    # If we have a valid origin, add it to the headers
    if origin:
        cors_headers['Access-Control-Allow-Origin'] = origin
    else:
        # Fallback to the first allowed origin if no valid origin found
        # This is safer than using '*' when credentials are enabled
        cors_headers['Access-Control-Allow-Origin'] = ALLOWED_ORIGINS[0]
    
    print(f"Generated CORS headers with origin: {cors_headers['Access-Control-Allow-Origin']}")
    return cors_headers

def get_user_from_cognito_context(event):
    """
    Extract user information from the Cognito authorizer context.
    
    Args:
        event: Lambda event object
    
    Returns:
        User ID if found, or None if not found
    """
    print(f"Attempting to extract user from event: {json.dumps(event)}")
    try:
        # Check if the event contains the requestContext with authorizer information
        print("Checking for requestContext and authorizer information")
        if ('requestContext' in event and 
            'authorizer' in event['requestContext'] and 
            'claims' in event['requestContext']['authorizer']):
            
            claims = event['requestContext']['authorizer']['claims']
            print(f"Found claims in authorizer context: {claims}")
            
            # Try to get the user's sub (unique identifier) from claims
            if 'sub' in claims:
                print(f"Found user sub in claims: {claims['sub']}")
                return claims['sub']
            
            # Alternatively, try to get the user's email
            if 'email' in claims:
                print(f"Found user email in claims: {claims['email']}")
                return claims['email']
        
        print("No user identification found in claims")
        return None  # No user ID found
    except Exception as e:
        print(f"Error extracting user from Cognito context: {str(e)}")
        return None

def lambda_handler(event, context):
    """
    Lambda handler to list predictions for a logged-in user.
    
    Args:
        event: Lambda event object
        context: Lambda context object
        
    Returns:
        API Gateway response with user's predictions or error message
    """
    print(f"Lambda handler invoked with event: {json.dumps(event)}")
    
    # Get CORS headers for this request
    cors_headers = get_cors_headers(event)
    
    # Handle OPTIONS request (preflight)
    if event.get('httpMethod') == 'OPTIONS':
        print("Handling OPTIONS preflight request")
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': ''
        }
    
    try:
        # Get user ID from Cognito context
        print("Attempting to get user ID from Cognito context")
        user_id = get_user_from_cognito_context(event)
        print(f"Retrieved user_id: {user_id}")
        
        # If no user ID found, return unauthorized error
        if not user_id:
            print("No user ID found - returning unauthorized error")
            return {
                'statusCode': 401,
                'headers': cors_headers,
                'body': json.dumps({'error': 'User not authenticated'})
            }
        
        # Initialize DynamoDB client
        print("Initializing DynamoDB client")
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('calledit-db')
        print("DynamoDB table connection established")
        
        # Query DynamoDB for items with the user's ID
        # We're using a begins_with query on the PK to find all predictions for this user
        # The format is USER:[cognitouser]:Call:[datetime]
        print(f"Querying DynamoDB for items with PK prefix USER:{user_id}")
        # Query DynamoDB for items with the user's ID
        print(f"Querying DynamoDB for predictions with PK USER:{user_id}")
        # Use ScanIndexForward=False to sort in descending order (newest first)
        response = table.query(
            KeyConditionExpression=Key('PK').eq(f'USER:{user_id}') & Key('SK').begins_with('PREDICTION#'),
            ScanIndexForward=False  # This will sort by SK in descending order (newest first)
        )

        print(f"DynamoDB query response: {json.dumps(response, cls=DecimalEncoder)}")
        
        # Extract items from response
        items = response.get('Items', [])
        print(f"Found {len(items)} items for user")
        
        # Format the predictions for the frontend
        predictions = []
        print("Beginning to format predictions")
        for item in items:
            # Process item (skip logging raw item to avoid Decimal issues)
            # Extract the prediction data from the DynamoDB item
            prediction = {
                'prediction_statement': item.get('prediction_statement', ''),
                'verification_date': item.get('verification_date', ''),
                'prediction_date': item.get('prediction_date', item.get('createdAt', '')),  # Use prediction_date or fall back to createdAt
                'verifiable_category': item.get('verifiable_category', 'human_verifiable_only'),
                'category_reasoning': item.get('category_reasoning', ''),
                'verification_method': {
                    'source': item.get('verification_method', {}).get('source', []),
                    'criteria': item.get('verification_method', {}).get('criteria', []),
                    'steps': item.get('verification_method', {}).get('steps', [])
                },
                'initial_status': item.get('initial_status', 'Pending'),
                # Add verification status fields if they exist
                'verification_status': item.get('verification_status', ''),
                'verification_confidence': float(item.get('verification_confidence', 0)) if item.get('verification_confidence') else None,
                'verification_reasoning': item.get('verification_reasoning', '')
            }
            print(f"Formatted prediction: {json.dumps(prediction, cls=DecimalEncoder)}")
            predictions.append(prediction)
        
        print(f"Returning successful response with {len(predictions)} predictions")
        # Return successful response with predictions
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'results': predictions}, cls=DecimalEncoder)
        }
        
    except ClientError as e:
        print(f"DynamoDB error: {str(e)}")
        print(f"Error details: {e.response['Error']}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Database error: {str(e)}'}, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error args: {e.args}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Unexpected error: {str(e)}'}, cls=DecimalEncoder)
        }
