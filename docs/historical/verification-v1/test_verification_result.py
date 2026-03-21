#!/usr/bin/env python3
"""
Test the verification result structures and tool gap analysis
"""

from verification_result import (
    VerificationResult, VerificationStatus, ToolGap, 
    MCPToolSuggestions, create_tool_gap_result
)
from datetime import datetime

def test_basic_verification_result():
    """Test basic verification result creation"""
    print("🧪 Testing basic verification result...")
    
    result = VerificationResult(
        prediction_id="test_123",
        status=VerificationStatus.TRUE,
        confidence=0.95,
        reasoning="Verified through reasoning",
        verification_date=datetime.now(),
        tools_used=["reasoning"],
        agent_thoughts="This is clearly true based on logic"
    )
    
    assert result.is_successful_verification()
    assert not result.needs_tool_development()
    print("✅ Basic verification result works")

def test_tool_gap_result():
    """Test tool gap result creation"""
    print("🧪 Testing tool gap result...")
    
    tool_gap = ToolGap(
        missing_tool="weather_api",
        suggested_mcp_tool="mcp-weather",
        tool_specification="get_weather(location, date) -> weather_data",
        priority="HIGH"
    )
    
    result = VerificationResult(
        prediction_id="test_456",
        status=VerificationStatus.TOOL_GAP,
        confidence=0.0,
        reasoning="Cannot verify without weather data",
        verification_date=datetime.now(),
        tools_used=[],
        agent_thoughts="Need weather API",
        tool_gap=tool_gap
    )
    
    assert not result.is_successful_verification()
    assert result.needs_tool_development()
    assert result.tool_gap.missing_tool == "weather_api"
    print("✅ Tool gap result works")

def test_mcp_tool_suggestions():
    """Test MCP tool suggestion logic"""
    print("🧪 Testing MCP tool suggestions...")
    
    # Weather prediction
    weather_gap = MCPToolSuggestions.suggest_tool("It will rain tomorrow", "api_tool_verifiable")
    assert weather_gap is not None
    assert weather_gap.missing_tool == "weather_api"
    assert weather_gap.suggested_mcp_tool == "mcp-weather"
    assert weather_gap.priority == "HIGH"
    print("✅ Weather tool suggestion works")
    
    # Sports prediction
    sports_gap = MCPToolSuggestions.suggest_tool("Lakers will win the NBA game", "api_tool_verifiable")
    assert sports_gap is not None
    assert sports_gap.missing_tool == "sports_api"
    assert sports_gap.suggested_mcp_tool == "mcp-espn"
    print("✅ Sports tool suggestion works")
    
    # Financial prediction
    finance_gap = MCPToolSuggestions.suggest_tool("Apple stock will hit $200", "api_tool_verifiable")
    assert finance_gap is not None
    assert finance_gap.missing_tool == "financial_api"
    assert finance_gap.suggested_mcp_tool == "mcp-yahoo-finance"
    print("✅ Financial tool suggestion works")
    
    # No suggestion needed
    no_gap = MCPToolSuggestions.suggest_tool("I will feel happy", "human_verifiable_only")
    assert no_gap is None
    print("✅ No suggestion for non-API predictions works")

def test_create_tool_gap_result():
    """Test the helper function for creating tool gap results"""
    print("🧪 Testing tool gap result creation...")
    
    result = create_tool_gap_result(
        prediction_id="test_789",
        prediction_text="It will be sunny in Tokyo tomorrow",
        category="api_tool_verifiable",
        reasoning="Need weather data for Tokyo"
    )
    
    assert result.status == VerificationStatus.TOOL_GAP
    assert result.confidence == 0.0
    assert result.tool_gap is not None
    assert result.tool_gap.missing_tool == "weather_api"
    print("✅ Tool gap result creation works")

def test_result_serialization():
    """Test converting results to dictionary for JSON"""
    print("🧪 Testing result serialization...")
    
    result = create_tool_gap_result(
        prediction_id="test_serialize",
        prediction_text="Bitcoin will hit $200k",
        category="api_tool_verifiable", 
        reasoning="Need crypto price data"
    )
    
    result_dict = result.to_dict()
    
    assert "prediction_id" in result_dict
    assert "status" in result_dict
    assert "tool_gap" in result_dict
    assert result_dict["tool_gap"] is not None
    assert "missing_tool" in result_dict["tool_gap"]
    
    print("✅ Result serialization works")
    print(f"   Sample serialized result: {result_dict['tool_gap']['missing_tool']}")

def main():
    """Run all tests"""
    print("🚀 Testing Verification Result System")
    print("=" * 50)
    
    try:
        test_basic_verification_result()
        test_tool_gap_result()
        test_mcp_tool_suggestions()
        test_create_tool_gap_result()
        test_result_serialization()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed! Verification result system is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()