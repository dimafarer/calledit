#!/usr/bin/env python3
"""
Full Category Test - Test all 25 predictions and recommend category changes
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Import from automation directory
sys.path.append(str(Path(__file__).parent.parent / "automation"))
from agent_factory import create_calledit_agent, create_test_context

def load_all_test_cases():
    """Load all refined verifiability test cases."""
    test_file = Path(__file__).parent.parent / "refined_verifiability_categories.json"
    
    try:
        with open(test_file, 'r') as f:
            data = json.load(f)
            return data["refined_verifiability_categories"]
    except FileNotFoundError:
        print(f"Error: Test file not found at {test_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in test file: {e}")
        sys.exit(1)

def analyze_category_fit(response_text, current_category, test_case):
    """
    Analyze if the agent's response suggests the prediction belongs in a different category.
    
    Returns:
        dict: Analysis with recommended category
    """
    
    # Parse JSON response
    try:
        if response_text.startswith('```json'):
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                parsed = json.loads(json_match.group(1))
            else:
                parsed = json.loads(response_text)
        else:
            parsed = json.loads(response_text)
    except json.JSONDecodeError:
        return {
            "recommended_category": current_category,
            "confidence": "low",
            "reasoning": "Could not parse JSON response",
            "category_fit": "unknown"
        }
    
    # Extract verification method
    verification_method = parsed.get("verification_method", {})
    sources = verification_method.get("source", [])
    steps = verification_method.get("steps", [])
    
    # Convert to text for analysis
    all_text = " ".join([str(s) for s in sources + steps]).lower()
    
    # Analyze what the agent suggests for verification
    analysis = {
        "mentions_current_time": "current_time" in all_text or "current time" in all_text,
        "mentions_apis": any(word in all_text for word in ["api", "service", "data feed", "integration"]),
        "mentions_external_tools": any(word in all_text for word in ["tool", "application", "software", "system"]),
        "mentions_human_verification": any(word in all_text for word in ["human", "personal", "direct", "observation", "manual", "individual"]),
        "mentions_pure_reasoning": any(word in all_text for word in ["calculation", "reasoning", "knowledge", "mathematical", "logical"]),
        "mentions_specific_apis": any(word in all_text for word in ["github", "reddit", "twitter", "flight", "weather", "bitcoin", "stock"])
    }
    
    # Determine recommended category based on agent's approach
    if analysis["mentions_pure_reasoning"] and not analysis["mentions_apis"] and not analysis["mentions_current_time"]:
        recommended = "agent_verifiable"
        confidence = "high"
        reasoning = "Agent suggests pure reasoning/knowledge verification"
        
    elif analysis["mentions_current_time"]:
        recommended = "current_tool_verifiable"
        confidence = "high"
        reasoning = "Agent specifically mentions current_time tool"
        
    elif analysis["mentions_specific_apis"] or (analysis["mentions_apis"] and not analysis["mentions_external_tools"]):
        if any(word in all_text for word in ["weather", "bitcoin", "stock", "currency"]):
            recommended = "strands_tool_verifiable"
            confidence = "medium"
            reasoning = "Agent suggests APIs that could be Strands tools"
        else:
            recommended = "api_tool_verifiable"
            confidence = "medium"
            reasoning = "Agent suggests specific external APIs"
            
    elif analysis["mentions_human_verification"] or any(word in all_text for word in ["subjective", "personal", "individual"]):
        recommended = "human_verifiable_only"
        confidence = "high"
        reasoning = "Agent emphasizes human verification needs"
        
    elif analysis["mentions_external_tools"] or analysis["mentions_apis"]:
        recommended = "api_tool_verifiable"
        confidence = "medium"
        reasoning = "Agent suggests external tools/APIs"
        
    else:
        recommended = current_category
        confidence = "low"
        reasoning = "Unclear verification approach suggested"
    
    # Determine category fit
    if recommended == current_category:
        category_fit = "correct"
    else:
        category_fit = "should_move"
    
    return {
        "recommended_category": recommended,
        "confidence": confidence,
        "reasoning": reasoning,
        "category_fit": category_fit,
        "analysis_details": analysis
    }

def run_full_test(agent, test_case, context_template, category):
    """Run a single test and analyze category fit."""
    prediction = test_case["prediction"]
    test_id = test_case["id"]
    
    full_prompt = context_template.format(prompt=prediction)
    print(f"Running Test {test_id} ({category}): {prediction}")
    
    try:
        result = agent(full_prompt)
        response_text = str(result)
        
        # Analyze category fit
        category_analysis = analyze_category_fit(response_text, category, test_case)
        
        return {
            "test_id": test_id,
            "prediction": prediction,
            "current_category": category,
            "verification_approach": test_case.get("verification_approach", ""),
            "agent_response": response_text[:500] + "..." if len(response_text) > 500 else response_text,
            "category_analysis": category_analysis,
            "success": True,
            "error": None
        }
        
    except Exception as e:
        return {
            "test_id": test_id,
            "prediction": prediction,
            "current_category": category,
            "verification_approach": test_case.get("verification_approach", ""),
            "agent_response": None,
            "category_analysis": {"recommended_category": category, "confidence": "low", "reasoning": f"Test failed: {e}", "category_fit": "unknown"},
            "success": False,
            "error": str(e)
        }

def main():
    """Main full category test runner."""
    print("🚀 Starting Full Category Analysis (All 25 Predictions)")
    print("=" * 70)
    
    # Load test cases
    test_data = load_all_test_cases()
    
    # Create agent and context
    agent = create_calledit_agent()
    context_template = create_test_context("America/New_York")
    
    # Run all tests
    all_results = []
    categories = [
        ("agent_verifiable", "🧠 Agent-Verifiable"),
        ("current_tool_verifiable", "⏰ Current-Tool-Verifiable"),
        ("strands_tool_verifiable", "🔧 Strands-Tool-Verifiable"),
        ("api_tool_verifiable", "🌐 API-Tool-Verifiable"),
        ("human_verifiable_only", "👤 Human-Verifiable-Only")
    ]
    
    for category_key, category_name in categories:
        print(f"\n{category_name}")
        category_data = test_data[category_key]["examples"]
        
        # Test all examples from each category
        for test_case in category_data:
            result = run_full_test(agent, test_case, context_template, category_key)
            all_results.append(result)
            
            import time
            time.sleep(0.3)  # Shorter delay for full test
    
    # Analyze results and recommendations
    print("\n" + "=" * 70)
    print("📊 CATEGORY ANALYSIS & RECOMMENDATIONS")
    print("=" * 70)
    
    recommendations = []
    
    for category_key, category_name in categories:
        category_results = [r for r in all_results if r['current_category'] == category_key]
        if not category_results:
            continue
            
        print(f"\n{category_name}:")
        print("-" * 50)
        
        for result in category_results:
            analysis = result['category_analysis']
            fit_icon = "✅" if analysis['category_fit'] == 'correct' else "🔄" if analysis['category_fit'] == 'should_move' else "❓"
            
            print(f"\n{fit_icon} Test {result['test_id']}: {result['prediction']}")
            print(f"   Current: {result['current_category']}")
            print(f"   Recommended: {analysis['recommended_category']} ({analysis['confidence']} confidence)")
            print(f"   Reasoning: {analysis['reasoning']}")
            
            if analysis['category_fit'] == 'should_move':
                recommendations.append({
                    "test_id": result['test_id'],
                    "prediction": result['prediction'],
                    "from_category": result['current_category'],
                    "to_category": analysis['recommended_category'],
                    "confidence": analysis['confidence'],
                    "reasoning": analysis['reasoning']
                })
    
    # Summary of recommendations
    print(f"\n📋 CATEGORY CHANGE RECOMMENDATIONS")
    print("=" * 70)
    
    if recommendations:
        for rec in recommendations:
            print(f"\n🔄 Test {rec['test_id']}: {rec['prediction']}")
            print(f"   Move from: {rec['from_category']} → {rec['to_category']}")
            print(f"   Confidence: {rec['confidence']}")
            print(f"   Reason: {rec['reasoning']}")
    else:
        print("✅ No category changes recommended - all predictions are well-categorized!")
    
    # Statistics
    successful_tests = sum(1 for r in all_results if r['success'])
    move_recommendations = len(recommendations)
    
    print(f"\n📈 FULL TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Run: {len(all_results)}")
    print(f"Successful: {successful_tests}/{len(all_results)}")
    print(f"Category Changes Recommended: {move_recommendations}")
    print(f"Well-Categorized: {len(all_results) - move_recommendations}")
    
    print("\n" + "=" * 70)
    print("✅ FULL CATEGORY ANALYSIS COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()