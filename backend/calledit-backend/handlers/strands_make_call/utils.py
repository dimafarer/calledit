"""
Utility Functions for Prediction Verification System

This module provides shared utility functions for timezone handling,
logging configuration, and common operations used across the graph.

Following Strands best practices:
- Structured logging
- Clear error handling
- Reusable utility functions
"""

import logging
from datetime import datetime, timezone
import pytz
from typing import Tuple, Optional


# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure logging for the prediction verification system.
    
    Args:
        level: Logging level (default: INFO)
    """
    logging.basicConfig(
        format="%(levelname)s | %(name)s | %(message)s",
        level=level
    )


def get_current_datetime_in_timezones(user_timezone: str) -> Tuple[str, str, str, str]:
    """
    Get current datetime in both UTC and user's local timezone.
    
    This function handles timezone conversion and provides formatted strings
    for both UTC and local time, which are used throughout the graph.
    
    Args:
        user_timezone: User's timezone string (e.g., "America/New_York")
        
    Returns:
        Tuple of (formatted_date_utc, formatted_datetime_utc, 
                  formatted_date_local, formatted_datetime_local)
        
    Example:
        >>> get_current_datetime_in_timezones("America/New_York")
        ("2025-01-16", "2025-01-16 12:00:00 UTC", 
         "2025-01-16", "2025-01-16 07:00:00 EST")
    """
    # Get current time in UTC
    current_datetime_utc = datetime.now(timezone.utc)
    formatted_date_utc = current_datetime_utc.strftime("%Y-%m-%d")
    formatted_datetime_utc = current_datetime_utc.strftime("%Y-%m-%d %H:%M:%S %Z")
    
    # Convert to user's local timezone
    try:
        local_tz = pytz.timezone(user_timezone)
        current_datetime_local = current_datetime_utc.astimezone(local_tz)
        formatted_date_local = current_datetime_local.strftime("%Y-%m-%d")
        formatted_datetime_local = current_datetime_local.strftime("%Y-%m-%d %H:%M:%S %Z")
    except pytz.exceptions.UnknownTimeZoneError:
        # Fallback to UTC if timezone is invalid
        logger.warning(f"Invalid timezone '{user_timezone}', falling back to UTC")
        formatted_date_local = formatted_date_utc
        formatted_datetime_local = formatted_datetime_utc
    
    return (
        formatted_date_utc,
        formatted_datetime_utc,
        formatted_date_local,
        formatted_datetime_local
    )


def convert_local_to_utc(
    local_datetime_str: str,
    user_timezone: str,
    format_str: str = "%Y-%m-%d %H:%M:%S"
) -> Optional[str]:
    """
    Convert a local datetime string to UTC ISO format.
    
    This is used to convert verification dates from user's local time
    to UTC for storage in the database.
    
    Args:
        local_datetime_str: Local datetime string
        user_timezone: User's timezone string
        format_str: Format of the input datetime string
        
    Returns:
        UTC datetime in ISO format (YYYY-MM-DDTHH:MM:SSZ) or None if conversion fails
        
    Example:
        >>> convert_local_to_utc("2025-01-16 15:00:00", "America/New_York")
        "2025-01-16T20:00:00Z"
    """
    try:
        # Parse local datetime
        if "T" in local_datetime_str:
            # ISO format: 2025-06-27T15:00:00
            local_dt = datetime.fromisoformat(local_datetime_str.replace("Z", ""))
        else:
            # Simple format: 2025-06-27 15:00:00
            local_dt = datetime.strptime(local_datetime_str, format_str)
        
        # Localize to user's timezone
        local_tz = pytz.timezone(user_timezone)
        localized_dt = local_tz.localize(local_dt)
        
        # Convert to UTC
        utc_dt = localized_dt.astimezone(pytz.UTC)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        
    except Exception as e:
        logger.error(f"Error converting datetime: {e}")
        return None


def ensure_list(value: any) -> list:
    """
    Ensure a value is always a list of strings.
    
    This helper function is used to normalize verification method fields
    (source, criteria, steps) which should always be lists.
    
    Args:
        value: Value to convert to list
        
    Returns:
        List of strings
        
    Example:
        >>> ensure_list("single value")
        ["single value"]
        >>> ensure_list(["value1", "value2"])
        ["value1", "value2"]
        >>> ensure_list(None)
        []
    """
    if isinstance(value, str):
        return [value]
    elif isinstance(value, list):
        return [str(item) if not isinstance(item, dict) else str(item) for item in value]
    elif value is None:
        return []
    else:
        return [str(value)]


def validate_verifiable_category(category: str) -> str:
    """
    Validate and normalize verifiability category.
    
    Ensures the category is one of the 5 valid categories. Falls back to
    'human_verifiable_only' if invalid.
    
    Args:
        category: Category string to validate
        
    Returns:
        Valid category string
    """
    valid_categories = {
        "agent_verifiable",
        "current_tool_verifiable",
        "strands_tool_verifiable",
        "api_tool_verifiable",
        "human_verifiable_only"
    }
    
    if category in valid_categories:
        return category
    
    logger.warning(f"Invalid category '{category}', defaulting to human_verifiable_only")
    return "human_verifiable_only"
