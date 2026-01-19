"""
Pytest Fixtures for Integration Tests

Provides shared fixtures for all integration tests following Strands best practices.
"""

import pytest
import json
import sys
from pathlib import Path

# Add handlers directory to path so we can import prediction_graph
handlers_dir = Path(__file__).parent.parent.parent / "handlers" / "strands_make_call"
sys.path.insert(0, str(handlers_dir))


@pytest.fixture(scope="session")
def test_data_dir():
    """Path to test data directory containing JSON test cases"""
    return Path(__file__).parent / "test_cases"


@pytest.fixture
def backward_compat_cases(test_data_dir):
    """
    Load backward compatibility test cases.
    
    These test cases verify that the refactored 3-agent graph backend
    maintains full compatibility with the existing frontend.
    
    Task 17: Verify Backward Compatibility
    """
    with open(test_data_dir / "backward_compatibility.json") as f:
        return json.load(f)


@pytest.fixture
def parser_test_cases(test_data_dir):
    """
    Load parser agent test cases.
    
    Tests the Parser Agent's ability to:
    - Extract exact prediction text
    - Parse time references
    - Convert 12-hour to 24-hour format
    - Handle timezones correctly
    """
    with open(test_data_dir / "parser_agent.json") as f:
        return json.load(f)


@pytest.fixture
def categorizer_test_cases(test_data_dir):
    """
    Load categorizer agent test cases.
    
    Tests the Categorizer Agent's ability to:
    - Classify predictions into 5 verifiability categories
    - Provide reasoning for categorization
    - Handle edge cases
    """
    with open(test_data_dir / "categorizer_agent.json") as f:
        return json.load(f)


@pytest.fixture
def verification_builder_test_cases(test_data_dir):
    """
    Load verification builder agent test cases.
    
    Tests the Verification Builder Agent's ability to:
    - Generate verification methods with source, criteria, steps
    - Adapt to different verifiability categories
    - Provide actionable verification plans
    """
    with open(test_data_dir / "verification_builder.json") as f:
        return json.load(f)


@pytest.fixture
def test_datetime():
    """
    Standard test datetime for consistency across all tests.
    
    Using a fixed datetime ensures reproducible test results.
    """
    return {
        "utc": "2026-01-18 18:24:33 UTC",
        "local": "2026-01-18 13:24:33 EST",
        "timezone": "America/New_York"
    }


@pytest.fixture(scope="session", autouse=True)
def verify_aws_credentials():
    """
    Verify AWS credentials are configured before running tests.
    
    Integration tests require AWS credentials to invoke real agents
    via Bedrock API. This fixture runs once per test session and
    provides helpful error messages if credentials aren't configured.
    
    Credentials should be at: ~/.aws/credentials
    """
    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError
    
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"\n✅ AWS credentials verified: {identity['Arn']}")
    except NoCredentialsError:
        pytest.fail(
            "\n❌ AWS credentials not configured!\n"
            "Integration tests require AWS credentials to invoke real agents.\n"
            "Please configure credentials at: ~/.aws/credentials\n"
            "Or set AWS_PROFILE environment variable."
        )
    except ClientError as e:
        pytest.fail(
            f"\n❌ AWS credentials error: {str(e)}\n"
            "Please verify your AWS credentials are valid."
        )
    except Exception as e:
        pytest.fail(
            f"\n❌ Unexpected error verifying AWS credentials: {str(e)}"
        )


@pytest.fixture
def mock_callback_handler():
    """
    Simple callback handler for tests that don't need WebSocket streaming.
    
    For integration tests, we typically don't need to test WebSocket
    streaming - we just need to verify the graph execution and response.
    """
    def callback(**kwargs):
        """No-op callback handler"""
        pass
    
    return callback
