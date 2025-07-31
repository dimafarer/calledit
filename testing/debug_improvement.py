#!/usr/bin/env python3
import json
import websocket
import time

def debug_improvement():
    print("🔍 Debug Improvement Request")
    
    try:
        ws = websocket.create_connection("wss://0yv5r2auh5.execute-api.us-west-2.amazonaws.com/prod", timeout=5)
        print("✅ Connected")
        
        # Test improvement request
        message = {"action": "improve_section", "section": "prediction_statement"}
        print(f"📤 Sending: {message}")
        ws.send(json.dumps(message))
        
        # Get immediate response
        try:
            result = ws.recv()
            data = json.loads(result)
            print(f"📨 Response: {data}")
        except Exception as e:
            print(f"❌ No response: {e}")
        
        ws.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_improvement()