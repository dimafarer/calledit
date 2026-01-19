"""
Integration Tests for Parser Agent

Tests the Parser Agent's ability to:
- Extract exact prediction text (Property 2)
- Parse time references and convert formats (Property 3)
- Handle timezones correctly (Property 4)

Following Strands best practices:
- Real agent invocations with real LLM calls
- Structured test cases from JSON files
"""

import pytest
from prediction_graph import execute_prediction_graph


@pytest.mark.integration
class TestParserAgent:
    """
    Integration tests for Parser Agent.
    
    These tests invoke the full 3-agent graph but focus on validating
    the Parser Agent's outputs.
    """
    
    def test_exact_text_preservation(self, parser_test_cases, test_datetime):
        """
        Property 2: Parser preserves exact prediction text
        
        Validates: Requirements 2.1
        
        The parser should extract and preserve the exact prediction text
        without modification, paraphrasing, or interpretation.
        """
        for case in parser_test_cases:
            # Skip cases without expected_prediction
            if "expected_prediction" not in case:
                continue
            
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            # Verify prediction statement matches expected
            assert result["prediction_statement"] == case["expected_prediction"], \
                f"Test case {case['id']}: Expected '{case['expected_prediction']}' " \
                f"but got '{result['prediction_statement']}'"
    
    def test_time_format_conversion(self, parser_test_cases, test_datetime):
        """
        Property 3: Parser converts 12-hour to 24-hour format
        
        Validates: Requirements 2.3
        
        The parser should convert time references from 12-hour format
        (e.g., "3:00pm") to 24-hour format (e.g., "15:00").
        """
        for case in parser_test_cases:
            # Skip cases without contains_time
            if "contains_time" not in case:
                continue
            
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            # Verify verification_date contains expected time format
            assert case["contains_time"] in result["verification_date"], \
                f"Test case {case['id']}: Expected time '{case['contains_time']}' " \
                f"not found in verification_date '{result['verification_date']}'"
    
    def test_timezone_handling(self, parser_test_cases, test_datetime):
        """
        Property 4: Parser respects user timezone
        
        Validates: Requirements 2.4, 11.2
        
        The parser should handle timezone information correctly and
        parse dates relative to the user's timezone.
        """
        for case in parser_test_cases:
            # Skip cases without expected_timezone
            if "expected_timezone" not in case:
                continue
            
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            # Verify user_timezone is preserved in result
            assert result["user_timezone"] == case["expected_timezone"], \
                f"Test case {case['id']}: Expected timezone '{case['expected_timezone']}' " \
                f"but got '{result['user_timezone']}'"
    
    def test_date_reasoning_present(self, parser_test_cases, test_datetime):
        """
        Additional test: Verify date_reasoning is provided
        
        The parser should provide reasoning for how it parsed the date.
        """
        for case in parser_test_cases:
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            # Verify date_reasoning exists and is non-empty
            assert "date_reasoning" in result, \
                f"Test case {case['id']}: date_reasoning field missing"
            assert result["date_reasoning"], \
                f"Test case {case['id']}: date_reasoning is empty"
            assert len(result["date_reasoning"]) > 10, \
                f"Test case {case['id']}: date_reasoning is too short (likely fallback)"
    
    def test_verification_date_format(self, parser_test_cases, test_datetime):
        """
        Additional test: Verify verification_date has valid format
        
        The parser should return a verification_date in a valid datetime format.
        """
        for case in parser_test_cases:
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            # Verify verification_date exists and is non-empty
            assert "verification_date" in result, \
                f"Test case {case['id']}: verification_date field missing"
            assert result["verification_date"], \
                f"Test case {case['id']}: verification_date is empty"
            
            # Verify it contains date-like components (year, month, day)
            vd = result["verification_date"]
            assert any(char.isdigit() for char in vd), \
                f"Test case {case['id']}: verification_date contains no digits: '{vd}'"
