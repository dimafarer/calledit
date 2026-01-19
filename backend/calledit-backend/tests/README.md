# CalledIt Testing Framework

**Last Updated**: 2025-01-19  
**Approach**: Integration tests with real agent invocations (Strands best practice)

## Overview

This testing framework follows **Strands official best practices** for agent testing:
- ✅ Real agent invocations with real LLM calls
- ✅ Structured test cases from JSON files
- ✅ Integration testing focus (not mocks)
- ✅ End-to-end validation

**Reference**: [Strands Evaluation Documentation](https://strandsagents.com/latest/documentation/docs/user-guide/observability-evaluation/evaluation/)

## Why This Approach?

### ❌ Previous Approach (Deleted)
- Mock-heavy unit tests
- Tests passed locally but failed in production
- Didn't test real agent behavior
- Didn't catch real bugs

### ✅ Current Approach (Strands Best Practice)
- Real agent invocations
- Real LLM calls
- Tests actual behavior
- Catches real bugs
- Validates JSON parsing, tool usage, response format

## Directory Structure

```
tests/
├── pytest.ini                          # Pytest configuration
├── README.md                           # This file
├── integration/                        # Integration tests (real invocations)
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures
│   ├── test_cases/                    # Structured test data
│   │   ├── backward_compatibility.json
│   │   ├── parser_agent.json
│   │   ├── categorizer_agent.json
│   │   └── verification_builder.json
│   ├── test_backward_compatibility.py # Task 17 tests
│   ├── test_parser_agent.py          # Parser integration tests
│   ├── test_categorizer_agent.py     # Categorizer integration tests
│   └── test_verification_builder.py  # Verification Builder tests
```

## Running Tests

### Via Kiro IDE
1. Open the Testing panel in Kiro
2. Tests will be automatically discovered
3. Click to run individual tests or all tests
4. View results in the IDE

### Via Command Line

**Run all tests**:
```bash
cd backend/calledit-backend
/home/wsluser/projects/calledit/venv/bin/python -m pytest tests/ -v
```

**Run specific test file**:
```bash
/home/wsluser/projects/calledit/venv/bin/python -m pytest \
  tests/integration/test_backward_compatibility.py -v
```

**Run specific test**:
```bash
/home/wsluser/projects/calledit/venv/bin/python -m pytest \
  tests/integration/test_backward_compatibility.py::test_input_format_compatibility -v
```

**Run with markers**:
```bash
# Run only backward compatibility tests
/home/wsluser/projects/calledit/venv/bin/python -m pytest -m backward_compat -v

# Run only integration tests
/home/wsluser/projects/calledit/venv/bin/python -m pytest -m integration -v
```

**Generate HTML report**:
```bash
/home/wsluser/projects/calledit/venv/bin/python -m pytest \
  tests/ --html=test_report.html --self-contained-html
```

## Prerequisites

### AWS Credentials
Tests require AWS credentials to invoke real agents via Bedrock API.

**Credentials are configured at**: `~/.aws/credentials` (two levels up from project)

**Verify credentials**:
```bash
aws sts get-caller-identity
```

If credentials aren't configured, tests will fail with authentication errors.

### Python Dependencies
```bash
# Install test dependencies
/home/wsluser/projects/calledit/venv/bin/pip install -r requirements.txt
```

Required packages:
- `pytest>=7.0.0`
- `pytest-timeout>=2.1.0`
- `pytest-html>=3.1.0` (for HTML reports)
- `hypothesis>=6.0.0` (for property-based tests)

## Test Categories

### Integration Tests (`@pytest.mark.integration`)
Tests that invoke real agents with real LLM calls.

**Example**:
```python
@pytest.mark.integration
def test_parser_agent(test_cases):
    """Test parser agent with real invocations"""
    for case in test_cases:
        result = execute_prediction_graph(
            user_prompt=case["prompt"],
            user_timezone=case["timezone"],
            current_datetime_utc="2026-01-18 18:24:33 UTC",
            current_datetime_local="2026-01-18 13:24:33 EST",
            callback_handler=None
        )
        
        assert "prediction_statement" in result
        assert "verification_date" in result
```

### Backward Compatibility Tests (`@pytest.mark.backward_compat`)
Tests that verify the refactored backend maintains compatibility with the frontend.

**Task 17 Tests**:
- Input format compatibility (Property 27)
- Output format compatibility (Property 28)
- Action type support (Property 29)
- Event type consistency (Property 30)

## Test Data

Test cases are stored in JSON files under `integration/test_cases/`.

**Example** (`backward_compatibility.json`):
```json
[
  {
    "id": "weather-prediction",
    "prompt": "it will snow tonight",
    "timezone": "America/New_York",
    "expected_category": "api_tool_verifiable"
  }
]
```

## Writing New Tests

### 1. Create Test Case File

Add test cases to `integration/test_cases/your_test.json`:
```json
[
  {
    "id": "test-001",
    "prompt": "your test prediction",
    "timezone": "America/New_York",
    "expected_category": "agent_verifiable"
  }
]
```

### 2. Write Integration Test

Create `integration/test_your_feature.py`:
```python
import pytest
import json
from pathlib import Path
from prediction_graph import execute_prediction_graph

@pytest.fixture
def test_cases():
    """Load test cases"""
    test_data_dir = Path(__file__).parent / "test_cases"
    with open(test_data_dir / "your_test.json") as f:
        return json.load(f)

@pytest.mark.integration
def test_your_feature(test_cases, test_datetime):
    """Test your feature with real agent invocations"""
    for case in test_cases:
        # Invoke REAL agents with REAL LLM calls
        result = execute_prediction_graph(
            user_prompt=case["prompt"],
            user_timezone=case["timezone"],
            current_datetime_utc=test_datetime["utc"],
            current_datetime_local=test_datetime["local"],
            callback_handler=None
        )
        
        # Verify response
        assert "prediction_statement" in result
        assert result["verifiable_category"] == case["expected_category"]
```

### 3. Run Your Test

```bash
/home/wsluser/projects/calledit/venv/bin/python -m pytest \
  tests/integration/test_your_feature.py -v
```

## Key Principles

### ✅ DO
- Invoke real agents with real LLM calls
- Use structured test cases from JSON files
- Test end-to-end behavior
- Validate response structure and content
- Run tests in environment with AWS credentials

### ❌ DON'T
- Mock agent invocations
- Test without LLM calls
- Rely on pure unit tests for agent behavior
- Skip integration tests
- Test in environment without AWS access

## Troubleshooting

### Tests Fail with Authentication Error
**Problem**: AWS credentials not configured  
**Solution**: Verify `~/.aws/credentials` is configured correctly

### Tests Timeout
**Problem**: LLM calls taking too long  
**Solution**: Increase timeout in `pytest.ini` or use `-o timeout=600`

### Tests Pass Locally but Fail in CI
**Problem**: Different environment  
**Solution**: Ensure CI has AWS credentials configured

### Import Errors
**Problem**: Missing dependencies  
**Solution**: Install requirements: `pip install -r requirements.txt`

## References

- [Strands Evaluation Documentation](https://strandsagents.com/latest/documentation/docs/user-guide/observability-evaluation/evaluation/)
- [Testing Strategy Analysis](.kiro/specs/strands-graph-refactor/TESTING_STRATEGY_ANALYSIS.md)
- [Backward Compatibility Analysis](.kiro/specs/strands-graph-refactor/BACKWARD_COMPATIBILITY_ANALYSIS.md)
- [Strands Best Practices](.kiro/steering/strands-best-practices.md)

## Educational Value

This testing framework demonstrates:
1. **Strands best practices** - Following official documentation
2. **Real testing** - Not mocks, actual behavior
3. **Integration focus** - End-to-end validation
4. **Structured approach** - JSON test cases, clear organization
5. **Production confidence** - If tests pass, production works

**Key Lesson**: Tests should validate real behavior, not mock behavior!
