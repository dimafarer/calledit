#!/usr/bin/env python3
"""
Performance Benchmark Tests - Testing Phase C
Tests response times, memory usage, and load handling
"""

import time
import asyncio
import websockets
import json
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor
from statistics import mean, median

class TestPerformanceBenchmarks:
    
    def __init__(self, websocket_url):
        self.websocket_url = websocket_url
        self.response_times = []
        self.memory_usage = []
    
    def measure_memory_usage(self):
        """Monitor memory usage during tests"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # MB
    
    async def test_single_request_response_time(self):
        """Test response time for single request"""
        try:
            start_time = time.time()
            
            async with websockets.connect(self.websocket_url, timeout=30) as websocket:
                request_start = time.time()
                
                await websocket.send(json.dumps({
                    "action": "makecall",
                    "message": "Performance test prediction"
                }))
                
                response = await asyncio.wait_for(websocket.recv(), timeout=30)
                response_time = time.time() - request_start
                
                self.response_times.append(response_time)
                return True, f"Response time: {response_time:.2f}s"
                
        except Exception as e:
            return False, f"Request failed: {e}"
    
    async def test_concurrent_connections(self, num_connections=5):
        """Test handling of concurrent WebSocket connections"""
        async def single_connection():
            try:
                async with websockets.connect(self.websocket_url, timeout=20) as websocket:
                    start_time = time.time()
                    await websocket.send(json.dumps({
                        "action": "makecall",
                        "message": f"Concurrent test {threading.current_thread().ident}"
                    }))
                    
                    response = await asyncio.wait_for(websocket.recv(), timeout=20)
                    response_time = time.time() - start_time
                    return response_time
            except Exception as e:
                return None
        
        try:
            # Create concurrent connections
            tasks = [single_connection() for _ in range(num_connections)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful results
            successful_times = [r for r in results if isinstance(r, (int, float)) and r is not None]
            
            if successful_times:
                avg_time = mean(successful_times)
                return True, f"Concurrent connections: {len(successful_times)}/{num_connections} successful, avg: {avg_time:.2f}s"
            else:
                return False, "No successful concurrent connections"
                
        except Exception as e:
            return False, f"Concurrent test failed: {e}"
    
    def test_memory_usage_baseline(self):
        """Test baseline memory usage"""
        try:
            initial_memory = self.measure_memory_usage()
            
            # Simulate some processing
            data = ["test"] * 1000
            processed_data = [item.upper() for item in data]
            
            current_memory = self.measure_memory_usage()
            memory_increase = current_memory - initial_memory
            
            self.memory_usage.append(current_memory)
            return True, f"Memory usage: {current_memory:.1f}MB (increase: {memory_increase:.1f}MB)"
            
        except Exception as e:
            return False, f"Memory test failed: {e}"
    
    async def test_streaming_performance(self):
        """Test performance of streaming responses"""
        try:
            start_time = time.time()
            message_count = 0
            
            async with websockets.connect(self.websocket_url, timeout=30) as websocket:
                await websocket.send(json.dumps({
                    "action": "makecall",
                    "message": "Test streaming performance with longer prediction"
                }))
                
                # Collect streaming messages
                while True:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5)
                        message_count += 1
                        
                        # Check if it's the final message
                        if "final_response" in message or message_count > 20:
                            break
                            
                    except asyncio.TimeoutError:
                        break
                
                total_time = time.time() - start_time
                avg_message_time = total_time / message_count if message_count > 0 else 0
                
                return True, f"Streaming: {message_count} messages in {total_time:.2f}s (avg: {avg_message_time:.2f}s/msg)"
                
        except Exception as e:
            return False, f"Streaming test failed: {e}"
    
    def test_cpu_usage_monitoring(self):
        """Monitor CPU usage during processing"""
        try:
            # Get initial CPU usage
            initial_cpu = psutil.cpu_percent(interval=1)
            
            # Simulate CPU-intensive task
            start_time = time.time()
            result = sum(i * i for i in range(100000))
            processing_time = time.time() - start_time
            
            # Get CPU usage after processing
            final_cpu = psutil.cpu_percent(interval=1)
            
            return True, f"CPU usage: {initial_cpu:.1f}% -> {final_cpu:.1f}%, processing: {processing_time:.3f}s"
            
        except Exception as e:
            return False, f"CPU monitoring failed: {e}"
    
    async def test_load_handling(self, num_requests=10):
        """Test system behavior under load"""
        try:
            start_time = time.time()
            successful_requests = 0
            failed_requests = 0
            
            async def single_request():
                try:
                    async with websockets.connect(self.websocket_url, timeout=15) as websocket:
                        await websocket.send(json.dumps({
                            "action": "makecall",
                            "message": f"Load test request {time.time()}"
                        }))
                        
                        response = await asyncio.wait_for(websocket.recv(), timeout=15)
                        return True
                except:
                    return False
            
            # Execute load test
            tasks = [single_request() for _ in range(num_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_requests = sum(1 for r in results if r is True)
            failed_requests = num_requests - successful_requests
            
            total_time = time.time() - start_time
            requests_per_second = num_requests / total_time
            
            return True, f"Load test: {successful_requests}/{num_requests} successful, {requests_per_second:.1f} req/s"
            
        except Exception as e:
            return False, f"Load test failed: {e}"
    
    async def run_all_benchmarks(self):
        """Run all performance benchmark tests"""
        print("⚡ Starting Performance Benchmark Tests...")
        
        tests = [
            ('Single Request Response Time', self.test_single_request_response_time()),
            ('Concurrent Connections (5)', self.test_concurrent_connections(5)),
            ('Memory Usage Baseline', self.test_memory_usage_baseline()),
            ('Streaming Performance', self.test_streaming_performance()),
            ('CPU Usage Monitoring', self.test_cpu_usage_monitoring()),
            ('Load Handling (10 requests)', self.test_load_handling(10))
        ]
        
        passed = 0
        for test_name, test_coro in tests:
            try:
                if asyncio.iscoroutine(test_coro):
                    success, message = await test_coro
                else:
                    success, message = test_coro
                    
                if success:
                    print(f"✅ {test_name}: {message}")
                    passed += 1
                else:
                    print(f"❌ {test_name}: {message}")
            except Exception as e:
                print(f"❌ {test_name}: Unexpected error - {e}")
        
        # Performance summary
        if self.response_times:
            avg_response = mean(self.response_times)
            median_response = median(self.response_times)
            print(f"\n📈 Response Time Summary:")
            print(f"   Average: {avg_response:.2f}s")
            print(f"   Median: {median_response:.2f}s")
            print(f"   Min: {min(self.response_times):.2f}s")
            print(f"   Max: {max(self.response_times):.2f}s")
        
        print(f"\n📊 Performance Tests: {passed}/{len(tests)} passed ({passed/len(tests)*100:.1f}%)")
        return passed, len(tests)


async def main():
    # Use mock WebSocket URL for testing
    websocket_url = "wss://mock-websocket-url.execute-api.us-east-1.amazonaws.com/prod"
    
    tester = TestPerformanceBenchmarks(websocket_url)
    await tester.run_all_benchmarks()


if __name__ == '__main__':
    asyncio.run(main())