"""
Pytest Configuration and Fixtures for Strands Graph Tests

This module provides shared fixtures and configuration for testing
the prediction verification graph and its components.

Following Strands best practices:
- Reusable test fixtures
- Mock configurations
- Test data generators
"""

import pytest
from datetime import datetime, timezone
import pytz


@pytest.fixture
def sample_user_timezone():
    """Fixture providing a sample user timezone"""
    return "America/New_York"


@pytest.fixture
def sample_utc_datetime():
    """Fixture providing a sample UTC datetime"""
    return "2025-01-16 12:00:00 UTC"


@pytest.fixture
def sample_local_datetime():
    """Fixture providing a sample local datetime"""
    return "2025-01-16 07:00:00 EST"


@pytest.fixture
def sample_prediction_text():
    """Fixture providing sample prediction text"""
    return "It will rain before 3:00pm today"


@pytest.fixture
def sample_graph_state(sample_prediction_text, sample_user_timezone, 
                       sample_utc_datetime, sample_local_datetime):
    """
    Fixture providing a complete sample graph state.
    
    This represents the state after all agents have processed the prediction.
    """
    return {
        "user_prompt": sample_prediction_text,
        "user_timezone": sample_user_timezone,
        "current_datetime_utc": sample_utc_datetime,
        "current_datetime_local": sample_local_datetime,
        "prediction_statement": sample_prediction_text,
        "verification_date": "2025-01-16T15:00:00Z",
        "date_reasoning": "User specified 3:00pm (15:00 in 24-hour format) today",
        "verifiable_category": "api_tool_verifiable",
        "category_reasoning": "Requires weather API to verify rain prediction",
        "verification_method": {
            "source": ["Weather API", "Local weather station"],
            "criteria": ["Rain detected before 15:00 local time"],
            "steps": ["Query weather API at 15:00", "Check for rain events"]
        },
        "reviewable_sections": [],
        "initial_status": "pending"
    }


@pytest.fixture
def valid_categories():
    """Fixture providing the set of valid verifiability categories"""
    return {
        "agent_verifiable",
        "current_tool_verifiable",
        "strands_tool_verifiable",
        "api_tool_verifiable",
        "human_verifiable_only"
    }


@pytest.fixture
def mock_websocket_client():
    """
    Fixture providing a mock WebSocket client for testing.
    
    This mock tracks messages sent via post_to_connection for verification.
    """
    class MockWebSocketClient:
        def __init__(self):
            self.messages = []
        
        def post_to_connection(self, ConnectionId, Data):
            """Mock post_to_connection method"""
            self.messages.append({
                "connection_id": ConnectionId,
                "data": Data
            })
            return {"ResponseMetadata": {"HTTPStatusCode": 200}}
        
        def get_messages(self):
            """Get all messages sent"""
            return self.messages
        
        def clear_messages(self):
            """Clear message history"""
            self.messages = []
    
    return MockWebSocketClient()


@pytest.fixture
def sample_lambda_event(sample_prediction_text, sample_user_timezone):
    """
    Fixture providing a sample Lambda event for WebSocket message.
    
    This represents the event structure from API Gateway WebSocket.
    """
    return {
        "requestContext": {
            "connectionId": "test-connection-123",
            "domainName": "test.execute-api.us-east-1.amazonaws.com",
            "stage": "prod"
        },
        "body": f'{{"prompt": "{sample_prediction_text}", "timezone": "{sample_user_timezone}", "action": "makecall"}}'
    }


# Hypothesis strategies for property-based testing
try:
    from hypothesis import strategies as st
    
    # Strategy for generating prediction text
    prediction_text_strategy = st.text(min_size=1, max_size=200)
    
    # Strategy for generating timezone strings
    timezone_strategy = st.sampled_from([
        "UTC",
        "America/New_York",
        "America/Los_Angeles",
        "Europe/London",
        "Asia/Tokyo",
        "Australia/Sydney"
    ])
    
    # Strategy for generating time references
    time_reference_strategy = st.sampled_from([
        "3:00pm",
        "this morning",
        "this afternoon",
        "this evening",
        "tonight",
        "tomorrow",
        "next week"
    ])
    
except ImportError:
    # Hypothesis not installed yet
    pass
