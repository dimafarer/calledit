"""
Verifiability Analyzer - Analyzes agent responses for verifiability handling
"""

import json
import re

def analyze_verifiability_response(response_text, expected_category):
    """
    Analyze agent response for verifiability handling quality.
    
    Args:
        response_text (str): Raw agent response
        expected_category (str): Expected verifiability category
        
    Returns:
        dict: Analysis results
    """
    
    # Parse JSON response
    try:
        if response_text.startswith('```json'):
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                parsed = json.loads(json_match.group(1))
            else:
                parsed = json.loads(response_text)
        else:
            parsed = json.loads(response_text)
    except json.JSONDecodeError:
        return {
            "parsed_successfully": False,
            "category_recognition": 0,
            "verification_method_quality": 0,
            "tool_awareness": 0,
            "limitation_recognition": 0,
            "overall_score": 0,
            "issues": ["Failed to parse JSON response"]
        }
    
    # Extract key fields
    verification_method = parsed.get("verification_method", {})
    sources = verification_method.get("source", [])
    criteria = verification_method.get("criteria", [])
    steps = verification_method.get("steps", [])
    
    # Convert to strings for analysis
    sources_text = " ".join([str(s) for s in sources]).lower()
    criteria_text = " ".join([str(c) for c in criteria]).lower()
    steps_text = " ".join([str(s) for s in steps]).lower()
    all_text = f"{sources_text} {criteria_text} {steps_text}"
    
    analysis = {
        "parsed_successfully": True,
        "verification_sources": sources,
        "verification_criteria": criteria,
        "verification_steps": steps,
        "issues": []
    }
    
    # Analyze category recognition
    category_score = analyze_category_recognition(all_text, expected_category)
    analysis["category_recognition"] = category_score
    
    # Analyze verification method quality
    method_score = analyze_verification_method_quality(verification_method, expected_category)
    analysis["verification_method_quality"] = method_score
    
    # Analyze tool awareness
    tool_score = analyze_tool_awareness(all_text, expected_category)
    analysis["tool_awareness"] = tool_score
    
    # Analyze limitation recognition
    limitation_score = analyze_limitation_recognition(all_text, expected_category)
    analysis["limitation_recognition"] = limitation_score
    
    # Calculate overall score
    analysis["overall_score"] = (category_score + method_score + tool_score + limitation_score) / 4
    
    return analysis

def analyze_category_recognition(text, expected_category):
    """Analyze if agent recognizes the verifiability category."""
    
    if expected_category == "self_verifiable":
        # Look for indicators of human verification needs
        human_indicators = ["personal", "direct", "individual", "self", "human", "observation", "confirmation"]
        score = sum(1 for indicator in human_indicators if indicator in text)
        return min(score / 3, 1.0)  # Max score of 1.0
        
    elif expected_category == "tool_verifiable":
        # Look for indicators of API/automation possibilities
        api_indicators = ["api", "data", "service", "monitor", "track", "automated", "system"]
        score = sum(1 for indicator in api_indicators if indicator in text)
        return min(score / 3, 1.0)
        
    elif expected_category == "backlog_verifiable":
        # Look for indicators of complex verification needs
        complex_indicators = ["news", "monitor", "aggregate", "complex", "multiple", "sources"]
        score = sum(1 for indicator in complex_indicators if indicator in text)
        return min(score / 3, 1.0)
    
    return 0.0

def analyze_verification_method_quality(verification_method, expected_category):
    """Analyze quality of suggested verification methods."""
    
    sources = verification_method.get("source", [])
    criteria = verification_method.get("criteria", [])
    steps = verification_method.get("steps", [])
    
    # Basic quality checks
    has_sources = len(sources) > 0
    has_criteria = len(criteria) > 0
    has_steps = len(steps) > 0
    
    quality_score = 0
    if has_sources: quality_score += 0.3
    if has_criteria: quality_score += 0.3
    if has_steps: quality_score += 0.4
    
    # Category-specific quality assessment
    if expected_category == "self_verifiable":
        # Should emphasize human verification
        human_sources = any("personal" in str(s).lower() or "direct" in str(s).lower() for s in sources)
        if human_sources: quality_score += 0.2
        
    elif expected_category == "tool_verifiable":
        # Should suggest specific APIs or data sources
        api_sources = any("api" in str(s).lower() or "service" in str(s).lower() for s in sources)
        if api_sources: quality_score += 0.2
        
    elif expected_category == "backlog_verifiable":
        # Should acknowledge complexity
        complex_steps = any("monitor" in str(s).lower() or "aggregate" in str(s).lower() for s in steps)
        if complex_steps: quality_score += 0.2
    
    return min(quality_score, 1.0)

def analyze_tool_awareness(text, expected_category):
    """Analyze agent's awareness of tool development possibilities."""
    
    if expected_category == "tool_verifiable":
        # Should suggest specific tools or APIs
        tool_mentions = ["api", "integration", "service", "tool", "automated"]
        score = sum(1 for mention in tool_mentions if mention in text)
        return min(score / 2, 1.0)
        
    elif expected_category == "backlog_verifiable":
        # Should acknowledge tool development complexity
        complexity_mentions = ["complex", "development", "multiple sources", "aggregation"]
        score = sum(1 for mention in complexity_mentions if mention in text)
        return min(score / 2, 1.0)
        
    elif expected_category == "self_verifiable":
        # Should recognize automation limitations
        limitation_mentions = ["human", "personal", "direct", "manual"]
        score = sum(1 for mention in limitation_mentions if mention in text)
        return min(score / 2, 1.0)
    
    return 0.0

def analyze_limitation_recognition(text, expected_category):
    """Analyze if agent recognizes verification limitations."""
    
    if expected_category == "self_verifiable":
        # Should acknowledge need for human verification
        human_need = any(phrase in text for phrase in ["human", "personal", "direct observation", "individual"])
        return 1.0 if human_need else 0.0
        
    elif expected_category == "backlog_verifiable":
        # Should acknowledge complexity or development needs
        complexity_ack = any(phrase in text for phrase in ["complex", "multiple", "development", "challenging"])
        return 1.0 if complexity_ack else 0.0
        
    elif expected_category == "tool_verifiable":
        # Should suggest realistic automation
        automation_realism = any(phrase in text for phrase in ["api", "service", "data", "automated"])
        return 1.0 if automation_realism else 0.0
    
    return 0.0

def score_verifiability_test(analysis_result):
    """
    Generate overall test score and grade.
    
    Args:
        analysis_result (dict): Analysis results
        
    Returns:
        dict: Test score and details
    """
    
    if not analysis_result["parsed_successfully"]:
        return {
            "score": 0,
            "max_score": 4,
            "percentage": 0,
            "grade": "F",
            "details": ["JSON parsing failed"],
            "category": "Parse Error"
        }
    
    # Calculate weighted score
    weights = {
        "category_recognition": 0.3,
        "verification_method_quality": 0.3,
        "tool_awareness": 0.2,
        "limitation_recognition": 0.2
    }
    
    weighted_score = sum(analysis_result[key] * weight for key, weight in weights.items())
    percentage = weighted_score * 100
    
    # Assign grade
    if percentage >= 90: grade = "A"
    elif percentage >= 80: grade = "B"
    elif percentage >= 70: grade = "C"
    elif percentage >= 60: grade = "D"
    else: grade = "F"
    
    details = []
    if analysis_result["category_recognition"] >= 0.8:
        details.append("✅ Good category recognition")
    else:
        details.append("❌ Poor category recognition")
        
    if analysis_result["verification_method_quality"] >= 0.8:
        details.append("✅ Quality verification methods")
    else:
        details.append("❌ Weak verification methods")
    
    return {
        "score": weighted_score,
        "max_score": 1.0,
        "percentage": percentage,
        "grade": grade,
        "details": details,
        "category_scores": {
            "category_recognition": analysis_result["category_recognition"],
            "verification_method_quality": analysis_result["verification_method_quality"],
            "tool_awareness": analysis_result["tool_awareness"],
            "limitation_recognition": analysis_result["limitation_recognition"]
        }
    }