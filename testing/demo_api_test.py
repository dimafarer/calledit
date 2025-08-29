#!/usr/bin/env python3
"""
End-to-end API testing with demo prompts
Tests CalledIt backend with all verification categories
"""

import json
import websocket
import time
from demo_prompts import get_all_prompts

# Replace with your actual WebSocket URL
WEBSOCKET_URL = "wss://k0nut3n0xa.execute-api.us-west-2.amazonaws.com/prod"

def test_prediction_via_websocket(prompt, category_expected=None):
    """Test a single prediction via WebSocket streaming"""
    print(f"\n🧪 Testing: '{prompt}'")
    
    try:
        ws = websocket.create_connection(WEBSOCKET_URL, timeout=30)
        
        # Send prediction request
        message = {
            "action": "makecall",
            "prompt": prompt
        }
        ws.send(json.dumps(message))
        print("📤 Sent prediction request")
        
        result_data = {}
        start_time = time.time()
        
        while time.time() - start_time < 25:  # 25 second timeout
            try:
                response = ws.recv()
                data = json.loads(response)
                
                if data.get("type") == "stream":
                    print(f"📡 Stream: {data.get('content', '')[:100]}...")
                elif data.get("type") == "final_result":
                    result_data = data.get("data", {})
                    print(f"✅ Final result received")
                    break
                elif data.get("type") == "error":
                    print(f"❌ Error: {data.get('message')}")
                    ws.close()
                    return None
                    
            except Exception as e:
                if "timeout" in str(e).lower():
                    continue
                else:
                    print(f"❌ WebSocket error: {e}")
                    break
        
        ws.close()
        
        if result_data:
            category = result_data.get("verifiable_category", "unknown")
            statement = result_data.get("prediction_statement", prompt)
            reasoning = result_data.get("category_reasoning", "No reasoning provided")
            
            print(f"📊 Category: {category}")
            print(f"📝 Statement: {statement}")
            print(f"🧠 Reasoning: {reasoning[:150]}...")
            
            if category_expected and category != category_expected:
                print(f"⚠️  Expected {category_expected}, got {category}")
            
            return {
                "prompt": prompt,
                "category": category,
                "statement": statement,
                "reasoning": reasoning,
                "expected": category_expected,
                "success": True
            }
        else:
            print("❌ No final result received")
            return {"prompt": prompt, "success": False}
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return {"prompt": prompt, "success": False, "error": str(e)}

def run_demo_test(max_per_category=3):
    """Run demo test with limited prompts per category"""
    print("🚀 Starting CalledIt Demo API Test")
    print(f"Testing {max_per_category} prompts per category\n")
    
    all_prompts = get_all_prompts()
    results = []
    
    for category, prompts in all_prompts.items():
        print(f"\n🎯 Testing {category.upper().replace('_', ' ')} category:")
        
        # Test limited number of prompts per category
        test_prompts = prompts[:max_per_category]
        
        for prompt in test_prompts:
            result = test_prediction_via_websocket(prompt, category)
            if result:
                results.append(result)
            time.sleep(2)  # Brief pause between requests
    
    # Summary
    print(f"\n📊 DEMO TEST SUMMARY")
    print(f"Total tests: {len(results)}")
    successful = [r for r in results if r.get('success')]
    print(f"Successful: {len(successful)}")
    
    # Category accuracy
    correct_categories = [r for r in successful if r.get('category') == r.get('expected')]
    print(f"Correct categorization: {len(correct_categories)}/{len(successful)}")
    
    # Show category distribution
    categories = {}
    for result in successful:
        cat = result.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"\nCategory distribution:")
    for cat, count in categories.items():
        print(f"  {cat}: {count}")
    
    # Save results to file
    with open("demo_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to demo_results.json")
    
    return results

if __name__ == "__main__":
    results = run_demo_test(max_per_category=2)  # Test 2 per category for demo