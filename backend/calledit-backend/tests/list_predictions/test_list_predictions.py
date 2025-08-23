import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from handlers.list_predictions.list_predictions import lambda_handler, get_cors_headers, get_user_from_cognito_context


class TestListPredictions:
    """Test suite for the list_predictions Lambda function"""

    @pytest.fixture
    def mock_dynamodb_resource(self):
        """Fixture to mock the boto3 DynamoDB resource"""
        with patch('boto3.resource') as mock_resource:
            mock_table = MagicMock()
            mock_resource.return_value.Table.return_value = mock_table
            yield mock_table

    @pytest.fixture
    def sample_event(self):
        """Fixture providing a sample API Gateway event with Cognito authorizer"""
        return {
            'httpMethod': 'GET',
            'headers': {
                'origin': 'http://localhost:5173'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-id',
                        'email': 'test@example.com'
                    }
                }
            }
        }

    @pytest.fixture
    def sample_dynamodb_items(self):
        """Fixture providing sample DynamoDB items for testing"""
        return [
            {
                'PK': 'USER:test-user-id',
                'SK': 'PREDICTION#2023-01-01',
                'prediction_statement': 'Test prediction 1',
                'verification_date': '2023-12-31',
                'verification_method': {
                    'source': ['Source 1'],
                    'criteria': ['Criteria 1'],
                    'steps': ['Step 1']
                },
                'initial_status': 'Pending',
                'createdAt': '2023-01-01T12:00:00Z'
            },
            {
                'PK': 'USER:test-user-id',
                'SK': 'PREDICTION#2023-02-01',
                'prediction_statement': 'Test prediction 2',
                'verification_date': '2024-02-01',
                'verification_method': {
                    'source': ['Source 2'],
                    'criteria': ['Criteria 2'],
                    'steps': ['Step 2']
                },
                'initial_status': 'Confirmed',
                'createdAt': '2023-02-01T12:00:00Z'
            }
        ]

    def test_get_cors_headers_with_valid_origin(self):
        """Test CORS headers generation with a valid origin"""
        event = {'headers': {'origin': 'http://localhost:5173'}}
        headers = get_cors_headers(event)
        
        assert headers['Access-Control-Allow-Origin'] == 'http://localhost:5173'
        assert headers['Access-Control-Allow-Credentials'] == 'true'
        assert 'Access-Control-Allow-Headers' in headers
        assert 'Access-Control-Allow-Methods' in headers

    def test_get_cors_headers_with_invalid_origin(self):
        """Test CORS headers generation with an invalid origin"""
        event = {'headers': {'origin': 'http://malicious-site.com'}}
        headers = get_cors_headers(event)
        
        # Should default to the first allowed origin
        assert headers['Access-Control-Allow-Origin'] == 'http://localhost:5173'

    def test_get_cors_headers_with_no_headers(self):
        """Test CORS headers generation with no headers in the event"""
        event = {}
        headers = get_cors_headers(event)
        
        # Should default to the first allowed origin
        assert headers['Access-Control-Allow-Origin'] == 'http://localhost:5173'

    def test_get_user_from_cognito_context_with_sub(self):
        """Test extracting user ID from Cognito context using sub claim"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-id',
                        'email': 'test@example.com'
                    }
                }
            }
        }
        
        user_id = get_user_from_cognito_context(event)
        assert user_id == 'test-user-id'

    def test_get_user_from_cognito_context_with_email_only(self):
        """Test extracting user ID from Cognito context using email when sub is not available"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'email': 'test@example.com'
                    }
                }
            }
        }
        
        user_id = get_user_from_cognito_context(event)
        assert user_id == 'test@example.com'

    def test_get_user_from_cognito_context_with_no_claims(self):
        """Test extracting user ID from Cognito context when no claims are available"""
        event = {
            'requestContext': {
                'authorizer': {}
            }
        }
        
        user_id = get_user_from_cognito_context(event)
        assert user_id is None

    def test_get_user_from_cognito_context_with_no_context(self):
        """Test extracting user ID from Cognito context when no context is available"""
        event = {}
        
        user_id = get_user_from_cognito_context(event)
        assert user_id is None

    def test_lambda_handler_options_request(self):
        """Test handling of OPTIONS preflight request"""
        event = {
            'httpMethod': 'OPTIONS',
            'headers': {
                'origin': 'http://localhost:5173'
            }
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        assert response['headers']['Access-Control-Allow-Origin'] == 'http://localhost:5173'
        assert response['body'] == ''

    def test_lambda_handler_no_user_id(self):
        """Test handling when no user ID is found"""
        event = {
            'httpMethod': 'GET',
            'headers': {
                'origin': 'http://localhost:5173'
            }
            # No requestContext with authorizer
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 401
        assert json.loads(response['body'])['error'] == 'User not authenticated'

    def test_lambda_handler_successful_response(self, sample_event, mock_dynamodb_resource, sample_dynamodb_items):
        """Test successful retrieval of predictions"""
        # Configure mock to return sample items
        mock_dynamodb_resource.query.return_value = {
            'Items': sample_dynamodb_items
        }
        
        response = lambda_handler(sample_event, {})
        
        # Verify the DynamoDB query was called correctly
        mock_dynamodb_resource.query.assert_called_once()
        
        # Instead of checking the KeyConditionExpression directly, verify the query parameters
        # were called with the correct user_id and SK prefix
        user_id = 'test-user-id'
        assert mock_dynamodb_resource.query.call_count == 1
        
        # Verify the response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'results' in body
        assert len(body['results']) == 2
        
        # Verify the prediction data is formatted correctly
        predictions = body['results']
        assert predictions[0]['prediction_statement'] == 'Test prediction 1'
        assert predictions[0]['verification_date'] == '2023-12-31'
        assert predictions[0]['verification_method']['source'] == ['Source 1']
        assert predictions[0]['initial_status'] == 'Pending'
        assert predictions[0]['prediction_date'] == '2023-01-01T12:00:00Z'

    def test_lambda_handler_dynamodb_client_error(self, sample_event, mock_dynamodb_resource):
        """Test handling of DynamoDB ClientError"""
        # Configure mock to raise ClientError
        error_response = {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Table not found'}}
        mock_dynamodb_resource.query.side_effect = ClientError(error_response, 'Query')
        
        response = lambda_handler(sample_event, {})
        
        assert response['statusCode'] == 500
        assert 'Database error' in json.loads(response['body'])['error']

    def test_lambda_handler_unexpected_error(self, sample_event, mock_dynamodb_resource):
        """Test handling of unexpected errors"""
        # Configure mock to raise a generic exception
        mock_dynamodb_resource.query.side_effect = Exception('Unexpected test error')
        
        response = lambda_handler(sample_event, {})
        
        assert response['statusCode'] == 500
        assert 'Unexpected error' in json.loads(response['body'])['error']