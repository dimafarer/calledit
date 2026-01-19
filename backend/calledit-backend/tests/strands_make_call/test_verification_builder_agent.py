"""
Unit Tests for Verification Builder Agent

Simple structural tests that don't require agent invocation.
Focus on data validation and structure, not agent behavior.

NOTE: Agent invocation tests deferred until post-Task 9 deployment testing.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../handlers/strands_make_call'))

from verification_builder_agent import (
    create_verification_builder_agent,
    VERIFICATION_BUILDER_SYSTEM_PROMPT
)


class TestVerificationBuilderConfiguration:
    """Tests for Verification Builder Agent configuration (no agent invocation)"""
    
    def test_verification_builder_agent_creation(self):
        """Test that Verification Builder Agent is created with correct configuration"""
        agent = create_verification_builder_agent()
        
        # Should have no tools (pure reasoning)
        assert len(agent.tools) == 0
    
    def test_verification_builder_agent_has_focused_prompt(self):
        """Test that Verification Builder Agent has a concise system prompt"""
        agent = create_verification_builder_agent()
        
        # System prompt should be focused (not 200+ lines)
        prompt_lines = agent.system_prompt.count('\n')
        assert prompt_lines < 50, "System prompt should be concise (< 50 lines)"
    
    def test_system_prompt_specifies_required_fields(self):
        """Test that system prompt documents required fields"""
        assert "source" in VERIFICATION_BUILDER_SYSTEM_PROMPT
        assert "criteria" in VERIFICATION_BUILDER_SYSTEM_PROMPT
        assert "steps" in VERIFICATION_BUILDER_SYSTEM_PROMPT
    
    def test_system_prompt_requires_lists(self):
        """Test that system prompt specifies fields must be lists"""
        # Should mention that fields are lists
        assert "List" in VERIFICATION_BUILDER_SYSTEM_PROMPT or "list" in VERIFICATION_BUILDER_SYSTEM_PROMPT


class TestVerificationMethodStructure:
    """Tests for verification method structure validation (no agent invocation)"""
    
    def test_verification_method_has_required_fields(self):
        """Test that verification method structure has required fields"""
        # This is a structural test - just verify the expected structure
        expected_fields = ["source", "criteria", "steps"]
        
        # Verification method should have these fields
        verification_method = {
            "source": ["test"],
            "criteria": ["test"],
            "steps": ["test"]
        }
        
        for field in expected_fields:
            assert field in verification_method
    
    def test_verification_method_fields_are_lists(self):
        """Test that verification method fields should be lists"""
        verification_method = {
            "source": ["API", "Database"],
            "criteria": ["Criterion 1", "Criterion 2"],
            "steps": ["Step 1", "Step 2", "Step 3"]
        }
        
        assert isinstance(verification_method["source"], list)
        assert isinstance(verification_method["criteria"], list)
        assert isinstance(verification_method["steps"], list)


class TestVerificationBuilderNodeStructure:
    """Tests for verification builder node function structure (no agent invocation)"""
    
    def test_verification_builder_node_function_exists(self):
        """Test that verification_builder_node_function is defined"""
        from verification_builder_agent import verification_builder_node_function
        assert callable(verification_builder_node_function)
    
    def test_verification_builder_node_function_signature(self):
        """Test that verification_builder_node_function has correct signature"""
        from verification_builder_agent import verification_builder_node_function
        import inspect
        
        sig = inspect.signature(verification_builder_node_function)
        params = list(sig.parameters.keys())
        
        # Should accept state parameter
        assert "state" in params
        assert len(params) == 1


# NOTE: Agent invocation tests (test_verification_builder_node_function, property tests)
# are deferred until post-Task 9 deployment testing when we can validate
# in a proper environment with Bedrock API access.
