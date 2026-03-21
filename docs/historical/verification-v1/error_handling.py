"""
Strands Agent Error Handling Utilities
Implements best practices for robust error handling and fallback mechanisms
"""
import logging
import json
from typing import Any, Dict, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)

class AgentError(Exception):
    """Base exception for agent-related errors"""
    pass

class ToolError(Exception):
    """Exception for tool-related failures"""
    pass

class StreamingError(Exception):
    """Exception for streaming-related failures"""
    pass

def with_agent_fallback(fallback_response: Dict[str, Any]):
    """Decorator for agent calls with fallback response"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Agent error in {func.__name__}: {str(e)}", exc_info=True)
                return fallback_response
        return wrapper
    return decorator

def safe_agent_call(agent, prompt: str, fallback_response: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Safely execute agent call with error handling
    """
    if fallback_response is None:
        fallback_response = {
            "prediction_statement": prompt,
            "verifiable_category": "human_verifiable_only",
            "category_reasoning": "Unable to process prediction due to system error",
            "verification_method": {"source": "manual", "criteria": ["Human verification required"]},
            "error": "Agent processing failed"
        }
    
    try:
        result = agent(prompt)
        logger.info(f"Agent call successful for prompt: {prompt[:50]}...")
        return result
    except Exception as e:
        logger.error(f"Agent call failed: {str(e)}", exc_info=True)
        return fallback_response

def safe_streaming_callback(connection_id: str, api_gateway_client, fallback_message: str = "Processing..."):
    """
    Create a safe streaming callback with error handling
    """
    def callback(**kwargs):
        try:
            if "data" in kwargs:
                message = json.dumps({"type": "text", "content": kwargs["data"]})
            elif "current_tool_use" in kwargs:
                tool_name = kwargs["current_tool_use"].get("name", "unknown")
                message = json.dumps({"type": "tool", "content": f"[Using tool: {tool_name}]"})
            else:
                message = json.dumps({"type": "status", "content": fallback_message})
            
            api_gateway_client.post_to_connection(
                ConnectionId=connection_id,
                Data=message
            )
        except Exception as e:
            logger.error(f"Streaming callback error: {str(e)}")
            # Don't re-raise - continue processing
            
    return callback

class ToolFallbackManager:
    """Manages tool fallbacks and graceful degradation"""
    
    def __init__(self):
        self.tool_failures = {}
    
    def record_failure(self, tool_name: str):
        """Record a tool failure"""
        self.tool_failures[tool_name] = self.tool_failures.get(tool_name, 0) + 1
        logger.warning(f"Tool {tool_name} failed {self.tool_failures[tool_name]} times")
    
    def should_use_fallback(self, tool_name: str, max_failures: int = 3) -> bool:
        """Check if we should use fallback for a tool"""
        return self.tool_failures.get(tool_name, 0) >= max_failures
