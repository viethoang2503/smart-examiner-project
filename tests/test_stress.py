"""
FocusGuard Stress Tests
Tests server under multiple concurrent client connections
"""

import asyncio
import aiohttp
import time
import sys
import os
import random
import string
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List

# Add project path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.constants import Config

BASE_URL = f"http://localhost:{Config.SERVER_PORT}"
WS_URL = f"ws://localhost:{Config.SERVER_PORT}/ws"


@dataclass
class ClientStats:
    """Statistics for a simulated client"""
    client_id: int
    requests_sent: int = 0
    requests_failed: int = 0
    total_time: float = 0.0
    avg_response_time: float = 0.0


async def simulate_client(client_id: int, duration_seconds: int = 30) -> ClientStats:
    """Simulate a single client making requests"""
    stats = ClientStats(client_id=client_id)
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        while time.time() - start_time < duration_seconds:
            try:
                request_start = time.time()
                
                # Simulate API call
                async with session.get(f"{BASE_URL}/", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        stats.requests_sent += 1
                    else:
                        stats.requests_failed += 1
                
                stats.total_time += time.time() - request_start
                
                # Small delay between requests
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
            except Exception as e:
                stats.requests_failed += 1
    
    if stats.requests_sent > 0:
        stats.avg_response_time = (stats.total_time / stats.requests_sent) * 1000
    
    return stats


async def run_stress_test(num_clients: int, duration_seconds: int = 30):
    """Run stress test with specified number of clients"""
    print(f"\n{'='*60}")
    print(f"Stress Test: {num_clients} concurrent clients for {duration_seconds}s")
    print(f"{'='*60}")
    
    # Create tasks for all clients
    tasks = [
        simulate_client(i, duration_seconds) 
        for i in range(num_clients)
    ]
    
    start_time = time.time()
    results: List[ClientStats] = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # Aggregate results
    total_requests = sum(r.requests_sent for r in results)
    total_failed = sum(r.requests_failed for r in results)
    avg_response_times = [r.avg_response_time for r in results if r.avg_response_time > 0]
    
    if avg_response_times:
        avg_response = sum(avg_response_times) / len(avg_response_times)
    else:
        avg_response = 0
    
    print(f"\nResults:")
    print(f"  Total requests: {total_requests}")
    print(f"  Failed requests: {total_failed}")
    print(f"  Success rate: {(total_requests/(total_requests+total_failed))*100:.1f}%")
    print(f"  Avg response time: {avg_response:.2f}ms")
    print(f"  Throughput: {total_requests/total_time:.1f} req/s")
    
    return {
        "num_clients": num_clients,
        "total_requests": total_requests,
        "failed_requests": total_failed,
        "avg_response_time": avg_response,
        "throughput": total_requests / total_time
    }


async def measure_websocket_connections(num_connections: int = 20):
    """Test multiple WebSocket connections"""
    print(f"\n{'='*60}")
    print(f"WebSocket Connection Test: {num_connections} connections")
    print(f"{'='*60}")
    
    connections = []
    successful = 0
    failed = 0
    
    async with aiohttp.ClientSession() as session:
        for i in range(num_connections):
            try:
                ws = await session.ws_connect(
                    f"{WS_URL}?student_id=stress_test_{i}",
                    timeout=aiohttp.ClientTimeout(total=5)
                )
                connections.append(ws)
                successful += 1
            except Exception as e:
                failed += 1
        
        print(f"  Successful connections: {successful}")
        print(f"  Failed connections: {failed}")
        
        # Send heartbeats
        for ws in connections:
            try:
                await ws.send_json({"type": "heartbeat"})
            except:
                pass
        
        # Close connections
        for ws in connections:
            await ws.close()
    
    return {"successful": successful, "failed": failed}


def run_all_stress_tests():
    """Run all stress tests"""
    print("=" * 60)
    print("FocusGuard Stress Testing Suite")
    print("=" * 60)
    
    # Check server
    import requests
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"✅ Server is running at {BASE_URL}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Server not running at {BASE_URL}")
        print("Please start the server first: python run_server.py")
        return
    
    results = []
    
    # Test with increasing number of clients
    for num_clients in [5, 10, 20]:
        try:
            result = asyncio.run(run_stress_test(num_clients, duration_seconds=15))
            results.append(result)
        except Exception as e:
            print(f"Error with {num_clients} clients: {e}")
    
    # Test WebSocket connections
    try:
        ws_result = asyncio.run(measure_websocket_connections(20))
    except Exception as e:
        print(f"WebSocket test error: {e}")
        ws_result = None
    
    # Summary
    print("\n" + "=" * 60)
    print("STRESS TEST SUMMARY")
    print("=" * 60)
    
    for result in results:
        status = "✅" if result["avg_response_time"] < 200 else "⚠️"
        print(f"{status} {result['num_clients']:2d} clients: "
              f"{result['throughput']:.1f} req/s, "
              f"{result['avg_response_time']:.1f}ms avg")
    
    if ws_result:
        status = "✅" if ws_result["failed"] == 0 else "⚠️"
        print(f"{status} WebSocket: {ws_result['successful']}/{ws_result['successful']+ws_result['failed']} connections")
    
    print("\n✅ Stress tests completed!")


if __name__ == "__main__":
    run_all_stress_tests()
