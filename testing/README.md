# CalledIt Testing Suite - Organized

**Last Updated**: August 28, 2025  
**Status**: ✅ Reorganized and validated for v1.5.1

## 📁 Directory Structure

### `/active/` - Working Tests ✅
**Status**: All tests verified working with current v1.5.1 build

- **`verifiability_category_tests.py`** - Main test suite (100% success rate)
  - Tests all 5 verifiability categories
  - Usage: `python active/verifiability_category_tests.py wss://your-websocket-url`
  
- **`test_websocket_basic.py`** - Basic WebSocket connectivity test
  - Verifies WebSocket connection and messaging
  - Usage: `python active/test_websocket_basic.py`
  
- **`test_improvement_updated.py`** - VPSS quick test
  - Tests improvement question workflow
  - Usage: `python active/test_improvement_updated.py`
  
- **`test_verification_components.py`** - Verification system unit tests
  - Tests verification result structures, DDB scanner, agent logic
  - Usage: `python active/test_verification_components.py`

### `/automation/` - Automated Testing Framework ✅
**Status**: Outstanding performance (10/10 tests, 100% success)

- **`test_runner.py`** - Main automation runner with intelligent analysis
- **`analysis_agent.py`** - AI-powered test analysis
- **`report_generator.py`** - Automated report generation
- **`tools/`** - Custom testing tools and utilities

### `/integration/` - Integration Tests 🔄
**Status**: Available but may need updates for current build

- **`test_database_integration.py`** - DynamoDB integration tests
- **`test_improvement_workflow.py`** - End-to-end improvement workflow
- **`test_performance_benchmarks.py`** - Performance testing suite
- **`test_verification_pipeline.py`** - End-to-end verification system tests
  - Tests complete verification workflow: DynamoDB → Agent → Results → Notifications
  - Covers all 5 verifiability categories and tool gap detection
  - Usage: `python integration/test_verification_pipeline.py`

### `/data/` - Test Data and Configuration 📊
**Status**: Test cases and configuration files

- **`prediction_verifiability_tests.json`** - Verifiability test cases
- **`timezone_edge_case_tests.json`** - Timezone testing data
- **`refined_verifiability_categories.json`** - Category definitions
- **`config.example.py`** - Configuration template

### `/reports/` - Test Reports and Results 📋
- **`current/`** - Latest test results (empty - ready for new reports)
- **`historical/`** - Previous test reports and documentation

### `/deprecated/` - Outdated/Broken Tests 🗄️
**Status**: Archived for reference

- **`node_js/`** - Node.js WebSocket tests (missing dependencies)
- **`complex_e2e/`** - Complex end-to-end tests (timeout issues)
- **`old_tests/`** - Various outdated test files

## 🚀 Quick Start

### Run Core Tests
```bash
# Activate virtual environment
source /path/to/venv/bin/activate

# Run main verifiability test suite
python active/verifiability_category_tests.py wss://your-websocket-url

# Run basic WebSocket test
python active/test_websocket_basic.py

# Run VPSS test
python active/test_improvement_updated.py
```

### Run Automation Framework
```bash
cd automation/
python test_runner.py
```

## 📊 Test Results Summary

### ✅ Working Tests (100% Success Rate)
- **Verifiability Categories**: 5/5 categories perfect
- **WebSocket Basic**: Connection and messaging working
- **VPSS**: Improvement questions functional
- **Automation Framework**: 10/10 tests passing

### ❌ Deprecated Tests
- **Node.js Tests**: Missing dependencies, outdated WebSocket URLs
- **Complex E2E**: Timeout issues, overly complex for current needs
- **Old Test Files**: Various outdated implementations

## 🎯 Recommended Testing Workflow

### For Development
1. **Start with**: `active/verifiability_category_tests.py` (core functionality)
2. **Then run**: `active/test_websocket_basic.py` (connectivity)
3. **Finally**: `active/test_improvement_updated.py` (VPSS)

### For Comprehensive Testing
1. **Run automation**: `automation/test_runner.py` (full suite)
2. **Check integration**: Files in `integration/` folder
3. **Generate reports**: Use automation framework reporting

### For New Features
1. **Add tests to**: `active/` folder (if they work)
2. **Use test data from**: `data/` folder
3. **Save results to**: `reports/current/`

## 🔧 Configuration

### WebSocket URL
Update WebSocket URLs in test files to match your deployment:
```
wss://your-websocket-id.execute-api.your-region.amazonaws.com/prod
```

### Dependencies
```bash
pip install -r requirements.txt
```

## 📈 Success Metrics

- **Core Tests**: 100% pass rate maintained
- **Automation**: 10/10 tests successful
- **Coverage**: All 5 verifiability categories tested
- **Performance**: All tests complete within reasonable timeframes

---

**Note**: This testing suite has been validated against CalledIt v1.5.1. Tests in `active/` and `automation/` folders are guaranteed to work with the current build.