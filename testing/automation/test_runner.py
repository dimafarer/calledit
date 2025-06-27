#!/usr/bin/env python3
"""
Direct Agent Test Runner - Tests CalledIt agent with edge case prompts
"""

import json
import sys
from pathlib import Path
from agent_factory import create_calledit_agent, create_test_context
from result_parser import parse_agent_response, analyze_time_handling, score_test_result
from analysis_agent import analyze_test_results

def load_test_cases():
    """Load test cases from JSON file."""
    test_file = Path(__file__).parent.parent / "timezone_edge_case_tests.json"
    
    try:
        with open(test_file, 'r') as f:
            data = json.load(f)
            return data["timezone_edge_case_tests"]
    except FileNotFoundError:
        print(f"Error: Test file not found at {test_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in test file: {e}")
        sys.exit(1)

def run_single_test(agent, test_case, context_template):
    """
    Run a single test case against the agent.
    
    Args:
        agent: CalledIt agent instance
        test_case: Test case dictionary
        context_template: Context template string
        
    Returns:
        dict: Test result with response and metadata
    """
    prompt = test_case["prompt"]
    test_id = test_case["id"]
    
    # Create full prompt with context
    full_prompt = context_template.format(prompt=prompt)
    
    print(f"Running Test {test_id}: {prompt}")
    
    try:
        # Call the agent directly
        result = agent(full_prompt)
        
        # Extract response text
        response_text = str(result)
        
        return {
            "test_id": test_id,
            "prompt": prompt,
            "challenge": test_case["challenge"],
            "expected_behavior": test_case["expected_behavior"],
            "agent_response": response_text,
            "success": True,
            "error": None
        }
        
    except Exception as e:
        return {
            "test_id": test_id,
            "prompt": prompt,
            "challenge": test_case["challenge"],
            "expected_behavior": test_case["expected_behavior"],
            "agent_response": None,
            "success": False,
            "error": str(e)
        }

def main():
    """Main test runner function."""
    print("🚀 Starting CalledIt Agent Direct Testing")
    print("=" * 50)
    
    # Load test cases
    test_cases = load_test_cases()
    print(f"Loaded {len(test_cases)} test cases")
    
    # Create agent and context
    agent = create_calledit_agent()
    context_template = create_test_context("America/New_York")
    
    # Run tests
    results = []
    
    # Run all test cases for Milestone 2
    for test_case in test_cases:
        print(f"\n🧪 Running Test {test_case['id']}")
        result = run_single_test(agent, test_case, context_template)
        results.append(result)
        
        # Brief pause between tests
        import time
        time.sleep(0.5)
    
    # Analyze results
    print("\n" + "=" * 50)
    print("📊 ANALYZING RESULTS")
    print("=" * 50)
    
    analyzed_results = []
    
    for result in results:
        if result['success']:
            # Parse and analyze the response
            parsed = parse_agent_response(result['agent_response'])
            analysis = analyze_time_handling(parsed)
            score = score_test_result(parsed, analysis)
            
            analyzed_results.append({
                **result,
                "parsed": parsed,
                "analysis": analysis,
                "score": score
            })
        else:
            analyzed_results.append({
                **result,
                "parsed": None,
                "analysis": None,
                "score": {"score": 0, "max_score": 5, "percentage": 0, "grade": "F", "details": ["Test failed to run"], "issues": [result['error']]}
            })
    
    # Display detailed results
    print("\n" + "=" * 50)
    print("📊 DETAILED TEST RESULTS")
    print("=" * 50)
    
    for result in analyzed_results:
        print(f"\n📝 Test {result['test_id']}: {result['prompt']}")
        print(f"Challenge: {result['challenge']}")
        print(f"Success: {'✅' if result['success'] else '❌'}")
        print(f"Score: {result['score']['score']}/{result['score']['max_score']} ({result['score']['percentage']:.0f}%) - Grade: {result['score']['grade']}")
        
        if result['success'] and result['parsed']:
            print(f"Verification Date: {result['parsed']['verification_date']}")
            print(f"Timezone Handling: {result['analysis']['timezone_handling']}")
            
            if result['score']['issues']:
                print("Issues Found:")
                for issue in result['score']['issues']:
                    print(f"  ⚠️  {issue}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        print("-" * 50)
    
    # Summary
    successful_tests = sum(1 for r in analyzed_results if r['success'])
    total_score = sum(r['score']['score'] for r in analyzed_results)
    max_total_score = sum(r['score']['max_score'] for r in analyzed_results)
    average_score = (total_score / max_total_score * 100) if max_total_score > 0 else 0
    
    print(f"\n📈 FINAL SUMMARY")
    print("=" * 50)
    print(f"Tests Run: {len(analyzed_results)}")
    print(f"Successful: {successful_tests}/{len(analyzed_results)}")
    print(f"Overall Score: {total_score}/{max_total_score} ({average_score:.1f}%)")
    
    # Run intelligent analysis with Strands agent
    print("\n" + "=" * 50)
    print("🤖 INTELLIGENT ANALYSIS (Strands Agent)")
    print("=" * 50)
    
    try:
        analysis_report = analyze_test_results(analyzed_results)
        print(analysis_report)
    except Exception as e:
        print(f"⚠️ Analysis agent error: {e}")
        print("Continuing with basic analysis...")
    
    print("\n" + "=" * 50)
    print("✅ MILESTONE 3 COMPLETE - Intelligent Analysis Added")
    print("=" * 50)

if __name__ == "__main__":
    main()