"""
Dispatch 50 real coding tasks to Grace's Kimi, Qwen, Opus, Ollama agents
via the RUNNING backend API — uses Grace's own endpoints, not standalone imports.
All tasks run in PARALLEL via ThreadPoolExecutor.
"""
import time
import json
import threading
import concurrent.futures
import requests

API = "http://localhost:8000"

# Verify backend is alive
try:
    r = requests.get(f"{API}/health", timeout=10)
    h = r.json()
    print(f"Backend: {h['status']}, LLM: {h['llm_running']}, Models: {h['models_available']}")
except Exception as e:
    print(f"Backend not reachable: {e}")
    exit(1)

# Verify coding agents are ready
r = requests.get(f"{API}/coding-agent/governance/status", timeout=10).json()
agents = list(r.get("data", {}).get("agents", {}).keys())
print(f"Coding agents: {agents}")
print(f"Max concurrent: {r['data']['max_concurrent_jobs']}")

# 50 real tasks — dispatched via brain/code endpoint
TASKS = [
    # QWEN — 13 tasks
    ("qwen", "api/health.py", "Analyze health endpoint for race conditions"),
    ("qwen", "api/brain_api_v2.py", "Review brain router for dead routes"),
    ("qwen", "database/session.py", "Check for connection leaks"),
    ("qwen", "database/connection.py", "Review connection pooling config"),
    ("qwen", "core/lifecycle_cortex.py", "Analyze startup ordering bugs"),
    ("qwen", "llm_orchestrator/factory.py", "Review fallback chain edge cases"),
    ("qwen", "cognitive/event_bus.py", "Check for memory leaks in subscribers"),
    ("qwen", "api/stream_api.py", "Review SSE connection cleanup"),
    ("qwen", "security/middleware.py", "Audit for bypass vulnerabilities"),
    ("qwen", "cognitive/trust_engine.py", "Review trust scoring edge cases"),
    ("qwen", "core/resilience.py", "Analyze circuit breaker thread safety"),
    ("qwen", "api/unified_problems_api.py", "Review severity validation"),
    ("qwen", "cognitive/consensus_engine.py", "Check for deadlock potential"),
    # KIMI — 13 tasks
    ("kimi", "app.py", "Analyze startup bottlenecks"),
    ("kimi", "settings.py", "Review for insecure defaults"),
    ("kimi", "api/ingest.py", "Check file type validation gaps"),
    ("kimi", "api/retrieve.py", "Review for query injection risks"),
    ("kimi", "cognitive/coding_agents.py", "Analyze thread safety issues"),
    ("kimi", "cognitive/ghost_memory.py", "Check for unbounded growth"),
    ("kimi", "api/sandbox_api.py", "Review code execution escape risks"),
    ("kimi", "cognitive/healing_swarm.py", "Analyze infinite retry loops"),
    ("kimi", "cognitive/spindle_event_store.py", "Review data loss scenarios"),
    ("kimi", "api/learning_memory_api.py", "Check input validation"),
    ("kimi", "api/governance_api.py", "Review authorization checks"),
    ("kimi", "core/governance_engine.py", "Analyze rule conflict detection"),
    ("kimi", "api/validation_api.py", "Check missing error responses"),
    # OPUS — 13 tasks
    ("opus", "cognitive/central_orchestrator.py", "Deep analysis of event routing correctness"),
    ("opus", "core/brain_orchestrator.py", "Analyze domain routing gaps"),
    ("opus", "cognitive/consensus_pipeline.py", "Review multi-model agreement logic"),
    ("opus", "cognitive/immune_system.py", "Analyze false positive detection"),
    ("opus", "cognitive/spindle_projection.py", "Review data consistency"),
    ("opus", "cognitive/mirror_self_modeling.py", "Analyze self-model accuracy"),
    ("opus", "core/coding_pipeline.py", "Analyze safety gate bypasses"),
    ("opus", "cognitive/architecture_proposer.py", "Review hallucination risks"),
    ("opus", "cognitive/sandbox_engine.py", "Analyze execution isolation"),
    ("opus", "api/ml_intelligence_api.py", "Review model drift detection"),
    ("opus", "cognitive/proactive_healing_engine.py", "Analyze unnecessary interventions"),
    ("opus", "cognitive/learning_memory.py", "Review embedding quality"),
    ("opus", "cognitive/meta_loop_orchestrator.py", "Analyze recursive healing risks"),
    # OLLAMA — 6 tasks
    ("ollama", "api/auth.py", "Review auth middleware for token validation"),
    ("ollama", "api/admin_api.py", "Check admin API access control"),
    ("ollama", "api/voice_api.py", "Review WebSocket lifecycle"),
    ("ollama", "api/completion_api.py", "Check code completion for injection"),
    ("ollama", "api/codebase_api.py", "Review file access path traversal"),
    ("ollama", "api/genesis_api.py", "Analyze genesis key integrity"),
    # PARALLEL (all agents) — 5 tasks
    ("all", "app.py", "Top 3 stability risks in Grace main app"),
    ("all", "cognitive/coding_agents.py", "Production readiness review"),
    ("all", "database/session.py", "Production safety audit"),
    ("all", "cognitive/spindle_event_store.py", "Data integrity under load"),
    ("all", "llm_orchestrator/factory.py", "Graceful degradation audit"),
]

print(f"\nDispatching {len(TASKS)} tasks in PARALLEL via backend API...")
print("=" * 90)

results_lock = threading.Lock()
results = []
count = [0]

def dispatch_task(idx, agent, file_path, description):
    """Dispatch one task via Grace's brain/code API."""
    t0 = time.time()
    try:
        if agent == "all":
            # Dispatch to all agents in parallel via brain
            task_results = []
            for a in ["qwen", "kimi", "opus"]:
                r = requests.post(f"{API}/brain/code", json={
                    "action": "analyze",
                    "payload": {
                        "file_path": file_path,
                        "description": description,
                        "agent": a,
                    }
                }, timeout=120)
                task_results.append((a, r.json()))
            dur = time.time() - t0
            with results_lock:
                for a, data in task_results:
                    count[0] += 1
                    ok = data.get("ok", False)
                    conf = data.get("data", {}).get("confidence", 0) if isinstance(data.get("data"), dict) else 0
                    icon = "OK" if ok else "FAIL"
                    print(f"  [{count[0]:02d}] [{icon}] {a:6s} | {file_path:45s} | conf={conf:.2f} | {dur:.1f}s")
                    results.append({"agent": a, "ok": ok, "data": data, "file": file_path, "time": dur})
        else:
            r = requests.post(f"{API}/brain/code", json={
                "action": "analyze",
                "payload": {
                    "file_path": file_path,
                    "description": description,
                    "agent": agent,
                }
            }, timeout=120)
            dur = time.time() - t0
            data = r.json()
            ok = data.get("ok", False)
            conf = data.get("data", {}).get("confidence", 0) if isinstance(data.get("data"), dict) else 0
            with results_lock:
                count[0] += 1
                icon = "OK" if ok else "FAIL"
                print(f"  [{count[0]:02d}] [{icon}] {agent:6s} | {file_path:45s} | conf={conf:.2f} | {dur:.1f}s")
                results.append({"agent": agent, "ok": ok, "data": data, "file": file_path, "time": dur})
    except Exception as e:
        dur = time.time() - t0
        with results_lock:
            count[0] += 1
            print(f"  [{count[0]:02d}] [ERR]  {agent:6s} | {file_path:45s} | {str(e)[:50]} | {dur:.1f}s")
            results.append({"agent": agent, "ok": False, "error": str(e), "file": file_path, "time": dur})

start_all = time.time()

# 20 parallel threads — all hitting the running backend API
with concurrent.futures.ThreadPoolExecutor(max_workers=20, thread_name_prefix="dispatch") as executor:
    futures = []
    for i, (agent, fp, desc) in enumerate(TASKS):
        futures.append(executor.submit(dispatch_task, i, agent, fp, desc))
    concurrent.futures.wait(futures, timeout=600)

total_time = time.time() - start_all

print(f"\n{'=' * 90}")
print("RESULTS SUMMARY")
print("=" * 90)

ok_count = sum(1 for r in results if r.get("ok"))
fail_count = sum(1 for r in results if not r.get("ok"))
by_agent = {}
for r in results:
    a = r["agent"]
    by_agent.setdefault(a, {"ok": 0, "fail": 0, "time": 0})
    if r.get("ok"):
        by_agent[a]["ok"] += 1
    else:
        by_agent[a]["fail"] += 1
    by_agent[a]["time"] += r.get("time", 0)

print(f"Total dispatched:  {len(TASKS)} tasks")
print(f"Total results:     {len(results)}")
print(f"Succeeded:         {ok_count}")
print(f"Failed:            {fail_count}")
print(f"Wall-clock time:   {total_time:.1f}s")
print(f"Parallelism:       20 threads")
print()

for a, s in sorted(by_agent.items()):
    total = s["ok"] + s["fail"]
    avg = s["time"] / total if total else 0
    print(f"  {a:8s}: {s['ok']:2d}/{total:2d} passed | avg time: {avg:.1f}s")

# Show sample outputs
print(f"\n{'=' * 90}")
print("SAMPLE AGENT OUTPUTS")
print("=" * 90)
seen = set()
for r in results:
    if r.get("ok") and r["agent"] not in seen:
        seen.add(r["agent"])
        d = r.get("data", {}).get("data", {})
        analysis = d.get("analysis", "") if isinstance(d, dict) else ""
        if analysis:
            print(f"\n--- {r['agent'].upper()} on {r['file']} ---")
            print(analysis[:500])
        if len(seen) >= 4:
            break

# Final pool status
try:
    s = requests.get(f"{API}/coding-agent/governance/status", timeout=10).json()
    d = s.get("data", {})
    print(f"\nFinal pool: {d.get('active_jobs', 0)} active, {d.get('channel_messages', 0)} channel msgs")
    gs = d.get("group_session", {})
    print(f"Group session: {gs.get('total_actions', 0)} actions, {len(gs.get('by_agent', {}))} agents")
except:
    pass

print("\nDONE.")
