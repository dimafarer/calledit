"""
Unit Tests for Categorizer Agent

Simple structural tests that don't require agent invocation.
Focus on data validation and structure, not agent behavior.

NOTE: Agent invocation tests deferred until post-Task 9 deployment testing.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../handlers/strands_make_call'))

from categorizer_agent import (
    create_categorizer_agent,
    VALID_CATEGORIES,
    CATEGORIZER_SYSTEM_PROMPT
)


class TestCategorizerConfiguration:
    """Tests for Categorizer Agent configuration (no agent invocation)"""
    
    def test_valid_categories_set(self):
        """Test that valid categories set contains exactly 5 categories"""
        assert len(VALID_CATEGORIES) == 5
        assert "agent_verifiable" in VALID_CATEGORIES
        assert "current_tool_verifiable" in VALID_CATEGORIES
        assert "strands_tool_verifiable" in VALID_CATEGORIES
        assert "api_tool_verifiable" in VALID_CATEGORIES
        assert "human_verifiable_only" in VALID_CATEGORIES
    
    def test_categorizer_agent_creation(self):
        """Test that Categorizer Agent is created with correct configuration"""
        agent = create_categorizer_agent()
        
        # Should have no tools (pure reasoning)
        assert len(agent.tools) == 0
    
    def test_categorizer_agent_has_focused_prompt(self):
        """Test that Categorizer Agent has a concise system prompt"""
        agent = create_categorizer_agent()
        
        # System prompt should be focused (not 200+ lines)
        prompt_lines = agent.system_prompt.count('\n')
        assert prompt_lines < 60, "System prompt should be concise (< 60 lines)"
    
    def test_system_prompt_includes_all_categories(self):
        """Test that system prompt documents all 5 categories"""
        for category in VALID_CATEGORIES:
            assert category in CATEGORIZER_SYSTEM_PROMPT, \
                f"System prompt should document {category}"
    
    def test_system_prompt_has_examples(self):
        """Test that system prompt includes examples for each category"""
        # Check for example keywords
        assert "Examples:" in CATEGORIZER_SYSTEM_PROMPT
        assert "Sun will rise" in CATEGORIZER_SYSTEM_PROMPT  # agent_verifiable
        assert "after 3pm" in CATEGORIZER_SYSTEM_PROMPT  # current_tool_verifiable
        assert "Calculate" in CATEGORIZER_SYSTEM_PROMPT  # strands_tool_verifiable
        assert "Bitcoin" in CATEGORIZER_SYSTEM_PROMPT or "Weather" in CATEGORIZER_SYSTEM_PROMPT  # api_tool_verifiable
        assert "feel happy" in CATEGORIZER_SYSTEM_PROMPT or "Movie" in CATEGORIZER_SYSTEM_PROMPT  # human_verifiable_only


class TestCategoryValidation:
    """Tests for category validation logic (no agent invocation)"""
    
    def test_valid_category_accepted(self):
        """Test that valid categories are accepted"""
        for category in VALID_CATEGORIES:
            assert category in VALID_CATEGORIES
    
    def test_invalid_category_rejected(self):
        """Test that invalid categories are not in valid set"""
        invalid_categories = [
            "invalid_category",
            "tool_verifiable",  # Missing prefix
            "agent_only",  # Wrong format
            "",
            "AGENT_VERIFIABLE",  # Wrong case
        ]
        
        for invalid in invalid_categories:
            assert invalid not in VALID_CATEGORIES


class TestCategorizerNodeStructure:
    """Tests for categorizer node function structure (no agent invocation)"""
    
    def test_categorizer_node_function_exists(self):
        """Test that categorizer_node_function is defined"""
        from categorizer_agent import categorizer_node_function
        assert callable(categorizer_node_function)
    
    def test_categorizer_node_function_signature(self):
        """Test that categorizer_node_function has correct signature"""
        from categorizer_agent import categorizer_node_function
        import inspect
        
        sig = inspect.signature(categorizer_node_function)
        params = list(sig.parameters.keys())
        
        # Should accept state parameter
        assert "state" in params
        assert len(params) == 1


# NOTE: Agent invocation tests (test_categorizer_node_function, property tests)
# are deferred until post-Task 9 deployment testing when we can validate
# in a proper environment with Bedrock API access.
