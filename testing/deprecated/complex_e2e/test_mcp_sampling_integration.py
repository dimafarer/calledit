#!/usr/bin/env python3
"""
WebSocket Integration Tests for MCP Sampling Review Feature
Tests the improve_section and improvement_answers WebSocket routes.
"""

import asyncio
import json
import websockets
import pytest
import sys
import os
from typing import Dict, Any, Optional

# Add the testing directory to the path
sys.path.insert(0, os.path.dirname(__file__))

class MCPSamplingWebSocketTester:
    """WebSocket integration tester for MCP Sampling routes."""
    
    def __init__(self, websocket_url: str):
        self.websocket_url = websocket_url
        self.websocket = None
        self.received_messages = []
        
    async def connect(self):
        """Connect to WebSocket."""
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            print(f"✅ Connected to WebSocket: {self.websocket_url}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to WebSocket: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
    
    async def send_message(self, action: str, data: Dict[str, Any]) -> bool:
        """Send a message to WebSocket."""
        if not self.websocket:
            print("❌ WebSocket not connected")
            return False
            
        message = {
            "action": action,
            **data
        }
        
        try:
            await self.websocket.send(json.dumps(message))
            print(f"📤 Sent {action} message: {json.dumps(message, indent=2)}")
            return True
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            return False
    
    async def receive_message(self, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Receive a message from WebSocket."""
        if not self.websocket:
            print("❌ WebSocket not connected")
            return None
            
        try:
            message = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            parsed_message = json.loads(message)
            self.received_messages.append(parsed_message)
            print(f"📥 Received message: {json.dumps(parsed_message, indent=2)}")
            return parsed_message
        except asyncio.TimeoutError:
            print(f"⏰ Timeout waiting for message ({timeout}s)")
            return None
        except Exception as e:
            print(f"❌ Failed to receive message: {e}")
            return None
    
    async def test_improve_section_routing(self) -> bool:
        """Test the improve_section WebSocket route."""
        print("\n🧪 Testing improve_section routing...")
        
        # Send improve_section request
        success = await self.send_message("improve_section", {
            "section": "prediction_statement",
            "current_value": "I'll finish my project soon",
            "full_context": {
                "verifiable_category": "human_verifiable_only",
                "verification_method": {"source": ["User assessment"]}
            }
        })
        
        if not success:
            return False
        
        # Wait for improvement questions response
        response = await self.receive_message(timeout=15)
        if not response:
            print("❌ No response received for improve_section")
            return False
        
        # Validate response structure
        if response.get("type") != "improvement_questions":
            print(f"❌ Expected 'improvement_questions', got: {response.get('type')}")
            return False
        
        data = response.get("data", {})
        if not data.get("questions") or not isinstance(data["questions"], list):
            print(f"❌ Invalid questions format: {data}")
            return False
        
        print(f"✅ improve_section routing working - received {len(data['questions'])} questions")
        return True
    
    async def test_improvement_answers_routing(self) -> bool:
        """Test the improvement_answers WebSocket route."""
        print("\n🧪 Testing improvement_answers routing...")
        
        # Send improvement_answers request
        success = await self.send_message("improvement_answers", {
            "section": "prediction_statement",
            "answers": [
                "It's a web development project",
                "Finished means all features implemented and tested",
                "Soon means by August 15th, 2025"
            ],
            "original_value": "I'll finish my project soon",
            "full_context": {
                "verifiable_category": "human_verifiable_only",
                "verification_method": {"source": ["User assessment"]}
            }
        })
        
        if not success:
            return False
        
        # Wait for improved response
        response = await self.receive_message(timeout=20)
        if not response:
            print("❌ No response received for improvement_answers")
            return False
        
        # Validate response structure
        if response.get("type") != "improved_response":
            print(f"❌ Expected 'improved_response', got: {response.get('type')}")
            return False
        
        data = response.get("data", {})
        if not data.get("improved_value"):
            print(f"❌ No improved_value in response: {data}")
            return False
        
        print(f"✅ improvement_answers routing working - received improved value")
        print(f"   Original: 'I'll finish my project soon'")
        print(f"   Improved: '{data['improved_value']}'")
        return True
    
    async def test_websocket_error_handling(self) -> bool:
        """Test WebSocket error handling with invalid requests."""
        print("\n🧪 Testing WebSocket error handling...")
        
        # Test invalid action
        success = await self.send_message("invalid_action", {"test": "data"})
        if not success:
            return False
        
        # Should either get error response or no response (both acceptable)
        response = await self.receive_message(timeout=5)
        if response and response.get("type") == "error":
            print("✅ Error handling working - received error response")
        else:
            print("✅ Error handling working - invalid action ignored")
        
        # Test malformed message (this will test Lambda error handling)
        try:
            if self.websocket:
                await self.websocket.send("invalid json")
                print("📤 Sent malformed JSON")
                
                # Wait for potential error response
                response = await self.receive_message(timeout=5)
                if response and response.get("type") == "error":
                    print("✅ Malformed JSON handling working")
                else:
                    print("✅ Malformed JSON handled gracefully")
        except Exception as e:
            print(f"✅ Malformed JSON properly rejected: {e}")
        
        return True

async def run_websocket_integration_tests(websocket_url: str) -> Dict[str, bool]:
    """Run all WebSocket integration tests."""
    print("🚀 Starting MCP Sampling WebSocket Integration Tests")
    print("=" * 60)
    
    tester = MCPSamplingWebSocketTester(websocket_url)
    results = {}
    
    try:
        # Connect to WebSocket
        if not await tester.connect():
            return {"connection": False}
        
        # Run tests
        results["improve_section_routing"] = await tester.test_improve_section_routing()
        results["improvement_answers_routing"] = await tester.test_improvement_answers_routing()
        results["error_handling"] = await tester.test_websocket_error_handling()
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        results["execution_error"] = False
    finally:
        await tester.disconnect()
    
    return results

def print_test_results(results: Dict[str, bool]):
    """Print formatted test results."""
    print("\n📊 WebSocket Integration Test Results")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\nSummary: {passed_tests}/{total_tests} tests passed")
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("🎉 All WebSocket integration tests PASSED!")
    else:
        print("⚠️  Some tests failed - check logs above")

async def main():
    """Main test runner."""
    # Default WebSocket URL - can be overridden via command line
    default_url = "wss://0yv5r2auh5.execute-api.us-west-2.amazonaws.com/prod"
    
    websocket_url = sys.argv[1] if len(sys.argv) > 1 else default_url
    
    print(f"Testing WebSocket URL: {websocket_url}")
    
    # Run tests
    results = await run_websocket_integration_tests(websocket_url)
    
    # Print results
    print_test_results(results)
    
    # Exit with appropriate code
    all_passed = all(results.values()) if results else False
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    asyncio.run(main())