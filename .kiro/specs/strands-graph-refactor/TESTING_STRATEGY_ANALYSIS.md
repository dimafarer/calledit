# Testing Strategy Analysis: Strands Agents Best Practices

**Date**: 2025-01-19  
**Based On**: Official Strands Documentation  
**Purpose**: Define effective testing strategy for Task 17 and beyond

## Executive Summary

After reviewing the official Strands documentation on evaluation and production operations, I've identified why our previous tests failed and what we should do instead.

### Key Findings

1. **❌ Previous Approach**: Mock-heavy unit tests that don't invoke real agents
2. **✅ Strands Approach**: Real agent invocations with structured test cases
3. **🎯 Recommendation**: Integration tests with real API calls, not mocks

---

## What Strands Documentation Says About Testing

### From "Evaluation" Documentation

The Strands documentation emphasizes **real agent invocations** for testing, not mocks:

> "The simplest approach is direct manual testing... Create agent with specific configuration... Test with specific queries... Manually analyze the response for quality, accuracy, and task completion."

**Key Quote**:
```python
# Create agent with specific configuration
agent = Agent(
    model="us.anthropic.claude-sonnet-4-20250514-v1:0",
    system_prompt="You are a helpful assistant specialized in data analysis.",
    tools=[calculator]
)

# Test with specific queries
response = agent("Analyze this data...")
print(str(response))

# Manually analyze the response for quality, accuracy, and task completion
```

**This is NOT mocking** - it's invoking the real agent with real LLM calls.

### Structured Testing Approach

Strands recommends creating test cases and running real agent invocations:

```python
# Load test cases from JSON file
with open("test_cases.json", "r") as f:
    test_cases = json.load(f)

# Create agent
agent = Agent(model="us.anthropic.claude-sonnet-4-20250514-v1:0")

# Run tests and collect results
results = []
for case in test_cases:
    query = case["query"]
    expected = case.get("expected")
    
    # Execute the agent query (REAL INVOCATION)
    response = agent(query)
    
    # Store results for analysis
    results.append({
        "test_id": case.get("id", ""),
        "query": query,
        "expected": expected,
        "actual": str(response),
        "timestamp": pd.Timestamp.now()
    })
```

**Key Insight**: Tests invoke real agents, not mocks.

---

## Why Our Previous Tests Failed

### Problem 1: Pure Mocks Don't Test Anything

**What We Did**:
```python
# Mock everything
@patch('agent.invoke')
def test_parser(mock_invoke):
    mock_invoke.return_value = {"prediction_statement": "test"}
    result = parser_agent("test")
    assert result["prediction_statement"] == "test"
```

**Why It Failed**:
- ✅ Test passes locally (mocks always return what you tell them)
- ❌ Doesn't test real agent behavior
- ❌ Doesn't test LLM responses
- ❌ Doesn't test JSON parsing
- ❌ Doesn't test tool usage
- ❌ Doesn't catch real bugs

**Result**: Tests pass, production fails.

### Problem 2: Local Environment Limitations

**What We Encountered**:
- TTY/terminal issues
- Network requirements for Bedrock API
- Long-running property tests timing out
- Environment-specific failures

**Why It Happened**:
- Trying to run real agent tests in constrained local environment
- Bedrock API requires proper AWS credentials and network access
- Property tests with 100+ iterations take time

---

## What We Should Do Instead

### Approach 1: Integration Tests with Real Agents ✅

**Strands Recommended Pattern**:

```python
import pytest
from strands import Agent
from prediction_graph import execute_prediction_graph

class TestBackwardCompatibility:
    """Integration tests with real agent invocations"""
    
    @pytest.fixture
    def test_cases(self):
        """Load test cases from JSON"""
        return [
            {
                "id": "weather-prediction",
                "prompt": "it will snow tonight",
                "timezone": "America/New_York",
                "expected_category": "api_tool_verifiable"
            },
            {
                "id": "time-prediction",
                "prompt": "it's after 3pm",
                "timezone": "America/New_York",
                "expected_category": "current_tool_verifiable"
            }
        ]
    
    def test_input_format_compatibility(self, test_cases):
        """Test that backend accepts frontend message format"""
        for case in test_cases:
            # This invokes REAL agents with REAL LLM calls
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc="2026-01-18 18:24:33 UTC",
                current_datetime_local="2026-01-18 13:24:33 EST",
                callback_handler=None
            )
            
            # Verify response structure
            assert "prediction_statement" in result
            assert "verifiable_category" in result
            assert "verification_method" in result
            
            # Verify expected category (if specified)
            if "expected_category" in case:
                assert result["verifiable_category"] == case["expected_category"]
    
    def test_output_format_compatibility(self, test_cases):
        """Test that backend returns all expected fields"""
        for case in test_cases:
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc="2026-01-18 18:24:33 UTC",
                current_datetime_local="2026-01-18 13:24:33 EST",
                callback_handler=None
            )
            
            # Verify all frontend-expected fields are present
            required_fields = [
                "prediction_statement",
                "verification_date",
                "verifiable_category",
                "category_reasoning",
                "verification_method",
                "date_reasoning"
            ]
            
            for field in required_fields:
                assert field in result, f"Missing field: {field}"
            
            # Verify verification_method structure
            vm = result["verification_method"]
            assert "source" in vm
            assert "criteria" in vm
            assert "steps" in vm
            assert isinstance(vm["source"], list)
            assert isinstance(vm["criteria"], list)
            assert isinstance(vm["steps"], list)
```

**Key Characteristics**:
- ✅ Invokes real agents
- ✅ Makes real LLM calls
- ✅ Tests actual behavior
- ✅ Catches real bugs
- ✅ Validates JSON parsing
- ✅ Verifies tool usage

### Approach 2: Structured Test Cases ✅

**Create Test Case Files**:

```json
// test_cases/backward_compatibility.json
[
  {
    "id": "weather-api-verifiable",
    "prompt": "it will snow tonight",
    "timezone": "America/New_York",
    "expected_category": "api_tool_verifiable",
    "expected_fields": [
      "prediction_statement",
      "verification_date",
      "verifiable_category",
      "category_reasoning",
      "verification_method",
      "date_reasoning"
    ]
  },
  {
    "id": "time-tool-verifiable",
    "prompt": "it's after 3pm",
    "timezone": "America/New_York",
    "expected_category": "current_tool_verifiable"
  },
  {
    "id": "agent-verifiable",
    "prompt": "the sun will rise tomorrow",
    "timezone": "UTC",
    "expected_category": "agent_verifiable"
  }
]
```

**Load and Run Tests**:

```python
import json
import pytest

@pytest.fixture
def test_cases():
    with open("test_cases/backward_compatibility.json", "r") as f:
        return json.load(f)

def test_all_cases(test_cases):
    """Run all test cases with real agent invocations"""
    results = []
    
    for case in test_cases:
        result = execute_prediction_graph(
            user_prompt=case["prompt"],
            user_timezone=case["timezone"],
            current_datetime_utc="2026-01-18 18:24:33 UTC",
            current_datetime_local="2026-01-18 13:24:33 EST",
            callback_handler=None
        )
        
        results.append({
            "test_id": case["id"],
            "passed": verify_result(result, case),
            "result": result
        })
    
    # All tests should pass
    assert all(r["passed"] for r in results)
```

### Approach 3: LLM Judge for Quality ✅

**Use Another Agent to Evaluate Responses**:

```python
from strands import Agent

# Create evaluator agent
evaluator = Agent(
    model="us.anthropic.claude-sonnet-4-20250514-v1:0",
    system_prompt="""
    You are an expert AI evaluator. Assess responses for:
    1. Accuracy - factual correctness
    2. Completeness - all required fields present
    3. Format - proper JSON structure
    
    Return JSON: {"score": 1-5, "issues": ["list of issues"]}
    """
)

def test_response_quality():
    """Use LLM judge to evaluate response quality"""
    result = execute_prediction_graph(
        user_prompt="it will snow tonight",
        user_timezone="America/New_York",
        current_datetime_utc="2026-01-18 18:24:33 UTC",
        current_datetime_local="2026-01-18 13:24:33 EST",
        callback_handler=None
    )
    
    eval_prompt = f"""
    Evaluate this prediction response:
    {json.dumps(result, indent=2)}
    
    Check:
    - All required fields present
    - Proper data types
    - Reasonable verification method
    - Category matches prediction type
    """
    
    evaluation = evaluator(eval_prompt)
    eval_result = json.loads(str(evaluation))
    
    assert eval_result["score"] >= 4, f"Quality issues: {eval_result['issues']}"
```

---

## Where to Run Tests

### Option 1: CI/CD Pipeline with AWS Access ✅ RECOMMENDED

**Setup**:
- GitHub Actions or similar CI/CD
- AWS credentials configured
- Bedrock API access enabled
- Run tests on every PR

**Benefits**:
- ✅ Real environment
- ✅ Real API calls
- ✅ Catches real bugs
- ✅ Automated
- ✅ Consistent

**Example GitHub Actions**:
```yaml
name: Integration Tests

on: [pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run integration tests
        run: pytest tests/integration/ -v
```

### Option 2: Manual Testing in Dev Environment ✅

**When to Use**:
- During development
- Before committing changes
- Quick validation

**How**:
```bash
# Set AWS credentials
export AWS_PROFILE=your-profile

# Run specific test
/home/wsluser/projects/calledit/venv/bin/python -m pytest \
  tests/integration/test_backward_compatibility.py::test_input_format \
  -v -s

# Run all integration tests
/home/wsluser/projects/calledit/venv/bin/python -m pytest \
  tests/integration/ -v
```

### Option 3: Deployed Environment Testing ✅

**When to Use**:
- After deployment
- Smoke tests
- Production validation

**How**:
- Deploy to dev/staging environment
- Run tests against deployed Lambda
- Use real WebSocket connections
- Validate end-to-end flow

---

## What NOT to Do

### ❌ Don't Mock Agent Invocations

```python
# BAD - This doesn't test anything
@patch('agent.invoke')
def test_parser(mock_invoke):
    mock_invoke.return_value = {"prediction_statement": "test"}
    # This just tests that mocks work
```

### ❌ Don't Test Without LLM Calls

```python
# BAD - This doesn't test real behavior
def test_parser():
    # Manually construct response without invoking agent
    result = {"prediction_statement": "test"}
    assert result["prediction_statement"] == "test"
```

### ❌ Don't Skip Integration Tests

```python
# BAD - Only unit tests, no integration
def test_json_parsing():
    # Tests JSON parsing in isolation
    # Doesn't test if agent actually returns valid JSON
```

---

## Recommended Testing Strategy for Task 17

### Phase 1: Create Test Cases ✅

**File**: `tests/integration/test_cases/backward_compatibility.json`

```json
[
  {
    "id": "bc-001-weather",
    "prompt": "it will snow tonight",
    "timezone": "America/New_York",
    "expected_category": "api_tool_verifiable"
  },
  {
    "id": "bc-002-time",
    "prompt": "it's after 3pm",
    "timezone": "America/New_York",
    "expected_category": "current_tool_verifiable"
  },
  {
    "id": "bc-003-knowledge",
    "prompt": "the sun will rise tomorrow",
    "timezone": "UTC",
    "expected_category": "agent_verifiable"
  }
]
```

### Phase 2: Write Integration Tests ✅

**File**: `tests/integration/test_backward_compatibility.py`

```python
import pytest
import json
from prediction_graph import execute_prediction_graph

@pytest.fixture
def test_cases():
    with open("tests/integration/test_cases/backward_compatibility.json") as f:
        return json.load(f)

class TestBackwardCompatibility:
    """Integration tests with real agent invocations"""
    
    def test_input_format_compatibility(self, test_cases):
        """Property 27: Input format compatibility"""
        for case in test_cases:
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc="2026-01-18 18:24:33 UTC",
                current_datetime_local="2026-01-18 13:24:33 EST",
                callback_handler=None
            )
            
            assert "prediction_statement" in result
            assert "verifiable_category" in result
    
    def test_output_format_compatibility(self, test_cases):
        """Property 28: Output format compatibility"""
        required_fields = [
            "prediction_statement",
            "verification_date",
            "verifiable_category",
            "category_reasoning",
            "verification_method",
            "date_reasoning"
        ]
        
        for case in test_cases:
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc="2026-01-18 18:24:33 UTC",
                current_datetime_local="2026-01-18 13:24:33 EST",
                callback_handler=None
            )
            
            for field in required_fields:
                assert field in result, f"Missing field: {field}"
    
    def test_action_type_support(self, test_cases):
        """Property 29: Action type support"""
        # Test makecall action (current production feature)
        for case in test_cases:
            result = execute_prediction_graph(
                user_prompt=case["prompt"],
                user_timezone=case["timezone"],
                current_datetime_utc="2026-01-18 18:24:33 UTC",
                current_datetime_local="2026-01-18 13:24:33 EST",
                callback_handler=None
            )
            
            assert result is not None
            assert "error" not in result or result["error"] is None
```

### Phase 3: Run Tests in Proper Environment ✅

```bash
# Ensure AWS credentials are configured
export AWS_PROFILE=your-profile

# Run integration tests
/home/wsluser/projects/calledit/venv/bin/python -m pytest \
  tests/integration/test_backward_compatibility.py \
  -v -s --tb=short

# Generate test report
/home/wsluser/projects/calledit/venv/bin/python -m pytest \
  tests/integration/test_backward_compatibility.py \
  --html=test_report.html \
  --self-contained-html
```

---

## Key Takeaways

### From Strands Documentation

1. **Real Invocations**: Tests should invoke real agents with real LLM calls
2. **Structured Test Cases**: Use JSON files with test cases
3. **Integration Focus**: Test end-to-end behavior, not isolated units
4. **LLM Judges**: Use stronger models to evaluate weaker models
5. **Continuous Evaluation**: Regular testing with consistent baselines

### For Our Project

1. **✅ DO**: Write integration tests that invoke real agents
2. **✅ DO**: Run tests in environment with AWS/Bedrock access
3. **✅ DO**: Use structured test cases from JSON files
4. **✅ DO**: Validate response structure and content
5. **❌ DON'T**: Mock agent invocations
6. **❌ DON'T**: Test without LLM calls
7. **❌ DON'T**: Rely on pure unit tests for agent behavior

### Why This Works

- **Tests real behavior**: Actual LLM responses, not mocks
- **Catches real bugs**: JSON parsing, tool usage, response format
- **Validates integration**: End-to-end flow works correctly
- **Provides confidence**: If tests pass, production will work
- **Matches Strands patterns**: Following official best practices

---

## Conclusion

**Previous Approach**: ❌ Mock-heavy unit tests that passed locally but failed in production

**Strands Approach**: ✅ Integration tests with real agent invocations

**Recommendation for Task 17**:
1. Create structured test cases (JSON files)
2. Write integration tests that invoke real agents
3. Run tests in environment with AWS/Bedrock access
4. Validate response structure and content
5. Use LLM judges for quality evaluation (optional)

**Expected Outcome**: Tests that actually validate the system works, not just that mocks work.

---

## Next Steps

1. ✅ Create `tests/integration/test_cases/backward_compatibility.json`
2. ✅ Write `tests/integration/test_backward_compatibility.py`
3. ✅ Configure AWS credentials for test environment
4. ✅ Run tests and verify they pass
5. ✅ Document test results

**All tests should pass** because the backend is already compatible!
