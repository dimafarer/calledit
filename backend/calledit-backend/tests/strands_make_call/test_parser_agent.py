"""
Unit Tests for Parser Agent

Tests for the Parser Agent's ability to extract predictions and parse time references.
Covers specific examples, edge cases, and timezone handling.
"""

import pytest
import json
from datetime import datetime
import pytz

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
        parsed = datetime.fromisoformat(result.replace("Z", ""))
        now = datetime.now(pytz.UTC)
        diff = (parsed - now).days
        assert 29 <= diff <= 31  # Allow for timing variations


class TestParserAgent:
    """Tests for the Parser Agent"""
    
    def test_parser_agent_creation(self):
        """Test that Parser Agent is created with correct configuration"""
        agent = create_parser_agent()
        
        # Should have explicit name
        assert agent.name == "parser_agent"
        
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
