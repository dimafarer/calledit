import json
import pytest
from unittest.mock import patch, MagicMock

from handlers.list_predictions.list_predictions import lambda_handler, get_user_from_cognito_context

@pytest.fixture
def mock_event():
    return {
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
def mock_context():
    return {}

@pytest.fixture
def mock_dynamodb_response():
    return {
        'Items': [
            {
                'PK': 'USER:test-user-id',
                'SK': 'PREDICTION#2023-01-02T12:00:00',
                'userId': 'test-user-id',
                'prediction_statement': 'Test prediction 2',
                'verification_date': '2024-12-31',
                'verification_method': {
                    'source': ['Source 3'],
                    'criteria': ['Criteria 2', 'Criteria 3'],
                    'steps': ['Step 3']
                },
                'initial_status': 'Pending',
                'createdAt': '2023-01-02T12:00:00'
            },
            {
                'PK': 'USER:test-user-id',
                'SK': 'PREDICTION#2023-01-01T12:00:00',
                'userId': 'test-user-id',
                'prediction_statement': 'Test prediction 1',
                'verification_date': '2023-12-31',
                'verification_method': {
                    'source': ['Source 1', 'Source 2'],
                    'criteria': ['Criteria 1'],
                    'steps': ['Step 1', 'Step 2']
                },
                'initial_status': 'Pending',
                'createdAt': '2023-01-01T12:00:00'
            }
        ]
    }

def test_get_user_from_cognito_context(mock_event):
    # Test with valid event containing sub
    user_id = get_user_from_cognito_context(mock_event)
    assert user_id == 'test-user-id'
    
    # Test with event missing sub but containing email
    event_with_email = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        }
    }
    user_id = get_user_from_cognito_context(event_with_email)
    assert user_id == 'test@example.com'
    
    # Test with invalid event
    user_id = get_user_from_cognito_context({})
    assert user_id is None

@patch('handlers.list_predictions.list_predictions.boto3.resource')
def test_lambda_handler_success(mock_boto3_resource, mock_event, mock_context, mock_dynamodb_response):
    # Setup mock DynamoDB table and query response
    mock_table = MagicMock()
    mock_table.query.return_value = mock_dynamodb_response
    
    mock_dynamodb = MagicMock()
    mock_dynamodb.Table.return_value = mock_table
    
    mock_boto3_resource.return_value = mock_dynamodb
    
    # Call the lambda handler
    response = lambda_handler(mock_event, mock_context)
    
    # Verify the response
    assert response['statusCode'] == 200
    
    # Parse the response body
    body = json.loads(response['body'])
    assert 'results' in body
    assert len(body['results']) == 2
    
    # Verify the predictions data and order (newest first)
    predictions = body['results']
    # First prediction should be the newest one (2023-01-02)
    assert predictions[0]['prediction_statement'] == 'Test prediction 2'
    assert predictions[0]['created_at'] == '2023-01-02T12:00:00'
    # Second prediction should be the older one (2023-01-01)
    assert predictions[1]['prediction_statement'] == 'Test prediction 1'
    assert predictions[1]['created_at'] == '2023-01-01T12:00:00'
    
    # Verify DynamoDB was queried correctly with the right format
    mock_table.query.assert_called_once()
    args, kwargs = mock_table.query.call_args
    assert 'KeyConditionExpression' in kwargs
    assert 'ScanIndexForward' in kwargs
    assert kwargs['ScanIndexForward'] is False  # Verify descending order
    
    # Extract the user_id from the mock event
    user_id = mock_event['requestContext']['authorizer']['claims']['sub']
    
    # Verify that the query is using the correct format (USER:{user_id})
    # Convert the KeyConditionExpression to string and check if it contains the expected pattern
    key_condition_str = str(kwargs['KeyConditionExpression'])
    assert f"'USER:{user_id}'" in key_condition_str

@patch('handlers.list_predictions.list_predictions.boto3.resource')
def test_lambda_handler_no_auth(mock_boto3_resource, mock_context):
    # Test with event missing authentication
    event_no_auth = {}
    
    response = lambda_handler(event_no_auth, mock_context)
    
    # Verify unauthorized response
    assert response['statusCode'] == 401
    body = json.loads(response['body'])
    assert 'error' in body
    assert 'User not authenticated' in body['error']
    
    # Verify DynamoDB was not queried
    mock_boto3_resource.assert_not_called()

@patch('handlers.list_predictions.list_predictions.boto3.resource')
def test_lambda_handler_db_error(mock_boto3_resource, mock_event, mock_context):
    # Setup mock to raise an exception
    mock_table = MagicMock()
    mock_table.query.side_effect = Exception('Test database error')
    
    mock_dynamodb = MagicMock()
    mock_dynamodb.Table.return_value = mock_table
    
@patch('handlers.list_predictions.list_predictions.boto3.resource')
def test_lambda_handler_query_format(mock_boto3_resource, mock_event, mock_context):
    """
    Test to specifically verify that the query is using the correct format
    without the ":Call:" suffix, which was the root cause of the issue.
    Also verifies that ScanIndexForward is set to False for descending order.
    """
    # Setup mock DynamoDB table and query response
    mock_table = MagicMock()
    mock_table.query.return_value = {'Items': []}  # Empty response is fine for this test
    
    mock_dynamodb = MagicMock()
    mock_dynamodb.Table.return_value = mock_table
    
    mock_boto3_resource.return_value = mock_dynamodb
    
    # Call the lambda handler
    lambda_handler(mock_event, mock_context)
    
    # Verify DynamoDB was queried with the correct format
    mock_table.query.assert_called_once()
    args, kwargs = mock_table.query.call_args
    
    # Extract the user_id from the mock event
    user_id = mock_event['requestContext']['authorizer']['claims']['sub']
    
    # Convert the KeyConditionExpression to string
    key_condition_str = str(kwargs['KeyConditionExpression'])
    
    # Verify that the query is using just USER:{user_id} and not USER:{user_id}:Call:
    assert f"'USER:{user_id}'" in key_condition_str
    
    # The key point: Make sure we're not using the old format with ":Call:" suffix
    # This is important because we want to match all records for this user, not just calls
    assert not f"'USER:{user_id}:Call:'" in key_condition_str
    
    # Verify that ScanIndexForward is set to False for descending order (newest first)
    assert 'ScanIndexForward' in kwargs
    assert kwargs['ScanIndexForward'] is False