"""
Verification Builder Agent for Prediction Verification System

This agent constructs detailed verification methods with source, criteria, and steps.
It's the third agent in the graph workflow.

Following Strands best practices:
- Single responsibility (verification method building only)
- Focused system prompt (~25 lines)
- Explicit model specification
- No tools needed (pure reasoning)
"""

import logging
import json
from strands import Agent

logger = logging.getLogger(__name__)


# Verification Builder Agent System Prompt (focused, ~25 lines)
VERIFICATION_BUILDER_SYSTEM_PROMPT = """You are a verification method builder. Create detailed verification plans.

For the given prediction and category, specify:
- source: List of reliable sources to check (e.g., APIs, databases, tools)
- criteria: List of measurable criteria for determining truth
- steps: List of detailed verification steps to execute

Make verification methods:
- Specific and actionable
- Appropriate for the verifiability category
- Measurable and objective
- Realistic and achievable

IMPORTANT: All three fields (source, criteria, steps) must be lists, not single strings.

Return JSON:
{
    "verification_method": {
        "source": ["source1", "source2"],
        "criteria": ["criterion1", "criterion2"],
        "steps": ["step1", "step2", "step3"]
    }
}
"""


def create_verification_builder_agent() -> Agent:
    """
    Create the Verification Builder Agent with explicit configuration.
    
    Following Strands best practices:
    - Explicit model selection (Bedrock model ID)
    - Focused system prompt
    - No tools (pure reasoning task)
    
    Returns:
        Configured Verification Builder Agent
    """
    agent = Agent(
        model="anthropic.claude-3-5-sonnet-20241022-v2:0",
        system_prompt=VERIFICATION_BUILDER_SYSTEM_PROMPT
    )
    
    logger.info("Verification Builder Agent created with explicit model configuration")
    return agent


def verification_builder_node_function(state: dict) -> dict:
    """
    Verification Builder node function for the prediction verification graph.
    
    This function follows the Strands graph node pattern:
    1. Receive state from previous node (Categorizer)
    2. Build prompt from state
    3. Invoke agent
    4. Parse response (single json.loads call)
    5. Validate verification_method structure
    6. Update and return state
    
    Args:
        state: Graph state containing prediction_statement, verifiable_category, verification_date
        
    Returns:
        Updated state with verification_method
        
    Raises:
        Exception: If agent invocation or JSON parsing fails
    """
    # Build prompt from state
    prompt = f"""PREDICTION: {state['prediction_statement']}
CATEGORY: {state['verifiable_category']}
VERIFICATION DATE: {state['verification_date']}

Build a detailed verification method for this prediction.
"""
    
    # Create and invoke agent
    verification_builder_agent = create_verification_builder_agent()
    
    try:
        response = verification_builder_agent(prompt)
        
        # Parse response (single json.loads call - Strands best practice)
        result = json.loads(str(response))
        
        # Extract verification_method
        verification_method = result.get("verification_method", {})
        
        # Validate structure - ensure all fields are lists
        if not isinstance(verification_method.get("source"), list):
            source_val = verification_method.get("source", "Manual verification")
            verification_method["source"] = [source_val] if source_val else ["Manual verification"]
        
        if not isinstance(verification_method.get("criteria"), list):
            criteria_val = verification_method.get("criteria", "Human judgment required")
            verification_method["criteria"] = [criteria_val] if criteria_val else ["Human judgment required"]
        
        if not isinstance(verification_method.get("steps"), list):
            steps_val = verification_method.get("steps", "Manual review needed")
            verification_method["steps"] = [steps_val] if steps_val else ["Manual review needed"]
        
        logger.info(f"Verification Builder Agent created method with {len(verification_method.get('steps', []))} steps")
        logger.debug(f"Verification method: {json.dumps(verification_method, indent=2)}")
        
        # Update and return state
        return {
            **state,
            "verification_method": verification_method
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {str(e)}")
        # Simple fallback - Strands best practice
        return {
            **state,
            "verification_method": {
                "source": ["Manual verification"],
                "criteria": ["Human judgment required"],
                "steps": ["Manual review needed due to parsing error"]
            },
            "error": f"Verification Builder JSON decode error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Verification Builder Agent failed: {str(e)}", exc_info=True)
        # Simple fallback
        return {
            **state,
            "verification_method": {
                "source": ["Manual verification"],
                "criteria": ["Human judgment required"],
                "steps": ["Manual review needed due to agent error"]
            },
            "error": f"Verification Builder Agent error: {str(e)}"
        }
