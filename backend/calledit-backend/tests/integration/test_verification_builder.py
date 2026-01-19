"""
Integration Tests for Verification Builder Agent

Tests the Verification Builder Agent's ability to:
- Generate complete verification methods (Property 9)
- Adapt to different verifiability categories
- Provide actionable verification plans

Following Strands best practices:
- Real agent invocations with real LLM calls
- Structured test cases from JSON files
"""

import pytest
from prediction_graph import execute_prediction_graph


@pytest.mark.integration
class TestVerificationBuilderAgent:
    """
    Integration tests for Verification Builder Agent.
    
    These tests invoke the full 3-agent graph but focus on validating
    the Verification Builder Agent's outputs.
    """
    
    def test_verification_method_structure(self, verification_builder_test_cases, test_datetime):
        """
        Property 9: Verification Builder output structure completeness
        
        Validates: Requirements 4.1, 4.2, 4.3, 4.4
        
        The verification builder should generate a complete verification_method
        with all required fields:
        - source (list of strings)
        - criteria (list of strings)
        - steps (list of strings)
        """
        for case in verification_builder_test_cases:
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            vm = result["verification_method"]
            
            # Verify all required fields are present
            assert "source" in vm, \
                f"Test case {case['id']}: verification_method missing 'source'"
            assert "criteria" in vm, \
                f"Test case {case['id']}: verification_method missing 'criteria'"
            assert "steps" in vm, \
                f"Test case {case['id']}: verification_method missing 'steps'"
            
            # Verify all fields are lists
            assert isinstance(vm["source"], list), \
                f"Test case {case['id']}: verification_method.source is not a list"
            assert isinstance(vm["criteria"], list), \
                f"Test case {case['id']}: verification_method.criteria is not a list"
            assert isinstance(vm["steps"], list), \
                f"Test case {case['id']}: verification_method.steps is not a list"
            
            # Verify lists are not empty
            assert len(vm["source"]) > 0, \
                f"Test case {case['id']}: verification_method.source is empty"
            assert len(vm["criteria"]) > 0, \
                f"Test case {case['id']}: verification_method.criteria is empty"
            assert len(vm["steps"]) > 0, \
                f"Test case {case['id']}: verification_method.steps is empty"
            
            # Verify list elements are strings
            assert all(isinstance(s, str) for s in vm["source"]), \
                f"Test case {case['id']}: verification_method.source contains non-strings"
            assert all(isinstance(c, str) for c in vm["criteria"]), \
                f"Test case {case['id']}: verification_method.criteria contains non-strings"
            assert all(isinstance(s, str) for s in vm["steps"]), \
                f"Test case {case['id']}: verification_method.steps contains non-strings"
    
    def test_verification_method_adapts_to_category(self, verification_builder_test_cases, test_datetime):
        """
        Additional test: Verify verification method adapts to category
        
        The verification builder should generate different verification
        methods based on the verifiability category.
        """
        for case in verification_builder_test_cases:
            # Skip cases without expected_source_contains
            if "expected_source_contains" not in case:
                continue
            
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            vm = result["verification_method"]
            source_text = " ".join(vm["source"]).lower()
            
            # Verify source mentions expected keywords
            assert case["expected_source_contains"].lower() in source_text, \
                f"Test case {case['id']}: Expected source to contain '{case['expected_source_contains']}' " \
                f"but got: {vm['source']}"
    
    def test_verification_method_has_sufficient_detail(self, verification_builder_test_cases, test_datetime):
        """
        Additional test: Verify verification method has sufficient detail
        
        The verification builder should provide enough detail in each field
        to be actionable.
        """
        for case in verification_builder_test_cases:
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            vm = result["verification_method"]
            
            # Verify each source item has reasonable length
            for source in vm["source"]:
                assert len(source) > 3, \
                    f"Test case {case['id']}: Source item too short: '{source}'"
            
            # Verify each criteria item has reasonable length
            for criteria in vm["criteria"]:
                assert len(criteria) > 5, \
                    f"Test case {case['id']}: Criteria item too short: '{criteria}'"
            
            # Verify each step item has reasonable length
            for step in vm["steps"]:
                assert len(step) > 5, \
                    f"Test case {case['id']}: Step item too short: '{step}'"
    
    def test_verification_method_count_expectations(self, verification_builder_test_cases, test_datetime):
        """
        Additional test: Verify verification method has expected counts
        
        For test cases with expected counts, verify the verification builder
        generates the appropriate number of items.
        """
        for case in verification_builder_test_cases:
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            vm = result["verification_method"]
            
            # Check expected counts if specified
            if "expected_criteria_count" in case:
                assert len(vm["criteria"]) >= case["expected_criteria_count"], \
                    f"Test case {case['id']}: Expected at least {case['expected_criteria_count']} criteria " \
                    f"but got {len(vm['criteria'])}"
            
            if "expected_steps_count" in case:
                assert len(vm["steps"]) >= case["expected_steps_count"], \
                    f"Test case {case['id']}: Expected at least {case['expected_steps_count']} steps " \
                    f"but got {len(vm['steps'])}"
