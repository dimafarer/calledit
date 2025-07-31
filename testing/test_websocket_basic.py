#!/usr/bin/env python3
import json
import websocket
import time

def test_basic_connection():
    print("🔗 Testing basic WebSocket connection...")
    
    try:
        ws = websocket.create_connection("wss://0yv5r2auh5.execute-api.us-west-2.amazonaws.com/prod", timeout=10)
        print("✅ Connected successfully")
        
        # Send simple makecall
        message = {"action": "makecall", "prompt": "test", "timezone": "UTC"}
        ws.send(json.dumps(message))
        print("📤 Sent message")
        
        # Try to get one response
        result = ws.recv()
        data = json.loads(result)
        print(f"📨 Received: {data.get('type', 'unknown')}")
        
        ws.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_basic_connection()