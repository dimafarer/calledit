"""
Timezone Analysis Tool - Custom Strands tool for analyzing timezone handling
"""

from strands import tool
import json
from datetime import datetime

@tool
def analyze_timezone_patterns(test_results: str) -> str:
    """
    Analyze timezone handling patterns across multiple test results.
    
    Args:
        test_results (str): JSON string containing test results
        
    Returns:
        str: Analysis of timezone patterns and issues
    """
    try:
        results = json.loads(test_results)
    except json.JSONDecodeError:
        return "Error: Could not parse test results JSON"
    
    analysis = {
        "total_tests": len(results),
        "successful_tests": 0,
        "timezone_issues": [],
        "time_format_issues": [],
        "business_context_handling": [],
        "cross_day_boundary_tests": [],
        "vague_time_interpretations": []
    }
    
    for result in results:
        if result.get('success'):
            analysis["successful_tests"] += 1
            
            parsed = result.get('parsed', {})
            verification_date = parsed.get('verification_date', '')
            date_reasoning = parsed.get('date_reasoning', '')
            prompt = result.get('prompt', '')
            
            # Check for timezone issues
            if 'UTC' in date_reasoning or 'utc' in date_reasoning.lower():
                analysis["timezone_issues"].append({
                    "test_id": result.get('test_id'),
                    "issue": "Contains UTC references",
                    "prompt": prompt
                })
            
            # Check time format
            if verification_date and ':' in verification_date:
                time_part = verification_date.split(' ')[-1]
                if time_part and ':' in time_part:
                    hour = int(time_part.split(':')[0])
                    if hour > 23:
                        analysis["time_format_issues"].append({
                            "test_id": result.get('test_id'),
                            "issue": f"Invalid hour: {hour}",
                            "verification_date": verification_date
                        })
            
            # Identify business context tests
            business_keywords = ['market', 'business', 'lunch', 'rush']
            if any(keyword in prompt.lower() for keyword in business_keywords):
                analysis["business_context_handling"].append({
                    "test_id": result.get('test_id'),
                    "prompt": prompt,
                    "verification_time": verification_date,
                    "reasoning_quality": "good" if len(date_reasoning) > 100 else "brief"
                })
            
            # Identify cross-day boundary tests
            cross_day_keywords = ['tomorrow', 'midnight', 'next', 'week']
            if any(keyword in prompt.lower() for keyword in cross_day_keywords):
                analysis["cross_day_boundary_tests"].append({
                    "test_id": result.get('test_id'),
                    "prompt": prompt,
                    "verification_date": verification_date
                })
            
            # Identify vague time interpretations
            vague_keywords = ['morning', 'evening', 'afternoon', 'rush']
            if any(keyword in prompt.lower() for keyword in vague_keywords):
                analysis["vague_time_interpretations"].append({
                    "test_id": result.get('test_id'),
                    "prompt": prompt,
                    "interpretation": verification_date,
                    "reasoning": date_reasoning[:200] + "..." if len(date_reasoning) > 200 else date_reasoning
                })
    
    return json.dumps(analysis, indent=2)

@tool
def suggest_additional_edge_cases(current_test_results: str) -> str:
    """
    Suggest additional edge cases based on current test coverage.
    
    Args:
        current_test_results (str): JSON string of current test results
        
    Returns:
        str: Suggested additional test cases
    """
    suggestions = [
        {
            "category": "International Timezone Handling",
            "test_case": "The London market will close at 4:30 PM GMT",
            "challenge": "Tests handling of explicit timezone references"
        },
        {
            "category": "Daylight Saving Time",
            "test_case": "The meeting is scheduled for 2:30 AM on the night we spring forward",
            "challenge": "Tests DST transition edge case"
        },
        {
            "category": "Multiple Time References",
            "test_case": "The event starts at 9 AM and ends by 5 PM today",
            "challenge": "Tests handling of multiple time points in one prediction"
        },
        {
            "category": "Relative Time with Context",
            "test_case": "The package will arrive in 2 hours",
            "challenge": "Tests relative time calculation from current moment"
        },
        {
            "category": "Weekend/Holiday Boundaries",
            "test_case": "The office will be closed on the next business day",
            "challenge": "Tests business day calculation with weekends/holidays"
        }
    ]
    
    return json.dumps(suggestions, indent=2)