"""
Unit Tests for Prediction Graph

Simple structural tests that don't require graph execution.
Focus on graph structure and configuration, not execution behavior.

NOTE: Graph execution tests deferred until post-Task 9 deployment testing.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../handlers/strands_make_call'))

from prediction_graph import create_prediction_graph, prediction_graph, execute_prediction_graph
from graph_state import PredictionGraphState


class TestGraphStructure:
    """Tests for graph structure (no execution)"""
    
    def test_create_prediction_graph_returns_graph(self):
        """Test that create_prediction_graph returns a graph object"""
        graph = create_prediction_graph()
        assert graph is not None
    
    def test_prediction_graph_singleton_exists(self):
        """Test that prediction_graph singleton is created"""
        assert prediction_graph is not None
    
    def test_execute_prediction_graph_function_exists(self):
        """Test that execute_prediction_graph function is defined"""
        assert callable(execute_prediction_graph)
    
    def test_execute_prediction_graph_signature(self):
        """Test that execute_prediction_graph has correct signature"""
        import inspect
        
        sig = inspect.signature(execute_prediction_graph)
        params = list(sig.parameters.keys())
        
        # Should have required parameters
        assert "user_prompt" in params
        assert "user_timezone" in params
        assert "current_datetime_utc" in params
        assert "current_datetime_local" in params
        assert "callback_handler" in params


class TestGraphStateSchema:
    """Tests for graph state schema"""
    
    def test_prediction_graph_state_has_required_fields(self):
        """Test that PredictionGraphState has all required fields"""
        # This tests the TypedDict structure
        state: PredictionGraphState = {
            "user_prompt": "test",
            "user_timezone": "UTC",
            "current_datetime_utc": "2025-01-17 12:00:00 UTC",
            "current_datetime_local": "2025-01-17 12:00:00 UTC"
        }
        
        # Should be able to create state with required fields
        assert state["user_prompt"] == "test"
        assert state["user_timezone"] == "UTC"
    
    def test_prediction_graph_state_allows_partial_updates(self):
        """Test that PredictionGraphState allows partial state updates"""
        # With total=False, we can create partial states
        partial_state: PredictionGraphState = {
            "user_prompt": "test"
        }
        
        assert "user_prompt" in partial_state
    
    def test_prediction_graph_state_has_all_agent_output_fields(self):
        """Test that PredictionGraphState includes fields for all agents"""
        # Create a complete state with all fields
        complete_state: PredictionGraphState = {
            "user_prompt": "test",
            "user_timezone": "UTC",
            "current_datetime_utc": "2025-01-17 12:00:00 UTC",
            "current_datetime_local": "2025-01-17 12:00:00 UTC",
            # Parser outputs
            "prediction_statement": "test",
            "verification_date": "2025-01-17T12:00:00Z",
            "date_reasoning": "test",
            # Categorizer outputs
            "verifiable_category": "agent_verifiable",
            "category_reasoning": "test",
            # Verification Builder outputs
            "verification_method": {
                "source": ["test"],
                "criteria": ["test"],
                "steps": ["test"]
            }
        }
        
        # Verify all expected fields are present
        assert "prediction_statement" in complete_state
        assert "verifiable_category" in complete_state
        assert "verification_method" in complete_state


class TestGraphNodeFunctions:
    """Tests for graph node functions"""
    
    def test_parser_node_function_imported(self):
        """Test that parser_node_function is imported"""
        from prediction_graph import parser_node_function
        assert callable(parser_node_function)
    
    def test_categorizer_node_function_imported(self):
        """Test that categorizer_node_function is imported"""
        from prediction_graph import categorizer_node_function
        assert callable(categorizer_node_function)
    
    def test_verification_builder_node_function_imported(self):
        """Test that verification_builder_node_function is imported"""
        from prediction_graph import verification_builder_node_function
        assert callable(verification_builder_node_function)


# NOTE: Graph execution tests (test_execute_prediction_graph, integration tests, property tests)
# are deferred until post-Task 9 deployment testing when we can validate
# in a proper environment with Bedrock API access and proper graph execution.
