import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from handlers.make_call.make_call import lambda_handler, ensure_list


class TestMakeCall:
    """Test suite for the make_call Lambda function"""

    @pytest.fixture
    def mock_bedrock_client(self):
        """Fixture to mock the boto3 Bedrock client"""
        with patch('boto3.client') as mock_client:
            mock_bedrock = MagicMock()
            mock_client.return_value = mock_bedrock
            yield mock_bedrock

    @pytest.fixture
    def sample_event(self):
        """Fixture providing a sample API Gateway event with query parameters"""
        return {
            'queryStringParameters': {
                'prompt': 'Tesla will reach a market cap of $1 trillion by the end of 2025'
            }
        }

    @pytest.fixture
    def sample_bedrock_response(self):
        """Fixture providing a sample Bedrock response"""
        response_json = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "text": """```json
{
  "prediction_statement": "Tesla will reach a market cap of $1 trillion by the end of 2025",
  "verification_date": "2025-12-31",
  "verification_method": {
    "source": ["Yahoo Finance", "Bloomberg Terminal", "Tesla Investor Relations"],
    "criteria": ["Tesla's market capitalization must be at or above $1 trillion USD", "Verification must occur on or before December 31, 2025"],
    "steps": ["Check Tesla's stock ticker (TSLA) on a financial data platform", "Multiply the share price by the number of outstanding shares", "Confirm the market cap is at or above $1 trillion USD"]
  },
  "initial_status": "pending"
}
```"""
                        }
                    ]
                }
            }
        }
        
        # Create a mock response object with a read method that returns the JSON
        mock_response = {
            'body': BytesIO(json.dumps(response_json).encode('utf-8'))
        }
        return mock_response

    def test_ensure_list_with_string(self):
        """Test ensure_list function with a string input"""
        result = ensure_list("test")
        assert result == ["test"]
        assert isinstance(result, list)

    def test_ensure_list_with_list(self):
        """Test ensure_list function with a list input"""
        result = ensure_list(["item1", "item2"])
        assert result == ["item1", "item2"]
        assert isinstance(result, list)

    def test_ensure_list_with_none(self):
        """Test ensure_list function with None input"""
        result = ensure_list(None)
        assert result == []
        assert isinstance(result, list)

    def test_ensure_list_with_dict(self):
        """Test ensure_list function with a dict in the list"""
        result = ensure_list([{"key": "value"}])
        assert result == ['{"key": "value"}']
        assert isinstance(result, list)

    def test_lambda_handler_missing_prompt(self):
        """Test lambda_handler with missing prompt parameter"""
        event = {'queryStringParameters': {}}
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 400
        assert json.loads(response['body'])['error'] == 'No prompt provided'

    def test_lambda_handler_no_query_params(self):
        """Test lambda_handler with no query parameters"""
        event = {}
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 400
        assert json.loads(response['body'])['error'] == 'No prompt provided'

    def test_lambda_handler_successful_response(self, sample_event, mock_bedrock_client, sample_bedrock_response):
        """Test successful invocation of the Bedrock model"""
        # Configure mock to return sample response
        mock_bedrock_client.invoke_model.return_value = sample_bedrock_response
        
        response = lambda_handler(sample_event, {})
        
        # Verify Bedrock client was called correctly
        mock_bedrock_client.invoke_model.assert_called_once()
        call_args = mock_bedrock_client.invoke_model.call_args[1]
        assert call_args['modelId'] == 'us.amazon.nova-pro-v1:0'
        
        # Verify the request body contains the expected prompt
        request_body = json.loads(call_args['body'])
        assert 'Tesla will reach a market cap of $1 trillion by the end of 2025' in request_body['messages'][0]['content'][0]['text']
        
        # Verify the response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'results' in body
        
        # Verify the prediction data is formatted correctly
        prediction = body['results'][0]
        assert prediction['prediction_statement'] == 'Tesla will reach a market cap of $1 trillion by the end of 2025'
        assert prediction['verification_date'] == '2025-12-31'
        assert len(prediction['verification_method']['source']) == 3
        assert 'Yahoo Finance' in prediction['verification_method']['source']
        assert len(prediction['verification_method']['criteria']) == 2
        assert len(prediction['verification_method']['steps']) == 3
        assert prediction['initial_status'] == 'pending'

    def test_lambda_handler_invalid_json_response(self, sample_event, mock_bedrock_client):
        """Test handling of invalid JSON in the model response"""
        # Create a response with invalid JSON
        invalid_response = {
            'body': BytesIO(json.dumps({
                "output": {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "text": "```json\nThis is not valid JSON\n```"
                            }
                        ]
                    }
                }
            }).encode('utf-8'))
        }
        
        mock_bedrock_client.invoke_model.return_value = invalid_response
        
        response = lambda_handler(sample_event, {})
        
        assert response['statusCode'] == 500
        assert 'Invalid response format from model' in json.loads(response['body'])['error']

    def test_lambda_handler_unexpected_response_format(self, sample_event, mock_bedrock_client):
        """Test handling of unexpected response format from the model"""
        # Create a response with unexpected format
        unexpected_response = {
            'body': BytesIO(json.dumps({
                # Missing 'output' key
                "something_else": {}
            }).encode('utf-8'))
        }
        
        mock_bedrock_client.invoke_model.return_value = unexpected_response
        
        response = lambda_handler(sample_event, {})
        
        assert response['statusCode'] == 500
        assert 'Internal server error' in json.loads(response['body'])['error']

    def test_lambda_handler_bedrock_exception(self, sample_event, mock_bedrock_client):
        """Test handling of exceptions from the Bedrock client"""
        # Configure mock to raise an exception
        mock_bedrock_client.invoke_model.side_effect = Exception("Bedrock service error")
        
        response = lambda_handler(sample_event, {})
        
        assert response['statusCode'] == 500
        assert 'Internal server error' in json.loads(response['body'])['error']
        assert 'Bedrock service error' in json.loads(response['body'])['details']

    def test_lambda_handler_partial_json_response(self, sample_event, mock_bedrock_client):
        """Test handling of partial JSON in the model response (missing fields)"""
        # Create a response with partial JSON (missing fields)
        partial_response = {
            'body': BytesIO(json.dumps({
                "output": {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "text": """```json
{
  "prediction_statement": "Tesla will reach a market cap of $1 trillion by the end of 2025"
  // Missing other fields
}
```"""
                            }
                        ]
                    }
                }
            }).encode('utf-8'))
        }
        
        mock_bedrock_client.invoke_model.return_value = partial_response
        
        response = lambda_handler(sample_event, {})
        
        assert response['statusCode'] == 500
        assert 'Invalid response format from model' in json.loads(response['body'])['error']