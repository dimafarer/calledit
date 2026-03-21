#!/usr/bin/env python3
"""
Verification Result Data Structures
Enhanced with tool gap analysis and MCP suggestions
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class VerificationStatus(Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    INCONCLUSIVE = "INCONCLUSIVE"
    ERROR = "ERROR"
    TOOL_GAP = "TOOL_GAP"

@dataclass
class ToolGap:
    """Information about missing tools needed for verification"""
    missing_tool: str
    suggested_mcp_tool: Optional[str] = None
    tool_specification: Optional[str] = None
    priority: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    examples: List[str] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []

@dataclass
class VerificationResult:
    """Complete verification result with tool gap analysis"""
    prediction_id: str
    status: VerificationStatus
    confidence: float  # 0.0 to 1.0
    reasoning: str
    verification_date: datetime
    tools_used: List[str]
    agent_thoughts: str
    processing_time_ms: int = 0
    
    # Error handling
    error_message: Optional[str] = None
    
    # Tool gap analysis
    tool_gap: Optional[ToolGap] = None
    
    # Verification details
    actual_outcome: Optional[str] = None
    verification_method: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "prediction_id": self.prediction_id,
            "status": self.status.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "verification_date": self.verification_date.isoformat(),
            "tools_used": self.tools_used,
            "agent_thoughts": self.agent_thoughts,
            "processing_time_ms": self.processing_time_ms,
            "error_message": self.error_message,
            "actual_outcome": self.actual_outcome,
            "verification_method": self.verification_method
        }
        
        # Add tool gap information if present
        if self.tool_gap:
            result["tool_gap"] = {
                "missing_tool": self.tool_gap.missing_tool,
                "suggested_mcp_tool": self.tool_gap.suggested_mcp_tool,
                "tool_specification": self.tool_gap.tool_specification,
                "priority": self.tool_gap.priority,
                "examples": self.tool_gap.examples
            }
        else:
            result["tool_gap"] = None
            
        return result
    
    def is_successful_verification(self) -> bool:
        """Check if verification was completed (not a tool gap or error)"""
        return self.status in [VerificationStatus.TRUE, VerificationStatus.FALSE]
    
    def needs_tool_development(self) -> bool:
        """Check if this result indicates a tool gap"""
        return self.status == VerificationStatus.TOOL_GAP

class MCPToolSuggestions:
    """Known MCP tools for common verification needs"""
    
    WEATHER_TOOLS = {
        "mcp-weather": "General weather data API integration",
        "mcp-openweathermap": "OpenWeatherMap API for detailed weather",
        "mcp-noaa": "NOAA weather service for US weather data"
    }
    
    FINANCIAL_TOOLS = {
        "mcp-finance": "General financial data API",
        "mcp-yahoo-finance": "Yahoo Finance API integration",
        "mcp-alpha-vantage": "Alpha Vantage financial data",
        "mcp-coinbase": "Cryptocurrency price data"
    }
    
    SPORTS_TOOLS = {
        "mcp-sports": "General sports data API",
        "mcp-espn": "ESPN sports data integration",
        "mcp-nba": "NBA-specific game and player data",
        "mcp-nfl": "NFL game results and statistics"
    }
    
    NEWS_TOOLS = {
        "mcp-news": "General news API integration",
        "mcp-wikipedia": "Wikipedia data for event verification",
        "mcp-reuters": "Reuters news API",
        "mcp-newsapi": "NewsAPI.org integration"
    }
    
    SOCIAL_TOOLS = {
        "mcp-twitter": "Twitter/X API integration",
        "mcp-reddit": "Reddit API for sentiment analysis",
        "mcp-social": "General social media monitoring"
    }
    
    @classmethod
    def suggest_tool(cls, prediction_text: str, category: str) -> Optional[ToolGap]:
        """Suggest appropriate MCP tool based on prediction content"""
        text_lower = prediction_text.lower()
        
        # Weather predictions
        if any(word in text_lower for word in ['weather', 'rain', 'sunny', 'snow', 'temperature', 'storm']):
            return ToolGap(
                missing_tool="weather_api",
                suggested_mcp_tool="mcp-weather",
                tool_specification="get_weather(location: str, date: str) -> {temperature: float, conditions: str, precipitation: float, humidity: float}",
                priority="HIGH",
                examples=[prediction_text]
            )
        
        # Sports predictions
        if any(word in text_lower for word in ['nba', 'nfl', 'game', 'team', 'win', 'championship', 'score']):
            return ToolGap(
                missing_tool="sports_api",
                suggested_mcp_tool="mcp-espn",
                tool_specification="get_game_result(team1: str, team2: str, date: str) -> {winner: str, score: str, status: str}",
                priority="MEDIUM",
                examples=[prediction_text]
            )
        
        # Financial predictions (beyond Bitcoin)
        if any(word in text_lower for word in ['stock', 'price', 'market', 'shares', 'nasdaq', 'dow']) and 'bitcoin' not in text_lower:
            return ToolGap(
                missing_tool="financial_api",
                suggested_mcp_tool="mcp-yahoo-finance",
                tool_specification="get_stock_price(symbol: str, date: str) -> {price: float, volume: int, change: float}",
                priority="MEDIUM",
                examples=[prediction_text]
            )
        
        # News/event predictions
        if any(word in text_lower for word in ['news', 'event', 'announcement', 'release', 'launch', 'election']):
            return ToolGap(
                missing_tool="news_api",
                suggested_mcp_tool="mcp-news",
                tool_specification="search_events(query: str, date_range: str) -> {events: List[dict], sources: List[str]}",
                priority="LOW",
                examples=[prediction_text]
            )
        
        return None

def create_tool_gap_result(prediction_id: str, prediction_text: str, category: str, reasoning: str) -> VerificationResult:
    """Create a verification result indicating a tool gap"""
    tool_gap = MCPToolSuggestions.suggest_tool(prediction_text, category)
    
    if not tool_gap:
        # Generic tool gap
        tool_gap = ToolGap(
            missing_tool="unknown_api",
            suggested_mcp_tool="custom_mcp_tool",
            tool_specification=f"Custom tool needed for: {prediction_text}",
            priority="LOW",
            examples=[prediction_text]
        )
    
    return VerificationResult(
        prediction_id=prediction_id,
        status=VerificationStatus.TOOL_GAP,
        confidence=0.0,
        reasoning=reasoning,
        verification_date=datetime.now(),
        tools_used=[],
        agent_thoughts=f"Cannot verify '{prediction_text}' - missing required tool: {tool_gap.missing_tool}",
        tool_gap=tool_gap,
        verification_method="tool_gap_analysis"
    )