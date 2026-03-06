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

# NOTE: parser_node_function() was removed in v2 cleanup (Spec 1).
# It was leftover from a custom-node architecture where each agent had a
# node function that manually managed graph state (receive state → build
# prompt → invoke agent → parse JSON → update state). The graph now uses
# create_parser_agent() with the plain Agent pattern instead, where Strands
# Graph handles input propagation between nodes automatically.
# See: .kiro/specs/v2-cleanup-foundation/design.md, Component 1

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
    # Validate timezone first
    validated_timezone = timezone
    try:
        tz = pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning(f"Unknown timezone '{timezone}', falling back to UTC")
        validated_timezone = "UTC"
        tz = pytz.UTC
    
    # Get current time in the validated timezone for relative base
    now_in_tz = datetime.now(tz)
    
    # Parse with timezone awareness and relative base
    parsed_date = dateparser.parse(
        date_string, 
        settings={
            'TIMEZONE': validated_timezone,
            'RETURN_AS_TIMEZONE_AWARE': True,
            'RELATIVE_BASE': now_in_tz.replace(tzinfo=None),
            'PREFER_DATES_FROM': 'future'
        }
    )
    
    if parsed_date:
        # Convert to UTC and return ISO format
        utc_date = parsed_date.astimezone(pytz.UTC)
        return utc_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        # Default to 30 days in the future if parsing fails
        logger.warning(f"Could not parse '{date_string}', defaulting to 30 days from now")
        default_date = now_in_tz + timedelta(days=30)
        return default_date.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# PROMPT HARDENING NOTE: The "Return ONLY the raw JSON object" instruction is
# critical. Without it, Claude models often wrap JSON in ```json ``` markdown
# blocks, which breaks direct json.loads() parsing. The explicit negative
# instructions ("Do not wrap", "Do not include") work better than implicit
# positive ones ("Return JSON:"). This was the root cause of the 120-line
# extract_json_from_text() regex helper — fixed at the source now.
# See: .kiro/specs/v2-cleanup-foundation/design.md, Component 3, Step 1

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

Return ONLY the raw JSON object. Do not wrap in markdown code blocks. Do not include any text before or after the JSON.

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
    - Explicit model selection (Bedrock model ID)
    - Focused system prompt
    - Appropriate tools (current_time, parse_relative_date)
    
    Note: Strands Agent API does not accept 'name' parameter.
    Use model parameter with full Bedrock model ID.
    
    Returns:
        Configured Parser Agent
    """
    # Model: Claude Sonnet 4 (upgraded from 3.5 Sonnet v2 in Spec 1)
    # Why Sonnet 4: Better instruction following (critical for clean JSON output),
    # same Sonnet tier cost/latency, current Strands SDK default.
    # Why us. prefix: Cross-region inference — works in all US regions.
    # See: .kiro/specs/v2-cleanup-foundation/design.md, Component 3, Step 0
    agent = Agent(
        model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        tools=[current_time, parse_relative_date],
        system_prompt=PARSER_SYSTEM_PROMPT
    )
    
    logger.info("Parser Agent created with explicit model configuration")
    return agent



