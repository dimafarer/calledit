import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import pytest
from unittest.mock import patch, MagicMock, Mock

# Mock strands_agents before importing ReviewAgent
sys.modules['strands_agents'] = Mock()
sys.modules['strands_agents.tools'] = Mock()
sys.modules['strands_tools'] = Mock()

from handlers.strands_make_call.review_agent import ReviewAgent

class TestReviewAgent:
    
    @pytest.fixture
    def review_agent(self):
        """Fixture providing ReviewAgent instance"""
        return ReviewAgent()
    
    @pytest.fixture
    def sample_call_response(self):
        """Fixture providing sample call response for testing"""
        return {
            "prediction_statement": "Bitcoin will hit $100k today",
            "verification_date": "2025-01-27T23:59:59Z",
            "verifiable_category": "api_tool_verifiable",
            "category_reasoning": "Requires external API to check Bitcoin price",
            "verification_method": {
                "source": ["CoinGecko API"],
                "criteria": ["BTC/USD price exceeds $100,000"],
                "steps": ["Check BTC price at end of day"]
            }
        }
    
    def test_review_agent_initialization(self, review_agent):
        """Test that ReviewAgent initializes correctly"""
        assert isinstance(review_agent, ReviewAgent)
        assert review_agent.name == "ReviewAgent"
        assert "reviews prediction calls" in review_agent.description.lower()
    
    def test_review_call_response_structure(self):
        """Test that review_call_response returns proper structure"""
        result = self.review_agent.review_call_response(self.sample_call_response)
        
        # Should return a dictionary with reviewable_sections
        self.assertIsInstance(result, dict)
        self.assertIn('reviewable_sections', result)
        self.assertIsInstance(result['reviewable_sections'], list)
    
    def test_review_identifies_improvable_sections(self):
        """Test that review can identify sections that could be improved"""
        result = self.review_agent.review_call_response(self.sample_call_response)
        
        # Should have some reviewable sections for a basic prediction
        reviewable_sections = result.get('reviewable_sections', [])
        
        # Each section should have required fields
        for section in reviewable_sections:
            self.assertIn('section', section)
            self.assertIn('improvable', section)
            self.assertIn('questions', section)
            self.assertIn('reasoning', section)
            
            # Questions should be a list
            self.assertIsInstance(section['questions'], list)
            
            # If improvable, should have questions
            if section['improvable']:
                self.assertGreater(len(section['questions']), 0)
    
    def test_ask_improvement_questions(self):
        """Test that improvement questions are generated properly"""
        section = "prediction_statement"
        questions = ["What specific time of day?", "Any location constraints?"]
        
        result = self.review_agent.ask_improvement_questions(section, questions)
        
        # Should return a string with friendly questions
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        
        # Should mention the section being improved
        self.assertIn(section.replace('_', ' '), result.lower())
    
    def test_regenerate_with_improvements(self):
        """Test that regeneration works with user input"""
        section = "prediction_statement"
        user_input = "I meant before 3pm Eastern time"
        original_prediction = "Bitcoin will hit $100k today"
        
        result = self.review_agent.regenerate_with_improvements(
            self.sample_call_response, section, user_input, original_prediction
        )
        
        # Should return proper structure
        self.assertIsInstance(result, dict)
        self.assertIn('change_type', result)
        self.assertIn('updated_response', result)
        self.assertIn('changes_made', result)
        
        # Change type should be valid
        self.assertIn(result['change_type'], ['significant', 'minor'])
        
        # Updated response should have same structure as original
        updated = result['updated_response']
        self.assertIn('prediction_statement', updated)
        self.assertIn('verification_date', updated)
        self.assertIn('verifiable_category', updated)
        
        # Changes made should be a list
        self.assertIsInstance(result['changes_made'], list)
    
    def test_handles_invalid_json_gracefully(self):
        """Test that agent handles invalid JSON responses gracefully"""
        # This test would require mocking the agent's invoke method
        # to return invalid JSON, but for now we test the fallback behavior
        
        # Test with empty response
        result = self.review_agent.review_call_response({})
        self.assertIsInstance(result, dict)
        self.assertIn('reviewable_sections', result)
    
    def test_all_sections_can_be_reviewed(self):
        """Test that all expected sections can be reviewed"""
        expected_sections = [
            'prediction_statement',
            'verification_date', 
            'verifiable_category',
            'category_reasoning',
            'verification_method'
        ]
        
        result = self.review_agent.review_call_response(self.sample_call_response)
        reviewable_sections = result.get('reviewable_sections', [])
        
        # Get list of sections that were reviewed
        reviewed_section_names = [s['section'] for s in reviewable_sections]
        
        # Should review at least some of the expected sections
        # (Not all sections may be improvable for every prediction)
        self.assertGreater(len(reviewed_section_names), 0)
        
        # All reviewed sections should be from expected list
        for section_name in reviewed_section_names:
            self.assertIn(section_name, expected_sections)

