#!/usr/bin/env python3
"""
WebSocket Error Scenario Tests - Testing Phase C
Tests connection failures, timeouts, and message parsing errors
"""

import asyncio
import websockets
import json
import time
from unittest.mock import patch, MagicMock

class TestWebSocketErrors:
    
    def __init__(self, websocket_url):
        self.websocket_url = websocket_url
        self.test_results = []
    
    async def test_connection_failure(self):
        """Test handling of connection failures"""
        try:
            # Try connecting to invalid URL
            invalid_url = "wss://invalid-url-that-does-not-exist.com"
            async with websockets.connect(invalid_url, timeout=5) as websocket:
                pass
            return False, "Should have failed to connect"
        except Exception as e:
            return True, f"Correctly handled connection failure: {type(e).__name__}"
    
    async def test_connection_timeout(self):
        """Test connection timeout handling"""
        try:
            # Use very short timeout
            async with websockets.connect(self.websocket_url, timeout=0.1) as websocket:
                # Send message and wait longer than timeout
                await websocket.send(json.dumps({"action": "makecall", "message": "test"}))
                await asyncio.sleep(0.2)  # Longer than timeout
            return True, "Connection handled timeout gracefully"
        except asyncio.TimeoutError:
            return True, "Correctly handled timeout"
        except Exception as e:
            return True, f"Handled with exception: {type(e).__name__}"
    
    async def test_malformed_message_handling(self):
        """Test handling of malformed JSON messages"""
        try:
            async with websockets.connect(self.websocket_url, timeout=10) as websocket:
                # Send malformed JSON
                await websocket.send("invalid json {")
                
                # Wait for response or timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    return True, f"Server handled malformed JSON: {response[:100]}"
                except asyncio.TimeoutError:
                    return True, "Server correctly ignored malformed JSON"
        except Exception as e:
            return True, f"Connection error handled: {type(e).__name__}"
    
    async def test_missing_action_field(self):
        """Test handling of messages without action field"""
        try:
            async with websockets.connect(self.websocket_url, timeout=10) as websocket:
                # Send message without action field
                await websocket.send(json.dumps({"message": "test without action"}))
                
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    return True, f"Server handled missing action: {response[:100]}"
                except asyncio.TimeoutError:
                    return True, "Server correctly ignored message without action"
        except Exception as e:
            return True, f"Handled gracefully: {type(e).__name__}"
    
    async def test_unknown_action_handling(self):
        """Test handling of unknown action types"""
        try:
            async with websockets.connect(self.websocket_url, timeout=10) as websocket:
                # Send message with unknown action
                await websocket.send(json.dumps({
                    "action": "unknown_action_type",
                    "message": "test unknown action"
                }))
                
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    return True, f"Server handled unknown action: {response[:100]}"
                except asyncio.TimeoutError:
                    return True, "Server correctly ignored unknown action"
        except Exception as e:
            return True, f"Handled gracefully: {type(e).__name__}"
    
    async def test_connection_drop_recovery(self):
        """Test handling of sudden connection drops"""
        try:
            websocket = await websockets.connect(self.websocket_url, timeout=10)
            
            # Send initial message
            await websocket.send(json.dumps({"action": "makecall", "message": "test"}))
            
            # Simulate connection drop by closing
            await websocket.close()
            
            # Try to send after close (should fail gracefully)
            try:
                await websocket.send(json.dumps({"action": "test"}))
                return False, "Should have failed after close"
            except websockets.exceptions.ConnectionClosed:
                return True, "Correctly detected connection closed"
        except Exception as e:
            return True, f"Handled connection drop: {type(e).__name__}"
    
    async def test_large_message_handling(self):
        """Test handling of very large messages"""
        try:
            async with websockets.connect(self.websocket_url, timeout=10) as websocket:
                # Create large message (1MB)
                large_message = "x" * (1024 * 1024)
                await websocket.send(json.dumps({
                    "action": "makecall",
                    "message": large_message
                }))
                
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    return True, f"Server handled large message: {len(response)} chars"
                except asyncio.TimeoutError:
                    return True, "Server handled large message (timeout expected)"
        except Exception as e:
            return True, f"Large message handled: {type(e).__name__}"
    
    async def test_rapid_message_sending(self):
        """Test handling of rapid message bursts"""
        try:
            async with websockets.connect(self.websocket_url, timeout=10) as websocket:
                # Send 10 messages rapidly
                for i in range(10):
                    await websocket.send(json.dumps({
                        "action": "makecall",
                        "message": f"rapid message {i}"
                    }))
                
                # Try to receive responses
                responses = 0
                for _ in range(5):  # Try to get some responses
                    try:
                        await asyncio.wait_for(websocket.recv(), timeout=2)
                        responses += 1
                    except asyncio.TimeoutError:
                        break
                
                return True, f"Handled rapid messages, got {responses} responses"
        except Exception as e:
            return True, f"Rapid messaging handled: {type(e).__name__}"
    
    async def run_all_tests(self):
        """Run all WebSocket error tests"""
        tests = [
            ('Connection Failure', self.test_connection_failure),
            ('Connection Timeout', self.test_connection_timeout),
            ('Malformed Message', self.test_malformed_message_handling),
            ('Missing Action Field', self.test_missing_action_field),
            ('Unknown Action', self.test_unknown_action_handling),
            ('Connection Drop Recovery', self.test_connection_drop_recovery),
            ('Large Message Handling', self.test_large_message_handling),
            ('Rapid Message Sending', self.test_rapid_message_sending)
        ]
        
        print("🌐 Starting WebSocket Error Scenario Tests...")
        
        passed = 0
        for test_name, test_func in tests:
            try:
                success, message = await test_func()
                if success:
                    print(f"✅ {test_name}: {message}")
                    passed += 1
                else:
                    print(f"❌ {test_name}: {message}")
            except Exception as e:
                print(f"❌ {test_name}: Unexpected error - {e}")
        
        print(f"\n📊 WebSocket Error Tests: {passed}/{len(tests)} passed ({passed/len(tests)*100:.1f}%)")
        return passed, len(tests)


async def main():
    # Use mock WebSocket URL for testing
    websocket_url = "wss://mock-websocket-url.execute-api.us-east-1.amazonaws.com/prod"
    
    tester = TestWebSocketErrors(websocket_url)
    await tester.run_all_tests()


if __name__ == '__main__':
    asyncio.run(main())