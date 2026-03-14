import pytest
import time
from backend.cognitive.memory_mesh_metrics import (
    PerformanceMetrics,
    TimedOperation,
    get_performance_metrics,
    _global_metrics
)

@pytest.fixture
def metrics():
    # Use isolated metrics instance for test
    return PerformanceMetrics(max_samples=100)

def test_record_latencies(metrics):
    metrics.record_query_latency(150.0)
    metrics.record_query_latency(200.0)
    metrics.record_embedding_latency(400.0)
    metrics.record_vector_search_latency(50.0)
    metrics.record_stats_query_latency(10.0)
    
    assert len(metrics.query_latencies) == 2
    assert len(metrics.embedding_latencies) == 1
    assert len(metrics.vector_search_latencies) == 1
    assert len(metrics.stats_query_latencies) == 1
    
    assert metrics.total_queries == 2

def test_percentiles(metrics):
    for i in range(1, 101):  # 1 to 100
        metrics.record_query_latency(float(i))
        
    percentiles = metrics.get_query_percentiles()
    
    assert percentiles["p50"] == 51.0  # (0-indexed 50 is 51 in 1-100)
    assert percentiles["p95"] == 96.0
    assert percentiles["p99"] == 100.0
    assert percentiles["min"] == 1.0
    assert percentiles["max"] == 100.0
    assert percentiles["mean"] == 50.5

def test_cache_metrics(metrics):
    metrics.record_cache_hit()
    metrics.record_cache_hit()
    metrics.record_cache_miss()
    
    assert metrics.cache_hits == 2
    assert metrics.cache_misses == 1
    assert metrics.get_cache_hit_rate() == 2/3

def test_timed_operation(metrics):
    with TimedOperation(metrics, "query"):
        time.sleep(0.01) # 10 ms sleep
        
    assert len(metrics.query_latencies) == 1
    assert metrics.query_latencies[0] >= 10.0 # Should be at least ~10ms

def test_alerts_and_health(metrics):
    # Simulate high latency
    metrics.record_query_latency(1200.0) # > 1000 triggers alert
    assert len(metrics.performance_alerts) == 1
    assert "High query latency" in metrics.performance_alerts[0]["message"]
    
    # Force low hit rate
    metrics.cache_misses = 150
    metrics.cache_hits = 10
    
    health = metrics.check_performance_health()
    assert health["status"] == "degraded" or health["status"] == "unhealthy"
    
def test_reset(metrics):
    metrics.record_query_latency(100)
    metrics.record_cache_hit()
    
    metrics.reset_metrics()
    
    assert len(metrics.query_latencies) == 0
    assert metrics.cache_hits == 0
    assert metrics.total_queries == 0
    assert len(metrics.performance_alerts) == 0

def test_global_metrics_singleton():
    import backend.cognitive.memory_mesh_metrics as mm_metrics
    mm_metrics._global_metrics = None
    
    m1 = get_performance_metrics()
    m2 = get_performance_metrics()
    
    assert m1 is m2

if __name__ == "__main__":
    pytest.main(['-v', __file__])
