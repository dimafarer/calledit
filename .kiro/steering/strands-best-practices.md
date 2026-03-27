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

## Dependency Management - MANDATORY

**RULE**: ALL Python dependencies MUST be tracked in requirements.txt files

**Project Structure**:
- Root `requirements.txt` - Development dependencies (pytest, hypothesis, etc.)
- Lambda handler `requirements.txt` - Runtime dependencies for each Lambda function

**Adding Dependencies**:

1. **Development Dependencies** (testing, linting, etc.):
```bash
# Add to root requirements.txt
echo "hypothesis>=6.0.0" >> requirements.txt

# Install in venv
/home/wsluser/projects/calledit/venv/bin/pip install -r requirements.txt
```

2. **Lambda Runtime Dependencies** (needed in deployed Lambda):
```bash
# Add to Lambda handler requirements.txt
echo "strands-agents>=1.7.0" >> backend/calledit-backend/handlers/strands_make_call/requirements.txt

# Install in venv for local testing
/home/wsluser/projects/calledit/venv/bin/pip install -r backend/calledit-backend/handlers/strands_make_call/requirements.txt
```

**Requirements File Locations**:
- `/home/wsluser/projects/calledit/requirements.txt` - Root (dev dependencies)
- `backend/calledit-backend/handlers/strands_make_call/requirements.txt` - Strands Lambda
- `backend/calledit-backend/handlers/auth_token/requirements.txt` - Auth Lambda
- `backend/calledit-backend/handlers/list_predictions/requirements.txt` - List Lambda
- `backend/calledit-backend/handlers/write_to_db/requirements.txt` - Write Lambda
- `backend/calledit-backend/handlers/websocket/requirements.txt` - WebSocket Lambda

**Rules**:
1. ✅ ALWAYS add dependencies to appropriate requirements.txt FIRST
2. ✅ THEN install using `pip install -r requirements.txt`
3. ❌ NEVER use `pip install package-name` without updating requirements.txt
4. ✅ Pin versions for production dependencies (e.g., `strands-agents==1.7.0`)
5. ✅ Use minimum versions for dev dependencies (e.g., `hypothesis>=6.0.0`)

**Why This Matters**:
- Ensures reproducible builds
- SAM CLI uses Lambda requirements.txt for deployment
- Other developers can install exact dependencies
- CI/CD pipelines need requirements.txt

## TTY Error Handling - RESOLVED (March 27, 2026)

**STATUS**: The TTY issue has been fixed. Agent commands should now work normally.

**Root Cause**: Amazon Q CLI shell integration (`q init bash pre/post`) injected `PROMPT_COMMAND` hooks (`__bp_precmd_invoke_cmd`, `__fig_post_prompt`) that conflicted with Kiro's own shell integration for capturing command output. This caused `Exit Code: -1` and empty output on the agent side, even though commands executed successfully in the user's terminal.

**Fix Applied** (in `~/.bashrc`):
1. Both Amazon Q pre/post blocks wrapped with `if [[ "$TERM_PROGRAM" != "kiro" ]]` guards
2. `unset TTY` at the end of `.bashrc` as a safety net for the `TTY=not a tty` env var pollution

**If TTY errors reappear**: The fix may have been overwritten by an Amazon Q CLI update (it manages those blocks). Re-apply the guards in `~/.bashrc`. Check with `head -5 ~/.bashrc && tail -7 ~/.bashrc`.

**For `agentcore` commands**: `agentcore launch` and `agentcore invoke` still require a real TTY — ask the user to run those manually and paste output.

---

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

**Two Node Patterns**:

1. **Plain Agent Nodes** (for conversational text-based workflows):
   - Agents return text that flows to next agent
   - No JSON parsing needed
   - Simple text-based conversation flow

2. **Custom Nodes** (for structured data workflows):
   - Agents return JSON that needs parsing
   - Need to build prompts from accumulated state
   - Structured data transformation between agents

**Graph Structure with Plain Agents** (conversational or JSON workflows):
```python
from strands.multiagent import GraphBuilder
from strands import Agent

# Create agents
agent1 = Agent(model="claude-3-5-sonnet-20241022", system_prompt="...")
agent2 = Agent(model="claude-3-5-sonnet-20241022", system_prompt="...")

# Build graph
builder = GraphBuilder()
builder.add_node(agent1, "node1")  # Agent first, then ID
builder.add_node(agent2, "node2")
builder.add_edge("node1", "node2")
builder.set_entry_point("node1")

graph = builder.build()

# Execute graph
result = graph("Initial task")

# Parse results from each node
node1_output = str(result.results["node1"].result)
node2_output = str(result.results["node2"].result)

# If agents return JSON, parse after execution
import json
node1_data = json.loads(node1_output)
node2_data = json.loads(node2_output)
```

**How Graph Input Propagation Works**:
- Entry nodes receive the original task as input
- Dependent nodes receive: original task + results from all completed dependencies
- The Graph automatically formats this as a combined input
- No manual state management needed!

**When to Use Custom Nodes** (MultiAgentBase):
- ✅ Deterministic business logic (validation, calculations, rules)
- ✅ Data processing pipelines (transformations, filtering)
- ✅ Hybrid workflows (combine AI with deterministic steps)
- ❌ NOT for state management between agents (Graph handles this automatically)
- ❌ NOT for JSON parsing between agents (parse results after graph execution)

**Important**: Strands Graph requires nodes to be Agent objects or MultiAgentBase subclasses. Plain functions are NOT supported as graph nodes.

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
9. ❌ **Plain functions as graph nodes**: Graph requires Agent or MultiAgentBase objects
10. ❌ **Wrong node pattern**: Using plain agents when you need structured data flow (use custom nodes)

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
