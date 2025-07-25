import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime
import pytz
from handlers.strands_make_call.strands_make_call_stream import (
    lambda_handler,
    parse_relative_date,
    ensure_list
)


class TestStrandsMakeCallStream:
    """Test suite for the strands_make_call_stream Lambda function"""

    @pytest.fixture
    def mock_websocket_event(self):
        """Fixture providing a sample WebSocket event"""
        return {
            'requestContext': {
                'connectionId': 'test-connection-id',
                'domainName': 'test-domain.com',
                'stage': 'prod'
            },
            'body': json.dumps({
                'prompt': 'Bitcoin will hit $100k tomorrow',
                'timezone': 'America/New_York'
            })
        }

    @pytest.fixture
    def mock_api_gateway_client(self):
        """Fixture to mock API Gateway Management API client"""
        with patch('boto3.client') as mock_client:
            mock_api_gateway = MagicMock()
            mock_client.return_value = mock_api_gateway
            yield mock_api_gateway

    @pytest.fixture
    def mock_strands_agent(self):
        """Fixture to mock Strands Agent"""
        with patch('handlers.strands_make_call.strands_make_call_stream.Agent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent
            
            # Mock agent response with verifiability categorization
            mock_response = {
                "prediction_statement": "Bitcoin will reach $100,000 on 2025-01-28",
                "verification_date": "2025-01-28 23:59:59",
                "verifiable_category": "api_tool_verifiable",
                "category_reasoning": "Requires external cryptocurrency price APIs",
                "verification_method": {
                    "source": ["CoinGecko API", "CoinMarketCap"],
                    "criteria": ["BTC/USD price exceeds $100,000"],
                    "steps": ["Check BTC price on 2025-01-28"]
                },
                "initial_status": "pending",
                "date_reasoning": "Set to end of day for full day verification"
            }
            
            mock_agent.return_value = json.dumps(mock_response)
            yield mock_agent

    def test_parse_relative_date_with_valid_input(self):
        """Test parsing relative dates with valid input"""
        result = parse_relative_date("tomorrow", "America/New_York")
        
        # Should return a valid ISO format date
        assert result.endswith('Z')
        assert 'T' in result
        
        # Should be parseable as datetime
        parsed = datetime.fromisoformat(result.replace('Z', '+00:00'))
        assert isinstance(parsed, datetime)

    def test_ensure_list_with_string(self):
        """Test ensure_list with string input"""
        result = ensure_list("test string")
        assert result == ["test string"]

    def test_ensure_list_with_list(self):
        """Test ensure_list with list input"""
        input_list = ["item1", "item2", {"key": "value"}]
        result = ensure_list(input_list)
        
        assert len(result) == 3
        assert result[0] == "item1"
        assert result[1] == "item2"
        assert '"key": "value"' in result[2]  # Dict should be JSON stringified

    def test_lambda_handler_missing_connection_info(self):
        """Test handler with missing WebSocket connection information"""
        event = {'requestContext': {}}
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 400
        assert 'Missing WebSocket connection information' in json.loads(response['body'])['error']

    def test_lambda_handler_missing_prompt(self, mock_websocket_event):
        """Test handler with missing prompt"""
        mock_websocket_event['body'] = json.dumps({'timezone': 'UTC'})
        
        response = lambda_handler(mock_websocket_event, {})
        
        assert response['statusCode'] == 400
        assert 'No prompt provided' in json.loads(response['body'])['error']

    @patch('handlers.strands_make_call.strands_make_call_stream.current_time')
    def test_lambda_handler_successful_processing(
        self, 
        mock_current_time,
        mock_websocket_event, 
        mock_api_gateway_client, 
        mock_strands_agent
    ):
        """Test successful prediction processing with verifiability categorization"""
        
        # Mock datetime for consistent testing
        with patch('handlers.strands_make_call.strands_make_call_stream.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.strftime.return_value = "2025-01-27 22:00:00 EST"
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat
            mock_datetime.strptime = datetime.strptime
            
            response = lambda_handler(mock_websocket_event, {})
            
            # Verify successful response
            assert response['statusCode'] == 200
            assert 'Streaming completed' in json.loads(response['body'])['status']
            
            # Verify API Gateway calls were made
            assert mock_api_gateway_client.post_to_connection.call_count >= 2

    def test_lambda_handler_verifiability_category_validation(
        self, 
        mock_websocket_event, 
        mock_api_gateway_client
    ):
        """Test verifiability category validation with invalid category"""
        
        with patch('handlers.strands_make_call.strands_make_call_stream.Agent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent
            
            # Mock response with invalid category
            invalid_response = {
                "prediction_statement": "Test prediction",
                "verification_date": "2025-01-28 23:59:59",
                "verifiable_category": "invalid_category",  # Invalid category
                "verification_method": {"source": [], "criteria": [], "steps": []},
                "initial_status": "pending"
            }
            
            mock_agent.return_value = json.dumps(invalid_response)
            
            with patch('handlers.strands_make_call.strands_make_call_stream.datetime') as mock_datetime:
                mock_now = MagicMock()
                mock_now.strftime.return_value = "2025-01-27 22:00:00 EST"
                mock_datetime.now.return_value = mock_now
                mock_datetime.fromisoformat = datetime.fromisoformat
                mock_datetime.strptime = datetime.strptime
                
                response = lambda_handler(mock_websocket_event, {})
                
                # Should still succeed but fallback to human_verifiable_only
                assert response['statusCode'] == 200

    def test_lambda_handler_all_valid_categories(
        self, 
        mock_websocket_event, 
        mock_api_gateway_client
    ):
        """Test all valid verifiability categories are accepted"""
        
        valid_categories = [
            "agent_verifiable",
            "current_tool_verifiable",
            "strands_tool_verifiable", 
            "api_tool_verifiable",
            "human_verifiable_only"
        ]
        
        for category in valid_categories:
            with patch('handlers.strands_make_call.strands_make_call_stream.Agent') as mock_agent_class:
                mock_agent = MagicMock()
                mock_agent_class.return_value = mock_agent
                
                # Mock response with current category
                response_data = {
                    "prediction_statement": f"Test prediction for {category}",
                    "verification_date": "2025-01-28 23:59:59",
                    "verifiable_category": category,
                    "category_reasoning": f"Test reasoning for {category}",
                    "verification_method": {"source": [], "criteria": [], "steps": []},
                    "initial_status": "pending"
                }
                
                mock_agent.return_value = json.dumps(response_data)
                
                with patch('handlers.strands_make_call.strands_make_call_stream.datetime') as mock_datetime:
                    mock_now = MagicMock()
                    mock_now.strftime.return_value = "2025-01-27 22:00:00 EST"
                    mock_datetime.now.return_value = mock_now
                    mock_datetime.fromisoformat = datetime.fromisoformat
                    mock_datetime.strptime = datetime.strptime
                    
                    response = lambda_handler(mock_websocket_event, {})
                    
                    assert response['statusCode'] == 200