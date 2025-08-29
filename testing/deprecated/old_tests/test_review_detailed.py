#!/usr/bin/env python3
"""
Detailed test of the MCP Sampling review feature
"""

import json
import websocket
import time
import sys

def test_review_detailed(websocket_url):
    """Test the review feature with detailed output"""
    print("🔍 Detailed MCP Sampling Review Test")
    print("=" * 50)
    
    try:
        # Connect to WebSocket
        ws = websocket.create_connection(websocket_url)
        
        # Send prediction that should have improvable sections
        message = {
            "action": "makecall",
            "prompt": "I think it will rain tomorrow",
            "timezone": "America/New_York"
        }
        ws.send(json.dumps(message))
        
        # Collect all messages
        messages = []
        timeout = 90  # Longer timeout for review
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = ws.recv()
                data = json.loads(result)
                messages.append(data)
                
                # Show detailed message info
                if data.get("type") == "status":
                    print(f"📊 Status: {data.get('status')} - {data.get('message', '')}")
                elif data.get("type") == "text":
                    print(f"💬 Text: {data.get('content', '')[:50]}...")
                elif data.get("type") == "tool":
                    print(f"🔧 Tool: {data.get('name')}")
                elif data.get("type") == "call_response":
                    print(f"📋 Call Response received")
                elif data.get("type") == "review_complete":
                    print(f"🔍 Review Complete received")
                elif data.get("type") == "complete":
                    print(f"✅ Complete received")
                    break
                    
            except websocket.WebSocketTimeoutError:
                continue
                
        ws.close()
        
        # Analyze messages in detail
        call_response = None
        review_complete = None
        
        for msg in messages:
            if msg.get("type") == "call_response":
                call_response = json.loads(msg.get("content", "{}"))
            elif msg.get("type") == "review_complete":
                review_complete = msg.get("data", {})
        
        print("\n" + "=" * 50)
        print("📋 DETAILED ANALYSIS:")
        
        if call_response:
            print(f"✅ Call Response Found:")
            print(f"   Category: {call_response.get('verifiable_category')}")
            print(f"   Statement: {call_response.get('prediction_statement')}")
            print(f"   Reasoning: {call_response.get('category_reasoning', '')[:100]}...")
        else:
            print("❌ No Call Response found")
        
        if review_complete:
            print(f"✅ Review Complete Found:")
            sections = review_complete.get("reviewable_sections", [])
            print(f"   Total Reviewable Sections: {len(sections)}")
            
            if sections:
                for i, section in enumerate(sections):
                    print(f"   Section {i+1}:")
                    print(f"     Field: {section.get('section')}")
                    print(f"     Improvable: {section.get('improvable')}")
                    print(f"     Questions: {section.get('questions', [])}")
                    print(f"     Reasoning: {section.get('reasoning', '')[:80]}...")
            else:
                print("   ⚠️  No reviewable sections found")
                print("   This could mean:")
                print("     - Review agent didn't find improvements needed")
                print("     - Review agent failed to process")
                print("     - Import error with review_agent.py")
        else:
            print("❌ No Review Complete found")
        
        # Show all message types received
        message_types = [msg.get("type") for msg in messages]
        print(f"\n📨 Message Types Received: {list(set(message_types))}")
        print(f"📊 Total Messages: {len(messages)}")
        
        return call_response is not None and review_complete is not None
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def main():
    websocket_url = "wss://0yv5r2auh5.execute-api.us-west-2.amazonaws.com/prod"
    
    if len(sys.argv) > 1:
        websocket_url = sys.argv[1]
    
    print(f"🔗 Using WebSocket URL: {websocket_url}")
    
    success = test_review_detailed(websocket_url)
    
    if success:
        print("\n🎉 Basic review feature working!")
    else:
        print("\n💥 Review feature has issues!")

if __name__ == "__main__":
    main()