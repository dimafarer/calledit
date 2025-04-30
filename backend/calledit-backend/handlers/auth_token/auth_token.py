import json
import os
import urllib.parse
import urllib.request
import boto3
import base64
from botocore.exceptions import ClientError

# Get environment variables
USER_POOL_ID = os.environ.get('USER_POOL_ID')
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET', '')  # Optional, if your app has a client secret
REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Create Cognito Identity Provider client
cognito_idp = boto3.client('cognito-idp', region_name=REGION)

def lambda_handler(event, context):
    """
    Lambda function to exchange authorization code for tokens
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        code = body.get('code')
        redirect_uri = body.get('redirectUri')
        
        if not code or not redirect_uri:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': True
                },
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Exchange authorization code for tokens
        token_endpoint = f'https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/openid-configuration'
        
        # If client secret exists, create authorization header
        auth_header = None
        if CLIENT_SECRET:
            auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
            auth_bytes = auth_string.encode('ascii')
            base64_bytes = base64.b64encode(auth_bytes)
            base64_auth = base64_bytes.decode('ascii')
            auth_header = f"Basic {base64_auth}"
        
        # Prepare token request
        token_url = f"https://{USER_POOL_ID.split('_')[0]}.auth.{REGION}.amazoncognito.com/oauth2/token"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        if auth_header:
            headers['Authorization'] = auth_header
        
        data = {
            'grant_type': 'authorization_code',
            'client_id': CLIENT_ID,
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        # Encode data for x-www-form-urlencoded
        encoded_data = urllib.parse.urlencode(data).encode('ascii')
        
        # Create request
        req = urllib.request.Request(token_url, encoded_data, headers)
        
        # Send request
        with urllib.request.urlopen(req) as response:
            response_data = json.loads(response.read().decode('utf-8'))
        
        # Return tokens
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            },
            'body': json.dumps({
                'accessToken': response_data.get('access_token'),
                'idToken': response_data.get('id_token'),
                'refreshToken': response_data.get('refresh_token'),
                'expiresIn': response_data.get('expires_in')
            })
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            },
            'body': json.dumps({'error': str(e)})
        }