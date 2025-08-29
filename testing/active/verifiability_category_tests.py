#!/usr/bin/env python3
"""
Verifiability Category Tests for CalledIt

Tests the 5 verifiability categories:
1. agent_verifiable
2. current_tool_verifiable  
3. strands_tool_verifiable
4. api_tool_verifiable
5. human_verifiable_only
"""

import json
import websocket
import time
import sys
from datetime import datetime

class VerifiabilityCategoryTester:
    def __init__(self, websocket_url):
        self.websocket_url = websocket_url
        self.test_results = []
        
    def test_category(self, prediction_text, expected_category, test_name):
        """Test a single prediction and verify its category"""
        print(f"\n🧪 Testing: {test_name}")
        print(f"Prediction: {prediction_text}")
        print(f"Expected: {expected_category}")
        
        try:
            # Connect to WebSocket
            ws = websocket.create_connection(self.websocket_url)
            
            # Send prediction
            message = {
                "action": "makecall",
                "prompt": prediction_text,
                "timezone": "America/New_York"
            }
            ws.send(json.dumps(message))
            
            # Collect response
            response_data = None
            timeout = 60  # 60 second timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    result = ws.recv()
                    data = json.loads(result)
                    
                    if data.get("type") == "call_response":
                        response_data = json.loads(data.get("content", "{}"))
                        break
                        
                except websocket.WebSocketTimeoutError:
                    continue
                    
            ws.close()
            
            if not response_data:
                print("❌ TIMEOUT - No response received")
                self.test_results.append({
                    "test_name": test_name,
                    "prediction": prediction_text,
                    "expected": expected_category,
                    "actual": "TIMEOUT",
                    "passed": False
                })
                return False
                
            actual_category = response_data.get("verifiable_category", "MISSING")
            category_reasoning = response_data.get("category_reasoning", "No reasoning")
            
            passed = actual_category == expected_category
            status = "✅ PASS" if passed else "❌ FAIL"
            
            print(f"Actual: {actual_category}")
            print(f"Reasoning: {category_reasoning}")
            print(f"Result: {status}")
            
            self.test_results.append({
                "test_name": test_name,
                "prediction": prediction_text,
                "expected": expected_category,
                "actual": actual_category,
                "reasoning": category_reasoning,
                "passed": passed
            })
            
            return passed
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            self.test_results.append({
                "test_name": test_name,
                "prediction": prediction_text,
                "expected": expected_category,
                "actual": f"ERROR: {str(e)}",
                "passed": False
            })
            return False
    
    def run_all_tests(self):
        """Run all verifiability category tests"""
        print("🚀 Starting Verifiability Category Tests")
        print("=" * 50)
        
        test_cases = [
            {
                "prediction": "The sun will rise tomorrow morning",
                "expected": "agent_verifiable",
                "name": "Agent Verifiable - Natural Law"
            },
            {
                "prediction": "It's currently past 11:00 PM",
                "expected": "current_tool_verifiable", 
                "name": "Current Tool Verifiable - Time Check"
            },
            {
                "prediction": "Calculate: 15% compound interest on $1000 over 5 years will exceed $2000",
                "expected": "strands_tool_verifiable",
                "name": "Strands Tool Verifiable - Math Calculation"
            },
            {
                "prediction": "Bitcoin will hit $100k tomorrow",
                "expected": "api_tool_verifiable",
                "name": "API Tool Verifiable - Market Data"
            },
            {
                "prediction": "I will feel happy when I wake up tomorrow",
                "expected": "human_verifiable_only",
                "name": "Human Verifiable Only - Subjective Feeling"
            }
        ]
        
        passed_tests = 0
        total_tests = len(test_cases)
        
        for test_case in test_cases:
            if self.test_category(
                test_case["prediction"],
                test_case["expected"], 
                test_case["name"]
            ):
                passed_tests += 1
            
            # Small delay between tests
            time.sleep(2)
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Print detailed results
        print("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result["passed"] else "❌"
            print(f"{status} {result['test_name']}")
            print(f"   Expected: {result['expected']}")
            print(f"   Actual: {result['actual']}")
            if result.get("reasoning"):
                print(f"   Reasoning: {result['reasoning'][:100]}...")
            print()
        
        return passed_tests == total_tests

def main():
    # WebSocket URL - update this to match your deployment
    websocket_url = "wss://0yv5r2auh5.execute-api.us-west-2.amazonaws.com/prod"
    
    if len(sys.argv) > 1:
        websocket_url = sys.argv[1]
    
    print(f"🔗 Using WebSocket URL: {websocket_url}")
    
    tester = VerifiabilityCategoryTester(websocket_url)
    success = tester.run_all_tests()
    
    if success:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()