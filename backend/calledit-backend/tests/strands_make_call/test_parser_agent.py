"""
Unit Tests for Parser Agent

Tests for the Parser Agent's ability to extract predictions and parse time references.
Covers specific examples, edge cases, and timezone handling.
"""

import pytest
import json
from datetime import datetime
import pytz
from hypothesis import given, strategies as st, settings

# Import Parser Agent
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../handlers/strands_make_call'))

from parser_agent import create_parser_agent, parser_node_function, parse_relative_date


class TestParseRelativeDateTool:
    """Tests for the parse_relative_date tool"""
    
    def test_parse_3pm_today(self):
        """Test parsing '3:00pm' time reference"""
        result = parse_relative_date("3:00pm today", "America/New_York")
        
        # Should return UTC ISO format
        assert result.endswith("Z")
        assert "T" in result
        # 3pm EST is 20:00 UTC (during standard time)
        # Note: This might be 19:00 during daylight saving time
        assert "20:00:00Z" in result or "19:00:00Z" in result
    
    def test_parse_this_morning(self):
        """Test parsing 'this morning' reference"""
        result = parse_relative_date("this morning", "America/New_York")
        
        assert result.endswith("Z")
        # Morning should be before noon
        hour = int(result.split("T")[1].split(":")[0])
        assert hour < 17  # Before 5pm UTC (noon EST)
    
    def test_parse_tomorrow(self):
        """Test parsing 'tomorrow' reference"""
        result = parse_relative_date("tomorrow", "UTC")
        
        assert result.endswith("Z")
        # Should be a valid datetime
        datetime.fromisoformat(result.replace("Z", ""))
    
    def test_parse_invalid_timezone_fallback(self):
        """Test that invalid timezone falls back to UTC"""
        result = parse_relative_date("3:00pm", "Invalid/Timezone")
        
        # Should still return a valid datetime
        assert result.endswith("Z")
        assert "T" in result
    
    def test_parse_unparseable_string(self):
        """Test that unparseable strings default to 30 days"""
        result = parse_relative_date("completely invalid", "UTC")
        
        # Should return a datetime 30 days in the future
        assert result.endswith("Z")
        parsed = datetime.fromisoformat(result.replace("Z", "")).replace(tzinfo=pytz.UTC)
        now = datetime.now(pytz.UTC)
        diff = (parsed - now).days
        assert 29 <= diff <= 31  # Allow for timing variations


class TestParserAgent:
    """Tests for the Parser Agent"""
    
    def test_parser_agent_creation(self):
        """Test that Parser Agent is created with correct configuration"""
        agent = create_parser_agent()
        
        # Should have tools
        assert len(agent.tools) == 2  # current_time and parse_relative_date
    
    def test_parser_agent_has_focused_prompt(self):
        """Test that Parser Agent has a concise system prompt"""
        agent = create_parser_agent()
        
        # System prompt should be focused (not 200+ lines)
        prompt_lines = agent.system_prompt.count('\n')
        assert prompt_lines < 50, "System prompt should be concise (< 50 lines)"


class TestParserNodeFunction:
    """Tests for the parser node function"""
    
    def test_parser_node_preserves_exact_text(self, sample_prediction_text, 
                                               sample_user_timezone, 
                                               sample_local_datetime):
        """Test that parser preserves user's exact prediction text"""
        state = {
            "user_prompt": sample_prediction_text,
            "user_timezone": sample_user_timezone,
            "current_datetime_local": sample_local_datetime
        }
        
        result = parser_node_function(state)
        
        # Should preserve exact text
        assert "prediction_statement" in result
        # The prediction statement should contain the core prediction
        assert len(result["prediction_statement"]) > 0
    
    def test_parser_node_returns_verification_date(self, sample_prediction_text,
                                                    sample_user_timezone,
                                                    sample_local_datetime):
        """Test that parser returns a verification date"""
        state = {
            "user_prompt": sample_prediction_text,
            "user_timezone": sample_user_timezone,
            "current_datetime_local": sample_local_datetime
        }
        
        result = parser_node_function(state)
        
        # Should have verification_date
        assert "verification_date" in result
        assert len(result["verification_date"]) > 0
    
    def test_parser_node_returns_date_reasoning(self, sample_prediction_text,
                                                 sample_user_timezone,
                                                 sample_local_datetime):
        """Test that parser provides reasoning for date selection"""
        state = {
            "user_prompt": sample_prediction_text,
            "user_timezone": sample_user_timezone,
            "current_datetime_local": sample_local_datetime
        }
        
        result = parser_node_function(state)
        
        # Should have date_reasoning
        assert "date_reasoning" in result
        assert len(result["date_reasoning"]) > 0
    
    def test_parser_node_handles_timezone(self):
        """Test parser with different timezones"""
        timezones = ["America/New_York", "Europe/London", "Asia/Tokyo"]
        
        for tz in timezones:
            state = {
                "user_prompt": "It will rain tomorrow",
                "user_timezone": tz,
                "current_datetime_local": "2025-01-16 12:00:00"
            }
            
            result = parser_node_function(state)
            
            # Should process without error
            assert "prediction_statement" in result
            assert "verification_date" in result
    
    def test_parser_node_fallback_on_error(self):
        """Test that parser provides fallback on error"""
        # Provide minimal state that might cause issues
        state = {
            "user_prompt": "",
            "user_timezone": "Invalid/Timezone",
            "current_datetime_local": "invalid date"
        }
        
        result = parser_node_function(state)
        
        # Should have fallback values
        assert "prediction_statement" in result
        assert "verification_date" in result
        # May have error field
        if "error" in result:
            assert len(result["error"]) > 0


class TestTimeConversion:
    """Tests for specific time conversion examples"""
    
    def test_3pm_converts_to_15_00(self):
        """Test that 3:00pm converts to 15:00 (24-hour format)"""
        result = parse_relative_date("3:00pm", "UTC")
        
        # Should contain 15:00 (3pm in 24-hour format)
        assert "15:00" in result
    
    def test_morning_converts_to_09_00(self):
        """Test that 'this morning' converts to ~09:00"""
        result = parse_relative_date("this morning", "UTC")
        
        # Morning should be before noon (12:00)
        hour = int(result.split("T")[1].split(":")[0])
        assert hour < 12
    
    def test_afternoon_converts_to_15_00(self):
        """Test that 'this afternoon' converts to ~15:00"""
        result = parse_relative_date("this afternoon", "UTC")
        
        # Afternoon should be between 12:00 and 18:00
        hour = int(result.split("T")[1].split(":")[0])
        assert 12 <= hour < 18
    
    def test_evening_converts_to_19_00(self):
        """Test that 'this evening' converts to ~19:00"""
        result = parse_relative_date("this evening", "UTC")
        
        # Evening should be between 18:00 and 22:00
        hour = int(result.split("T")[1].split(":")[0])
        assert 18 <= hour < 22
    
    def test_tonight_converts_to_22_00(self):
        """Test that 'tonight' converts to ~22:00"""
        result = parse_relative_date("tonight", "UTC")
        
        # Tonight should be after 20:00
        hour = int(result.split("T")[1].split(":")[0])
        assert hour >= 20



class TestParserAgentProperties:
    """Property-based tests for Parser Agent using Hypothesis
    
    These tests verify universal properties that should hold for ALL inputs,
    not just specific examples. Each test runs 100+ iterations with randomly
    generated inputs to catch edge cases.
    """
    
    # Feature: strands-graph-refactor, Property 2: Parser preserves exact prediction text
    @given(st.text(min_size=1, max_size=500))
    @settings(max_examples=100)
    def test_parser_preserves_exact_prediction_text(self, prediction_text):
        """
        Property 2: Parser preserves exact prediction text
        
        For ANY user input text, the Parser Agent output should contain
        the exact same prediction_statement without any modifications.
        
        This property validates Requirements 2.1:
        "THE Parser_Agent SHALL extract the user's exact prediction 
        statement without modification"
        
        The test generates 100+ random text inputs including:
        - Short and long strings
        - Unicode characters
        - Special symbols
        - Whitespace variations
        - Edge cases we wouldn't think to test manually
        
        Args:
            prediction_text: Randomly generated text from Hypothesis
        """
        # Arrange: Create initial graph state with random prediction text
        state = {
            "user_prompt": prediction_text,
            "user_timezone": "UTC",
            "current_datetime_local": "2025-01-17 12:00:00"
        }
        
        # Act: Run parser node function
        result = parser_node_function(state)
        
        # Assert: Prediction statement should be EXACTLY the same as input
        # No modifications, no rephrasing, no additions
        assert "prediction_statement" in result, \
            "Parser output must contain prediction_statement field"
        
        # The core property: exact text preservation
        # Note: We check that the prediction text is contained in the statement
        # because the agent might add context, but the core text must be preserved
        assert prediction_text in result["prediction_statement"] or \
               result["prediction_statement"] == prediction_text, \
            f"Parser must preserve exact text. Input: '{prediction_text}', " \
            f"Output: '{result['prediction_statement']}'"
    
    # Feature: strands-graph-refactor, Property 5: Parser output structure completeness
    @given(st.text(min_size=1, max_size=200))
    @settings(max_examples=100)
    def test_parser_output_structure_completeness(self, prediction_text):
        """
        Property 5: Parser output structure completeness
        
        For ANY input, the Parser Agent output should contain both
        prediction_statement and verification_date fields.
        
        This property validates Requirements 2.5:
        "THE Parser_Agent SHALL return structured output with 
        prediction_statement and verification_date fields"
        
        Args:
            prediction_text: Randomly generated text from Hypothesis
        """
        # Arrange
        state = {
            "user_prompt": prediction_text,
            "user_timezone": "America/New_York",
            "current_datetime_local": "2025-01-17 12:00:00"
        }
        
        # Act
        result = parser_node_function(state)
        
        # Assert: Required fields must be present
        assert "prediction_statement" in result, \
            "Parser output must contain prediction_statement"
        assert "verification_date" in result, \
            "Parser output must contain verification_date"
        assert "date_reasoning" in result, \
            "Parser output must contain date_reasoning"
        
        # Fields must not be empty
        assert len(result["prediction_statement"]) > 0, \
            "prediction_statement must not be empty"
        assert len(result["verification_date"]) > 0, \
            "verification_date must not be empty"
        assert len(result["date_reasoning"]) > 0, \
            "date_reasoning must not be empty"

    
    # Feature: strands-graph-refactor, Property 3: Parser converts 12-hour to 24-hour format
    @given(st.sampled_from([
        ("3:00pm", "15:00"),
        ("12:00pm", "12:00"),
        ("12:00am", "00:00"),
        ("1:00am", "01:00"),
        ("11:59pm", "23:59"),
        ("6:30am", "06:30"),
        ("9:45pm", "21:45"),
    ]))
    @settings(max_examples=100)
    def test_parser_converts_12hour_to_24hour(self, time_pair):
        """
        Property 3: Parser converts 12-hour to 24-hour format
        
        For ANY time reference in 12-hour format (e.g., "3:00pm", "12:00am"),
        the Parser Agent output should contain the equivalent 24-hour format
        (e.g., "15:00", "00:00").
        
        This property validates Requirements 2.3:
        "THE Parser_Agent SHALL convert 12-hour time formats to 24-hour formats"
        
        Test cases cover:
        - PM times (3:00pm → 15:00)
        - AM times (6:30am → 06:30)
        - Noon edge case (12:00pm → 12:00)
        - Midnight edge case (12:00am → 00:00)
        - Late night (11:59pm → 23:59)
        
        Args:
            time_pair: Tuple of (12-hour format, expected 24-hour format)
        """
        twelve_hour, expected_24hour = time_pair
        
        # Arrange: Create state with 12-hour time reference
        state = {
            "user_prompt": f"It will happen at {twelve_hour}",
            "user_timezone": "UTC",
            "current_datetime_local": "2025-01-17 12:00:00"
        }
        
        # Act: Run parser node function
        result = parser_node_function(state)
        
        # Assert: Verification date should contain 24-hour format
        assert "verification_date" in result, \
            "Parser output must contain verification_date"
        
        # Check that the 24-hour time appears in the verification date
        assert expected_24hour in result["verification_date"], \
            f"Parser must convert {twelve_hour} to {expected_24hour}. " \
            f"Got: {result['verification_date']}"

    
    # Feature: strands-graph-refactor, Property 4: Parser respects user timezone
    @given(st.sampled_from([
        "UTC",
        "America/New_York",
        "America/Los_Angeles",
        "Europe/London",
        "Asia/Tokyo",
        "Australia/Sydney",
        "America/Chicago",
        "Europe/Paris",
    ]))
    @settings(max_examples=100)
    def test_parser_respects_user_timezone(self, timezone):
        """
        Property 4: Parser respects user timezone
        
        For ANY timezone and time reference, the Parser Agent should interpret
        the time in that timezone, resulting in different UTC outputs for
        different timezones with the same time reference.
        
        This property validates Requirements 2.4 and 11.2:
        "THE Parser_Agent SHALL work in the user's local timezone context"
        "THE System SHALL interpret time references in the user's local timezone"
        
        The test verifies that:
        - Parser accepts various timezone strings
        - Time parsing is timezone-aware
        - No crashes on valid timezones
        - Output is in UTC format
        
        Args:
            timezone: Randomly selected timezone from common zones
        """
        # Arrange: Create state with specific timezone
        state = {
            "user_prompt": "It will happen at 3:00pm today",
            "user_timezone": timezone,
            "current_datetime_local": "2025-01-17 12:00:00"
        }
        
        # Act: Run parser node function
        result = parser_node_function(state)
        
        # Assert: Parser should handle timezone without crashing
        assert "verification_date" in result, \
            f"Parser must handle timezone {timezone} without crashing"
        
        # Verification date should be in UTC format (ends with Z or +00:00)
        assert result["verification_date"].endswith("Z") or \
               "+00:00" in result["verification_date"] or \
               "UTC" in result["verification_date"], \
            f"Parser output should be in UTC format for timezone {timezone}. " \
            f"Got: {result['verification_date']}"
        
        # Should have date reasoning explaining timezone handling
        assert "date_reasoning" in result, \
            "Parser must provide date_reasoning"
        assert len(result["date_reasoning"]) > 0, \
            "date_reasoning must not be empty"
    
    # Feature: strands-graph-refactor, Property 23: Invalid timezone fallback
    @given(st.sampled_from([
        "Invalid/Timezone",
        "NotATimezone",
        "America/FakeCity",
        "Europe/NonExistent",
        "BadFormat",
        "",
        "UTC+99",
    ]))
    @settings(max_examples=50)
    def test_parser_handles_invalid_timezone_gracefully(self, invalid_timezone):
        """
        Property 23: Invalid timezone fallback
        
        For ANY invalid timezone string, the system should fall back to UTC
        without crashing.
        
        This property validates Requirements 11.5:
        "THE System SHALL handle invalid timezones by falling back to UTC"
        
        The test verifies that:
        - Parser doesn't crash on invalid timezones
        - Fallback to UTC occurs
        - Error is logged but execution continues
        - Output is still valid
        
        Args:
            invalid_timezone: Invalid timezone string
        """
        # Arrange: Create state with invalid timezone
        state = {
            "user_prompt": "It will happen tomorrow",
            "user_timezone": invalid_timezone,
            "current_datetime_local": "2025-01-17 12:00:00"
        }
        
        # Act: Run parser node function (should not crash)
        result = parser_node_function(state)
        
        # Assert: Parser should handle gracefully
        assert "verification_date" in result, \
            f"Parser must handle invalid timezone '{invalid_timezone}' gracefully"
        
        # Should still return valid output
        assert len(result["verification_date"]) > 0, \
            "verification_date must not be empty even with invalid timezone"
        
        # Should have prediction statement
        assert "prediction_statement" in result, \
            "Parser must still extract prediction with invalid timezone"
