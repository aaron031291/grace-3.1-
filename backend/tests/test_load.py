"""
Load and Stress Tests for GRACE API
====================================
Tests for performance under load and stress conditions.

Usage:
    pytest tests/test_load.py -v
    pytest tests/test_load.py -v -k "test_concurrent"
"""

import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
import statistics


class TestLoadBasic:
    """Basic load tests for API endpoints."""

    def test_health_endpoint_load(self, client):
        """Test health endpoint under load."""
        num_requests = 100
        results = []

        start_total = time.time()

        for _ in range(num_requests):
            start = time.time()
            response = client.get("/health")
            elapsed = (time.time() - start) * 1000  # ms
            results.append({
                "status": response.status_code,
                "latency_ms": elapsed
            })

        total_time = time.time() - start_total

        # Calculate metrics
        latencies = [r["latency_ms"] for r in results]
        success_count = sum(1 for r in results if r["status"] == 200)

        metrics = {
            "total_requests": num_requests,
            "successful": success_count,
            "failed": num_requests - success_count,
            "total_time_s": round(total_time, 2),
            "requests_per_second": round(num_requests / total_time, 2),
            "avg_latency_ms": round(statistics.mean(latencies), 2),
            "p50_latency_ms": round(statistics.median(latencies), 2),
            "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
            "p99_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.99)], 2),
            "max_latency_ms": round(max(latencies), 2),
            "min_latency_ms": round(min(latencies), 2)
        }

        print(f"\n=== Health Endpoint Load Test ===")
        for key, value in metrics.items():
            print(f"  {key}: {value}")

        # Assertions
        assert success_count >= num_requests * 0.99  # 99% success rate
        assert metrics["avg_latency_ms"] < 100  # Avg under 100ms
        assert metrics["p95_latency_ms"] < 200  # P95 under 200ms

    def test_search_endpoint_load(self, client):
        """Test search endpoint under moderate load."""
        num_requests = 50
        results = []

        queries = [
            "machine learning",
            "artificial intelligence",
            "neural networks",
            "deep learning",
            "natural language processing"
        ]

        start_total = time.time()

        for i in range(num_requests):
            query = queries[i % len(queries)]
            start = time.time()
            response = client.post(
                "/retrieve/search",
                json={"query": query, "top_k": 5}
            )
            elapsed = (time.time() - start) * 1000
            results.append({
                "status": response.status_code,
                "latency_ms": elapsed
            })

        total_time = time.time() - start_total

        latencies = [r["latency_ms"] for r in results]
        success_count = sum(1 for r in results if r["status"] in [200, 404])

        metrics = {
            "total_requests": num_requests,
            "successful": success_count,
            "total_time_s": round(total_time, 2),
            "requests_per_second": round(num_requests / total_time, 2),
            "avg_latency_ms": round(statistics.mean(latencies), 2),
            "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2)
        }

        print(f"\n=== Search Endpoint Load Test ===")
        for key, value in metrics.items():
            print(f"  {key}: {value}")

        # Assertions - search can be slower
        assert success_count >= num_requests * 0.95
        assert metrics["avg_latency_ms"] < 2000  # Under 2 seconds avg


class TestConcurrentLoad:
    """Concurrent load tests using threading."""

    def test_concurrent_health_requests(self, client):
        """Test concurrent health check requests."""
        num_requests = 100
        num_workers = 10
        results = []
        errors = []

        def make_request():
            try:
                start = time.time()
                response = client.get("/health")
                elapsed = (time.time() - start) * 1000
                return {
                    "status": response.status_code,
                    "latency_ms": elapsed
                }
            except Exception as e:
                return {"error": str(e)}

        start_total = time.time()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]

            for future in as_completed(futures):
                result = future.result()
                if "error" in result:
                    errors.append(result)
                else:
                    results.append(result)

        total_time = time.time() - start_total

        latencies = [r["latency_ms"] for r in results]
        success_count = sum(1 for r in results if r["status"] == 200)

        print(f"\n=== Concurrent Health Requests ({num_workers} workers) ===")
        print(f"  Total requests: {num_requests}")
        print(f"  Successful: {success_count}")
        print(f"  Errors: {len(errors)}")
        print(f"  Total time: {round(total_time, 2)}s")
        print(f"  Throughput: {round(num_requests / total_time, 2)} req/s")
        if latencies:
            print(f"  Avg latency: {round(statistics.mean(latencies), 2)}ms")
            print(f"  P95 latency: {round(sorted(latencies)[int(len(latencies) * 0.95)], 2)}ms")

        # Assertions
        assert len(errors) < num_requests * 0.05  # Less than 5% errors
        assert success_count >= num_requests * 0.90  # 90% success

    def test_concurrent_mixed_endpoints(self, client):
        """Test concurrent requests to different endpoints."""
        num_requests = 60
        num_workers = 6
        results = {"health": [], "search": [], "chats": []}
        errors = []

        def make_health_request():
            try:
                start = time.time()
                response = client.get("/health")
                return {"type": "health", "status": response.status_code, "latency_ms": (time.time() - start) * 1000}
            except Exception as e:
                return {"type": "health", "error": str(e)}

        def make_search_request():
            try:
                start = time.time()
                response = client.post("/retrieve/search", json={"query": "test", "top_k": 3})
                return {"type": "search", "status": response.status_code, "latency_ms": (time.time() - start) * 1000}
            except Exception as e:
                return {"type": "search", "error": str(e)}

        def make_chats_request():
            try:
                start = time.time()
                response = client.get("/chats")
                return {"type": "chats", "status": response.status_code, "latency_ms": (time.time() - start) * 1000}
            except Exception as e:
                return {"type": "chats", "error": str(e)}

        # Mix of requests
        request_funcs = [make_health_request, make_search_request, make_chats_request] * (num_requests // 3)

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(func) for func in request_funcs]

            for future in as_completed(futures):
                result = future.result()
                if "error" in result:
                    errors.append(result)
                else:
                    results[result["type"]].append(result)

        print(f"\n=== Concurrent Mixed Endpoints ({num_workers} workers) ===")
        for endpoint, data in results.items():
            if data:
                latencies = [r["latency_ms"] for r in data]
                print(f"  {endpoint}: {len(data)} requests, avg {round(statistics.mean(latencies), 2)}ms")
        print(f"  Errors: {len(errors)}")

        # Basic assertion
        total_success = sum(len(v) for v in results.values())
        assert total_success >= len(request_funcs) * 0.85


class TestStress:
    """Stress tests for high load scenarios."""

    def test_burst_traffic(self, client):
        """Test handling of burst traffic."""
        burst_size = 50
        results = []

        start = time.time()

        # Send burst of requests as fast as possible
        for _ in range(burst_size):
            response = client.get("/health")
            results.append(response.status_code)

        elapsed = time.time() - start

        success_count = sum(1 for s in results if s == 200)
        rate_limited = sum(1 for s in results if s == 429)

        print(f"\n=== Burst Traffic Test ===")
        print(f"  Burst size: {burst_size}")
        print(f"  Time: {round(elapsed, 2)}s")
        print(f"  Success: {success_count}")
        print(f"  Rate limited: {rate_limited}")
        print(f"  Throughput: {round(burst_size / elapsed, 2)} req/s")

        # Either succeed or rate limit (both are acceptable)
        assert success_count + rate_limited == burst_size

    def test_sustained_load(self, client):
        """Test sustained load over time."""
        duration_seconds = 10
        results = []

        start = time.time()
        request_count = 0

        while time.time() - start < duration_seconds:
            response = client.get("/health")
            results.append({
                "status": response.status_code,
                "time": time.time() - start
            })
            request_count += 1
            time.sleep(0.05)  # ~20 req/s

        success_count = sum(1 for r in results if r["status"] == 200)

        print(f"\n=== Sustained Load Test ({duration_seconds}s) ===")
        print(f"  Total requests: {request_count}")
        print(f"  Success: {success_count}")
        print(f"  Success rate: {round(success_count / request_count * 100, 2)}%")
        print(f"  Avg rate: {round(request_count / duration_seconds, 2)} req/s")

        # Should maintain high success rate under sustained load
        assert success_count / request_count >= 0.95


class TestMemoryLeak:
    """Tests for memory leak detection."""

    def test_repeated_requests_memory(self, client):
        """Check for memory growth during repeated requests."""
        try:
            import psutil
            process = psutil.Process()
        except ImportError:
            pytest.skip("psutil not installed")

        num_requests = 200

        # Initial memory
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB

        # Make many requests
        for _ in range(num_requests):
            client.get("/health")

        # Final memory
        final_memory = process.memory_info().rss / (1024 * 1024)  # MB
        memory_growth = final_memory - initial_memory

        print(f"\n=== Memory Leak Test ===")
        print(f"  Initial memory: {round(initial_memory, 2)} MB")
        print(f"  Final memory: {round(final_memory, 2)} MB")
        print(f"  Growth: {round(memory_growth, 2)} MB")
        print(f"  Growth per request: {round(memory_growth / num_requests * 1000, 2)} KB")

        # Memory growth should be reasonable (less than 100MB for 200 requests)
        assert memory_growth < 100, f"Excessive memory growth: {memory_growth}MB"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Create test client."""
    try:
        from app import app
        return TestClient(app)
    except ImportError:
        pytest.skip("App not available for testing")


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
