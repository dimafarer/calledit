import pytest
import json
from unittest.mock import Mock, patch
import sys
import os

# Add the handlers directory to the path so we can import the ReviewAgent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'handlers', 'strands_make_call'))

from review_agent import ReviewAgent


class TestReviewAgent:
    """Unit tests for ReviewAgent VPSS (Verifiable Prediction Structuring System) functionality."""
    
    @pytest.fixture
    def sample_prediction_response(self):
        """Sample prediction response for testing."""
        return {
            "prediction_statement": "I'll finish my project soon",
            "verification_date": "2025-08-13T21:47:00Z",
            "verifiable_category": "human_verifiable_only",
            "category_reasoning": "Project completion is subjective",
            "verification_method": {
                "source": ["User's own assessment"],
                "criteria": ["User considers project complete"],
                "steps": ["User must assess completion"]
            },
            "initial_status": "pending"
        }
    
    @pytest.fixture
    def mock_agent_response_valid_json(self):
        """Mock agent response with valid JSON."""
        return {
            "reviewable_sections": [
                {
                    "section": "prediction_statement",
                    "improvable": True,
                    "questions": ["What specific project?", "What does 'finished' mean?"],
                    "reasoning": "Statement is too vague"
                }
            ]
        }
    
    @pytest.fixture
    def mock_agent_response_markdown_json(self):
        """Mock agent response with JSON in markdown code blocks."""
        return '''Here's my analysis:

```json
{
    "reviewable_sections": [
        {
            "section": "verification_method",
            "improvable": true,
            "questions": ["How do you track progress?"],
            "reasoning": "Method is too subjective"
        }
    ]
}
```

That's my recommendation.'''
    
    @pytest.fixture
    def mock_agent_response_malformed(self):
        """Mock agent response with malformed JSON."""
        return '''The prediction needs improvement in these areas:
        
        {
            "reviewable_sections": [
                {
                    "section": "date_reasoning"
                    "improvable": true,  // missing comma
                    "questions": ["What timeframe?"]
                }
            ]
        }'''

    def test_review_agent_initialization(self):
        """Test ReviewAgent initializes correctly."""
        agent = ReviewAgent()
        assert agent is not None
        assert agent.agent is not None
        assert agent.callback_handler is None
        
        # Test with callback handler
        mock_callback = Mock()
        agent_with_callback = ReviewAgent(callback_handler=mock_callback)
        assert agent_with_callback.callback_handler == mock_callback

    @patch('review_agent.Agent')
    def test_review_prediction_valid_json(self, mock_agent_class, sample_prediction_response, mock_agent_response_valid_json):
        """Test review_prediction with valid JSON response."""
        # Setup mock
        mock_agent_instance = Mock()
        mock_agent_instance.return_value = json.dumps(mock_agent_response_valid_json)
        mock_agent_class.return_value = mock_agent_instance
        
        # Test
        review_agent = ReviewAgent()
        result = review_agent.review_prediction(sample_prediction_response)
        
        # Assertions
        assert result == mock_agent_response_valid_json
        assert len(result["reviewable_sections"]) == 1
        assert result["reviewable_sections"][0]["section"] == "prediction_statement"
        assert result["reviewable_sections"][0]["improvable"] is True
        assert len(result["reviewable_sections"][0]["questions"]) == 2

    @patch('review_agent.Agent')
    def test_review_prediction_markdown_json(self, mock_agent_class, sample_prediction_response, mock_agent_response_markdown_json):
        """Test review_prediction with JSON in markdown code blocks."""
        # Setup mock
        mock_agent_instance = Mock()
        mock_agent_instance.return_value = mock_agent_response_markdown_json
        mock_agent_class.return_value = mock_agent_instance
        
        # Test
        review_agent = ReviewAgent()
        result = review_agent.review_prediction(sample_prediction_response)
        
        # Assertions
        assert "reviewable_sections" in result
        assert len(result["reviewable_sections"]) == 1
        assert result["reviewable_sections"][0]["section"] == "verification_method"

    @patch('review_agent.Agent')
    def test_review_prediction_malformed_json_fallback(self, mock_agent_class, sample_prediction_response, mock_agent_response_malformed):
        """Test review_prediction fallback with malformed JSON."""
        # Setup mock
        mock_agent_instance = Mock()
        mock_agent_instance.return_value = mock_agent_response_malformed
        mock_agent_class.return_value = mock_agent_instance
        
        # Test
        review_agent = ReviewAgent()
        result = review_agent.review_prediction(sample_prediction_response)
        
        # Assertions - should fallback to empty sections
        assert result == {"reviewable_sections": []}

    @patch('review_agent.Agent')
    def test_generate_improvement_questions_valid_response(self, mock_agent_class):
        """Test generate_improvement_questions with valid JSON response."""
        # Setup mock
        mock_agent_instance = Mock()
        mock_agent_instance.return_value = '{"questions": ["Question 1?", "Question 2?", "Question 3?"]}'
        mock_agent_class.return_value = mock_agent_instance
        
        # Test
        review_agent = ReviewAgent()
        result = review_agent.generate_improvement_questions("prediction_statement", "I'll finish soon")
        
        # Assertions
        assert len(result) == 3
        assert result[0] == "Question 1?"
        assert result[1] == "Question 2?"
        assert result[2] == "Question 3?"

    @patch('review_agent.Agent')
    def test_generate_improvement_questions_fallback(self, mock_agent_class):
        """Test generate_improvement_questions fallback with invalid JSON."""
        # Setup mock
        mock_agent_instance = Mock()
        mock_agent_instance.return_value = 'Invalid JSON response'
        mock_agent_class.return_value = mock_agent_instance
        
        # Test
        review_agent = ReviewAgent()
        result = review_agent.generate_improvement_questions("prediction_statement", "I'll finish soon")
        
        # Assertions - should fallback to generic question
        assert len(result) == 1
        assert "prediction_statement" in result[0]
        assert "more specific" in result[0]

    @patch('review_agent.Agent')
    def test_regenerate_section(self, mock_agent_class):
        """Test regenerate_section method."""
        # Setup mock
        mock_agent_instance = Mock()
        mock_agent_instance.return_value = "I'll finish my web development project by August 15th, 2025"
        mock_agent_class.return_value = mock_agent_instance
        
        # Test
        review_agent = ReviewAgent()
        result = review_agent.regenerate_section(
            "prediction_statement",
            "I'll finish my project soon",
            "It's a web development project, deadline is August 15th",
            {"verifiable_category": "human_verifiable_only"}
        )
        
        # Assertions
        assert result == "I'll finish my web development project by August 15th, 2025"
        assert "web development" in result
        assert "August 15th" in result

    @patch('review_agent.Agent')
    def test_json_parsing_edge_cases(self, mock_agent_class):
        """Test various JSON parsing edge cases."""
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance
        
        review_agent = ReviewAgent()
        
        # Test case 1: JSON with extra whitespace
        mock_agent_instance.return_value = '''
        
        {
            "reviewable_sections": []
        }
        
        '''
        result = review_agent.review_prediction({})
        assert result == {"reviewable_sections": []}
        
        # Test case 2: JSON with code block and extra text
        mock_agent_instance.return_value = '''
        Based on my analysis:
        
        ```json
        {"reviewable_sections": [{"section": "test", "improvable": false, "questions": [], "reasoning": "test"}]}
        ```
        
        This is my final recommendation.
        '''
        result = review_agent.review_prediction({})
        assert len(result["reviewable_sections"]) == 1
        assert result["reviewable_sections"][0]["section"] == "test"

    @patch('review_agent.Agent')
    def test_review_prediction_with_callback_handler(self, mock_agent_class):
        """Test ReviewAgent with callback handler."""
        # Setup
        mock_callback = Mock()
        mock_agent_instance = Mock()
        mock_agent_instance.return_value = '{"reviewable_sections": []}'
        mock_agent_class.return_value = mock_agent_instance
        
        # Test
        review_agent = ReviewAgent(callback_handler=mock_callback)
        result = review_agent.review_prediction({"test": "data"})
        
        # Assertions
        assert result == {"reviewable_sections": []}
        # Verify Agent was initialized with callback handler
        mock_agent_class.assert_called_once()
        call_args = mock_agent_class.call_args
        assert call_args[1]['callback_handler'] == mock_callback

    def test_system_prompt_content(self):
        """Test that ReviewAgent has proper system prompt."""
        with patch('review_agent.Agent') as mock_agent_class:
            ReviewAgent()
            
            # Verify Agent was called with system prompt
            mock_agent_class.assert_called_once()
            call_args = mock_agent_class.call_args
            system_prompt = call_args[1]['system_prompt']
            
            # Check key elements of system prompt
            assert "prediction review expert" in system_prompt
            assert "reviewable_sections" in system_prompt
            assert "improvable" in system_prompt
            assert "questions" in system_prompt
            assert "reasoning" in system_prompt