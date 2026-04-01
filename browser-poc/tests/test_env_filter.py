"""Tests for filter_aws_env_vars — Property 1 + unit tests.

Feature: browser-tool-fix, Property 1: AWS environment variable filtering masks secrets
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hypothesis import given, strategies as st
from main import filter_aws_env_vars, SENSITIVE_PATTERNS


# ---------------------------------------------------------------------------
# Property 1: AWS environment variable filtering masks secrets
# For any dict of env vars, only AWS_-prefixed keys are returned,
# and sensitive values are masked.
# ---------------------------------------------------------------------------

# Strategy: generate dicts with a mix of AWS_ and non-AWS_ keys
aws_key = st.text(min_size=1, max_size=30).map(lambda s: f"AWS_{s}")
non_aws_key = st.text(min_size=1, max_size=30).filter(lambda s: not s.startswith("AWS_"))
env_value = st.text(min_size=0, max_size=100)

env_dict_strategy = st.dictionaries(
    keys=st.one_of(aws_key, non_aws_key),
    values=env_value,
    min_size=0,
    max_size=20,
)


# Feature: browser-tool-fix, Property 1: AWS environment variable filtering masks secrets
@given(env_dict=env_dict_strategy)
def test_only_aws_prefixed_keys_returned(env_dict):
    """All returned keys start with AWS_."""
    result = filter_aws_env_vars(env_dict)
    for key in result:
        assert key.startswith("AWS_"), f"Non-AWS key in output: {key}"


# Feature: browser-tool-fix, Property 1: AWS environment variable filtering masks secrets
@given(env_dict=env_dict_strategy)
def test_sensitive_values_masked(env_dict):
    """Keys containing sensitive patterns have masked values."""
    result = filter_aws_env_vars(env_dict)
    for key, value in result.items():
        upper_key = key.upper()
        if any(pat in upper_key for pat in SENSITIVE_PATTERNS):
            assert value == "***MASKED***", f"{key} should be masked but got: {value}"


# Feature: browser-tool-fix, Property 1: AWS environment variable filtering masks secrets
@given(env_dict=env_dict_strategy)
def test_non_sensitive_values_preserved(env_dict):
    """AWS_ keys without sensitive patterns keep their original values."""
    result = filter_aws_env_vars(env_dict)
    for key, value in result.items():
        upper_key = key.upper()
        if not any(pat in upper_key for pat in SENSITIVE_PATTERNS):
            assert value == env_dict[key], f"{key} value changed: {env_dict[key]} -> {value}"


# Feature: browser-tool-fix, Property 1: AWS environment variable filtering masks secrets
@given(env_dict=env_dict_strategy)
def test_no_non_aws_keys_leak(env_dict):
    """No non-AWS_ keys appear in the output."""
    result = filter_aws_env_vars(env_dict)
    non_aws_in_input = {k for k in env_dict if not k.startswith("AWS_")}
    for key in non_aws_in_input:
        assert key not in result, f"Non-AWS key leaked: {key}"


# ---------------------------------------------------------------------------
# Unit tests (specific examples)
# ---------------------------------------------------------------------------

def test_empty_dict():
    assert filter_aws_env_vars({}) == {}


def test_no_aws_keys():
    assert filter_aws_env_vars({"HOME": "/home/user", "PATH": "/usr/bin"}) == {}


def test_aws_region_visible():
    result = filter_aws_env_vars({"AWS_REGION": "us-west-2"})
    assert result == {"AWS_REGION": "us-west-2"}


def test_aws_default_region_visible():
    result = filter_aws_env_vars({"AWS_DEFAULT_REGION": "us-east-1"})
    assert result == {"AWS_DEFAULT_REGION": "us-east-1"}


def test_secret_access_key_masked():
    result = filter_aws_env_vars({"AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI"})
    assert result == {"AWS_SECRET_ACCESS_KEY": "***MASKED***"}


def test_session_token_masked():
    result = filter_aws_env_vars({"AWS_SESSION_TOKEN": "FwoGZXIvYXdzE..."})
    assert result == {"AWS_SESSION_TOKEN": "***MASKED***"}


def test_access_key_id_masked():
    """AWS_ACCESS_KEY_ID contains KEY, so it should be masked."""
    result = filter_aws_env_vars({"AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7"})
    assert result == {"AWS_ACCESS_KEY_ID": "***MASKED***"}


def test_mixed_keys():
    env = {
        "AWS_REGION": "us-west-2",
        "AWS_SECRET_ACCESS_KEY": "secret123",
        "HOME": "/home/user",
        "AWS_SESSION_TOKEN": "token456",
    }
    result = filter_aws_env_vars(env)
    assert result == {
        "AWS_REGION": "us-west-2",
        "AWS_SECRET_ACCESS_KEY": "***MASKED***",
        "AWS_SESSION_TOKEN": "***MASKED***",
    }
