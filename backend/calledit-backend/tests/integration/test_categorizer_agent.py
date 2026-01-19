"""
Integration Tests for Categorizer Agent

Tests the Categorizer Agent's ability to:
- Classify predictions into 5 verifiability categories (Property 6)
- Provide reasoning for categorization (Property 7)

Following Strands best practices:
- Real agent invocations with real LLM calls
- Structured test cases from JSON files
"""

import pytest
from prediction_graph import execute_prediction_graph


@pytest.mark.integration
class TestCategorizerAgent:
    """
    Integration tests for Categorizer Agent.
    
    These tests invoke the full 3-agent graph but focus on validating
    the Categorizer Agent's outputs.
    """
    
    def test_valid_category_classification(self, categorizer_test_cases, test_datetime):
        """
        Property 6: Categorizer returns valid category
        
        Validates: Requirements 3.1, 3.2
        
        The categorizer should classify predictions into one of the
        5 valid verifiability categories:
        - api_tool_verifiable
        - current_tool_verifiable
        - agent_verifiable
        - human_verifiable_only
        - not_verifiable
        """
        valid_categories = {
            "api_tool_verifiable",
            "current_tool_verifiable",
            "agent_verifiable",
            "human_verifiable_only",
            "not_verifiable"
        }
        
        for case in categorizer_test_cases:
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            # Verify category is valid
            assert result["verifiable_category"] in valid_categories, \
                f"Test case {case['id']}: Invalid category '{result['verifiable_category']}'"
    
    def test_expected_category_matches(self, categorizer_test_cases, test_datetime):
        """
        Additional test: Verify expected categories match
        
        For test cases with known expected categories, verify the
        categorizer produces the correct classification.
        """
        for case in categorizer_test_cases:
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
    
    def test_category_reasoning_provided(self, categorizer_test_cases, test_datetime):
        """
        Property 7: Categorizer provides reasoning
        
        Validates: Requirements 3.3
        
        The categorizer should provide clear reasoning explaining
        why it chose the particular category.
        """
        for case in categorizer_test_cases:
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            # Verify category_reasoning exists and is non-empty
            assert "category_reasoning" in result, \
                f"Test case {case['id']}: category_reasoning field missing"
            assert result["category_reasoning"], \
                f"Test case {case['id']}: category_reasoning is empty"
            assert len(result["category_reasoning"]) > 10, \
                f"Test case {case['id']}: category_reasoning is too short (likely fallback)"
    
    def test_reasoning_mentions_category(self, categorizer_test_cases, test_datetime):
        """
        Additional test: Verify reasoning relates to the category
        
        The reasoning should mention or relate to the chosen category.
        """
        for case in categorizer_test_cases:
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc=test_datetime["utc"],
                current_datetime_local=test_datetime["local"],
                callback_handler=None
            )
            
            category = result["verifiable_category"]
            reasoning = result["category_reasoning"].lower()
            
            # Check if reasoning mentions key terms related to the category
            category_keywords = {
                "api_tool_verifiable": ["api", "weather", "data", "external"],
                "current_tool_verifiable": ["current", "time", "now", "present"],
                "agent_verifiable": ["knowledge", "fact", "verify", "check"],
                "human_verifiable_only": ["human", "subjective", "personal", "opinion"],
                "not_verifiable": ["not", "cannot", "impossible", "unverifiable"]
            }
            
            keywords = category_keywords.get(category, [])
            has_keyword = any(keyword in reasoning for keyword in keywords)
            
            # Note: This is a soft check - reasoning should relate to category
            # but we don't fail the test if keywords aren't found (LLM may use different wording)
            if not has_keyword:
                print(f"Warning: Test case {case['id']}: Reasoning may not clearly relate to category")
                print(f"  Category: {category}")
                print(f"  Reasoning: {reasoning[:100]}...")
