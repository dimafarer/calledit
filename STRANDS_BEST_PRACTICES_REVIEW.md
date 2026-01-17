# Strands Implementation Best Practices Review

**Date**: January 16, 2026  
**Project**: CalledIt - Verifiable Prediction Structuring System  
**Status**: Recommendations for Improvement

---

## 📊 Overall Assessment

Your Strands implementation is **solid and functional**, but there are several opportunities to:
- Simplify code and reduce complexity
- Better leverage Strands SDK features
- Improve maintainability and error handling
- Follow Strands best practices more closely

---

## 🎯 Key Recommendations

### 1. **Simplify Agent Initialization** ⭐ HIGH PRIORITY

**Current Issue**: You're creating agents in multiple places with inconsistent patterns.

**Your Code** (`review_agent.py`):
```python
class ReviewAgent:
    def __init__(self, callback_handler=None):
        self.callback_handler = callback_handler
        self.agent = Agent(
            callback_handler=callback_handler,
            system_prompt="""..."""
        )
```

**Strands Best Practice**:
```python
class ReviewAgent:
    def __init__(self, callback_handler=None):
        self.agent = Agent(
            name="review_agent",  # Add descriptive name
            model="claude-3-sonnet-20241022",  # Explicit model selection
            callback_handler=callback_handler,
            system_prompt="""..."""
        )
        # No need to store callback_handler separately
```

**Benefits**:
- Explicit model selection (you're using defaults)
- Named agents for better debugging
- Cleaner initialization

---

### 2. **Use Class-Based Tools for Stateful Operations** ⭐ HIGH PRIORITY

**Current Issue**: Your `ReviewAgent` class methods aren't leveraging Strands' class-based tool pattern.

**Recommendation**: Convert `ReviewAgent` methods into proper Strands tools:

```python
from strands import Agent, tool

class ReviewAgent:
    def __init__(self, callback_handler=None):
        self.agent = Agent(
            name="review_agent",
            tools=[self.review_prediction_tool, self.regenerate_section_tool],
            callback_handler=callback_handler
        )
    
    @tool
    def review_prediction_tool(self, prediction_response: dict) -> dict:
        """
        Review a prediction response and identify improvable sections.
        
        Args:
            prediction_response: The prediction to review
        """
        # Your review logic here
        pass
    
    @tool
    def regenerate_section_tool(self, section_name: str, original_value: str, 
                                 user_input: str, full_context: dict) -> dict:
        """
        Regenerate a section with user clarifications.
        
        Args:
            section_name: The section to improve
            original_value: Current value
            user_input: User's clarifications
            full_context: Full prediction context
        """
        # Your regeneration logic here
        pass
```

**Benefits**:
- Tools are discoverable and reusable
- Better separation of concerns
- Agent can reason about which tool to use
- Follows Strands patterns

---

### 3. **Improve Callback Handler Implementation** ⭐ MEDIUM PRIORITY

**Current Issue**: Your callback handler in `strands_make_call_stream.py` doesn't follow best practices.

**Your Code**:
```python
def stream_callback_handler(**kwargs):
    """Callback handler that streams responses back to the client."""
    try:
        if "data" in kwargs:
            # Send text chunks
            api_gateway_management_api.post_to_connection(...)
        elif "current_tool_use" in kwargs:
            # Send tool usage
            api_gateway_management_api.post_to_connection(...)
    except Exception as e:
        print(f"Error sending to WebSocket: {str(e)}")
```

**Strands Best Practice**:
```python
def stream_callback_handler(**kwargs):
    """
    Callback handler following Strands best practices:
    1. Keep it fast
    2. Handle all event types
    3. Graceful error handling
    4. Use request_state for accumulated state
    """
    try:
        # Text generation events
        if "data" in kwargs:
            api_gateway_management_api.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    "type": "text",
                    "content": kwargs["data"]
                })
            )
        
        # Tool usage events
        elif "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
            api_gateway_management_api.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    "type": "tool",
                    "name": kwargs["current_tool_use"]["name"],
                    "input": kwargs["current_tool_use"].get("input", {})
                })
            )
        
        # Lifecycle events
        elif kwargs.get("init_event_loop"):
            # Event loop initialized
            pass
        elif kwargs.get("start_event_loop"):
            # Cycle starting
            pass
        elif kwargs.get("complete"):
            # Cycle completed
            api_gateway_management_api.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({"type": "status", "status": "complete"})
            )
        elif kwargs.get("force_stop"):
            # Force stopped
            reason = kwargs.get("force_stop_reason", "unknown")
            logger.warning(f"Agent force-stopped: {reason}")
        
        # Message events (complete messages)
        elif "message" in kwargs:
            # Complete message created
            pass
            
    except Exception as e:
        # Graceful error handling - don't crash the agent
        logger.error(f"Callback handler error: {str(e)}", exc_info=True)
        # Don't re-raise - callback errors shouldn't stop agent execution
```

**Benefits**:
- Handles all Strands event types
- Better lifecycle tracking
- Graceful error handling
- Follows documented patterns

---

### 4. **Remove Manual JSON Parsing** ⭐ HIGH PRIORITY

**Current Issue**: You have extensive manual JSON parsing logic that Strands handles automatically.

**Your Code** (multiple places):
```python
try:
    prediction_json = json.loads(response_str)
except json.JSONDecodeError:
    import re
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_str)
    if json_match:
        try:
            prediction_json = json.loads(json_match.group(1))
        except json.JSONDecodeError:
            # More fallback logic...
```

**Strands Best Practice**:
```python
# Strands agents return structured data automatically
# Just use the response directly
response = agent(prompt)

# If you need JSON, specify it in your system prompt:
system_prompt = """
Always return valid JSON in this exact format:
{
    "field1": "value1",
    "field2": "value2"
}
"""

# Then parse once:
try:
    result = json.loads(str(response))
except json.JSONDecodeError:
    # Use fallback
    result = fallback_response
```

**Benefits**:
- Much simpler code
- Fewer edge cases
- Easier to maintain
- Trust Strands to handle formatting

---

### 5. **Consolidate Error Handling** ⭐ MEDIUM PRIORITY

**Current Issue**: You have custom error handling wrappers (`safe_agent_call`, `with_agent_fallback`) that duplicate Strands functionality.

**Your Code** (`error_handling.py`):
```python
def safe_agent_call(agent, prompt, fallback_response):
    try:
        response = agent(prompt)
        return response
    except Exception as e:
        logger.error(f"Agent call failed: {str(e)}")
        return fallback_response
```

**Recommendation**: Use Strands' built-in error handling and simplify:

```python
# Instead of wrapping every call, handle errors at the agent level
agent = Agent(
    name="prediction_agent",
    tools=[current_time],
    # Strands handles retries and errors internally
)

# Then just use try/except where you actually need custom fallback:
try:
    response = agent(prompt)
except Exception as e:
    logger.error(f"Agent failed: {str(e)}", exc_info=True)
    response = fallback_response
```

**Benefits**:
- Less custom code to maintain
- Leverage Strands' built-in resilience
- Clearer error boundaries

---

### 6. **Use Async Properly** ⭐ LOW PRIORITY

**Current Issue**: You're not using Strands' async capabilities in Lambda.

**Current Code**: All synchronous
```python
response = agent(prompt)
```

**Strands Best Practice** (for Lambda):
```python
import asyncio

async def lambda_handler(event, context):
    # Use async agent invocation
    response = await agent.invoke_async(prompt)
    
    # Or use async streaming
    async for event in agent.stream_async(prompt):
        # Process events
        pass
```

**Benefits**:
- Better performance in Lambda
- Non-blocking I/O
- Proper async/await patterns

**Note**: This is lower priority since your current sync approach works fine for Lambda.

---

### 7. **Simplify Tool Definitions** ⭐ MEDIUM PRIORITY

**Current Issue**: Your `parse_relative_date` tool has complex logic that could be simplified.

**Your Code**:
```python
@tool
def parse_relative_date(date_string: str, timezone: str = "UTC") -> str:
    """Convert a relative date string to an actual datetime."""
    try:
        tz = pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        tz = pytz.UTC
    
    parsed_date = dateparser.parse(date_string, settings={...})
    if parsed_date:
        utc_date = parsed_date.astimezone(pytz.UTC)
        return utc_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        default_date = datetime.now(tz) + timedelta(days=30)
        return default_date.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
```

**Strands Best Practice**:
```python
@tool
def parse_relative_date(date_string: str, timezone: str = "UTC") -> dict:
    """
    Convert a relative date string to an actual datetime.
    
    Args:
        date_string: A relative date/time string like 'tomorrow', '3:00pm today'
        timezone: Timezone to use for parsing (default: UTC)
        
    Returns:
        dict: Contains 'iso_date', 'success', and optional 'error'
    """
    try:
        tz = pytz.timezone(timezone)
        parsed_date = dateparser.parse(
            date_string, 
            settings={'TIMEZONE': timezone, 'RETURN_AS_TIMEZONE_AWARE': True}
        )
        
        if parsed_date:
            utc_date = parsed_date.astimezone(pytz.UTC)
            return {
                "status": "success",
                "content": [{
                    "json": {
                        "iso_date": utc_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "success": True
                    }
                }]
            }
        else:
            # Return error instead of fallback
            return {
                "status": "error",
                "content": [{
                    "text": f"Could not parse date: {date_string}"
                }]
            }
            
    except Exception as e:
        return {
            "status": "error",
            "content": [{
                "text": f"Error parsing date: {str(e)}"
            }]
        }
```

**Benefits**:
- Proper ToolResult format
- Clear success/error states
- Agent can handle errors intelligently

---

### 8. **Reduce System Prompt Complexity** ⭐ MEDIUM PRIORITY

**Current Issue**: Your system prompts are very long and prescriptive.

**Your Code** (`strands_make_call_stream.py`):
```python
system_prompt="""You are a prediction verification expert. Your task is to:
    1. Analyze predictions WITHOUT modifying the original statement
    2. Create structured verification criteria
    3. Specify how to verify the prediction
    4. Categorize the verifiability of each prediction
    
    CRITICAL: Never modify or rephrase the user's original prediction statement...
    
    TOOL USAGE:
    - Use current_time tool once to get the current date and time context
    
    TIME HANDLING RULES:
    - Users think in 12-hour clock (3:00pm, this morning, this afternoon)
    - You must convert to 24-hour format for precision
    ...
    [200+ more lines]
"""
```

**Strands Best Practice**:
```python
# Keep system prompts focused and concise
system_prompt="""You are a prediction verification expert.

Your task:
1. Analyze the user's prediction (preserve exact wording)
2. Determine verification method and category
3. Return structured JSON response

Use the current_time tool to get date/time context.

Return JSON format:
{
    "prediction_statement": "exact user text",
    "verification_date": "ISO format",
    "verifiable_category": "one of 5 categories",
    "verification_method": {...}
}
"""

# Put detailed instructions in the user prompt instead:
user_prompt = f"""
Analyze this prediction: "{prompt}"

Current context:
- Date: {formatted_date_local}
- Time: {formatted_datetime_local}
- Timezone: {user_timezone}

Categories: agent_verifiable, current_tool_verifiable, strands_tool_verifiable, 
api_tool_verifiable, human_verifiable_only

Provide verification method with source, criteria, and steps.
"""
```

**Benefits**:
- Shorter, more focused system prompts
- Easier to maintain and update
- Better token efficiency
- Context-specific details in user prompts

---

## 📋 Priority Implementation Order

### Phase 1: Quick Wins (1-2 hours)
1. ✅ Add agent names and explicit models
2. ✅ Simplify JSON parsing (remove regex fallbacks)
3. ✅ Improve callback handler event handling

### Phase 2: Structural Improvements (2-4 hours)
4. ✅ Convert ReviewAgent methods to proper tools
5. ✅ Consolidate error handling
6. ✅ Simplify system prompts

### Phase 3: Advanced (4-6 hours)
7. ✅ Implement async patterns
8. ✅ Refactor tool definitions with proper ToolResult format

---

## 🎯 Expected Benefits

After implementing these recommendations:

- **30-40% less code** (remove manual JSON parsing, error wrappers)
- **Better maintainability** (follow Strands patterns)
- **Improved debugging** (named agents, proper event handling)
- **More robust** (leverage Strands' built-in error handling)
- **Easier to extend** (class-based tools, cleaner architecture)

---

## 📚 Additional Resources

- [Strands Custom Tools](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/custom-tools/)
- [Strands Callback Handlers](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/streaming/callback-handlers/)
- [Strands Agent API](https://strandsagents.com/latest/documentation/docs/api-reference/python/agent/)

---

**Next Steps**: Would you like me to help implement any of these recommendations? I can start with the high-priority items that will give you the biggest improvement with minimal effort.
