"""
Test script for Grace's self-modeling telemetry system.

This script demonstrates:
1. Running database migration to add telemetry tables
2. Tracking operations with telemetry
3. Viewing baselines and drift alerts
4. Capturing system state
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

import time
from telemetry.telemetry_service import get_telemetry_service
from telemetry.decorators import track_operation
from models.telemetry_models import OperationType
from database.connection import DatabaseConnection
from database.session import initialize_session_factory

print("=" * 60)
print("Grace Self-Modeling Telemetry System - Test Script")
print("=" * 60)

# Initialize database
print("\n[1/5] Initializing database connection...")
try:
    DatabaseConnection.initialize()
    initialize_session_factory()
    print("✓ Database initialized")
except Exception as e:
    print(f"✗ Failed to initialize database: {e}")
    sys.exit(1)

# Run migration
print("\n[2/5] Running telemetry table migration...")
try:
    from database.migrate_add_telemetry import migrate
    migrate()
    print("✓ Migration complete")
except Exception as e:
    print(f"✗ Migration failed: {e}")
    import traceback
    traceback.print_exc()
    # Continue anyway - tables might already exist

# Test telemetry tracking
print("\n[3/5] Testing operation tracking...")

@track_operation(OperationType.INGESTION, "test_ingestion", capture_inputs=True)
def test_ingestion_operation(filename: str, size_kb: int):
    """Simulated ingestion operation."""
    time.sleep(0.1)  # Simulate work
    return {"status": "success", "chunks": 10}

@track_operation(OperationType.RETRIEVAL, "test_retrieval", capture_inputs=True)
def test_retrieval_operation(query: str, limit: int = 5):
    """Simulated retrieval operation."""
    time.sleep(0.05)  # Simulate work
    return {"results": 3, "scores": [0.9, 0.8, 0.7]}

try:
    # Run some operations to generate telemetry data
    print("   Running test operations...")

    # Successful operations
    for i in range(5):
        test_ingestion_operation(f"doc_{i}.pdf", size_kb=100 + i * 10)
        test_retrieval_operation(f"query_{i}", limit=5)

    # Slower operation to trigger drift
    time.sleep(0.3)
    test_ingestion_operation("large_doc.pdf", size_kb=1000)

    print("✓ Operations tracked successfully")
except Exception as e:
    print(f"✗ Operation tracking failed: {e}")
    import traceback
    traceback.print_exc()

# Capture system state
print("\n[4/5] Capturing system state...")
try:
    telemetry = get_telemetry_service()
    state = telemetry.capture_system_state()
    print(f"✓ System state captured:")
    print(f"   - Ollama running: {state.ollama_running}")
    print(f"   - Qdrant connected: {state.qdrant_connected}")
    print(f"   - Documents: {state.document_count}")
    print(f"   - Chunks: {state.chunk_count}")
    print(f"   - CPU: {state.cpu_percent:.1f}%")
    print(f"   - Memory: {state.memory_percent:.1f}%")
except Exception as e:
    print(f"⚠ System state capture failed: {e}")
    import traceback
    traceback.print_exc()

# Query telemetry data
print("\n[5/5] Querying telemetry data...")
try:
    from database.session import get_session
    from models.telemetry_models import OperationLog, PerformanceBaseline, DriftAlert

    session = next(get_session())

    # Recent operations
    recent_ops = session.query(OperationLog).order_by(
        OperationLog.started_at.desc()
    ).limit(5).all()

    print(f"✓ Recent operations ({len(recent_ops)}):")
    for op in recent_ops:
        status_icon = "✓" if op.status.value == "completed" else "✗"
        print(f"   {status_icon} {op.operation_name}: {op.duration_ms:.1f}ms ({op.status.value})")

    # Baselines
    baselines = session.query(PerformanceBaseline).all()
    print(f"\n✓ Performance baselines ({len(baselines)}):")
    for baseline in baselines:
        print(f"   - {baseline.operation_name}:")
        print(f"     Mean: {baseline.mean_duration_ms:.1f}ms, "
              f"P95: {baseline.p95_duration_ms:.1f}ms, "
              f"Success rate: {baseline.success_rate:.1%}")

    # Drift alerts
    alerts = session.query(DriftAlert).filter(
        DriftAlert.resolved == False
    ).all()
    print(f"\n✓ Active drift alerts ({len(alerts)}):")
    for alert in alerts:
        print(f"   ⚠ {alert.drift_type} - {alert.operation_name} "
              f"(deviation: {alert.deviation_percent:.1f}%, severity: {alert.severity})")

    session.close()

except Exception as e:
    print(f"⚠ Query failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
print("\nTelemetry API endpoints are now available:")
print("  - GET  /telemetry/operations      - View operation logs")
print("  - GET  /telemetry/baselines        - View performance baselines")
print("  - GET  /telemetry/drift-alerts     - View drift alerts")
print("  - GET  /telemetry/system-state/current  - Current system state")
print("  - GET  /telemetry/stats            - Aggregated statistics")
print("  - GET  /telemetry/health           - Telemetry system health")
print("=" * 60)
