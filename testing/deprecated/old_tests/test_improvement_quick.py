#!/usr/bin/env python3
import json
import websocket
import time

def test_improvement_quick():
    print("🔧 Quick Improvement Test")
    
    try:
        ws = websocket.create_connection("wss://0yv5r2auh5.execute-api.us-west-2.amazonaws.com/prod", timeout=5)
        
        # Test improvement request
        message = {
            "action": "improve_section",
            "section": "prediction_statement",
            "current_value": "Bitcoin will hit $100k today"
        }
        ws.send(json.dumps(message))
        print("📤 Sent improvement request")
        
        # Wait for response with short timeout
        start_time = time.time()
        while time.time() - start_time < 10:
            try:
                result = ws.recv()
                data = json.loads(result)
                print(f"📨 Received: {data.get('type')} - {data}")
                
                if data.get("type") == "improvement_questions":
                    print("✅ Got improvement questions!")
                    ws.close()
                    return True
                elif data.get("type") == "error":
                    print(f"❌ Error: {data.get('message')}")
                    ws.close()
                    return False
                    
            except Exception as e:
                if "timeout" in str(e).lower():
                    continue
                else:
                    print(f"❌ Error: {e}")
                    break
        
        print("⏰ Timeout - no improvement questions received")
        ws.close()
        return False
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    success = test_improvement_quick()
    print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")