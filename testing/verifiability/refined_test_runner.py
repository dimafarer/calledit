#!/usr/bin/env python3
"""
Refined Verifiability Test Runner - Tests CalledIt agent with 5-category verifiability framework
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Import from automation directory
sys.path.append(str(Path(__file__).parent.parent / "automation"))
from agent_factory import create_calledit_agent, create_test_context

def load_refined_test_cases():
    """Load refined verifiability test cases from JSON file."""
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

def analyze_refined_response(response_text, category, test_case):
    """
    Analyze agent response for refined verifiability handling.
    
    Args:
        response_text (str): Raw agent response
        category (str): Verifiability category
        test_case (dict): Test case data
        
    Returns:
        dict: Analysis results
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
            "parsed_successfully": False,
            "category_appropriateness": 0,
            "verification_realism": 0,
            "tool_awareness": 0,
            "overall_score": 0,
            "issues": ["Failed to parse JSON response"]
        }
    
    # Extract verification method
    verification_method = parsed.get("verification_method", {})
    sources = verification_method.get("source", [])
    steps = verification_method.get("steps", [])
    
    # Convert to text for analysis
    all_text = " ".join([str(s) for s in sources + steps]).lower()
    
    # Category-specific analysis
    analysis = {
        "parsed_successfully": True,
        "verification_sources": sources,
        "verification_steps": steps,
        "issues": []
    }
    
    # Analyze based on category
    if category == "agent_verifiable":
        # Should not suggest external tools or APIs
        tool_mentions = sum(1 for word in ["api", "tool", "service", "external"] if word in all_text)
        analysis["category_appropriateness"] = max(0, 1.0 - (tool_mentions * 0.3))
        analysis["verification_realism"] = 1.0 if "reasoning" in all_text or "knowledge" in all_text else 0.5
        analysis["tool_awareness"] = 1.0 if tool_mentions == 0 else 0.0
        
    elif category == "current_tool_verifiable":
        # Should mention current_time tool
        time_tool_mentioned = "current_time" in all_text or "time" in all_text
        analysis["category_appropriateness"] = 1.0 if time_tool_mentioned else 0.3
        analysis["verification_realism"] = 1.0 if time_tool_mentioned else 0.5
        analysis["tool_awareness"] = 1.0 if time_tool_mentioned else 0.0
        
    elif category == "strands_tool_verifiable":
        # Should suggest realistic tools/APIs
        api_mentions = sum(1 for word in ["api", "service", "data", "tool"] if word in all_text)
        analysis["category_appropriateness"] = min(api_mentions * 0.4, 1.0)
        analysis["verification_realism"] = 1.0 if api_mentions > 0 else 0.3
        analysis["tool_awareness"] = min(api_mentions * 0.5, 1.0)
        
    elif category == "api_tool_verifiable":
        # Should suggest specific APIs or integrations
        api_mentions = sum(1 for word in ["api", "service", "integration", "query"] if word in all_text)
        analysis["category_appropriateness"] = min(api_mentions * 0.3, 1.0)
        analysis["verification_realism"] = 1.0 if api_mentions > 1 else 0.5
        analysis["tool_awareness"] = min(api_mentions * 0.4, 1.0)
        
    elif category == "human_verifiable_only":
        # Should emphasize human verification
        human_mentions = sum(1 for word in ["human", "personal", "direct", "observation", "manual"] if word in all_text)
        analysis["category_appropriateness"] = min(human_mentions * 0.4, 1.0)
        analysis["verification_realism"] = 1.0 if human_mentions > 0 else 0.3
        analysis["tool_awareness"] = 1.0 if human_mentions > 0 else 0.0
    
    # Calculate overall score
    analysis["overall_score"] = (
        analysis["category_appropriateness"] * 0.4 +
        analysis["verification_realism"] * 0.4 +
        analysis["tool_awareness"] * 0.2
    )
    
    return analysis

def run_refined_test(agent, test_case, context_template, category):
    """Run a single refined verifiability test."""
    prediction = test_case["prediction"]
    test_id = test_case["id"]
    
    full_prompt = context_template.format(prompt=prediction)
    print(f"Running Test {test_id} ({category}): {prediction}")
    
    try:
        result = agent(full_prompt)
        response_text = str(result)
        
        return {
            "test_id": test_id,
            "prediction": prediction,
            "category": category,
            "verification_approach": test_case.get("verification_approach", ""),
            "agent_response": response_text,
            "success": True,
            "error": None
        }
        
    except Exception as e:
        return {
            "test_id": test_id,
            "prediction": prediction,
            "category": category,
            "verification_approach": test_case.get("verification_approach", ""),
            "agent_response": None,
            "success": False,
            "error": str(e)
        }

def main():
    """Main refined verifiability test runner."""
    print("🚀 Starting Refined Verifiability Testing (5 Categories)")
    print("=" * 60)
    
    # Load test cases
    test_data = load_refined_test_cases()
    
    # Create agent and context
    agent = create_calledit_agent()
    context_template = create_test_context("America/New_York")
    
    # Run tests for each category (2 examples each for initial test)
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
        
        # Test first 2 examples from each category
        for test_case in category_data[:2]:
            result = run_refined_test(agent, test_case, context_template, category_key)
            all_results.append(result)
            
            import time
            time.sleep(0.5)
    
    # Analyze results
    print("\n" + "=" * 60)
    print("📊 ANALYZING REFINED RESULTS")
    print("=" * 60)
    
    analyzed_results = []
    
    for result in all_results:
        if result['success']:
            analysis = analyze_refined_response(result['agent_response'], result['category'], result)
            analyzed_results.append({
                **result,
                "analysis": analysis
            })
        else:
            analyzed_results.append({
                **result,
                "analysis": {"overall_score": 0, "issues": [result['error']]}
            })
    
    # Display results by category
    for category_key, category_name in categories:
        category_results = [r for r in analyzed_results if r['category'] == category_key]
        if not category_results:
            continue
            
        print(f"\n{category_name} Results:")
        print("-" * 40)
        
        category_scores = []
        for result in category_results:
            print(f"\n📝 Test {result['test_id']}: {result['prediction']}")
            print(f"Expected: {result['verification_approach']}")
            print(f"Success: {'✅' if result['success'] else '❌'}")
            
            if result['success'] and result['analysis']['parsed_successfully']:
                score = result['analysis']['overall_score']
                category_scores.append(score)
                print(f"Score: {score:.2f}/1.0 ({score*100:.0f}%)")
                print(f"Category Appropriateness: {result['analysis']['category_appropriateness']:.2f}")
                print(f"Verification Realism: {result['analysis']['verification_realism']:.2f}")
                print(f"Tool Awareness: {result['analysis']['tool_awareness']:.2f}")
            else:
                category_scores.append(0)
                print("Score: 0.00/1.0 (0%) - Failed")
            
            print("-" * 30)
        
        # Category summary
        if category_scores:
            avg_score = sum(category_scores) / len(category_scores)
            print(f"📈 {category_name} Average: {avg_score:.2f}/1.0 ({avg_score*100:.0f}%)")
    
    # Overall summary
    successful_tests = sum(1 for r in analyzed_results if r['success'])
    all_scores = [r['analysis']['overall_score'] for r in analyzed_results if r['success'] and r['analysis'].get('overall_score', 0) > 0]
    overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0
    
    print(f"\n📈 REFINED FRAMEWORK TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {len(analyzed_results)} (2 from each category)")
    print(f"Successful: {successful_tests}/{len(analyzed_results)}")
    print(f"Overall Average Score: {overall_avg:.2f}/1.0 ({overall_avg*100:.0f}%)")
    
    print("\n" + "=" * 60)
    print("✅ REFINED FRAMEWORK TESTING COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()