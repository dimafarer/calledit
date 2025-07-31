#!/usr/bin/env python3
"""
Test the MCP Sampling review feature
"""

import json
import websocket
import time
import sys

def test_review_feature(websocket_url):
    """Test the review feature with MCP Sampling"""
    print("🔍 Testing MCP Sampling Review Feature")
    print("=" * 50)
    
    try:
        # Connect to WebSocket
        ws = websocket.create_connection(websocket_url)
        
        # Send prediction
        message = {
            "action": "makecall",
            "prompt": "Bitcoin will hit $100k today",
            "timezone": "America/New_York"
        }
        ws.send(json.dumps(message))
        
        # Collect all messages
        messages = []
        timeout = 60
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = ws.recv()
                data = json.loads(result)
                messages.append(data)
                
                print(f"📨 Received: {data.get('type', 'unknown')}")
                
                if data.get("type") == "complete":
                    break
                    
            except websocket.WebSocketTimeoutError:
                continue
                
        ws.close()
        
        # Analyze messages
        call_response = None
        review_complete = None
        
        for msg in messages:
            if msg.get("type") == "call_response":
                call_response = json.loads(msg.get("content", "{}"))
            elif msg.get("type") == "review_complete":
                review_complete = msg.get("data", {})
        
        print("\n📋 RESULTS:")
        print(f"✅ Call Response: {'Found' if call_response else 'Missing'}")
        print(f"✅ Review Complete: {'Found' if review_complete else 'Missing'}")
        
        if call_response:
            print(f"   Category: {call_response.get('verifiable_category', 'Missing')}")
            print(f"   Statement: {call_response.get('prediction_statement', 'Missing')[:50]}...")
        
        if review_complete:
            sections = review_complete.get("reviewable_sections", [])
            print(f"   Reviewable Sections: {len(sections)}")
            for section in sections:
                print(f"     - {section.get('section', 'Unknown')}: {section.get('improvable', False)}")
        
        # Test success criteria
        success = (
            call_response is not None and
            review_complete is not None and
            call_response.get('verifiable_category') in [
                'agent_verifiable', 'current_tool_verifiable', 
                'strands_tool_verifiable', 'api_tool_verifiable', 
                'human_verifiable_only'
            ]
        )
        
        print(f"\n🎯 Overall Result: {'✅ PASS' if success else '❌ FAIL'}")
        return success
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def main():
    websocket_url = "wss://0yv5r2auh5.execute-api.us-west-2.amazonaws.com/prod"
    
    if len(sys.argv) > 1:
        websocket_url = sys.argv[1]
    
    print(f"🔗 Using WebSocket URL: {websocket_url}")
    
    success = test_review_feature(websocket_url)
    
    if success:
        print("🎉 Review feature test passed!")
        sys.exit(0)
    else:
        print("💥 Review feature test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()