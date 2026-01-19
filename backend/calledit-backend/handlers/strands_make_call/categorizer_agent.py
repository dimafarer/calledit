"""
Categorizer Agent for Prediction Verification System

This agent classifies predictions into one of 5 verifiability categories.
It's the second agent in the graph workflow.

Following Strands best practices:
- Single responsibility (categorization only)
- Focused system prompt (~30 lines)
- Explicit model specification
- No tools needed (pure reasoning)
"""

import logging
import json
from strands import Agent

logger = logging.getLogger(__name__)


# Valid verifiability categories
VALID_CATEGORIES = {
    "agent_verifiable",
    "current_tool_verifiable",
    "strands_tool_verifiable",
    "api_tool_verifiable",
    "human_verifiable_only"
}


# Categorizer Agent System Prompt (focused, ~30 lines)
CATEGORIZER_SYSTEM_PROMPT = """You are a verifiability categorizer. Classify predictions into exactly one category:

1. agent_verifiable - Pure reasoning/knowledge, no external tools needed
   Examples: "Sun will rise tomorrow", "2+2=4", "Christmas 2025 is Thursday"
   
2. current_tool_verifiable - Only needs current_time tool
   Examples: "It's after 3pm", "Today is a weekday", "We're in January 2025"
   
3. strands_tool_verifiable - Needs Strands library tools (calculator, python_repl)
   Examples: "Calculate compound interest", "Parse complex data", "Math computation"
   
4. api_tool_verifiable - Needs external APIs or MCP integrations
   Examples: "Bitcoin hits $100k", "Weather is sunny", "Stock prices", "Sports scores"
   
5. human_verifiable_only - Needs human observation/judgment
   Examples: "Movie will be good", "I will feel happy", "Meeting goes well"

IMPORTANT: Choose the MOST SPECIFIC category. If it can be verified with simpler tools, use that category.

Return JSON:
{
    "verifiable_category": "one of 5 categories above",
    "category_reasoning": "clear explanation of why you chose this category"
}
"""


def create_categorizer_agent() -> Agent:
    """
    Create the Categorizer Agent with explicit configuration.
    
    Following Strands best practices:
    - Explicit model selection (Bedrock model ID)
    - Focused system prompt
    - No tools (pure reasoning task)
    
    Returns:
        Configured Categorizer Agent
    """
    agent = Agent(
        model="anthropic.claude-3-5-sonnet-20241022-v2:0",
        system_prompt=CATEGORIZER_SYSTEM_PROMPT
    )
    
    logger.info("Categorizer Agent created with explicit model configuration")
    return agent


def categorizer_node_function(state: dict) -> dict:
    """
    Categorizer node function for the prediction verification graph.
    
    This function follows the Strands graph node pattern:
    1. Receive state from previous node (Parser)
    2. Build prompt from state
    3. Invoke agent
    4. Parse response (single json.loads call)
    5. Validate category
    6. Update and return state
    
    Args:
        state: Graph state containing prediction_statement, verification_date
        
    Returns:
        Updated state with verifiable_category, category_reasoning
        
    Raises:
        Exception: If agent invocation or JSON parsing fails
    """
    # Build prompt from state
    prompt = f"""PREDICTION: {state['prediction_statement']}
VERIFICATION DATE: {state['verification_date']}

Categorize this prediction's verifiability.
"""
    
    # Create and invoke agent
    categorizer_agent = create_categorizer_agent()
    
    try:
        response = categorizer_agent(prompt)
        
        # Parse response (single json.loads call - Strands best practice)
        result = json.loads(str(response))
        
        # Validate category is in valid set
        category = result.get("verifiable_category", "human_verifiable_only")
        if category not in VALID_CATEGORIES:
            logger.warning(f"Invalid category '{category}', defaulting to human_verifiable_only")
            category = "human_verifiable_only"
            result["category_reasoning"] = f"Invalid category returned, defaulted to human_verifiable_only. Original: {result.get('category_reasoning', 'N/A')}"
        
        logger.info(f"Categorizer Agent classified as: {category}")
        logger.debug(f"Category reasoning: {result.get('category_reasoning', 'N/A')}")
        
        # Update and return state
        return {
            **state,
            "verifiable_category": category,
            "category_reasoning": result.get("category_reasoning", "Category determined by agent")
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {str(e)}")
        # Simple fallback - Strands best practice
        return {
            **state,
            "verifiable_category": "human_verifiable_only",
            "category_reasoning": "Fallback: Could not parse agent response",
            "error": f"Categorizer JSON decode error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Categorizer Agent failed: {str(e)}", exc_info=True)
        # Simple fallback
        return {
            **state,
            "verifiable_category": "human_verifiable_only",
            "category_reasoning": "Fallback: Agent invocation failed",
            "error": f"Categorizer Agent error: {str(e)}"
        }
