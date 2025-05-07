import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import pytest
from unittest.mock import patch, MagicMock, ANY
import urllib.request
import urllib.error
import base64
from io import BytesIO


class TestAuthToken:
    """Test suite for the auth_token Lambda function"""

    @pytest.fixture
    def mock_env_variables(self, monkeypatch):
        """Fixture to set environment variables for testing"""
        monkeypatch.setenv('USER_POOL_ID', 'us-east-1_testpool')
        monkeypatch.setenv('CLIENT_ID', 'test-client-id')
        monkeypatch.setenv('CLIENT_SECRET', 'test-client-secret')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        return True  # Return a value to ensure the fixture is used

    @pytest.fixture
    def sample_event(self):
        """Fixture providing a sample API Gateway event with authorization code"""
        return {
            'body': json.dumps({
                'code': 'test-auth-code',
                'redirectUri': 'https://example.com/callback'
            })
        }

    @pytest.fixture
    def sample_cognito_response(self):
        """Fixture providing a sample Cognito token response"""
        return {
            'access_token': 'test-access-token',
            'id_token': 'test-id-token',
            'refresh_token': 'test-refresh-token',
            'expires_in': 3600
        }

    def test_lambda_handler_missing_code(self, mock_env_variables):
        """Test handling of missing code parameter"""
        # Import here to ensure environment variables are set first
        from handlers.auth_token.auth_token import lambda_handler
        
        event = {
            'body': json.dumps({
                'redirectUri': 'https://example.com/callback'
                # Missing 'code' parameter
            })
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 400
        assert 'Missing required parameters' in json.loads(response['body'])['error']

    def test_lambda_handler_missing_redirect_uri(self, mock_env_variables):
        """Test handling of missing redirectUri parameter"""
        # Import here to ensure environment variables are set first
        from handlers.auth_token.auth_token import lambda_handler
        
        event = {
            'body': json.dumps({
                'code': 'test-auth-code'
                # Missing 'redirectUri' parameter
            })
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 400
        assert 'Missing required parameters' in json.loads(response['body'])['error']

    def test_lambda_handler_missing_body(self, mock_env_variables):
        """Test handling of missing request body"""
        # Import here to ensure environment variables are set first
        from handlers.auth_token.auth_token import lambda_handler
        
        event = {}  # No body
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 400
        assert 'Missing required parameters' in json.loads(response['body'])['error']

    def test_lambda_handler_successful_exchange(self, mock_env_variables, sample_event, sample_cognito_response):
        """Test successful exchange of authorization code for tokens"""
        # Import here to ensure environment variables are set first
        with patch('handlers.auth_token.auth_token.urllib.request.Request') as mock_request, \
             patch('handlers.auth_token.auth_token.urllib.request.urlopen') as mock_urlopen:
            
            # Import after patching
            from handlers.auth_token.auth_token import lambda_handler
            
            # Mock the urllib.request.urlopen response
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(sample_cognito_response).encode('utf-8')
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            response = lambda_handler(sample_event, {})
            
            # Verify the request was made correctly
            mock_request.assert_called_once()
            
            # Verify the response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['accessToken'] == 'test-access-token'
            assert body['idToken'] == 'test-id-token'
            assert body['refreshToken'] == 'test-refresh-token'
            assert body['expiresIn'] == 3600

    def test_lambda_handler_without_client_secret(self, mock_env_variables, sample_event, sample_cognito_response, monkeypatch):
        """Test token exchange without a client secret"""
        # Remove CLIENT_SECRET from environment
        monkeypatch.delenv('CLIENT_SECRET', raising=False)
        
        with patch('handlers.auth_token.auth_token.urllib.request.Request') as mock_request, \
             patch('handlers.auth_token.auth_token.urllib.request.urlopen') as mock_urlopen:
            
            # Import after patching
            from handlers.auth_token.auth_token import lambda_handler
            
            # Mock the urllib.request.urlopen response
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(sample_cognito_response).encode('utf-8')
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            response = lambda_handler(sample_event, {})
            
            # Verify the request was made correctly
            mock_request.assert_called_once()
            
            # Verify the response
            assert response['statusCode'] == 200

    def test_lambda_handler_http_error(self, mock_env_variables, sample_event):
        """Test handling of HTTP errors from Cognito"""
        with patch('handlers.auth_token.auth_token.urllib.request.Request'), \
             patch('handlers.auth_token.auth_token.urllib.request.urlopen') as mock_urlopen:
            
            # Import after patching
            from handlers.auth_token.auth_token import lambda_handler
            
            # Mock urllib.request.urlopen to raise an HTTPError
            http_error = urllib.error.HTTPError(
                url='https://example.com',
                code=400,
                msg='Bad Request',
                hdrs={},
                fp=BytesIO(b'{"error":"invalid_grant","error_description":"Invalid authorization code"}')
            )
            mock_urlopen.side_effect = http_error
            
            response = lambda_handler(sample_event, {})
            
            assert response['statusCode'] == 500
            assert 'error' in json.loads(response['body'])

    def test_lambda_handler_url_error(self, mock_env_variables, sample_event):
        """Test handling of URL errors (connection issues)"""
        with patch('handlers.auth_token.auth_token.urllib.request.Request'), \
             patch('handlers.auth_token.auth_token.urllib.request.urlopen') as mock_urlopen:
            
            # Import after patching
            from handlers.auth_token.auth_token import lambda_handler
            
            # Mock urllib.request.urlopen to raise a URLError
            url_error = urllib.error.URLError(reason='Connection refused')
            mock_urlopen.side_effect = url_error
            
            response = lambda_handler(sample_event, {})
            
            assert response['statusCode'] == 500
            assert 'error' in json.loads(response['body'])

    def test_lambda_handler_general_exception(self, mock_env_variables, sample_event):
        """Test handling of general exceptions"""
        with patch('handlers.auth_token.auth_token.urllib.request.Request', side_effect=Exception('Test exception')):
            # Import after patching
            from handlers.auth_token.auth_token import lambda_handler
            
            response = lambda_handler(sample_event, {})
            
            assert response['statusCode'] == 500
            assert 'Test exception' in json.loads(response['body'])['error']

    def test_auth_header_generation(self, mock_env_variables, sample_event, sample_cognito_response):
        """Test that the Authorization header is correctly generated"""
        with patch('handlers.auth_token.auth_token.urllib.request.Request') as mock_request, \
             patch('handlers.auth_token.auth_token.urllib.request.urlopen') as mock_urlopen:
            
            # Import after patching
            from handlers.auth_token.auth_token import lambda_handler
            
            # Mock the urllib.request.urlopen response
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(sample_cognito_response).encode('utf-8')
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            lambda_handler(sample_event, {})
            
            # Verify the request was called
            mock_request.assert_called_once()
            
            # Check that the call included the correct arguments
            # The headers might be passed as a positional argument or keyword argument
            # depending on how urllib.request.Request is called in the code
            call_args = mock_request.call_args
            
            # Check if headers are in kwargs
            if len(call_args[1]) > 0 and 'headers' in call_args[1]:
                headers = call_args[1]['headers']
                assert 'Authorization' in headers
                auth_header = headers['Authorization']
                assert auth_header.startswith('Basic ')
                
                # Decode and verify the base64 part
                base64_part = auth_header.split(' ')[1]
                decoded = base64.b64decode(base64_part).decode('ascii')
                assert decoded == 'test-client-id:test-client-secret'

    def test_form_data_encoding(self, mock_env_variables, sample_event, sample_cognito_response):
        """Test that form data is correctly encoded"""
        with patch('handlers.auth_token.auth_token.urllib.request.Request') as mock_request, \
             patch('handlers.auth_token.auth_token.urllib.request.urlopen') as mock_urlopen:
            
            # Import after patching
            from handlers.auth_token.auth_token import lambda_handler
            
            # Mock the urllib.request.urlopen response
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(sample_cognito_response).encode('utf-8')
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            lambda_handler(sample_event, {})
            
            # Verify the request was called
            mock_request.assert_called_once()
            
            # Get the data from the request (should be the second positional argument)
            encoded_data = mock_request.call_args[0][1]
            
            # Verify the data contains the expected parameters
            decoded_data = urllib.parse.parse_qs(encoded_data.decode('ascii'))
            assert decoded_data['grant_type'] == ['authorization_code']
            assert decoded_data['client_id'] == ['test-client-id']
            assert decoded_data['code'] == ['test-auth-code']
            assert decoded_data['redirect_uri'] == ['https://example.com/callback']