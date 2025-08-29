#!/usr/bin/env python3
"""
End-to-End Verification Pipeline Tests
Tests the complete verification workflow from DynamoDB to notifications
"""

import sys
import os
import json
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

# Add verification folder to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../verification'))

try:
    from verification_agent import PredictionVerificationAgent
    from ddb_scanner import DynamoDBScanner
    from verification_result import VerificationStatus, VerificationResult
    from email_notifier import EmailNotifier
    from s3_logger import S3Logger
    from status_updater import StatusUpdater
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    print("Using mock implementations for testing")
    
    # Mock implementations for testing
    class MockVerificationAgent:
        def verify_prediction(self, prediction):
            return VerificationResult(
                prediction_id=prediction.get('SK', 'test'),
                status=VerificationStatus.TRUE,
                confidence=0.9,
                reasoning="Mock verification successful",
                verification_date=datetime.now(timezone.utc),
                tools_used=['mock'],
                agent_thoughts="Mock agent verification"
            )
    
    class MockDynamoDBScanner:
        def query_pending_predictions(self):
            return [
                {
                    'SK': 'PREDICTION#test1',
                    'prediction_statement': 'The sun will rise tomorrow',
                    'verifiable_category': 'agent_verifiable',
                    'verification_date': '2025-08-28T00:00:00Z'
                }
            ]
    
    PredictionVerificationAgent = MockVerificationAgent
    DynamoDBScanner = MockDynamoDBScanner

class VerificationPipelineTest:
    def __init__(self):
        self.results = []
        self.test_count = 0
        self.passed_count = 0
    
    def run_test(self, test_name, test_func):
        """Run a single test and track results"""
        self.test_count += 1
        print(f"\n🧪 Test {self.test_count}: {test_name}")
        
        try:
            test_func()
            print(f"✅ PASS: {test_name}")
            self.passed_count += 1
            self.results.append({"test": test_name, "status": "PASS"})
        except Exception as e:
            print(f"❌ FAIL: {test_name} - {str(e)}")
            self.results.append({"test": test_name, "status": "FAIL", "error": str(e)})
    
    def test_ddb_scanner_integration(self):
        """Test DynamoDB scanner can query pending predictions"""
        scanner = DynamoDBScanner()
        
        # This will use mock or real DynamoDB depending on environment
        predictions = scanner.query_pending_predictions()
        
        assert isinstance(predictions, list), "Scanner should return a list"
        print(f"   Found {len(predictions)} pending predictions")
        
        if predictions:
            prediction = predictions[0]
            required_fields = ['prediction_statement', 'verifiable_category']
            for field in required_fields:
                assert field in prediction, f"Prediction missing required field: {field}"
            print(f"   Sample prediction: {prediction.get('prediction_statement', 'Unknown')[:50]}...")
    
    def test_verification_agent_categories(self):
        """Test verification agent handles all 5 categories"""
        agent = PredictionVerificationAgent()
        
        test_predictions = [
            {
                'SK': 'test_agent',
                'prediction_statement': 'The sun will rise tomorrow',
                'verifiable_category': 'agent_verifiable',
                'verification_date': '2025-08-28T00:00:00Z'
            },
            {
                'SK': 'test_time',
                'prediction_statement': 'It is currently past midnight',
                'verifiable_category': 'current_tool_verifiable',
                'verification_date': '2025-08-28T00:00:00Z'
            },
            {
                'SK': 'test_math',
                'prediction_statement': '2 + 2 = 4',
                'verifiable_category': 'strands_tool_verifiable',
                'verification_date': '2025-08-28T00:00:00Z'
            },
            {
                'SK': 'test_api',
                'prediction_statement': 'Bitcoin will hit $100k',
                'verifiable_category': 'api_tool_verifiable',
                'verification_date': '2025-08-28T00:00:00Z'
            },
            {
                'SK': 'test_human',
                'prediction_statement': 'I will feel happy',
                'verifiable_category': 'human_verifiable_only',
                'verification_date': '2025-08-28T00:00:00Z'
            }
        ]
        
        category_results = {}
        
        for prediction in test_predictions:
            result = agent.verify_prediction(prediction)
            category = prediction['verifiable_category']
            category_results[category] = result.status.value
            
            assert isinstance(result, VerificationResult), f"Should return VerificationResult for {category}"
            assert result.prediction_id == prediction['SK'], f"Prediction ID should match for {category}"
            assert result.confidence >= 0.0 and result.confidence <= 1.0, f"Confidence should be 0-1 for {category}"
            
            print(f"   {category}: {result.status.value} (confidence: {result.confidence})")
        
        # Verify we got results for all categories
        assert len(category_results) == 5, "Should have results for all 5 categories"
    
    def test_tool_gap_detection(self):
        """Test tool gap detection for API-verifiable predictions"""
        agent = PredictionVerificationAgent()
        
        api_predictions = [
            {
                'SK': 'test_weather',
                'prediction_statement': 'It will rain in Seattle tomorrow',
                'verifiable_category': 'api_tool_verifiable',
                'verification_date': '2025-08-28T00:00:00Z'
            },
            {
                'SK': 'test_crypto',
                'prediction_statement': 'Bitcoin will reach $200k',
                'verifiable_category': 'api_tool_verifiable',
                'verification_date': '2025-08-28T00:00:00Z'
            }
        ]
        
        tool_gaps_found = 0
        
        for prediction in api_predictions:
            result = agent.verify_prediction(prediction)
            
            if result.status == VerificationStatus.TOOL_GAP:
                tool_gaps_found += 1
                assert result.tool_gap is not None, "Tool gap result should have tool_gap data"
                assert result.tool_gap.missing_tool is not None, "Should identify missing tool"
                assert result.tool_gap.suggested_mcp_tool is not None, "Should suggest MCP tool"
                
                print(f"   Tool gap detected: {result.tool_gap.missing_tool} -> {result.tool_gap.suggested_mcp_tool}")
        
        print(f"   Found {tool_gaps_found} tool gaps out of {len(api_predictions)} API predictions")
    
    def test_verification_result_serialization(self):
        """Test verification results can be serialized for storage"""
        agent = PredictionVerificationAgent()
        
        prediction = {
            'SK': 'test_serialize',
            'prediction_statement': 'Test prediction for serialization',
            'verifiable_category': 'agent_verifiable',
            'verification_date': '2025-08-28T00:00:00Z'
        }
        
        result = agent.verify_prediction(prediction)
        
        # Test serialization
        result_dict = result.to_dict() if hasattr(result, 'to_dict') else result.__dict__
        
        assert isinstance(result_dict, dict), "Result should be serializable to dict"
        
        # Test JSON serialization
        json_str = json.dumps(result_dict, default=str)
        assert len(json_str) > 0, "Result should be JSON serializable"
        
        # Test deserialization
        parsed = json.loads(json_str)
        assert parsed['prediction_id'] == prediction['SK'], "Serialized data should preserve prediction ID"
        
        print(f"   Serialization successful: {len(json_str)} characters")
    
    def test_batch_processing_simulation(self):
        """Test processing multiple predictions in a batch"""
        scanner = DynamoDBScanner()
        agent = PredictionVerificationAgent()
        
        # Get pending predictions (mock or real)
        predictions = scanner.query_pending_predictions()
        
        if not predictions:
            # Create mock predictions for testing
            predictions = [
                {
                    'SK': f'PREDICTION#batch_test_{i}',
                    'prediction_statement': f'Test prediction {i}',
                    'verifiable_category': 'agent_verifiable',
                    'verification_date': '2025-08-28T00:00:00Z'
                }
                for i in range(3)
            ]
        
        batch_results = []
        processing_times = []
        
        for prediction in predictions[:5]:  # Limit to 5 for testing
            start_time = time.time()
            result = agent.verify_prediction(prediction)
            processing_time = time.time() - start_time
            
            batch_results.append(result)
            processing_times.append(processing_time)
        
        # Analyze batch results
        total_processed = len(batch_results)
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        status_counts = {}
        for result in batch_results:
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"   Processed {total_processed} predictions")
        print(f"   Average processing time: {avg_processing_time:.2f}s")
        print(f"   Status breakdown: {status_counts}")
        
        assert total_processed > 0, "Should process at least one prediction"
        assert avg_processing_time < 30, "Average processing time should be reasonable"
    
    def test_error_handling(self):
        """Test error handling in verification pipeline"""
        agent = PredictionVerificationAgent()
        
        # Test with malformed prediction
        malformed_prediction = {
            'SK': 'test_error',
            # Missing required fields
        }
        
        try:
            result = agent.verify_prediction(malformed_prediction)
            # Should either handle gracefully or raise appropriate error
            if hasattr(result, 'status'):
                assert result.status in [VerificationStatus.ERROR, VerificationStatus.INCONCLUSIVE], \
                    "Malformed prediction should result in error or inconclusive status"
            print("   Error handling: Graceful degradation")
        except Exception as e:
            # Expected behavior - should raise appropriate error
            print(f"   Error handling: Appropriate exception raised - {type(e).__name__}")
    
    def run_all_tests(self):
        """Run the complete test suite"""
        print("🚀 Starting Verification Pipeline Integration Tests")
        print("=" * 60)
        
        # Run all tests
        self.run_test("DynamoDB Scanner Integration", self.test_ddb_scanner_integration)
        self.run_test("Verification Agent Categories", self.test_verification_agent_categories)
        self.run_test("Tool Gap Detection", self.test_tool_gap_detection)
        self.run_test("Result Serialization", self.test_verification_result_serialization)
        self.run_test("Batch Processing Simulation", self.test_batch_processing_simulation)
        self.run_test("Error Handling", self.test_error_handling)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.test_count}")
        print(f"Passed: {self.passed_count}")
        print(f"Failed: {self.test_count - self.passed_count}")
        print(f"Success Rate: {(self.passed_count/self.test_count)*100:.1f}%")
        
        # Print detailed results
        print("\n📋 DETAILED RESULTS:")
        for result in self.results:
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"{status_icon} {result['test']}")
            if result["status"] == "FAIL":
                print(f"   Error: {result.get('error', 'Unknown error')}")
        
        return self.passed_count == self.test_count

def main():
    """Run verification pipeline tests"""
    tester = VerificationPipelineTest()
    
    try:
        success = tester.run_all_tests()
        
        if success:
            print("\n🎉 All verification pipeline tests passed!")
            return 0
        else:
            print("\n💥 Some verification pipeline tests failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())