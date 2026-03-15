"""Test all 57 blackbox detectors and output full report."""
import sys, json, time, os
os.chdir(os.path.join(os.path.dirname(__file__), "backend"))
sys.path.insert(0, ".")

print("=== SPINDLE BLACKBOX SCANNER TEST ===\n")

from cognitive.spindle_blackbox_scanner import get_blackbox_scanner
scanner = get_blackbox_scanner()

print("Starting full scan...")
t0 = time.time()
report = scanner.run_scan()
elapsed = time.time() - t0

print(f"Scan completed in {elapsed:.1f}s")
print(f"Files scanned: {report.files_scanned}\n")

print("=== RESULTS ===")
print(f"Total issues:  {report.total_issues}")
print(f"Critical:      {report.critical_count}")
print(f"Warning:       {report.warning_count}")
print(f"Info:          {report.info_count}\n")

print("=== BY CATEGORY ===")
for cat, count in sorted(report.categories.items(), key=lambda x: -x[1]):
    print(f"  {cat:45s} {count:4d}")

print("\n=== SAMPLE ALERTS ===")
for sev in ["critical", "warning", "info"]:
    alerts = [a for a in report.alerts if a.severity == sev]
    print(f"\n--- {sev.upper()} ({len(alerts)} total) ---")
    for a in alerts[:5]:
        loc = ""
        if a.file:
            loc = f" @ {a.file}"
            if a.line:
                loc += f":{a.line}"
        print(f"  [{a.category}] {a.title}{loc}")
        if a.fix_suggestion:
            print(f"    fix: {a.fix_suggestion[:90]}")
    if len(alerts) > 5:
        print(f"  ... and {len(alerts) - 5} more")

print("\n=== DETECTOR EXECUTION CHECK ===")
# Check which categories actually produced results
all_detector_names = [
    "deterministic_validators", "orphan_finder", "no_output_components",
    "dead_event_handlers", "degradation_signals", "unregistered_brains",
    "silent_returns", "zombie_threads", "missing_timeouts",
    "unmonitored_services", "circular_imports", "duplicate_routes",
    "unused_models", "phantom_env_vars", "fire_and_forget",
    "missing_error_propagation", "disconnected_feedback_loops",
    "missing_shutdown", "schema_drift", "hardcoded_secrets",
    "unreachable_code", "stale_triggers",
    # Networking round 1
    "missing_http_timeouts", "swallowed_network_errors",
    "websocket_subscriber_leaks", "zmq_bridge_problems",
    "missing_frontend_timeouts", "no_retry_http_clients",
    "no_backend_offline_indicator",
    # Networking round 2
    "no_keepalive_connections", "unclosed_connections",
    "missing_circuit_breakers", "unbounded_queues",
    "no_websocket_heartbeat", "fire_and_forget_http",
    "no_idempotency_on_retry", "frontend_silent_catches",
    "frontend_ws_no_reconnect", "no_error_rate_tracking",
    "no_latency_tracking", "frontend_stale_ws_state",
    "ipc_echo_loop_risk",
    # Frontend
    "no_error_boundary", "useeffect_memory_leaks",
    "fetch_race_conditions", "missing_empty_states",
    "xss_dangerously_set", "localstorage_secrets",
    "console_log_pollution", "no_loading_states",
    "missing_key_props", "no_frontend_error_reporting",
    "missing_accessibility", "unhandled_promise_rejections",
    "excessive_inline_styles", "suspense_without_error_boundary",
    "hardcoded_api_urls",
]

found_categories = set(report.categories.keys())
# Map detector names to likely category names
print(f"Detectors registered: {len(all_detector_names)}")
print(f"Categories with findings: {len(found_categories)}")
print(f"Categories found: {', '.join(sorted(found_categories))}")

print("\n=== DONE ===")
