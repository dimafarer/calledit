"""
Analysis Agent - Intelligent analysis of CalledIt test results using Strands
"""

from strands import Agent
import json
from tools.timezone_analyzer import analyze_timezone_patterns, suggest_additional_edge_cases

def create_analysis_agent():
    """
    Create a Strands agent for analyzing test results.
    
    Returns:
        Agent: Configured analysis agent
    """
    
    system_prompt = """You are an expert AI testing analyst specializing in timezone and time interpretation systems. 
    Your role is to analyze test results from a prediction verification agent and provide intelligent insights.

    ANALYSIS CAPABILITIES:
    - Identify patterns in timezone handling across multiple tests
    - Evaluate time interpretation quality and consistency
    - Suggest improvements to agent prompts or logic
    - Recommend additional edge cases for testing
    - Generate executive summaries for stakeholders

    ANALYSIS STYLE:
    - Be concise but thorough in your analysis
    - Focus on actionable insights and recommendations
    - Highlight both strengths and potential improvements
    - Use clear, professional language suitable for technical teams
    - Provide specific examples when discussing issues or successes

    TOOLS AVAILABLE:
    - analyze_timezone_patterns: Analyze timezone handling patterns across test results
    - suggest_additional_edge_cases: Suggest new test cases based on current coverage

    OUTPUT FORMAT:
    Provide your analysis in clear sections:
    1. Executive Summary
    2. Key Findings
    3. Strengths Identified
    4. Areas for Improvement (if any)
    5. Recommendations
    6. Additional Test Cases (if applicable)
    """
    
    agent = Agent(
        tools=[analyze_timezone_patterns, suggest_additional_edge_cases],
        system_prompt=system_prompt
    )
    
    return agent

def analyze_test_results(test_results):
    """
    Analyze test results using the Strands analysis agent.
    
    Args:
        test_results (list): List of test result dictionaries
        
    Returns:
        str: Analysis report from the agent
    """
    agent = create_analysis_agent()
    
    # Convert test results to JSON for analysis
    results_json = json.dumps(test_results, indent=2)
    
    # Create analysis prompt
    prompt = f"""Please analyze these CalledIt agent test results and provide comprehensive insights:

TEST RESULTS:
{results_json}

Please provide a thorough analysis covering:
1. Overall performance assessment
2. Timezone handling quality
3. Time interpretation patterns
4. Business context understanding
5. Edge case coverage
6. Recommendations for improvement
7. Suggested additional test cases

Focus on actionable insights that can help improve the agent's performance."""

    # Get analysis from the agent
    result = agent(prompt)
    return str(result)