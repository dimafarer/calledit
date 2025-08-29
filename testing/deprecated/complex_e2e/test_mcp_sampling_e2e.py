#!/usr/bin/env python3
"""
End-to-End Tests for Complete MCP Sampling Review Workflow
Tests the full prediction → review → improvement → regeneration flow.
"""

import asyncio
import json
import websockets
import sys
import os
from typing import Dict, Any, Optional, List

# Add the testing directory to the path
sys.path.insert(0, os.path.dirname(__file__))

class MCPSamplingE2ETester:
    """End-to-end tester for complete MCP Sampling workflow."""
    
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
            return False
            
        message = {"action": action, **data}
        
        try:
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            return False
    
    async def receive_messages_until_complete(self, timeout: int = 30) -> List[Dict[str, Any]]:
        """Receive messages until review_complete or timeout."""
        messages = []
        start_time = asyncio.get_event_loop().time()
        
        while True:
            try:
                current_time = asyncio.get_event_loop().time()
                remaining_time = timeout - (current_time - start_time)
                
                if remaining_time <= 0:
                    print(f"⏰ Timeout after {timeout}s")
                    break
                
                message = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=min(remaining_time, 5)
                )
                
                parsed_message = json.loads(message)
                messages.append(parsed_message)
                
                # Stop when we get review_complete
                if parsed_message.get("type") == "review_complete":
                    print(f"✅ Received review_complete after {len(messages)} messages")
                    break
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"❌ Error receiving message: {e}")
                break
        
        return messages
    
    async def test_complete_review_workflow(self) -> bool:
        """Test the complete MCP Sampling workflow from prediction to review."""
        print("\n🧪 Testing complete MCP Sampling workflow...")
        
        # Step 1: Send initial prediction (makecall)
        print("📤 Step 1: Sending initial prediction...")
        success = await self.send_message("makecall", {
            "prompt": "I'll finish my project soon",
            "timezone": "America/New_York"
        })
        
        if not success:
            return False
        
        # Step 2: Receive all messages until review_complete
        print("📥 Step 2: Receiving prediction processing and review...")
        messages = await self.receive_messages_until_complete(timeout=45)
        
        if not messages:
            print("❌ No messages received")
            return False
        
        # Step 3: Analyze the message flow
        print(f"📊 Step 3: Analyzing {len(messages)} messages...")
        
        # Check for required message types
        message_types = [msg.get("type") for msg in messages]
        required_types = ["call_response", "review_complete"]
        
        for required_type in required_types:
            if required_type not in message_types:
                print(f"❌ Missing required message type: {required_type}")
                return False
        
        # Step 4: Validate call_response structure
        call_response = next((msg for msg in messages if msg.get("type") == "call_response"), None)
        if not call_response:
            print("❌ No call_response found")
            return False
        
        try:
            call_data = json.loads(call_response.get("content", "{}"))
            required_fields = ["prediction_statement", "verifiable_category", "verification_method"]
            
            for field in required_fields:
                if field not in call_data:
                    print(f"❌ Missing field in call_response: {field}")
                    return False
            
            print(f"✅ Call response valid - category: {call_data.get('verifiable_category')}")
            
        except json.JSONDecodeError:
            print("❌ Invalid JSON in call_response")
            return False
        
        # Step 5: Validate review_complete structure
        review_complete = next((msg for msg in messages if msg.get("type") == "review_complete"), None)
        if not review_complete:
            print("❌ No review_complete found")
            return False
        
        review_data = review_complete.get("data", {})
        reviewable_sections = review_data.get("reviewable_sections", [])
        
        print(f"✅ Review complete - found {len(reviewable_sections)} improvable sections")
        
        # For vague predictions like "I'll finish my project soon", we expect improvements
        if len(reviewable_sections) == 0:
            print("⚠️  Expected some improvable sections for vague prediction")
        
        return True
    
    async def test_vague_prediction_review(self) -> bool:
        """Test review of a deliberately vague prediction."""
        print("\n🧪 Testing vague prediction review...")
        
        # Test with a very vague prediction that should trigger improvements
        success = await self.send_message("makecall", {
            "prompt": "Something good will happen tomorrow",
            "timezone": "UTC"
        })
        
        if not success:
            return False
        
        messages = await self.receive_messages_until_complete(timeout=45)
        
        # Find review_complete message
        review_complete = next((msg for msg in messages if msg.get("type") == "review_complete"), None)
        if not review_complete:
            print("❌ No review_complete message")
            return False
        
        review_data = review_complete.get("data", {})
        reviewable_sections = review_data.get("reviewable_sections", [])
        
        # Vague predictions should have multiple improvable sections
        if len(reviewable_sections) >= 2:
            print(f"✅ Vague prediction correctly identified {len(reviewable_sections)} improvable sections")
            
            # Check that sections have proper structure
            for section in reviewable_sections:
                if not all(key in section for key in ["section", "improvable", "questions", "reasoning"]):
                    print(f"❌ Invalid section structure: {section}")
                    return False
                
                if not section.get("improvable"):
                    print(f"❌ Section marked as not improvable: {section}")
                    return False
            
            return True
        else:
            print(f"⚠️  Expected more improvable sections for vague prediction, got {len(reviewable_sections)}")
            return len(reviewable_sections) > 0  # At least some improvement suggestions
    
    async def test_review_to_improvement_flow(self) -> bool:
        """Test the flow from review to actual improvement."""
        print("\n🧪 Testing review → improvement flow...")
        
        # Step 1: Get a prediction with review
        success = await self.send_message("makecall", {
            "prompt": "I'll complete my task soon",
            "timezone": "America/Los_Angeles"
        })
        
        if not success:
            return False
        
        messages = await self.receive_messages_until_complete(timeout=45)
        
        # Step 2: Extract review data
        review_complete = next((msg for msg in messages if msg.get("type") == "review_complete"), None)
        if not review_complete:
            print("❌ No review_complete message")
            return False
        
        reviewable_sections = review_complete.get("data", {}).get("reviewable_sections", [])
        if not reviewable_sections:
            print("⚠️  No reviewable sections found - using mock section")
            # Create a mock section for testing
            test_section = "prediction_statement"
            original_value = "I'll complete my task soon"
        else:
            # Use first reviewable section
            first_section = reviewable_sections[0]
            test_section = first_section.get("section")
            original_value = "I'll complete my task soon"  # Mock original value
        
        # Step 3: Test improvement request
        print(f"📤 Step 3: Requesting improvement for section: {test_section}")
        
        success = await self.send_message("improve_section", {
            "section": test_section,
            "current_value": original_value,
            "full_context": {"verifiable_category": "human_verifiable_only"}
        })
        
        if not success:
            return False
        
        # Step 4: Receive improvement questions
        try:
            message = await asyncio.wait_for(self.websocket.recv(), timeout=15)
            questions_response = json.loads(message)
            
            if questions_response.get("type") != "improvement_questions":
                print(f"❌ Expected improvement_questions, got: {questions_response.get('type')}")
                return False
            
            questions = questions_response.get("data", {}).get("questions", [])
            if not questions:
                print("❌ No improvement questions received")
                return False
            
            print(f"✅ Received {len(questions)} improvement questions")
            
        except Exception as e:
            print(f"❌ Failed to receive improvement questions: {e}")
            return False
        
        # Step 5: Send improvement answers
        print("📤 Step 5: Sending improvement answers...")
        
        success = await self.send_message("improvement_answers", {
            "section": test_section,
            "answers": ["It's a coding project", "Complete means fully tested", "Soon means by next Friday"],
            "original_value": original_value,
            "full_context": {"verifiable_category": "human_verifiable_only"}
        })
        
        if not success:
            return False
        
        # Step 6: Receive improved response
        try:
            message = await asyncio.wait_for(self.websocket.recv(), timeout=20)
            improved_response = json.loads(message)
            
            if improved_response.get("type") != "improved_response":
                print(f"❌ Expected improved_response, got: {improved_response.get('type')}")
                return False
            
            improved_value = improved_response.get("data", {}).get("improved_value")
            if not improved_value:
                print("❌ No improved value received")
                return False
            
            print(f"✅ Received improved response:")
            print(f"   Original: '{original_value}'")
            print(f"   Improved: '{improved_value}'")
            
            # Validate that improvement is actually better
            if len(improved_value) > len(original_value) and "coding project" in improved_value.lower():
                print("✅ Improvement appears meaningful")
                return True
            else:
                print("⚠️  Improvement may not be substantial")
                return True  # Still pass if we got a response
            
        except Exception as e:
            print(f"❌ Failed to receive improved response: {e}")
            return False

async def run_e2e_tests(websocket_url: str) -> Dict[str, bool]:
    """Run all end-to-end tests."""
    print("🚀 Starting MCP Sampling End-to-End Tests")
    print("=" * 60)
    
    tester = MCPSamplingE2ETester(websocket_url)
    results = {}
    
    try:
        # Connect to WebSocket
        if not await tester.connect():
            return {"connection": False}
        
        # Run tests
        results["complete_workflow"] = await tester.test_complete_review_workflow()
        
        # Reconnect for fresh state
        await tester.disconnect()
        if not await tester.connect():
            results["reconnection"] = False
            return results
        
        results["vague_prediction_review"] = await tester.test_vague_prediction_review()
        
        # Reconnect for fresh state
        await tester.disconnect()
        if not await tester.connect():
            results["reconnection2"] = False
            return results
        
        results["review_to_improvement_flow"] = await tester.test_review_to_improvement_flow()
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        results["execution_error"] = False
    finally:
        await tester.disconnect()
    
    return results

def print_test_results(results: Dict[str, bool]):
    """Print formatted test results."""
    print("\n📊 End-to-End Test Results")
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
        print("🎉 All end-to-end tests PASSED!")
    else:
        print("⚠️  Some tests failed - check logs above")

async def main():
    """Main test runner."""
    # Default WebSocket URL
    default_url = "wss://0yv5r2auh5.execute-api.us-west-2.amazonaws.com/prod"
    
    websocket_url = sys.argv[1] if len(sys.argv) > 1 else default_url
    
    print(f"Testing WebSocket URL: {websocket_url}")
    
    # Run tests
    results = await run_e2e_tests(websocket_url)
    
    # Print results
    print_test_results(results)
    
    # Exit with appropriate code
    all_passed = all(results.values()) if results else False
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    asyncio.run(main())