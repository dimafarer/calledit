import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from datetime import datetime
from handlers.write_to_db.write_to_db import (
    lambda_handler, 
    get_cors_headers, 
    get_post_body_property,
    get_user_from_cognito_context
)


class TestWriteToDB:
    """Test suite for the write_to_db Lambda function"""

    @pytest.fixture
    def mock_dynamodb_resource(self):
        """Fixture to mock the boto3 DynamoDB resource"""
        with patch('boto3.resource') as mock_resource:
            mock_table = MagicMock()
            mock_resource.return_value.Table.return_value = mock_table
            yield mock_table

    @pytest.fixture
    def sample_event_api_gateway(self):
        """Fixture providing a sample API Gateway event with Cognito authorizer"""
        return {
            'httpMethod': 'POST',
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
            },
            'body': json.dumps({
                'prediction': {
                    'prediction_statement': 'Test prediction',
                    'verification_date': '2023-12-31',
                    'verification_method': {
                        'source': ['Source 1'],
                        'criteria': ['Criteria 1'],
                        'steps': ['Step 1']
                    },
                    'initial_status': 'Pending'
                }
            })
        }

    @pytest.fixture
    def sample_event_direct_lambda(self):
        """Fixture providing a sample direct Lambda invocation event"""
        return {
            'prediction': {
                'prediction_statement': 'Test prediction',
                'verification_date': '2023-12-31',
                'verification_method': {
                    'source': ['Source 1'],
                    'criteria': ['Criteria 1'],
                    'steps': ['Step 1']
                },
                'initial_status': 'Pending'
            }
        }

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
        assert user_id == 'USER-01'  # Default user ID

    def test_get_user_from_cognito_context_with_no_context(self):
        """Test extracting user ID from Cognito context when no context is available"""
        event = {}
        
        user_id = get_user_from_cognito_context(event)
        assert user_id == 'USER-01'  # Default user ID

    def test_get_post_body_property_direct_property(self):
        """Test extracting property directly from event"""
        event = {'test_property': 'test_value'}
        result = get_post_body_property(event, 'test_property')
        
        assert result == 'test_value'

    def test_get_post_body_property_from_body_string(self):
        """Test extracting property from stringified JSON body"""
        event = {
            'body': json.dumps({
                'test_property': 'test_value'
            })
        }
        
        result = get_post_body_property(event, 'test_property')
        assert result == 'test_value'

    def test_get_post_body_property_from_body_dict(self):
        """Test extracting property from dict body"""
        event = {
            'body': {
                'test_property': 'test_value'
            }
        }
        
        result = get_post_body_property(event, 'test_property')
        assert result == 'test_value'

    def test_get_post_body_property_from_nested_dict(self):
        """Test extracting property from nested dict in body"""
        event = {
            'body': {
                'outer': {
                    'test_property': 'test_value'
                }
            }
        }
        
        result = get_post_body_property(event, 'test_property')
        assert result == 'test_value'

    def test_get_post_body_property_not_found(self):
        """Test handling when property is not found"""
        event = {'body': json.dumps({'other_property': 'value'})}
        
        result = get_post_body_property(event, 'test_property')
        assert isinstance(result, dict)
        assert result['statusCode'] == 400
        assert 'error' in json.loads(result['body'])

    def test_get_post_body_property_invalid_json(self):
        """Test handling invalid JSON in body"""
        event = {'body': 'This is not valid JSON'}
        
        result = get_post_body_property(event, 'test_property')
        assert isinstance(result, dict)
        assert result['statusCode'] == 400
        assert 'Invalid JSON' in json.loads(result['body'])['error']

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

    def test_lambda_handler_missing_prediction(self):
        """Test handling when prediction is missing"""
        event = {
            'httpMethod': 'POST',
            'headers': {
                'origin': 'http://localhost:5173'
            },
            'body': json.dumps({
                'other_field': 'value'
            })
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 400
        assert 'Required property "prediction"' in json.loads(response['body'])['error']

    def test_lambda_handler_api_gateway_success(self, sample_event_api_gateway, mock_dynamodb_resource):
        """Test successful write to DynamoDB via API Gateway event"""
        # Configure mock to return success
        mock_dynamodb_resource.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        with patch('handlers.write_to_db.write_to_db.datetime') as mock_datetime:
            # Mock the datetime to return a fixed value
            mock_datetime.now.return_value.isoformat.return_value = '2023-01-01T12:00:00'
            
            response = lambda_handler(sample_event_api_gateway, {})
            
            # Verify DynamoDB put_item was called correctly
            mock_dynamodb_resource.put_item.assert_called_once()
            call_args = mock_dynamodb_resource.put_item.call_args[1]
            
            # Check the item structure
            item = call_args['Item']
            assert item['PK'] == 'USER:test-user-id'
            assert item['SK'] == 'PREDICTION#2023-01-01T12:00:00'
            assert item['userId'] == 'test-user-id'
            assert item['status'] == 'PENDING'
            assert item['createdAt'] == '2023-01-01T12:00:00'
            assert item['updatedAt'] == '2023-01-01T12:00:00'
            assert item['prediction_statement'] == 'Test prediction'
            
            # Verify the response
            assert response['statusCode'] == 200
            assert 'Prediction logged successfully' in json.loads(response['body'])['response']

    def test_lambda_handler_direct_lambda_success(self, sample_event_direct_lambda, mock_dynamodb_resource):
        """Test successful write to DynamoDB via direct Lambda invocation"""
        # Configure mock to return success
        mock_dynamodb_resource.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        with patch('handlers.write_to_db.write_to_db.datetime') as mock_datetime:
            # Mock the datetime to return a fixed value
            mock_datetime.now.return_value.isoformat.return_value = '2023-01-01T12:00:00'
            
            response = lambda_handler(sample_event_direct_lambda, {})
            
            # Verify DynamoDB put_item was called correctly
            mock_dynamodb_resource.put_item.assert_called_once()
            
            # Verify the response
            assert response['statusCode'] == 200
            assert 'Prediction logged successfully' in json.loads(response['body'])['response']

    def test_lambda_handler_dynamodb_error(self, sample_event_api_gateway, mock_dynamodb_resource):
        """Test handling of DynamoDB errors"""
        # Configure mock to raise ClientError
        error_response = {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Table not found'}}
        mock_dynamodb_resource.put_item.side_effect = ClientError(error_response, 'PutItem')
        
        response = lambda_handler(sample_event_api_gateway, {})
        
        assert response['statusCode'] == 500
        assert 'error' in json.loads(response['body'])

    def test_lambda_handler_unexpected_error(self, sample_event_api_gateway):
        """Test handling of unexpected errors"""
        # Use a patch to force an exception during execution
        with patch('boto3.resource', side_effect=Exception('Unexpected test error')):
            response = lambda_handler(sample_event_api_gateway, {})
            
            assert response['statusCode'] == 500
            assert 'Unexpected test error' in json.loads(response['body'])['error']