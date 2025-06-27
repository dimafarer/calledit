# CalledIt Testing Suite

This directory contains all testing-related files for the CalledIt application.

## Structure

```
testing/
├── README.md                           # This file
├── timezone_edge_case_tests.json       # Test case definitions
├── test_runner.md                      # Manual testing template
├── automated_test_plan.md              # Implementation plan for automation
└── automation/                         # Automated testing implementation
    ├── test_runner.py                  # Main test runner
    ├── api_client.py                   # WebSocket API client
    ├── requirements.txt                # Dependencies
    └── tools/                          # Custom Strands tools
```

## Test Types

### Manual Testing
- Use `test_runner.md` for manual test execution
- Test cases defined in `timezone_edge_case_tests.json`

### Automated Testing
- Implementation plan in `automated_test_plan.md`
- Automated tools in `automation/` directory

## Usage

### Manual Testing
1. Open `test_runner.md`
2. Follow the testing process
3. Record results in the template

### Automated Testing
1. Navigate to `automation/` directory
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `python test_runner.py`

## Test Cases

The test suite focuses on timezone and relative time edge cases:
1. Market close times
2. Vague time references (morning, evening)
3. Cross-day boundaries
4. Business hours
5. Ambiguous time expressions

See `timezone_edge_case_tests.json` for complete test definitions.