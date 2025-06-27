"""
Report Generator - Creates comprehensive test reports from analysis results
"""

import json
from datetime import datetime
from pathlib import Path

def generate_markdown_report(analyzed_results, output_path=None):
    """
    Generate a comprehensive markdown report from test results.
    
    Args:
        analyzed_results (list): List of analyzed test results
        output_path (str, optional): Path to save the report
        
    Returns:
        str: Generated markdown report content
    """
    
    # Calculate summary statistics
    total_tests = len(analyzed_results)
    successful_tests = sum(1 for r in analyzed_results if r['success'])
    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    
    total_score = sum(r['score']['score'] for r in analyzed_results)
    max_total_score = sum(r['score']['max_score'] for r in analyzed_results)
    average_score = (total_score / max_total_score * 100) if max_total_score > 0 else 0
    
    # Calculate grade distribution
    grades = {}
    for result in analyzed_results:
        grade = result['score']['grade']
        grades[grade] = grades.get(grade, 0) + 1
    
    # Determine average grade
    grade_values = {'A': 4, 'B': 3, 'C': 2, 'D': 1, 'F': 0}
    total_grade_points = sum(grade_values.get(grade, 0) * count for grade, count in grades.items())
    avg_grade_value = total_grade_points / total_tests if total_tests > 0 else 0
    average_grade = 'A' if avg_grade_value >= 3.5 else 'B' if avg_grade_value >= 2.5 else 'C' if avg_grade_value >= 1.5 else 'D' if avg_grade_value >= 0.5 else 'F'
    
    # Generate performance summary
    if success_rate == 100 and average_score >= 90:
        performance_summary = "🎉 **EXCELLENT** - All tests passed with outstanding scores. Agent demonstrates exceptional timezone handling capabilities."
    elif success_rate >= 90 and average_score >= 80:
        performance_summary = "✅ **GOOD** - Strong performance with minor areas for improvement."
    elif success_rate >= 70:
        performance_summary = "⚠️ **NEEDS IMPROVEMENT** - Several issues identified that require attention."
    else:
        performance_summary = "❌ **CRITICAL ISSUES** - Significant problems detected. Agent requires major fixes."
    
    # Generate detailed test results
    test_results_detail = []
    for result in analyzed_results:
        status_icon = "✅" if result['success'] else "❌"
        grade_icon = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "⚫"}.get(result['score']['grade'], "⚫")
        
        detail = f"""### {status_icon} Test {result['test_id']}: {result['prompt']}

**Challenge:** {result['challenge']}  
**Score:** {result['score']['score']}/{result['score']['max_score']} ({result['score']['percentage']:.0f}%) {grade_icon} Grade {result['score']['grade']}  
**Verification Date:** {result['parsed']['verification_date'] if result.get('parsed') else 'N/A'}  

**Expected Behavior:** {result['expected_behavior']}"""
        
        if result['success'] and result.get('parsed'):
            detail += f"\n**Date Reasoning:** {result['parsed']['date_reasoning'][:200]}{'...' if len(result['parsed']['date_reasoning']) > 200 else ''}"
        
        if result['score']['issues']:
            detail += "\n**Issues:**"
            for issue in result['score']['issues']:
                detail += f"\n- ⚠️ {issue}"
        
        test_results_detail.append(detail)
    
    # Collect strengths and issues
    all_issues = []
    strengths = []
    
    for result in analyzed_results:
        all_issues.extend(result['score']['issues'])
        if result['score']['grade'] == 'A':
            strengths.append(f"- Test {result['test_id']}: Excellent handling of '{result['challenge']}'")
    
    # Count issue frequency
    issue_counts = {}
    for issue in all_issues:
        issue_counts[issue] = issue_counts.get(issue, 0) + 1
    
    # Generate coverage table
    categories = {
        'Business Context': ['market', 'business', 'lunch'],
        'Cross-Day Boundaries': ['tomorrow', 'midnight', 'week'],
        'Vague Time References': ['morning', 'evening', 'afternoon'],
        'Specific Times': ['AM', 'PM', ':']
    }
    
    coverage_rows = []
    for category, keywords in categories.items():
        category_tests = [r for r in analyzed_results if any(kw.lower() in r['prompt'].lower() for kw in keywords)]
        if category_tests:
            pass_rate = sum(1 for t in category_tests if t['success']) / len(category_tests) * 100
            coverage_rows.append(f"| {category} | {len(category_tests)} | {pass_rate:.0f}% | {'✅ Excellent' if pass_rate == 100 else '⚠️ Issues found' if pass_rate < 100 else 'Good'} |")
    
    # Load template and populate
    template_path = Path(__file__).parent / "templates" / "report_template.md"
    with open(template_path, 'r') as f:
        template = f.read()
    
    report_content = template.format(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_tests=total_tests,
        successful_tests=successful_tests,
        success_rate=success_rate,
        total_score=total_score,
        max_total_score=max_total_score,
        average_score=average_score,
        average_grade=average_grade,
        performance_summary=performance_summary,
        test_results_detail="\n\n".join(test_results_detail),
        strengths="\n".join(strengths) if strengths else "- All major timezone handling patterns working correctly",
        issues="\n".join([f"- {issue} ({count} tests)" for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]]) if issue_counts else "- No significant issues detected",
        recommendations="- Agent is production-ready for timezone handling\n- Consider testing international timezones\n- Test daylight saving time transitions" if success_rate == 100 else "- Address identified issues before production deployment",
        coverage_table="\n".join(coverage_rows)
    )
    
    # Save report if path provided
    if output_path:
        with open(output_path, 'w') as f:
            f.write(report_content)
    
    return report_content

def update_test_runner_md(analyzed_results):
    """
    Update the manual test runner markdown with latest results.
    
    Args:
        analyzed_results (list): List of analyzed test results
    """
    
    # Generate results for manual template
    results_section = []
    
    for result in analyzed_results:
        verification_date = result['parsed']['verification_date'] if result.get('parsed') else 'N/A'
        date_reasoning = result['parsed']['date_reasoning'][:100] + '...' if result.get('parsed') and len(result['parsed']['date_reasoning']) > 100 else result['parsed']['date_reasoning'] if result.get('parsed') else 'N/A'
        issues = ', '.join(result['score']['issues']) if result['score']['issues'] else 'None'
        
        results_section.append(f"""### Test {result['test_id']}: {result['challenge']}
**Prompt:** "{result['prompt']}"
**Agent Response:**
- Verification Date: {verification_date}
- Date Reasoning: {date_reasoning}
- Issues Found: {issues}""")
    
    # Update the test runner file
    test_runner_path = Path(__file__).parent.parent / "test_runner.md"
    
    try:
        with open(test_runner_path, 'r') as f:
            content = f.read()
        
        # Replace the results section
        updated_content = content.replace(
            "## Test Results (Date: ______)",
            f"## Test Results (Date: {datetime.now().strftime('%Y-%m-%d')})\n\n" + "\n\n".join(results_section)
        )
        
        with open(test_runner_path, 'w') as f:
            f.write(updated_content)
            
    except FileNotFoundError:
        print("Warning: Could not update test_runner.md - file not found")