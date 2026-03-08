#!/usr/bin/env python3
"""
generate_playbooks.py
Generates 20 diverse YAML playbooks for Grace's self-healing capabilities.
Run this script to instantly augment the system's immune library.
"""
import os
import yaml

PLAYBOOKS = [
    # ── Database & State ──────────────────────────────────────────────────
    {
        "filename": "db_connection_pool_exhausted.yaml",
        "content": {
            "trigger": "database.pool.exhausted",
            "description": "Auto-kills idle DB connections when the SQLAlchemy pool limit is reached preventing new connections.",
            "conditions": [{"error_type": "TimeoutError"}, {"source": "database.pool"}],
            "remediation": [
                {"step": "clear_idle_connections", "description": "Trigger db engine dispose mapping to close idle threads", "module": "database.connection", "function": "dispose_engine"},
                {"step": "record_learning", "description": "Log pool exhaustion", "module": "api._genesis_tracker", "function": "track", "args": {"key_type": "system_event", "what_description": "DB Pool exhausted. Idle connections terminated.", "is_error": True}}
            ],
            "metrics": [{"name": "MTTR_pool_exhaustion", "description": "Seconds to clear pool"}],
            "escalation": {"trigger": "guardian.escalate('database_deadlock')", "condition": "Dispose fails to free connections after 3 seconds."},
            "learning": {"record_to": "knowledge_base/layer_1/db/pool_log.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["database", "pool", "exhaustion", "self_healing"]}
        }
    },
    {
        "filename": "db_deadlock_detected.yaml",
        "content": {
            "trigger": "database.transaction.deadlock",
            "description": "Rollback and retry blocking transactions that hit concurrent lock waiting states.",
            "conditions": [{"error_type": "DeadlockDetected"}, {"source": "database.transaction"}],
            "remediation": [
                {"step": "rollback_transaction", "description": "Rollback current SQLAlchemy session.", "module": "database.session", "function": "rollback"},
                {"step": "retry_with_backoff", "description": "Wait randomly 1-3 seconds and retry transaction", "module": "database.retry", "function": "exponential_backoff"},
            ],
            "metrics": [{"name": "deadlocks_healed", "description": "Count of successfully retried deadlocks"}],
            "escalation": {"trigger": "guardian.escalate('unresolvable_transaction_deadlock')", "condition": "Transaction fails after 3 retry backoffs."},
            "learning": {"record_to": "knowledge_base/layer_1/db/deadlock_log.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["database", "deadlock", "transaction", "self_healing"]}
        }
    },
    {
        "filename": "redis_out_of_memory.yaml",
        "content": {
            "trigger": "redis.memory.oom",
            "description": "Evict oldest non-critical cache keys to prevent Redis from completely stalling out.",
            "conditions": [{"error_type": "OOM command not allowed"}, {"service_target": "Redis"}],
            "remediation": [
                {"step": "flush_old_cache", "description": "Evict stale keys > 24 hours.", "module": "core.memory.redis_client", "function": "evict_stale"},
            ],
            "metrics": [{"name": "MTTR_redis_oom", "description": "Mean time to repair Redis limits"}],
            "escalation": {"trigger": "guardian.escalate('redis_hard_oom')", "condition": "Redis still OOM after forced eviction."},
            "learning": {"record_to": "knowledge_base/layer_1/infrastructure/redis_OOM.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["redis", "oom", "cache", "self_healing"]}
        }
    },
    {
        "filename": "qdrant_storage_full.yaml",
        "content": {
            "trigger": "qdrant.storage.critical",
            "description": "Trigger vector collection optimization and payload compression when disk space drops.",
            "conditions": [{"error_type": "StorageExhausted"}, {"service_target": "Qdrant"}],
            "remediation": [
                {"step": "trigger_optimization", "description": "Run Qdrant optimize_collection API call", "module": "vector_db.client", "function": "optimize_all_collections"},
            ],
            "metrics": [{"name": "qdrant_bytes_freed", "description": "Bytes freed post-optimization"}],
            "escalation": {"trigger": "guardian.escalate('vector_disk_full')", "condition": "Optimization does not free > 10% disk."},
            "learning": {"record_to": "knowledge_base/layer_1/infrastructure/qdrant_storage.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["qdrant", "vector_db", "storage", "self_healing"]}
        }
    },

    # ── ML & LLM Resilience ───────────────────────────────────────────────
    {
        "filename": "llm_context_window_exceeded.yaml",
        "content": {
            "trigger": "llm.context.exceeded",
            "description": "Auto-summarize or truncate prompt payloads before retry to bypass token limits.",
            "conditions": [{"error_type": "ContextWindowExceededError"}, {"source": "llm_orchestrator"}],
            "remediation": [
                {"step": "truncate_history", "description": "Drop oldest 30% of dialogue strings and retry.", "module": "llm_orchestrator.prompt_formatter", "function": "truncate_history_payload"},
                {"step": "record_learning", "description": "Track context drop", "module": "api._genesis_tracker", "function": "track", "args": {"key_type": "system_event", "what_description": "Context window exceeded. Dropped 30% of history.", "is_error": True}}
            ],
            "metrics": [{"name": "MTTR_context_window", "description": "Time to bypass context window length."}],
            "escalation": {"trigger": "guardian.escalate('payload_uncompressable')", "condition": "Context still exceeded after 2 truncations."},
            "learning": {"record_to": "knowledge_base/layer_2/llm/context_limit.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["llm", "context", "truncate", "self_healing"]}
        }
    },
    {
        "filename": "llm_provider_outage.yaml",
        "content": {
            "trigger": "llm.provider.outage",
            "description": "Failover to secondary API keys or local offline models when OpenAI/Anthropic 5xx out.",
            "conditions": [{"error_type": "APIConnectionError"}, {"source": "llm_orchestrator"}],
            "remediation": [
                {"step": "switch_model_provider", "description": "Reroute to local Ollama instance.", "module": "llm_orchestrator.factory", "function": "failover_to_local"},
            ],
            "metrics": [{"name": "MTTR_provider_failover", "description": "Seconds taken to failover to local model."}],
            "escalation": {"trigger": "guardian.escalate('all_llms_dead')", "condition": "Local failover also unconnected or missing weights."},
            "learning": {"record_to": "knowledge_base/layer_2/llm/provider_outage.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["llm", "failover", "ollama", "self_healing"]}
        }
    },
    {
        "filename": "malformed_json_response.yaml",
        "content": {
            "trigger": "llm.response.malformed_json",
            "description": "Trigger an LLM-based structured JSON repair loop when a model returns broken markdown chunks instead of schemas.",
            "conditions": [{"error_type": "JSONDecodeError"}, {"source": "llm_orchestrator"}],
            "remediation": [
                {"step": "run_json_repair", "description": "Use lightweight regex/repair algorithm locally on the string.", "module": "self_healing.auto_patcher", "function": "repair_json_string"},
            ],
            "metrics": [{"name": "json_parse_repairs", "description": "Count of successfully repaired JSON strings."}],
            "escalation": {"trigger": "guardian.escalate('unparseable_llm_output')", "condition": "Repair parser fails heavily syntaxed output."},
            "learning": {"record_to": "knowledge_base/layer_2/llm/bad_json.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["llm", "json", "repair", "self_healing"]}
        }
    },

    # ── Resource Constraints ──────────────────────────────────────────────
    {
        "filename": "disk_space_critical.yaml",
        "content": {
            "trigger": "os.disk.critical",
            "description": "Auto-clear .pytest_cache, logs, and temporary files when disk space < 10%.",
            "conditions": [{"metric": "disk_free_percent"}, {"threshold": "< 10"}],
            "remediation": [
                {"step": "clear_temp_caches", "description": "Delete all tmp and pycache directories", "module": "core.services.system_service", "function": "clear_disk_caches"},
            ],
            "metrics": [{"name": "gb_freed_automatically", "description": "Gigabytes cleared automatically."}],
            "escalation": {"trigger": "guardian.escalate('disk_full_fatal')", "condition": "Caches cleared but disk still < 10%."},
            "learning": {"record_to": "knowledge_base/layer_1/os/disk_space.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["os", "disk", "cache", "self_healing"]}
        }
    },
    {
        "filename": "memory_leak_detected.yaml",
        "content": {
            "trigger": "os.memory.leak",
            "description": "Hot-restart specific sub-processes consuming massive RAM.",
            "conditions": [{"metric": "process_ram_mb"}, {"threshold": "> 2000"}],
            "remediation": [
                {"step": "restart_memory_hog", "description": "Send SIGTERM and restart to leak process.", "module": "core.services.system_service", "function": "restart_process_by_pid"},
            ],
            "metrics": [{"name": "memory_leak_restarts", "description": "Count of times process was OOM-killed externally."}],
            "escalation": {"trigger": "guardian.escalate('memory_leak_fatal')", "condition": "Process exceeds 2GB again within 5 minutes."},
            "learning": {"record_to": "knowledge_base/layer_1/os/memory_leaks.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["os", "memory", "leak", "self_healing"]}
        }
    },
    {
        "filename": "cpu_spike_detected.yaml",
        "content": {
            "trigger": "os.cpu.spike",
            "description": "Drop background concurrency limit when CPU spins at 100% for over 60s.",
            "conditions": [{"metric": "cpu_percent"}, {"threshold": "> 95"}, {"duration": "60s"}],
            "remediation": [
                {"step": "shed_background_tasks", "description": "Temporarily pause async intelligence workers", "module": "core.intelligence.scheduler", "function": "pause_background_workers"},
            ],
            "metrics": [{"name": "cpu_spike_shedding", "description": "Count of times CPU load shedding fired."}],
            "escalation": {"trigger": "guardian.escalate('cpu_bound_deadlock')", "condition": "CPU remains 100% after shedding tasks."},
            "learning": {"record_to": "knowledge_base/layer_1/os/cpu_spikes.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["os", "cpu", "load_shedding", "self_healing"]}
        }
    },

    # ── Networking & APIs ─────────────────────────────────────────────────
    {
        "filename": "api_rate_limit_exceeded.yaml",
        "content": {
            "trigger": "network.rate_limit.exceeded",
            "description": "Apply exponential backoff parameters dynamically when 429s are hit.",
            "conditions": [{"error_type": "HTTPError 429"}],
            "remediation": [
                {"step": "apply_exponential_backoff", "description": "Delay future calls mapped by Retry-After header", "module": "core.resilience", "function": "apply_dynamic_backoff"},
            ],
            "metrics": [{"name": "rate_limits_bypassed", "description": "Count of successfully backed-off requests."}],
            "escalation": {"trigger": "guardian.escalate('external_api_blacklisted')", "condition": "Target API 403s our IP completely."},
            "learning": {"record_to": "knowledge_base/layer_1/network/rate_limits.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "api", "429", "self_healing"]}
        }
    },
    {
        "filename": "port_conflict_detected.yaml",
        "content": {
            "trigger": "network.port.conflict",
            "description": "Auto-increment binding ports for internal microservices.",
            "conditions": [{"error_type": "OSError: [Errno 98] Address already in use"}],
            "remediation": [
                {"step": "increment_bind_port", "description": "Override uvicorn start port +1", "module": "core.services.system_service", "function": "increment_env_port"},
            ],
            "metrics": [{"name": "port_conflicts_resolved", "description": "Count of port shifts."}],
            "escalation": {"trigger": "guardian.escalate('port_scanning_failed')", "condition": "Increment failed 5 consecutive times."},
            "learning": {"record_to": "knowledge_base/layer_1/network/port_conflicts.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "port", "conflict", "self_healing"]}
        }
    },
    {
        "filename": "route_not_found_404.yaml",
        "content": {
            "trigger": "api.route.missing",
            "description": "Inject a fuzzy-matcher to redirect to the closest active route for internal calls.",
            "conditions": [{"error_type": "HTTP 404"}, {"source": "internal_traffic_only"}],
            "remediation": [
                {"step": "fuzzy_route_match", "description": "Identify if a route was renamed and proxy silently.", "module": "api.health", "function": "register_fuzzy_proxy"},
            ],
            "metrics": [{"name": "fuzzy_route_matches", "description": "Count of 404s bypassed internally."}],
            "escalation": {"trigger": "guardian.escalate('api_route_broken')", "condition": "No fuzzy match > 0.9 confidence available."},
            "learning": {"record_to": "knowledge_base/layer_3/routing/fuzzy_404.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["routing", "api", "404", "self_healing"]}
        }
    },
    {
        "filename": "api_gateway_timeout.yaml",
        "content": {
            "trigger": "api.gateway.timeout",
            "description": "Increase worker timeouts temporarily during extremely long generation phases.",
            "conditions": [{"error_type": "HTTP 504 Gateway Timeout"}],
            "remediation": [
                {"step": "extend_proxy_timeout", "description": "Increase timeout length by 30s transparently for next attempt.", "module": "core.resilience", "function": "extend_gateway_timeout"},
            ],
            "metrics": [{"name": "timeouts_extended", "description": "Count of generation phases saved by timeout extension."}],
            "escalation": {"trigger": "guardian.escalate('process_stuck_infinite')", "condition": "Process times out at 300s max length."},
            "learning": {"record_to": "knowledge_base/layer_1/network/timeouts.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "timeout", "504", "self_healing"]}
        }
    },

    # ── Security ──────────────────────────────────────────────────────────
    {
        "filename": "auth_token_expired.yaml",
        "content": {
            "trigger": "security.auth.expired",
            "description": "Auto-refresh internal service account tokens seamlessly.",
            "conditions": [{"error_type": "HTTP 401 Unauthorized"}, {"source": "internal_jwt"}],
            "remediation": [
                {"step": "refresh_service_token", "description": "Request new JWT token using service secret.", "module": "core.security.tokens", "function": "refresh_internal_token"},
            ],
            "metrics": [{"name": "tokens_refreshed_seamlessly", "description": "Count of bypassed 401 errors."}],
            "escalation": {"trigger": "guardian.escalate('auth_secret_invalid')", "condition": "Secret fails to generate new token."},
            "learning": {"record_to": "knowledge_base/layer_1/security/token_refresh.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["security", "auth", "401", "self_healing"]}
        }
    },
    {
        "filename": "ssl_certificate_expired.yaml",
        "content": {
            "trigger": "security.ssl.expired",
            "description": "Auto-provision temporary self-signed certs for internal networks to prevent blocking.",
            "conditions": [{"error_type": "SSLCertVerificationError"}, {"source": "internal_requests"}],
            "remediation": [
                {"step": "provision_temporary_cert", "description": "Generate rotating internal SSL cert.", "module": "core.security.ssl", "function": "provision_fallback_cert"},
            ],
            "metrics": [{"name": "ssl_bypasses", "description": "Count of times internal SSL was auto-patched."}],
            "escalation": {"trigger": "guardian.escalate('ssl_provisioning_failed')", "condition": "OpenSSL fails to bind temporary cert."},
            "learning": {"record_to": "knowledge_base/layer_1/security/ssl_cert.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["security", "ssl", "cert", "self_healing"]}
        }
    },

    # ── CI/CD & Frontend ──────────────────────────────────────────────────
    {
        "filename": "frontend_build_failure.yaml",
        "content": {
            "trigger": "frontend.build.failure",
            "description": "Auto-clear vite caches and retry build if chunk corruption causes exits.",
            "conditions": [{"error_type": "Vite Error: chunk format missing"}],
            "remediation": [
                {"step": "clear_vite_cache", "description": "Wipe node_modules/.vite directory.", "module": "self_healing.auto_patcher", "function": "run_command", "args": {"cmd": "rm -rf frontend/node_modules/.vite"}},
                {"step": "rebuild_frontend", "description": "Run npm run build again.", "module": "self_healing.auto_patcher", "function": "run_command", "args": {"cmd": "cd frontend && npm run build"}}
            ],
            "metrics": [{"name": "vite_build_heals", "description": "Count of successfully retry builds."}],
            "escalation": {"trigger": "guardian.escalate('frontend_syntax_error')", "condition": "Build fails after cache clear."},
            "learning": {"record_to": "knowledge_base/layer_9/ci_cd/vite_build.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["frontend", "vite", "build", "self_healing"]}
        }
    },
    {
        "filename": "unhandled_promise_rejection.yaml",
        "content": {
            "trigger": "frontend.promise.unhandled",
            "description": "Inject global catch block fallbacks to stabilize the UI.",
            "conditions": [{"error_type": "UnhandledPromiseRejectionWarning"}],
            "remediation": [
                {"step": "inject_global_catch", "description": "Ensure App.jsx has a window.onunhandledrejection wrapper.", "module": "self_healing.auto_patcher", "function": "inject_js_global_catch"},
            ],
            "metrics": [{"name": "promises_caught", "description": "Count of promises caught automatically."}],
            "escalation": {"trigger": "guardian.escalate('fatal_frontend_crash')", "condition": "Promises crash despite global wrappers."},
            "learning": {"record_to": "knowledge_base/layer_9/ci_cd/promise_catch.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["frontend", "promise", "js", "self_healing"]}
        }
    },

    # ── System Runtime ────────────────────────────────────────────────────
    {
        "filename": "zombie_process_detected.yaml",
        "content": {
            "trigger": "os.process.zombie",
            "description": "Scan and SIGKILL orphaned Python/Node sub-processes that hold locks.",
            "conditions": [{"metric": "zombie_child_count"}, {"threshold": "> 5"}],
            "remediation": [
                {"step": "sigkill_orphans", "description": "Force kill orphaned child processes holding file handlers.", "module": "core.services.system_service", "function": "kill_orphans"},
            ],
            "metrics": [{"name": "orphans_reaped", "description": "Count of zombie processes terminated."}],
            "escalation": {"trigger": "guardian.escalate('unreapable_process')", "condition": "Orphans survive SIGKILL."},
            "learning": {"record_to": "knowledge_base/layer_1/os/zombies.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["os", "process", "zombie", "self_healing"]}
        }
    },
    {
        "filename": "missing_environment_variable.yaml",
        "content": {
            "trigger": "os.env.missing",
            "description": "Inject safe default values for non-critical missing configs that block boot.",
            "conditions": [{"error_type": "KeyError (os.environ)"}],
            "remediation": [
                {"step": "inject_default", "description": "Insert a safe generic string matching expected type via introspection.", "module": "core.services.system_service", "function": "inject_default_env"},
            ],
            "metrics": [{"name": "envs_auto_patched", "description": "Count of environment variables dynamically added at runtime."}],
            "escalation": {"trigger": "guardian.escalate('critical_secret_missing')", "condition": "Env var requires high-entropy cryptographic secret."},
            "learning": {"record_to": "knowledge_base/layer_1/os/env_missing.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["os", "env", "config", "self_healing"]}
        }
    }
]

def generate():
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "self_healing", "playbooks")
    os.makedirs(output_dir, exist_ok=True)
    
    count = 0
    for pb in PLAYBOOKS:
        filepath = os.path.join(output_dir, pb["filename"])
        
        # Format the YAML output cleanly
        yaml_content = f"# Grace self-healing playbook\n# {pb['content']['description']}\n---\n"
        yaml_content += yaml.dump(pb['content'], sort_keys=False, default_flow_style=False)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(yaml_content)
        count += 1
        print(f"Generated: {pb['filename']}")
        
    print(f"\nSuccessfully generated {count} YAML playbooks in {output_dir}")

if __name__ == "__main__":
    generate()
