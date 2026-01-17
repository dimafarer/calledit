"""
Parser Agent for Prediction Verification System

This agent extracts the user's exact prediction statement and parses temporal
references. It's the first agent in the graph workflow.

Following Strands best practices:
- Single responsibility (parsing only)
- Focused system prompt (~25 lines)
- Explicit agent name and model
- Uses tools for date parsing
"""

import logging
from datetime import datetime, timedelta
import dateparser
import pytz
from strands import Agent, tool
from strands_tools import current_time

logger = logging.getLogger(__name__)


@tool
def parse_relative_date(date_string: str, timezone: str = "UTC") -> str:
    """
    Convert a relative date string to an actual datetime.
    
    This tool is used by the Parser Agent to convert user's time references
    (like "3:00pm", "tomorrow", "next week") into concrete datetimes.
    
    Args:
        date_string: A relative date/time string like 'tomorrow', '3:00pm today', 'next week'
        timezone: Timezone to use for parsing relative dates (default: UTC)
        
    Returns:
        The parsed datetime in UTC ISO format (YYYY-MM-DDTHH:MM:SSZ)
        
    Example:
        >>> parse_relative_date("3:00pm today", "America/New_York")
        "2025-01-16T20:00:00Z"  # 3pm EST = 8pm UTC
    """
    try:
        tz = pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning(f"Unknown timezone '{timezone}', falling back to UTC")
        tz = pytz.UTC
    
    # Parse with timezone awareness
    parsed_date = dateparser.parse(
        date_string, 
        settings={'TIMEZONE': timezone, 'RETURN_AS_TIMEZONE_AWARE': True}
    )
    
    if parsed_date:
        # Convert to UTC and return ISO format
        utc_date = parsed_date.astimezone(pytz.UTC)
        return utc_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        # Default to 30 days in the future if parsing fails
        logger.warning(f"Could not parse '{date_string}', defaulting to 30 days from now")
        default_date = datetime.now(tz) + timedelta(days=30)
        return default_date.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# Parser Agent System Prompt (focused, ~25 lines)
PARSER_SYSTEM_PROMPT = """You are a prediction parser. Your task:
1. Extract the user's EXACT prediction statement (no modifications)
2. Parse time references using parse_relative_date tool
3. Convert 12-hour to 24-hour format (3:00pm → 15:00)
4. Work in user's local timezone

TIME CONVERSIONS:
- "3:00pm" → "15:00" (24-hour format)
- "this morning" → "09:00" (typical morning time)
- "this afternoon" → "15:00" (mid-afternoon)
- "this evening" → "19:00" (early evening)
- "tonight" → "22:00" (late evening)

IMPORTANT: Preserve the user's exact prediction text. Do not rephrase or add details.

Return JSON:
{
    "prediction_statement": "exact user text",
    "verification_date": "YYYY-MM-DD HH:MM:SS",
    "date_reasoning": "explanation of time parsing and conversion"
}
"""


def create_parser_agent() -> Agent:
    """
    Create the Parser Agent with explicit configuration.
    
    Following Strands best practices:
    - Explicit agent name for debugging
    - Explicit model selection
    - Focused system prompt
    - Appropriate tools (current_time, parse_relative_date)
    
    Returns:
        Configured Parser Agent
    """
    agent = Agent(
        name="parser_agent",
        model="claude-3-5-sonnet-20241022",
        tools=[current_time, parse_relative_date],
        system_prompt=PARSER_SYSTEM_PROMPT
    )
    
    logger.info("Parser Agent created with explicit configuration")
    return agent



def parser_node_function(state: dict) -> dict:
    """
    Parser node function for the prediction verification graph.
    
    This function follows the Strands graph node pattern:
    1. Receive state from previous node (or initial state)
    2. Build prompt from state
    3. Invoke agent
    4. Parse response (single json.loads call)
    5. Update and return state
    
    Args:
        state: Graph state containing user_prompt, user_timezone, current_datetime_local
        
    Returns:
        Updated state with prediction_statement, verification_date, date_reasoning
        
    Raises:
        Exception: If agent invocation or JSON parsing fails
    """
    import json
    
    # Build prompt from state
    prompt = f"""PREDICTION: {state['user_prompt']}
CURRENT DATE: {state['current_datetime_local']}
TIMEZONE: {state['user_timezone']}

Extract the prediction and parse the verification date.
"""
    
    # Create and invoke agent
    parser_agent = create_parser_agent()
    
    try:
        response = parser_agent(prompt)
        
        # Parse response (single json.loads call - Strands best practice)
        result = json.loads(str(response))
        
        logger.info(f"Parser Agent successfully processed prediction")
        logger.debug(f"Parsed result: {json.dumps(result, indent=2)}")
        
        # Update and return state
        return {
            **state,
            "prediction_statement": result["prediction_statement"],
            "verification_date": result["verification_date"],
            "date_reasoning": result["date_reasoning"]
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {str(e)}")
        # Simple fallback - Strands best practice
        return {
            **state,
            "prediction_statement": state['user_prompt'],
            "verification_date": state['current_datetime_local'],
            "date_reasoning": "Fallback: Could not parse agent response",
            "error": f"Parser JSON decode error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Parser Agent failed: {str(e)}", exc_info=True)
        # Simple fallback
        return {
            **state,
            "prediction_statement": state['user_prompt'],
            "verification_date": state['current_datetime_local'],
            "date_reasoning": "Fallback: Agent invocation failed",
            "error": f"Parser Agent error: {str(e)}"
        }
