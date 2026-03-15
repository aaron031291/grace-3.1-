"""Quick test of GraceMind API endpoints."""
import urllib.request, json, time

def test_status():
    print("=== TEST 1: GET /api/mind/status ===")
    r = urllib.request.urlopen("http://localhost:8000/api/mind/status", timeout=10)
    data = json.loads(r.read())
    print(f"  Name: {data['name']}")
    print(f"  Decisions: {data['decisions_made']}")
    print(f"  Subsystems: {list(data['subsystems'].keys())}")
    print(f"  Model trust: {data['trust_state']['models']}")
    ep = data.get("intelligence_report", {}).get("episodic_analysis", {})
    print(f"  Episodic: {ep.get('total', 0)} episodes, avg_trust={ep.get('avg_trust', 'N/A')}")
    print("  PASS\n")

def test_think():
    print("=== TEST 2: POST /api/mind/think ===")
    payload = json.dumps({
        "intent": "what is 2+2",
        "task_type": "chat",
        "source": "test",
        "skip_ooda": True,
        "skip_trust": True,
        "payload": {"message": "what is 2+2"}
    }).encode()
    req = urllib.request.Request(
        "http://localhost:8000/api/mind/think",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    r = urllib.request.urlopen(req, timeout=45)
    result = json.loads(r.read())
    elapsed = round(time.time() - t0, 1)

    print(f"  Decision ID: {result['decision_id']}")
    print(f"  Task type: {result['task_type']}")
    print(f"  OK: {result['ok']}")
    print(f"  Latency: {result['latency_ms']} ms (wall: {elapsed}s)")
    print(f"  Stages: {list(result.get('stages', {}).keys())}")

    brains = result.get("stages", {}).get("brains", {})
    if brains:
        print(f"  Brains called: {brains.get('brains_called', [])}")
        for bname, bres in brains.get("results", {}).items():
            ok = bres.get("ok", "?")
            err = bres.get("error", "")[:80] if not bres.get("ok") else ""
            print(f"    {bname}: ok={ok} {err}")

    print("  PASS\n")

def test_think_full():
    print("=== TEST 3: POST /api/mind/think (full pipeline with trust) ===")
    payload = json.dumps({
        "intent": "check system health status",
        "task_type": "heal",
        "source": "test",
        "skip_ooda": True,
    }).encode()
    req = urllib.request.Request(
        "http://localhost:8000/api/mind/think",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    r = urllib.request.urlopen(req, timeout=45)
    result = json.loads(r.read())
    elapsed = round(time.time() - t0, 1)

    print(f"  Decision ID: {result['decision_id']}")
    print(f"  OK: {result['ok']}")
    print(f"  Latency: {result['latency_ms']} ms (wall: {elapsed}s)")
    print(f"  Stages: {list(result.get('stages', {}).keys())}")

    trust = result.get("stages", {}).get("trust", {})
    if trust:
        print(f"  System Trust: {trust.get('system_trust', 'N/A')}")
        for bname, score in trust.get("per_brain", {}).items():
            print(f"    {bname}: trust={score['trust_score']}, confidence={score['confidence']}, trend={score['trend']}")

    print("  PASS\n")

if __name__ == "__main__":
    test_status()
    test_think()
    test_think_full()
    print("ALL TESTS PASSED")
