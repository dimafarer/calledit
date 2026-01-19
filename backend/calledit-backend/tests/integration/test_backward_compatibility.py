"""
Integration Tests for Backward Compatibility (Task 17)

Tests that verify the refactored 3-agent graph backend maintains
full compatibility with the existing frontend.

Following Strands best practices:
- Real agent invocations with real LLM calls
- Structured test cases from JSON files
- End-to-end validation

Properties tested:
- Property 27: Input format compatibility
- Property 28: Output format compatibility
- Property 29: Action type support
- Property 30: Event type consistency
"""

import pytest
from prediction_graph import execute_prediction_graph


@pytest.mark.integration
@pytest.mark.backward_compat
class TestBackwardCompatibility:
    """
    Integration tests for backward compatibility.
    
    These tests invoke REAL agents with REAL LLM calls to verify
    that the refactored backend maintains compatibility with the frontend.
    """
    
    def test_input_format_compatibility(self, backward_compat_cases, test_datetime):
        """
        Property 27: Input format compatibility
        
        Validates: Requirements 13.1
        
        Test that backend accepts all valid frontend message formats:
        - prompt (required)
        - timezone (optional, defaults to UTC)
        - action (optional, defaults to makecall)
        """
        for case in backward_compat_cases:
            # Invoke REAL agents with REAL LLM calls
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            # Verify backend accepted the input and returned a result
            assert result is not None, f"Test case {case['id']}: No result returned"
            assert isinstance(result, dict), f"Test case {case['id']}: Result is not a dictionary"
            
            # Verify no errors in processing
            if "error" in result:
                # Error field can exist but should be None or empty for successful processing
                assert result["error"] is None or result["error"] == "", \
                    f"Test case {case['id']}: Processing error: {result.get('error')}"
    
    def test_output_format_compatibility(self, backward_compat_cases, test_datetime):
        """
        Property 28: Output format compatibility
        
        Validates: Requirements 13.2, 13.5
        
        Test that backend returns all expected fields with correct data types:
        - prediction_statement (string)
        - verification_date (string)
        - verifiable_category (string)
        - category_reasoning (string)
        - verification_method (object with source, criteria, steps arrays)
        - date_reasoning (string)
        """
        required_fields = [
            "prediction_statement",
            "verification_date",
            "verifiable_category",
            "category_reasoning",
            "verification_method",
            "date_reasoning"
        ]
        
        for case in backward_compat_cases:
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            # Verify all required fields are present
            for field in required_fields:
                assert field in result, \
                    f"Test case {case['id']}: Missing required field '{field}'"
            
            # Verify field data types
            assert isinstance(result["prediction_statement"], str), \
                f"Test case {case['id']}: prediction_statement is not a string"
            assert isinstance(result["verification_date"], str), \
                f"Test case {case['id']}: verification_date is not a string"
            assert isinstance(result["verifiable_category"], str), \
                f"Test case {case['id']}: verifiable_category is not a string"
            assert isinstance(result["category_reasoning"], str), \
                f"Test case {case['id']}: category_reasoning is not a string"
            assert isinstance(result["date_reasoning"], str), \
                f"Test case {case['id']}: date_reasoning is not a string"
            
            # Verify verification_method structure
            vm = result["verification_method"]
            assert isinstance(vm, dict), \
                f"Test case {case['id']}: verification_method is not a dictionary"
            assert "source" in vm, \
                f"Test case {case['id']}: verification_method missing 'source'"
            assert "criteria" in vm, \
                f"Test case {case['id']}: verification_method missing 'criteria'"
            assert "steps" in vm, \
                f"Test case {case['id']}: verification_method missing 'steps'"
            assert isinstance(vm["source"], list), \
                f"Test case {case['id']}: verification_method.source is not a list"
            assert isinstance(vm["criteria"], list), \
                f"Test case {case['id']}: verification_method.criteria is not a list"
            assert isinstance(vm["steps"], list), \
                f"Test case {case['id']}: verification_method.steps is not a list"
    
    def test_action_type_support(self, backward_compat_cases, test_datetime):
        """
        Property 29: Action type support
        
        Validates: Requirements 13.3
        
        Test that backend supports the 'makecall' action (current production feature).
        
        Note: Future actions (improve_section, improvement_answers) will be
        tested in Task 15 when VPSS feedback loop is implemented.
        """
        for case in backward_compat_cases:
            # The execute_prediction_graph function implements the 'makecall' action
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            # Verify action was processed successfully
            assert result is not None, \
                f"Test case {case['id']}: makecall action returned no result"
            assert "prediction_statement" in result, \
                f"Test case {case['id']}: makecall action did not process prediction"
    
    def test_expected_categories(self, backward_compat_cases, test_datetime):
        """
        Additional test: Verify expected categories match
        
        This test validates that the categorizer agent produces
        the expected verifiability categories for known prediction types.
        """
        for case in backward_compat_cases:
            # Skip cases without expected_category
            if "expected_category" not in case:
                continue
            
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            # Verify category matches expectation
            assert result["verifiable_category"] == case["expected_category"], \
                f"Test case {case['id']}: Expected category '{case['expected_category']}' " \
                f"but got '{result['verifiable_category']}'"
    
    def test_verification_method_structure(self, backward_compat_cases, test_datetime):
        """
        Additional test: Verify verification_method has non-empty arrays
        
        This test validates that the verification builder agent produces
        meaningful verification methods with actual content.
        """
        for case in backward_compat_cases:
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            vm = result["verification_method"]
            
            # Verify arrays are not empty
            assert len(vm["source"]) > 0, \
                f"Test case {case['id']}: verification_method.source is empty"
            assert len(vm["criteria"]) > 0, \
                f"Test case {case['id']}: verification_method.criteria is empty"
            assert len(vm["steps"]) > 0, \
                f"Test case {case['id']}: verification_method.steps is empty"
            
            # Verify array elements are strings
            assert all(isinstance(s, str) for s in vm["source"]), \
                f"Test case {case['id']}: verification_method.source contains non-strings"
            assert all(isinstance(c, str) for c in vm["criteria"]), \
                f"Test case {case['id']}: verification_method.criteria contains non-strings"
            assert all(isinstance(s, str) for s in vm["steps"]), \
                f"Test case {case['id']}: verification_method.steps contains non-strings"
