#!/usr/bin/env python3
"""
Verifiability Test Runner - Tests CalledIt agent with verifiability predictions
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Import from automation directory
sys.path.append(str(Path(__file__).parent.parent / "automation"))
from agent_factory import create_calledit_agent, create_test_context
from verifiability_analyzer import analyze_verifiability_response, score_verifiability_test

def load_verifiability_test_cases():
    """Load verifiability test cases from JSON file."""
    test_file = Path(__file__).parent.parent / "prediction_verifiability_tests.json"
    
    try:
        with open(test_file, 'r') as f:
            data = json.load(f)
            return data["prediction_verifiability_tests"]
    except FileNotFoundError:
        print(f"Error: Test file not found at {test_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in test file: {e}")
        sys.exit(1)

def run_single_verifiability_test(agent, test_case, context_template, category):
    """
    Run a single verifiability test case against the agent.
    
    Args:
        agent: CalledIt agent instance
        test_case: Test case dictionary
        context_template: Context template string
        category: Verifiability category (self_verifiable, tool_verifiable, backlog_verifiable)
        
    Returns:
        dict: Test result with response and metadata
    """
    prediction = test_case["prediction"]
    test_id = test_case["id"]
    
    # Create full prompt with context
    full_prompt = context_template.format(prompt=prediction)
    
    print(f"Running Test {test_id} ({category}): {prediction}")
    
    try:
        # Call the agent directly
        result = agent(full_prompt)
        
        # Extract response text
        response_text = str(result)
        
        return {
            "test_id": test_id,
            "prediction": prediction,
            "category": category,
            "challenge": test_case["challenge"],
            "verification_method": test_case.get("verification_method", ""),
            "agent_response": response_text,
            "success": True,
            "error": None
        }
        
    except Exception as e:
        return {
            "test_id": test_id,
            "prediction": prediction,
            "category": category,
            "challenge": test_case["challenge"],
            "verification_method": test_case.get("verification_method", ""),
            "agent_response": None,
            "success": False,
            "error": str(e)
        }

def main():
    """Main verifiability test runner function."""
    print("🚀 Starting CalledIt Agent Verifiability Testing")
    print("=" * 60)
    
    # Load test cases
    test_data = load_verifiability_test_cases()
    
    # Count total tests
    total_tests = (len(test_data["self_verifiable"]) + 
                  len(test_data["tool_verifiable"]) + 
                  len(test_data["backlog_verifiable"]))
    print(f"Loaded {total_tests} verifiability test cases")
    
    # Create agent and context
    agent = create_calledit_agent()
    context_template = create_test_context("America/New_York")
    
    # Run tests for each category
    all_results = []
    
    # Test self-verifiable predictions (first 3 for Milestone 1)
    print(f"\n🧪 Testing Self-Verifiable Predictions (Sample)")
    for i, test_case in enumerate(test_data["self_verifiable"][:3]):
        result = run_single_verifiability_test(agent, test_case, context_template, "self_verifiable")
        all_results.append(result)
        
        import time
        time.sleep(0.5)
    
    # Test tool-verifiable predictions (first 3 for Milestone 1)
    print(f"\n🔧 Testing Tool-Verifiable Predictions (Sample)")
    for i, test_case in enumerate(test_data["tool_verifiable"][:3]):
        result = run_single_verifiability_test(agent, test_case, context_template, "tool_verifiable")
        all_results.append(result)
        
        import time
        time.sleep(0.5)
    
    # Test backlog-verifiable predictions (first 3 for Milestone 1)
    print(f"\n📚 Testing Backlog-Verifiable Predictions (Sample)")
    for i, test_case in enumerate(test_data["backlog_verifiable"][:3]):
        result = run_single_verifiability_test(agent, test_case, context_template, "backlog_verifiable")
        all_results.append(result)
        
        import time
        time.sleep(0.5)
    
    # Analyze results
    print("\n" + "=" * 60)
    print("📊 ANALYZING VERIFIABILITY RESULTS")
    print("=" * 60)
    
    analyzed_results = []
    
    for result in all_results:
        if result['success']:
            # Analyze verifiability handling
            analysis = analyze_verifiability_response(result['agent_response'], result['category'])
            score = score_verifiability_test(analysis)
            
            analyzed_results.append({
                **result,
                "analysis": analysis,
                "score": score
            })
        else:
            analyzed_results.append({
                **result,
                "analysis": None,
                "score": {"score": 0, "max_score": 1.0, "percentage": 0, "grade": "F", "details": ["Test failed to run"]}
            })
    
    # Display results by category
    categories = ["self_verifiable", "tool_verifiable", "backlog_verifiable"]
    category_names = ["Self-Verifiable", "Tool-Verifiable", "Backlog-Verifiable"]
    
    for category, category_name in zip(categories, category_names):
        category_results = [r for r in analyzed_results if r['category'] == category]
        if not category_results:
            continue
            
        print(f"\n📋 {category_name} Results:")
        print("-" * 40)
        
        for result in category_results:
            print(f"\n📝 Test {result['test_id']}: {result['prediction']}")
            print(f"Challenge: {result['challenge']}")
            print(f"Success: {'✅' if result['success'] else '❌'}")
            print(f"Score: {result['score']['score']:.2f}/1.0 ({result['score']['percentage']:.0f}%) - Grade: {result['score']['grade']}")
            
            if result['success'] and result['analysis']:
                print(f"Category Recognition: {result['analysis']['category_recognition']:.2f}")
                print(f"Method Quality: {result['analysis']['verification_method_quality']:.2f}")
                print(f"Tool Awareness: {result['analysis']['tool_awareness']:.2f}")
                print(f"Limitation Recognition: {result['analysis']['limitation_recognition']:.2f}")
            
            print("-" * 30)
    
    # Summary
    successful_tests = sum(1 for r in analyzed_results if r['success'])
    total_score = sum(r['score']['score'] for r in analyzed_results)
    max_total_score = sum(r['score']['max_score'] for r in analyzed_results)
    average_score = (total_score / max_total_score * 100) if max_total_score > 0 else 0
    
    print(f"\n📈 MILESTONE 1 SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {len(analyzed_results)} (sample from each category)")
    print(f"Successful: {successful_tests}/{len(analyzed_results)}")
    print(f"Overall Score: {total_score:.2f}/{max_total_score:.2f} ({average_score:.1f}%)")
    
    # Category breakdown
    for category, category_name in zip(categories, category_names):
        category_results = [r for r in analyzed_results if r['category'] == category]
        if category_results:
            cat_score = sum(r['score']['score'] for r in category_results) / len(category_results)
            print(f"{category_name}: {cat_score:.2f}/1.0 ({cat_score*100:.0f}%)")
    
    print("\n" + "=" * 60)
    print("✅ MILESTONE 1 COMPLETE - Verifiability Test Infrastructure")
    print("=" * 60)
    print("Next: Milestone 2 - Agent Response Analysis")

if __name__ == "__main__":
    main()