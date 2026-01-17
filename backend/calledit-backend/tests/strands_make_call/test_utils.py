"""
Unit Tests for Utility Functions

Tests for timezone handling, datetime conversion, and helper functions
used throughout the prediction verification system.
"""

import pytest
from datetime import datetime
import pytz

# Import utilities
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../handlers/strands_make_call'))

from utils import (
    get_current_datetime_in_timezones,
    convert_local_to_utc,
    ensure_list,
    validate_verifiable_category
)


class TestTimezoneHandling:
    """Tests for timezone conversion functions"""
    
    def test_get_current_datetime_valid_timezone(self):
        """Test getting current datetime with valid timezone"""
        date_utc, datetime_utc, date_local, datetime_local = get_current_datetime_in_timezones("America/New_York")
        
        # Should return 4 strings
        assert isinstance(date_utc, str)
        assert isinstance(datetime_utc, str)
        assert isinstance(date_local, str)
        assert isinstance(datetime_local, str)
        
        # UTC should contain "UTC"
        assert "UTC" in datetime_utc
        
        # Local should contain timezone abbreviation (EST or EDT)
        assert any(tz in datetime_local for tz in ["EST", "EDT"])
    
    def test_get_current_datetime_invalid_timezone_fallback(self):
        """Test that invalid timezone falls back to UTC"""
        date_utc, datetime_utc, date_local, datetime_local = get_current_datetime_in_timezones("Invalid/Timezone")
        
        # Should fall back to UTC for local time
        assert date_utc == date_local
        assert datetime_utc == datetime_local
    
    def test_convert_local_to_utc_simple_format(self):
        """Test converting local time to UTC with simple format"""
        result = convert_local_to_utc(
            "2025-01-16 15:00:00",
            "America/New_York"
        )
        
        # Should return UTC ISO format
        assert result is not None
        assert result.endswith("Z")
        assert "T" in result
        
        # 15:00 EST should be 20:00 UTC (5 hour difference)
        assert "20:00:00Z" in result
    
    def test_convert_local_to_utc_iso_format(self):
        """Test converting local time to UTC with ISO format"""
        result = convert_local_to_utc(
            "2025-01-16T15:00:00",
            "America/New_York"
        )
        
        assert result is not None
        assert result.endswith("Z")
        assert "20:00:00Z" in result
    
    def test_convert_local_to_utc_invalid_input(self):
        """Test that invalid input returns None"""
        result = convert_local_to_utc(
            "invalid datetime",
            "America/New_York"
        )
        
        assert result is None


class TestEnsureList:
    """Tests for ensure_list helper function"""
    
    def test_ensure_list_with_string(self):
        """Test converting string to list"""
        result = ensure_list("single value")
        assert result == ["single value"]
    
    def test_ensure_list_with_list(self):
        """Test that list is preserved"""
        result = ensure_list(["value1", "value2"])
        assert result == ["value1", "value2"]
    
    def test_ensure_list_with_none(self):
        """Test that None returns empty list"""
        result = ensure_list(None)
        assert result == []
    
    def test_ensure_list_with_number(self):
        """Test converting number to list"""
        result = ensure_list(42)
        assert result == ["42"]


class TestValidateVerifiableCategory:
    """Tests for category validation"""
    
    def test_validate_valid_categories(self, valid_categories):
        """Test that all valid categories pass validation"""
        for category in valid_categories:
            result = validate_verifiable_category(category)
            assert result == category
    
    def test_validate_invalid_category_fallback(self):
        """Test that invalid category falls back to human_verifiable_only"""
        result = validate_verifiable_category("invalid_category")
        assert result == "human_verifiable_only"
    
    def test_validate_empty_category_fallback(self):
        """Test that empty category falls back to human_verifiable_only"""
        result = validate_verifiable_category("")
        assert result == "human_verifiable_only"
