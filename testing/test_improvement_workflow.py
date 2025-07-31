#!/usr/bin/env python3
"""
Test the improvement workflow (Phase 3 & 4 of review feature)
"""

import json
import websocket
import time
import sys

def test_improvement_workflow(websocket_url):
    """Test the improvement request workflow"""
    print("🔧 Testing Improvement Workflow")
    print("=" * 50)
    
    try:
        # Connect to WebSocket
        ws = websocket.create_connection(websocket_url)
        
        # Test improvement request using makecall route
        message = {
            "action": "improve_section",
            "section": "prediction_statement",
            "current_value": "Bitcoin will hit $100k today"
        }
        ws.send(json.dumps(message))
        
        # Collect response
        timeout = 30
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = ws.recv()
                data = json.loads(result)
                
                print(f"📨 Received: {data.get('type')} - {data}")
                
                if data.get("type") == "improvement_questions":
                    print("✅ Improvement questions received!")
                    questions = data.get("data", {}).get("questions", [])
                    print(f"   Questions: {questions}")
                    
                    # Now test answering the questions
                    answer_message = {
                        "action": "improvement_answers",
                        "section": "prediction_statement",
                        "answers": ["Before 3pm EST", "New York area"],
                        "original_value": "Bitcoin will hit $100k today",
                        "full_context": {"verifiable_category": "api_tool_verifiable"}
                    }
                    ws.send(json.dumps(answer_message))
                    continue
                    
                elif data.get("type") == "improved_response":
                    print("✅ Improved response received!")
                    improved_value = data.get("data", {}).get("improved_value", "")
                    print(f"   Improved Value: {improved_value}")
                    break
                    
            except Exception as timeout_error:
                if "timeout" in str(timeout_error).lower():
                    continue
                else:
                    raise timeout_error
                
        ws.close()
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def main():
    websocket_url = "wss://0yv5r2auh5.execute-api.us-west-2.amazonaws.com/prod"
    
    if len(sys.argv) > 1:
        websocket_url = sys.argv[1]
    
    print(f"🔗 Using WebSocket URL: {websocket_url}")
    
    success = test_improvement_workflow(websocket_url)
    
    if success:
        print("\n🎉 Improvement workflow working!")
    else:
        print("\n💥 Improvement workflow has issues!")

if __name__ == "__main__":
    main()