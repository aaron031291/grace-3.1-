import requests
PORT = 8000  # Target FastAPI port

def test_endpoint(name, url, method="GET", json_data=None):
    try:
        url = f"http://localhost:{PORT}{url}"
        print(f"\n--- Testing {name} ---")
        print(f"{method} {url}")
        if method == "GET":
            response = requests.get(url, timeout=5)
        else:
            response = requests.post(url, json=json_data, timeout=5)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}") # using text in case it's not JSON
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: {e}")

# Test system endpoints
test_endpoint("Immune Status", "/api/immune/status")
test_endpoint("Start Background Loop", "/api/immune/loop/start", method="POST")

test_endpoint("Proactive Engine Status", "/api/proactive/status")
test_endpoint("Start Proactive Engine", "/api/proactive/start", method="POST")

# And trigger via Brain API v2
json_payload = {
    "playbook_id": "test",
    "trigger_id": "none"
}
test_endpoint("Brain API: Immune Scan", "/api/v2/system/immune_scan", method="POST", json_data=json_payload)

# Remaining System Endpoints
test_endpoint("Stop Background Loop", "/api/immune/loop/stop", method="POST")
test_endpoint("Immune Playbooks", "/api/immune/playbooks", method="GET")

test_endpoint("Stop Proactive Engine", "/api/proactive/stop", method="POST")
test_endpoint("Trigger Healing Cycle", "/api/proactive/trigger", method="POST", json_data={"source": "manual_test"})

# Stress Test Endpoints (from system_audit_api.py)
test_endpoint("Start Stress Test", "/api/audit/stress/start", method="POST", json_data={"duration": 10})
test_endpoint("Stress Test Status", "/api/audit/stress/status", method="GET")
test_endpoint("Stop Stress Test", "/api/audit/stress/stop", method="POST")

# Remaining Brain API v2 triggers
test_endpoint("Brain API: Diagnostic Sensors", "/api/v2/system/diagnostic_sensors", method="POST", json_data={})
test_endpoint("Brain API: Diagnostic Forensics", "/api/v2/system/diagnostic_forensics", method="POST", json_data={})
test_endpoint("Brain API: Stress Test Start", "/api/v2/system/stress_test_start", method="POST", json_data={"duration": 5})
