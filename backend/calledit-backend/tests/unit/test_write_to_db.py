import json
import pytest
from unittest.mock import patch, MagicMock

# Import the handler
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../handlers/write_to_db'))
from write_to_db import lambda_handler, get_post_body_property

@pytest.fixture()
def nova_response_event():
    """Generate a mock event with NovaResponse data"""
    return {
        "body": json.dumps({
            "prediction": {
                "prediction_statement": "Test prediction",
                "verification_date": "2023-12-31",
                "verification_method": {
                    "source": ["Test source"],
                    "criteria": ["Test criteria"],
                    "steps": ["Test step"]
                },
                "initial_status": "pending"
            }
        }),
        "resource": "/log-call",
        "httpMethod": "POST",
        "headers": {
            "Content-Type": "application/json"
        }
    }

def test_get_post_body_property():
    """Test the get_post_body_property function"""
    # Test with direct property
    event = {"prediction": {"test": "value"}}
    result = get_post_body_property(event, 'prediction')
    assert result == {"test": "value"}
    
    # Test with nested property in body
    event = {"body": json.dumps({"prediction": {"test": "value"}})}
    result = get_post_body_property(event, 'prediction')
    assert result == {"test": "value"}
    
    # Test with missing property
    event = {"body": json.dumps({"other": "value"})}
    result = get_post_body_property(event, 'prediction')
    assert 'statusCode' in result
    assert result['statusCode'] == 400

@patch('write_to_db.boto3.resource')
def test_lambda_handler_success(mock_resource, nova_response_event):
    """Test successful execution of the lambda handler"""
    # Setup mock DynamoDB
    mock_table = MagicMock()
    mock_resource.return_value.Table.return_value = mock_table
    mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    
    # Call the handler
    response = lambda_handler(nova_response_event, {})
    
    # Verify response
    assert response['statusCode'] == 200
    assert 'Prediction logged successfully' in response['body']
    
    # Verify DynamoDB was called with correct data
    mock_resource.assert_called_once_with('dynamodb')
    mock_resource.return_value.Table.assert_called_once_with('calledit-db')
    mock_table.put_item.assert_called_once()
    
    # Verify the item structure (partial check)
    call_args = mock_table.put_item.call_args[1]['Item']
    assert 'PK' in call_args
    assert 'SK' in call_args
    assert 'prediction_statement' in call_args
    assert call_args['prediction_statement'] == 'Test prediction'

@patch('write_to_db.boto3.resource')
def test_lambda_handler_error(mock_resource, nova_response_event):
    """Test error handling in the lambda handler"""
    # Setup mock to raise exception
    mock_resource.side_effect = Exception("Test error")
    
    # Call the handler
    response = lambda_handler(nova_response_event, {})
    
    # Verify error response
    assert response['statusCode'] == 500
    assert 'error' in json.loads(response['body'])