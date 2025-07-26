#!/usr/bin/env python3
"""
Strands Verification Agent
Intelligently verifies predictions with tool gap detection
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any
import logging

try:
    from strands_agents import Agent
    from strands_agents_tools import current_time
except ImportError:
    # Use mock for testing
    from mock_strands import MockStrandsModule, MockStrandsToolsModule
    Agent = MockStrandsModule.Agent
    current_time = MockStrandsToolsModule.current_time

from verification_result import (
    VerificationResult, VerificationStatus, 
    create_tool_gap_result, MCPToolSuggestions
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredictionVerificationAgent:
    def __init__(self):
        self.agent = Agent(
            name="prediction_verifier",
            model="claude-3-sonnet-20241022",
            tools=[current_time]
        )
    
    def verify_prediction(self, prediction: Dict[str, Any]) -> VerificationResult:
        """
        Verify a single prediction using appropriate method based on category
        """
        start_time = time.time()
        
        prediction_id = prediction.get('SK', 'unknown')
        statement = prediction.get('prediction_statement', '')
        category = prediction.get('verifiable_category', 'unknown')
        verification_date = prediction.get('verification_date', '')
        
        logger.info(f"Verifying prediction: {statement[:50]}...")
        logger.info(f"Category: {category}")
        
        try:
            # Route to appropriate verification method
            if category == 'agent_verifiable':
                result = self._verify_with_reasoning(prediction_id, statement, verification_date)
            elif category == 'current_tool_verifiable':
                result = self._verify_with_time_tool(prediction_id, statement, verification_date)
            elif category == 'strands_tool_verifiable':
                result = self._verify_with_calculation(prediction_id, statement, verification_date)
            elif category == 'api_tool_verifiable':
                result = self._verify_with_api_gap_detection(prediction_id, statement, verification_date)
            elif category == 'human_verifiable_only':
                result = self._mark_as_inconclusive(prediction_id, statement, verification_date)
            else:
                result = self._handle_unknown_category(prediction_id, statement, verification_date)
            
            # Add processing time
            result.processing_time_ms = int((time.time() - start_time) * 1000)
            
            return result
            
        except Exception as e:
            logger.error(f"Error verifying prediction: {str(e)}")
            return VerificationResult(
                prediction_id=prediction_id,
                status=VerificationStatus.ERROR,
                confidence=0.0,
                reasoning=f"Verification failed: {str(e)}",
                verification_date=datetime.now(timezone.utc),
                tools_used=[],
                agent_thoughts=f"Error during verification: {str(e)}",
                error_message=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def _verify_with_reasoning(self, prediction_id: str, statement: str, verification_date: str) -> VerificationResult:
        """Verify using pure reasoning for natural laws and facts"""
        
        prompt = f"""
        Verify this prediction using pure reasoning and established knowledge:
        
        Prediction: "{statement}"
        Verification Date: {verification_date}
        
        Analyze whether this prediction is TRUE or FALSE based on:
        1. Natural laws and scientific facts
        2. Logical reasoning
        3. Established knowledge
        
        Provide your reasoning and confidence level (0.0 to 1.0).
        """
        
        response = self.agent.run(prompt)
        
        # Parse agent response for verification result
        agent_thoughts = response.get('content', '')
        
        # Simple heuristic to determine TRUE/FALSE from agent response
        response_lower = agent_thoughts.lower()
        if 'true' in response_lower and 'false' not in response_lower:
            status = VerificationStatus.TRUE
            confidence = 0.9
        elif 'false' in response_lower and 'true' not in response_lower:
            status = VerificationStatus.FALSE
            confidence = 0.9
        else:
            status = VerificationStatus.INCONCLUSIVE
            confidence = 0.5
        
        return VerificationResult(
            prediction_id=prediction_id,
            status=status,
            confidence=confidence,
            reasoning=f"Verified through reasoning: {agent_thoughts[:200]}...",
            verification_date=datetime.now(timezone.utc),
            tools_used=['reasoning'],
            agent_thoughts=agent_thoughts,
            verification_method='agent_reasoning'
        )
    
    def _verify_with_time_tool(self, prediction_id: str, statement: str, verification_date: str) -> VerificationResult:
        """Verify using current time tool for time-based predictions"""
        
        prompt = f"""
        Verify this time-based prediction using the current_time tool:
        
        Prediction: "{statement}"
        Verification Date: {verification_date}
        
        Use the current_time tool to check the current date and time, then determine if this prediction is TRUE or FALSE.
        Consider timezone context and be precise about timing.
        """
        
        response = self.agent.run(prompt)
        
        agent_thoughts = response.get('content', '')
        tools_used = ['current_time'] if 'current_time' in str(response) else ['reasoning']
        
        # Parse response for verification
        response_lower = agent_thoughts.lower()
        if 'true' in response_lower and 'false' not in response_lower:
            status = VerificationStatus.TRUE
            confidence = 0.85
        elif 'false' in response_lower and 'true' not in response_lower:
            status = VerificationStatus.FALSE
            confidence = 0.85
        else:
            status = VerificationStatus.INCONCLUSIVE
            confidence = 0.6
        
        return VerificationResult(
            prediction_id=prediction_id,
            status=status,
            confidence=confidence,
            reasoning=f"Verified using time context: {agent_thoughts[:200]}...",
            verification_date=datetime.now(timezone.utc),
            tools_used=tools_used,
            agent_thoughts=agent_thoughts,
            verification_method='time_based_verification'
        )
    
    def _verify_with_calculation(self, prediction_id: str, statement: str, verification_date: str) -> VerificationResult:
        """Verify mathematical/computational predictions"""
        
        prompt = f"""
        Verify this mathematical or computational prediction:
        
        Prediction: "{statement}"
        
        Perform any necessary calculations or logical analysis to determine if this is TRUE or FALSE.
        Show your work and reasoning clearly.
        """
        
        response = self.agent.run(prompt)
        
        agent_thoughts = response.get('content', '')
        
        # Parse for mathematical verification
        response_lower = agent_thoughts.lower()
        if 'true' in response_lower or 'correct' in response_lower:
            status = VerificationStatus.TRUE
            confidence = 0.95
        elif 'false' in response_lower or 'incorrect' in response_lower:
            status = VerificationStatus.FALSE
            confidence = 0.95
        else:
            status = VerificationStatus.INCONCLUSIVE
            confidence = 0.7
        
        return VerificationResult(
            prediction_id=prediction_id,
            status=status,
            confidence=confidence,
            reasoning=f"Mathematical verification: {agent_thoughts[:200]}...",
            verification_date=datetime.now(timezone.utc),
            tools_used=['calculation'],
            agent_thoughts=agent_thoughts,
            verification_method='mathematical_verification'
        )
    
    def _verify_with_api_gap_detection(self, prediction_id: str, statement: str, verification_date: str) -> VerificationResult:
        """Handle API-verifiable predictions by detecting tool gaps"""
        
        # Check if we have the necessary tools
        statement_lower = statement.lower()
        
        # Bitcoin predictions - we could implement this
        if 'bitcoin' in statement_lower:
            return create_tool_gap_result(
                prediction_id=prediction_id,
                prediction_text=statement,
                category='api_tool_verifiable',
                reasoning="Bitcoin price verification requires cryptocurrency API integration"
            )
        
        # Weather predictions
        if any(word in statement_lower for word in ['rain', 'sunny', 'weather', 'temperature']):
            return create_tool_gap_result(
                prediction_id=prediction_id,
                prediction_text=statement,
                category='api_tool_verifiable',
                reasoning="Weather verification requires weather API integration"
            )
        
        # Sports predictions
        if any(word in statement_lower for word in ['nba', 'game', 'win', 'team', 'championship']):
            return create_tool_gap_result(
                prediction_id=prediction_id,
                prediction_text=statement,
                category='api_tool_verifiable',
                reasoning="Sports result verification requires sports data API integration"
            )
        
        # Generic API tool gap
        return create_tool_gap_result(
            prediction_id=prediction_id,
            prediction_text=statement,
            category='api_tool_verifiable',
            reasoning="External API verification required but no suitable tool available"
        )
    
    def _mark_as_inconclusive(self, prediction_id: str, statement: str, verification_date: str) -> VerificationResult:
        """Mark human-verifiable predictions as inconclusive"""
        
        return VerificationResult(
            prediction_id=prediction_id,
            status=VerificationStatus.INCONCLUSIVE,
            confidence=0.0,
            reasoning="Human verification required - subjective or personal prediction",
            verification_date=datetime.now(timezone.utc),
            tools_used=[],
            agent_thoughts=f"This prediction '{statement}' requires human assessment as it involves subjective or personal elements that cannot be objectively verified by automated tools.",
            verification_method='human_assessment_required'
        )
    
    def _handle_unknown_category(self, prediction_id: str, statement: str, verification_date: str) -> VerificationResult:
        """Handle predictions with unknown categories"""
        
        # Try to categorize and then verify
        prompt = f"""
        Analyze this prediction and determine how it could be verified:
        
        Prediction: "{statement}"
        
        Can this be verified through:
        1. Pure reasoning/knowledge?
        2. Current time/date checking?
        3. Mathematical calculation?
        4. External API data?
        5. Human assessment only?
        
        Then attempt verification if possible.
        """
        
        response = self.agent.run(prompt)
        agent_thoughts = response.get('content', '')
        
        return VerificationResult(
            prediction_id=prediction_id,
            status=VerificationStatus.INCONCLUSIVE,
            confidence=0.3,
            reasoning=f"Unknown category - attempted analysis: {agent_thoughts[:200]}...",
            verification_date=datetime.now(timezone.utc),
            tools_used=['reasoning'],
            agent_thoughts=agent_thoughts,
            verification_method='category_analysis'
        )

def main():
    """Test the verification agent"""
    agent = PredictionVerificationAgent()
    
    # Test predictions
    test_predictions = [
        {
            'SK': 'test_1',
            'prediction_statement': 'The sun will rise tomorrow',
            'verifiable_category': 'agent_verifiable',
            'verification_date': '2025-01-28T00:00:00Z'
        },
        {
            'SK': 'test_2', 
            'prediction_statement': 'It will rain in Seattle today',
            'verifiable_category': 'api_tool_verifiable',
            'verification_date': '2025-01-27T23:59:59Z'
        },
        {
            'SK': 'test_3',
            'prediction_statement': 'I will feel happy tomorrow',
            'verifiable_category': 'human_verifiable_only',
            'verification_date': '2025-01-28T00:00:00Z'
        }
    ]
    
    print("🤖 Testing Strands Verification Agent")
    print("=" * 50)
    
    for prediction in test_predictions:
        print(f"\n🔍 Testing: {prediction['prediction_statement']}")
        print(f"Category: {prediction['verifiable_category']}")
        
        result = agent.verify_prediction(prediction)
        
        print(f"Result: {result.status.value}")
        print(f"Confidence: {result.confidence}")
        print(f"Reasoning: {result.reasoning}")
        
        if result.tool_gap:
            print(f"🔧 Tool Gap: {result.tool_gap.missing_tool}")
            print(f"💡 Suggested MCP: {result.tool_gap.suggested_mcp_tool}")

if __name__ == "__main__":
    main()