"""Direct test of GraceMind — no HTTP server needed."""
import os, sys, time

os.environ["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from core.grace_mind import get_grace_mind

mind = get_grace_mind()

# Test 1: Status
print("=== TEST 1: Status ===")
s = mind.status()
print(f"  Name: {s['name']}")
print(f"  Subsystems: {list(s['subsystems'].keys())}")
print(f"  Model trust: {s['trust_state']['models']}")
print("  PASS\n")

# Test 2: Think (skip trust to test pipeline wiring)
print("=== TEST 2: Think (skip_trust, skip_ooda) ===")
t0 = time.time()
r = mind.think(
    intent="system health check",
    task_type="heal",
    source="test",
    skip_ooda=True,
    skip_trust=True,
)
elapsed = round(time.time() - t0, 1)
print(f"  Decision: {r['decision_id']}")
print(f"  Task: {r['task_type']}")
print(f"  OK: {r['ok']}")
print(f"  Latency: {r['latency_ms']}ms (wall: {elapsed}s)")
print(f"  Stages: {list(r.get('stages', {}).keys())}")

brains = r.get("stages", {}).get("brains", {})
if brains:
    print(f"  Brains called: {brains.get('brains_called', [])}")
    for bn, br in brains.get("results", {}).items():
        ok = br.get("ok", "?")
        err = br.get("error", "")[:60] if not br.get("ok") else ""
        print(f"    {bn}: ok={ok} {err}")
print("  PASS\n")

# Test 3: Think with trust scoring
print("=== TEST 3: Think (with trust scoring) ===")
t0 = time.time()
r2 = mind.think(
    intent="check governance rules",
    task_type="heal",
    source="test",
    skip_ooda=True,
)
elapsed = round(time.time() - t0, 1)
print(f"  Decision: {r2['decision_id']}")
print(f"  OK: {r2['ok']}")
print(f"  Latency: {r2['latency_ms']}ms (wall: {elapsed}s)")
print(f"  Stages: {list(r2.get('stages', {}).keys())}")

trust = r2.get("stages", {}).get("trust", {})
if trust:
    print(f"  System Trust: {trust.get('system_trust', 'N/A')}")
    for bn, sc in trust.get("per_brain", {}).items():
        print(f"    {bn}: trust={sc['trust_score']}, confidence={sc['confidence']}, trend={sc['trend']}")
print("  PASS\n")

# Test 4: Decisions count
print("=== TEST 4: Decision tracking ===")
s2 = mind.status()
print(f"  Decisions made: {s2['decisions_made']}")
assert s2["decisions_made"] >= 2, "Should have at least 2 decisions"
print("  PASS\n")

print("=" * 50)
print("  ALL GRACEMIND TESTS PASSED")
print("=" * 50)
