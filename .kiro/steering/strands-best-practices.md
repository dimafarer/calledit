---
inclusion: always
---

# Strands Agent Development Best Practices

This steering document provides guidance on Strands agent development best practices to follow during implementation. Use this as a reference when building agents, graphs, and tools.

## Python Virtual Environment - MANDATORY

**RULE**: Always use the virtual environment at `/home/wsluser/projects/calledit/venv`

**All Python commands MUST use the venv**:

```bash
# ✅ CORRECT: Use venv python
/home/wsluser/projects/calledit/venv/bin/python -m pytest tests/

# ✅ CORRECT: Use venv pip
/home/wsluser/projects/calledit/venv/bin/pip install hypothesis

# ❌ WRONG: System python
python -m pytest tests/

# ❌ WRONG: System pip
pip install hypothesis
```

**Running tests**:
```bash
# Always use venv python for pytest
/home/wsluser/projects/calledit/venv/bin/python -m pytest tests/strands_make_call/test_utils.py -v
```

**Installing packages**:
```bash
# Always use venv pip
/home/wsluser/projects/calledit/venv/bin/pip install package-name
```

## Core Principles

### 1. Agent Design Philosophy

**Single Responsibility**: Each agent should have ONE clear purpose
- ✅ Good: "Parser Agent extracts predictions and parses time references"
- ❌ Bad: "Agent handles parsing, categorization, verification, and review"

**Focused Prompts**: Keep system prompts concise (20-30 lines)
- Move detailed instructions to user prompts (context-specific)
- Move examples to user prompts (not system prompts)
- Trust the model - Claude is smart enough without excessive examples

**Explicit Configuration**: Always specify agent names and models
```python
agent = Agent(
    name="parser_agent",  # Descriptive name for debugging
    model="claude-3-5-sonnet-20241022",  # Explicit model selection
    system_prompt="..."
)
```

### 2. Graph Pattern Usage

**When to Use Graph**:
- ✅ Sequential workflows with clear dependencies
- ✅ Tasks requiring different specialized perspectives
- ✅ Processes needing conditional logic or feedback loops
- ✅ Complex multi-step processes with distinct stages

**Graph Structure**:
```python
from strands.multiagent import GraphBuilder

# Define state schema
class MyGraphState(TypedDict):
    input_field: str
    output_field: str

# Build graph
builder = GraphBuilder(state_schema=MyGraphState)
builder.add_node("node1", node_function)
builder.add_node("node2", node_function)
builder.add_edge("node1", "node2")
builder.set_entry_point("node1")

graph = builder.compile()
```

**Node Functions**: Each node receives state, invokes agent, updates state
```python
def my_node_function(state: MyGraphState) -> MyGraphState:
    """Node function pattern"""
    # Build prompt from state
    prompt = f"Process this: {state['input_field']}"
    
    # Invoke agent
    response = my_agent(prompt)
    
    # Parse response (single json.loads call)
    result = json.loads(str(response))
    
    # Update and return state
    return {
        **state,
        "output_field": result["output"]
    }
```

### 3. JSON Parsing Best Practices

**Trust Strands Structured Output**:
```python
# ✅ Good: Single parse attempt
try:
    result = json.loads(str(response))
except json.JSONDecodeError:
    result = fallback_response

# ❌ Bad: Complex regex fallbacks
try:
    result = json.loads(response_str)
except:
    match = re.search(r'```json\s*(.*?)\s*```', response_str)
    if match:
        try:
            result = json.loads(match.group(1))
        except:
            # More fallback logic...
```

**Specify Format in Prompts**:
```python
system_prompt = """
Return valid JSON in this exact format:
{
    "field1": "value1",
    "field2": "value2"
}
"""
```

### 4. Error Handling Strategy

**Use Strands Built-in Mechanisms**:
```python
# ✅ Good: Simple try/except where needed
try:
    response = agent(prompt)
except Exception as e:
    logger.error(f"Agent failed: {str(e)}", exc_info=True)
    response = fallback_response

# ❌ Bad: Custom wrapper functions
def safe_agent_call(agent, prompt, fallback):
    try:
        return agent(prompt)
    except:
        return fallback
```

**Graceful Callback Errors**:
```python
def callback_handler(**kwargs):
    try:
        # Process events
        pass
    except Exception as e:
        logger.error(f"Callback error: {str(e)}", exc_info=True)
        # Don't re-raise - continue agent execution
```

### 5. Callback Handler Implementation

**Handle All Lifecycle Events**:
```python
def callback_handler(**kwargs):
    """Complete callback handler pattern"""
    try:
        # Text generation
        if "data" in kwargs:
            handle_text(kwargs["data"])
        
        # Tool usage
        elif "current_tool_use" in kwargs:
            handle_tool(kwargs["current_tool_use"])
        
        # Lifecycle events
        elif kwargs.get("init_event_loop"):
            logger.info("Event loop initialized")
        elif kwargs.get("start_event_loop"):
            logger.info("Cycle starting")
        elif kwargs.get("complete"):
            handle_completion()
        elif kwargs.get("force_stop"):
            logger.warning(f"Force stopped: {kwargs.get('force_stop_reason')}")
        
        # Message events
        elif "message" in kwargs:
            logger.debug(f"Message: {kwargs['message'].get('role')}")
            
    except Exception as e:
        logger.error(f"Callback error: {str(e)}", exc_info=True)
        # Never re-raise - callback errors shouldn't stop agent
```

### 6. Tool Development

**Simple Tool Pattern**:
```python
from strands import tool

@tool
def my_tool(input_param: str) -> str:
    """
    Clear description of what the tool does.
    
    Args:
        input_param: Description of parameter
        
    Returns:
        Description of return value
    """
    # Tool logic
    return result
```

**Tool with Context**:
```python
from strands import tool, ToolContext

@tool(context=True)
def my_tool_with_context(param: str, tool_context: ToolContext) -> str:
    """Tool that needs invocation state"""
    user_id = tool_context.invocation_state.get("user_id")
    # Use context...
    return result
```

### 7. Testing Best Practices

**Property-Based Testing**:
```python
from hypothesis import given, strategies as st

# Feature: feature-name, Property N: [property description]
@given(st.text(min_size=1))
def test_property(input_text):
    """For any input, property should hold"""
    result = function_under_test(input_text)
    assert property_holds(result)
```

**Unit Testing**:
```python
def test_specific_example():
    """Test specific example or edge case"""
    result = function_under_test("specific input")
    assert result == "expected output"
```

### 8. Logging Best Practices

**Use Structured Logging**:
```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Good logging
logger.info(f"Processing prediction: {prediction[:50]}...")
logger.error(f"Agent failed: {str(e)}", exc_info=True)
logger.debug(f"State: {json.dumps(state, indent=2)}")
```

### 9. State Management

**Graph State Pattern**:
```python
from typing import TypedDict, Optional

class MyGraphState(TypedDict):
    # Inputs
    user_input: str
    
    # Intermediate results
    parsed_data: str
    
    # Final outputs
    result: str
    
    # Metadata
    error: Optional[str]
```

**Invocation State** (for shared context):
```python
# Pass shared state that shouldn't be in prompts
invocation_state = {
    "user_id": "user123",
    "session_id": "sess456",
    "database_connection": db_conn
}

result = graph(prompt, invocation_state=invocation_state)
```

### 10. Async Patterns (Optional)

**Async Agent Invocation**:
```python
import asyncio

async def process_async():
    result = await agent.invoke_async(prompt)
    return result

# Or streaming
async for event in agent.stream_async(prompt):
    handle_event(event)
```

## Common Pitfalls to Avoid

1. ❌ **Over-specified prompts**: 200+ line prompts with excessive examples
2. ❌ **Complex JSON parsing**: Regex fallbacks and multiple parsing attempts
3. ❌ **Custom error wrappers**: Duplicating Strands functionality
4. ❌ **Incomplete callbacks**: Missing lifecycle events
5. ❌ **Implicit configuration**: Not specifying agent names or models
6. ❌ **Monolithic agents**: Single agent doing multiple unrelated tasks
7. ❌ **Callback re-raising**: Letting callback errors crash agent execution
8. ❌ **Manual state management**: Not using graph state properly

## Resources

- [Strands Documentation](https://strandsagents.com/latest/documentation/)
- [Graph Pattern Guide](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/graph/)
- [Custom Tools Guide](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/custom-tools/)
- [Callback Handlers Guide](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/streaming/callback-handlers/)

## Learning Approach

As you implement each task:
1. **Read the pattern** in this document
2. **Implement following the pattern**
3. **Test your implementation**
4. **Ask questions** if something is unclear
5. **Iterate** based on test results

The goal is to learn by doing - each agent you build will reinforce these patterns.
