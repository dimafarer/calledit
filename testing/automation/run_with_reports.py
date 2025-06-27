#!/usr/bin/env python3
"""
Test Runner with Report Generation - Milestone 4 Implementation
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from agent_factory import create_calledit_agent, create_test_context
from result_parser import parse_agent_response, analyze_time_handling, score_test_result
from analysis_agent import analyze_test_results
from report_generator import generate_markdown_report, update_test_runner_md

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
    """Run a single test case against the agent."""
    prompt = test_case["prompt"]
    test_id = test_case["id"]
    
    full_prompt = context_template.format(prompt=prompt)
    print(f"Running Test {test_id}: {prompt}")
    
    try:
        result = agent(full_prompt)
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
    """Main test runner with report generation."""
    print("🚀 Starting CalledIt Agent Testing with Report Generation")
    print("=" * 60)
    
    # Load test cases
    test_cases = load_test_cases()
    print(f"Loaded {len(test_cases)} test cases")
    
    # Create agent and context
    agent = create_calledit_agent()
    context_template = create_test_context("America/New_York")
    
    # Run tests
    results = []
    for test_case in test_cases:
        print(f"\n🧪 Running Test {test_case['id']}")
        result = run_single_test(agent, test_case, context_template)
        results.append(result)
        
        import time
        time.sleep(0.5)
    
    # Analyze results
    print("\n" + "=" * 60)
    print("📊 ANALYZING RESULTS")
    print("=" * 60)
    
    analyzed_results = []
    for result in results:
        if result['success']:
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
    
    # Summary
    successful_tests = sum(1 for r in analyzed_results if r['success'])
    total_score = sum(r['score']['score'] for r in analyzed_results)
    max_total_score = sum(r['score']['max_score'] for r in analyzed_results)
    average_score = (total_score / max_total_score * 100) if max_total_score > 0 else 0
    
    print(f"\n📈 SUMMARY: {successful_tests}/{len(analyzed_results)} tests successful")
    print(f"Overall Score: {total_score}/{max_total_score} ({average_score:.1f}%)")
    
    # Generate comprehensive report
    print("\n" + "=" * 60)
    print("📄 GENERATING COMPREHENSIVE REPORT")
    print("=" * 60)
    
    try:
        # Generate markdown report
        report_path = Path(__file__).parent.parent / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_content = generate_markdown_report(analyzed_results, report_path)
        print(f"📋 Detailed report saved to: {report_path}")
        
        # Update manual test runner
        update_test_runner_md(analyzed_results)
        print("📝 Updated manual test runner with latest results")
        
        # Show report preview
        print("\n📖 REPORT PREVIEW:")
        print("-" * 40)
        print(report_content[:800] + "..." if len(report_content) > 800 else report_content)
        
    except Exception as e:
        print(f"⚠️ Report generation error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ MILESTONE 4 COMPLETE - Report Generation Added")
    print("=" * 60)

if __name__ == "__main__":
    main()