"""
Result Parser - Extracts and analyzes key fields from agent responses
"""

import json
import re
from datetime import datetime

def parse_agent_response(response_text):
    """
    Parse agent response and extract key fields.
    
    Args:
        response_text (str): Raw agent response
        
    Returns:
        dict: Parsed response with extracted fields
    """
    try:
        # Try to parse as direct JSON
        parsed = json.loads(response_text)
        return {
            "parsed_successfully": True,
            "verification_date": parsed.get("verification_date"),
            "date_reasoning": parsed.get("date_reasoning"),
            "prediction_statement": parsed.get("prediction_statement"),
            "initial_status": parsed.get("initial_status"),
            "verification_method": parsed.get("verification_method", {}),
            "raw_response": response_text
        }
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                return {
                    "parsed_successfully": True,
                    "verification_date": parsed.get("verification_date"),
                    "date_reasoning": parsed.get("date_reasoning"),
                    "prediction_statement": parsed.get("prediction_statement"),
                    "initial_status": parsed.get("initial_status"),
                    "verification_method": parsed.get("verification_method", {}),
                    "raw_response": response_text
                }
            except json.JSONDecodeError:
                pass
        
        # If JSON parsing fails, return raw response
        return {
            "parsed_successfully": False,
            "verification_date": None,
            "date_reasoning": None,
            "prediction_statement": None,
            "initial_status": None,
            "verification_method": {},
            "raw_response": response_text,
            "parse_error": "Could not extract JSON from response"
        }

def analyze_time_handling(parsed_response):
    """
    Analyze time handling in the parsed response.
    
    Args:
        parsed_response (dict): Parsed agent response
        
    Returns:
        dict: Analysis of time handling
    """
    issues = []
    verification_date = parsed_response.get("verification_date")
    date_reasoning = parsed_response.get("date_reasoning", "")
    
    # Check for UTC references (should be none)
    if "UTC" in date_reasoning or "utc" in date_reasoning.lower():
        issues.append("Contains UTC references in reasoning")
    
    # Check verification date format
    if verification_date:
        # Should be in format: YYYY-MM-DD HH:MM:SS
        if not re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', verification_date):
            issues.append(f"Verification date format incorrect: {verification_date}")
        
        # Check if time is in 24-hour format
        time_part = verification_date.split(' ')[-1] if ' ' in verification_date else ""
        if time_part:
            hour = int(time_part.split(':')[0]) if ':' in time_part else 0
            if hour > 23:
                issues.append("Hour value exceeds 24-hour format")
    else:
        issues.append("No verification date provided")
    
    # Check for 12-hour to 24-hour conversion mention
    has_conversion_reasoning = any(phrase in date_reasoning.lower() for phrase in [
        "24-hour", "24 hour", "convert", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00"
    ])
    
    return {
        "issues": issues,
        "has_conversion_reasoning": has_conversion_reasoning,
        "verification_date_format": "valid" if verification_date and not any("format" in issue for issue in issues) else "invalid",
        "timezone_handling": "good" if not any("UTC" in issue for issue in issues) else "poor"
    }

def score_test_result(parsed_response, analysis):
    """
    Score the test result based on parsing and analysis.
    
    Args:
        parsed_response (dict): Parsed agent response
        analysis (dict): Time handling analysis
        
    Returns:
        dict: Test score and details
    """
    score = 0
    max_score = 5
    details = []
    
    # JSON parsing (1 point)
    if parsed_response["parsed_successfully"]:
        score += 1
        details.append("✅ JSON parsed successfully")
    else:
        details.append("❌ JSON parsing failed")
    
    # Verification date present (1 point)
    if parsed_response["verification_date"]:
        score += 1
        details.append("✅ Verification date provided")
    else:
        details.append("❌ No verification date")
    
    # Date reasoning present (1 point)
    if parsed_response["date_reasoning"]:
        score += 1
        details.append("✅ Date reasoning provided")
    else:
        details.append("❌ No date reasoning")
    
    # Good timezone handling (1 point)
    if analysis["timezone_handling"] == "good":
        score += 1
        details.append("✅ Good timezone handling (no UTC refs)")
    else:
        details.append("❌ Poor timezone handling (UTC references)")
    
    # Valid date format (1 point)
    if analysis["verification_date_format"] == "valid":
        score += 1
        details.append("✅ Valid verification date format")
    else:
        details.append("❌ Invalid verification date format")
    
    return {
        "score": score,
        "max_score": max_score,
        "percentage": (score / max_score) * 100,
        "grade": "A" if score >= 4 else "B" if score >= 3 else "C" if score >= 2 else "F",
        "details": details,
        "issues": analysis["issues"]
    }