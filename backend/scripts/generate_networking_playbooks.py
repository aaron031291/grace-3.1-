#!/usr/bin/env python3
"""
generate_networking_playbooks.py
Generates 20 specific networking self-healing playbooks.
"""
import os
import yaml

NETWORKING_PLAYBOOKS = [
    # ── Transport & Socket Layer ──────────────────────────────────────────
    {
        "filename": "tcp_connection_reset.yaml",
        "content": {
            "trigger": "network.tcp.connection_reset",
            "description": "Auto-recreates database/Redis connection instances upon ConnectionResetError.",
            "conditions": [{"error_type": "ConnectionResetError"}, {"source": "socket_layer"}],
            "remediation": [
                {"step": "recreate_connection_pool", "description": "Dispose old engine and recreate TCP socket.", "module": "database.connection", "function": "reconnect_engine"},
            ],
            "metrics": [{"name": "conn_resets_recovered", "description": "Instances of transparent TCP socket recovery."}],
            "escalation": {"trigger": "guardian.escalate('tcp_peer_dead')", "condition": "Recreated sockets reset immediately 3x."},
            "learning": {"record_to": "knowledge_base/layer_1/network/tcp_resets.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "tcp", "socket", "self_healing"]}
        }
    },
    {
        "filename": "too_many_open_files.yaml",
        "content": {
            "trigger": "os.limits.file_descriptors",
            "description": "Auto-kills idle network sockets and HTTP keep-alive handlers when OS file descriptors exhaust.",
            "conditions": [{"error_type": "OSError: [Errno 24] Too many open files"}],
            "remediation": [
                {"step": "flush_idle_sockets", "description": "Close all active keep-alive sessions not currently transmitting.", "module": "core.services.system_service", "function": "close_idle_sockets"},
            ],
            "metrics": [{"name": "fd_exhaustion_bypassed", "description": "Count of successful file descriptor purges."}],
            "escalation": {"trigger": "guardian.escalate('fatal_fd_exhaustion')", "condition": "Cannot open socket to logger after flush."},
            "learning": {"record_to": "knowledge_base/layer_1/os/file_descriptors.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["os", "network", "sockets", "self_healing"]}
        }
    },
    {
        "filename": "client_broken_pipe.yaml",
        "content": {
            "trigger": "network.client.broken_pipe",
            "description": "Gracefully handles UI clients disconnecting midway through long SSE streams without panicking.",
            "conditions": [{"error_type": "BrokenPipeError"}, {"source": "asgi_server"}],
            "remediation": [
                {"step": "terminate_generator", "description": "Kill the backend LLM/SSE generation to save compute.", "module": "api.stream_handlers", "function": "terminate_disconnected_stream"},
            ],
            "metrics": [{"name": "compute_saved_by_broken_pipe", "description": "Tokens saved by killing dead generators."}],
            "escalation": {"trigger": "guardian.escalate('ddos_broken_pipes')", "condition": "Thousands of broken pipes hit per minute."},
            "learning": {"record_to": "knowledge_base/layer_3/network/broken_pipes.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "sse", "broken_pipe", "self_healing"]}
        }
    },
    {
        "filename": "tls_handshake_timeout.yaml",
        "content": {
            "trigger": "network.tls.timeout",
            "description": "Dynamically extends SSL/TLS socket timeout limits when contacting slow external APIs.",
            "conditions": [{"error_type": "ssl.SSLError: The read operation timed out"}],
            "remediation": [
                {"step": "extend_tls_timeout", "description": "Increase socket default timeout constraint for External IP.", "module": "core.security.ssl", "function": "extend_domain_timeout"},
            ],
            "metrics": [{"name": "tls_timeouts_resolved", "description": "Count of connections succeeding post extension."}],
            "escalation": {"trigger": "guardian.escalate('tls_handshake_hang')", "condition": "TLS hangs past 60s timeout limit."},
            "learning": {"record_to": "knowledge_base/layer_1/security/tls_timeouts.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["security", "network", "tls", "self_healing"]}
        }
    },
    {
        "filename": "network_interface_down.yaml",
        "content": {
            "trigger": "os.network.interface_down",
            "description": "Rebinds services to fallback interfaces if the host ethernet/loopback drops.",
            "conditions": [{"error_type": "OSError: [Errno 10051] Network is unreachable"}],
            "remediation": [
                {"step": "rebind_0_0_0_0", "description": "Restart uvicorn binding globally instead of localhost specific.", "module": "core.services.system_service", "function": "restart_uvicorn_global_bind"},
            ],
            "metrics": [{"name": "interface_rebounds", "description": "Count of server re-bindings."}],
            "escalation": {"trigger": "guardian.escalate('server_offline')", "condition": "0.0.0.0 bind fails entirely."},
            "learning": {"record_to": "knowledge_base/layer_1/os/interface_down.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["os", "network", "bind", "self_healing"]}
        }
    },

    # ── DNS & Routing ─────────────────────────────────────────────────────
    {
        "filename": "dns_lookup_failed.yaml",
        "content": {
            "trigger": "network.dns.lookup_failed",
            "description": "Falls back to direct IP routing or secondary DNS resolvers if primary lookup fails.",
            "conditions": [{"error_type": "socket.gaierror: [Errno -2] Name or service not known"}],
            "remediation": [
                {"step": "fallback_dns_resolver", "description": "Query 8.8.8.8 for the failing domain directly.", "module": "core.services.system_service", "function": "resolve_domain_fallback"},
            ],
            "metrics": [{"name": "dns_fallbacks", "description": "Count of successfully routed requests post-fallback."}],
            "escalation": {"trigger": "guardian.escalate('dns_outage')", "condition": "8.8.8.8 resolver also unreachable."},
            "learning": {"record_to": "knowledge_base/layer_1/network/dns_failures.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "dns", "resolve", "self_healing"]}
        }
    },
    {
        "filename": "dns_cache_poisoned.yaml",
        "content": {
            "trigger": "network.dns.poisoned",
            "description": "Auto-flushes local application DNS caches if endpoints unexpectedly resolve to local loopbacks.",
            "conditions": [{"metric": "unexpected_loopback_resolution"}, {"source": "security_probe"}],
            "remediation": [
                {"step": "flush_python_dns_cache", "description": "Clear urllib3 and requests internal connection pools.", "module": "core.services.system_service", "function": "flush_dns_pools"},
            ],
            "metrics": [{"name": "dns_cache_flushes", "description": "Count of detected poisoning overrides."}],
            "escalation": {"trigger": "guardian.escalate('active_mitm_detected')", "condition": "External API resolves to 127.0.0.1 immediately post flush."},
            "learning": {"record_to": "knowledge_base/layer_1/security/dns_poison.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["security", "network", "dns", "self_healing"]}
        }
    },
    {
        "filename": "cors_policy_violation.yaml",
        "content": {
            "trigger": "security.cors.violation",
            "description": "Auto-appends the blocked frontend origin to FastAPI's CORS middleware dynamically when 403s occur on known IPs.",
            "conditions": [{"error_type": "HTTP 403 Forbidden"}, {"logs_contain": ["CORS"]}],
            "remediation": [
                {"step": "append_cors_origin", "description": "Add origin header to allowed hosts if IP matches trusted frontend mask.", "module": "api.health", "function": "dynamic_cors_append"},
            ],
            "metrics": [{"name": "cors_auto_allow", "description": "Count of seamless frontend UI connections granted."}],
            "escalation": {"trigger": "guardian.escalate('cors_brute_force')", "condition": "100+ different origins attempt CORS access."},
            "learning": {"record_to": "knowledge_base/layer_3/security/cors_blocks.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["security", "cors", "network", "self_healing"]}
        }
    },
    {
        "filename": "firewall_block_detected.yaml",
        "content": {
            "trigger": "network.firewall.block_detected",
            "description": "Detects dropped outbound packets to LLM APIs and attempts application-layer proxy rerouting.",
            "conditions": [{"error_type": "TimeoutError"}, {"source": "outbound_llm"}],
            "remediation": [
                {"step": "route_via_proxy", "description": "Switch requests to use an environment configured outbound proxy.", "module": "llm_orchestrator.factory", "function": "enable_proxy_routing"},
            ],
            "metrics": [{"name": "proxy_reroutes", "description": "Count of times we bypassed restrictive host firewalls."}],
            "escalation": {"trigger": "guardian.escalate('airgapped_environment_detected')", "condition": "Proxy proxy also times out."},
            "learning": {"record_to": "knowledge_base/layer_1/network/firewall_blocks.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "firewall", "proxy", "self_healing"]}
        }
    },

    # ── Load Balancing & Gateways ─────────────────────────────────────────
    {
        "filename": "load_balancer_502.yaml",
        "content": {
            "trigger": "network.lb.502",
            "description": "Pauses traffic routing to a degraded microservice and aggressively pings health endpoint.",
            "conditions": [{"error_type": "HTTP 502 Bad Gateway"}],
            "remediation": [
                {"step": "quarantine_backend_node", "description": "Remove the target microservice from the internal DNS/Proxy pool momentarily.", "module": "api.health", "function": "quarantine_service_node"},
            ],
            "metrics": [{"name": "nodes_quarantined", "description": "Count of times bad gateway nodes were removed."}],
            "escalation": {"trigger": "guardian.escalate('all_nodes_dead')", "condition": "0 active nodes remain in proxy pool."},
            "learning": {"record_to": "knowledge_base/layer_3/network/bad_gateway.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "502", "proxy", "self_healing"]}
        }
    },
    {
        "filename": "api_timeout_504_gateway.yaml",
        "content": {
            "trigger": "network.lb.504",
            "description": "Increases gateway worker timeout bounds dynamically when massive RAG tasks take > 60s.",
            "conditions": [{"error_type": "HTTP 504 Gateway Timeout"}],
            "remediation": [
                {"step": "increase_gateway_timeout", "description": "Bump Uvicorn/traefik timeout allowance for route.", "module": "core.resilience", "function": "extend_gateway_timeout"},
            ],
            "metrics": [{"name": "timeouts_auto_extended", "description": "Count of 504s solved by extending wait periods."}],
            "escalation": {"trigger": "guardian.escalate('rag_task_hanging')", "condition": "Timeout exceeds 5 minutes."},
            "learning": {"record_to": "knowledge_base/layer_3/network/gateway_timeout.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "504", "timeout", "self_healing"]}
        }
    },
    {
        "filename": "http_503_service_unavailable.yaml",
        "content": {
            "trigger": "network.lb.503",
            "description": "Catches upstream 503s and implements a randomized jitter backoff to avoid thundering herds.",
            "conditions": [{"error_type": "HTTP 503 Service Unavailable"}],
            "remediation": [
                {"step": "apply_jitter_backoff", "description": "Implement a localized randomized wait matching typical Retry-After headers.", "module": "core.resilience", "function": "jittered_retry"},
            ],
            "metrics": [{"name": "503_thundering_herd_bypassed", "description": "Count of randomized successful queries."}],
            "escalation": {"trigger": "guardian.escalate('upstream_permanently_down')", "condition": "503 persists for 30 minutes."},
            "learning": {"record_to": "knowledge_base/layer_3/network/service_unavailable.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "503", "jitter", "self_healing"]}
        }
    },
    {
        "filename": "ingress_traffic_spike.yaml",
        "content": {
            "trigger": "network.traffic.spike",
            "description": "Scales up application-level rate limiting proactively when massive a sudden spike comes.",
            "conditions": [{"metric": "requests_per_second"}, {"threshold": "> 500"}],
            "remediation": [
                {"step": "drop_rate_limit_bounds", "description": "Temporarily lower acceptable RPS bounds for non-admin IPs.", "module": "core.security", "function": "tighten_rate_limits"},
            ],
            "metrics": [{"name": "ddos_spikes_survived", "description": "Count of high traffic events gracefully limited."}],
            "escalation": {"trigger": "guardian.escalate('volumetric_ddos_detected')", "condition": "Server CPU 100% processing packet drops alone."},
            "learning": {"record_to": "knowledge_base/layer_3/network/traffic_spikes.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "traffic", "rate_limit", "self_healing"]}
        }
    },
    {
        "filename": "egress_bandwidth_throttled.yaml",
        "content": {
            "trigger": "network.traffic.bandwidth",
            "description": "Switches server outputs to Brotli/Gzip extreme compression when outbound bandwidth caps are nearing limits.",
            "conditions": [{"error_type": "Bandwidth limit exceeded"}],
            "remediation": [
                {"step": "force_gzip_compression", "description": "Ensure middleware compresses ALL outbounding text/json.", "module": "core.services.system_service", "function": "enable_extreme_compression"},
            ],
            "metrics": [{"name": "bandwidth_saved_mb", "description": "Megabytes compressed aggressively to save caps."}],
            "escalation": {"trigger": "guardian.escalate('bandwidth_hard_capped')", "condition": "Host OS kills our socket bindings for bandwidth usage."},
            "learning": {"record_to": "knowledge_base/layer_1/network/bandwidth_limits.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "bandwidth", "gzip", "self_healing"]}
        }
    },

    # ── Application-Level Networking (WebSockets & gRPC) ──────────────────
    {
        "filename": "websocket_disconnect_storm.yaml",
        "content": {
            "trigger": "network.websocket.storm",
            "description": "Triggers frontend clients to apply staggered reconnect delays preventing server crush after restart.",
            "conditions": [{"metric": "active_websocket_connections"}, {"threshold": "> 200 within 500ms"}],
            "remediation": [
                {"step": "issue_ws_reconnect_jitter", "description": "Send a Close frame with a custom 1013 code indicating retry delay bounds", "module": "api.stream_handlers", "function": "jitter_websocket_reconnects"},
            ],
            "metrics": [{"name": "ws_storms_calmed", "description": "Instances of smoothing connection avalanches."}],
            "escalation": {"trigger": "guardian.escalate('ws_pool_exhausted')", "condition": "Server exhausts async handlers accepting ws handshakes."},
            "learning": {"record_to": "knowledge_base/layer_3/network/websocket_storms.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "websocket", "jitter", "self_healing"]}
        }
    },
    {
        "filename": "websocket_heartbeat_failed.yaml",
        "content": {
            "trigger": "network.websocket.ghost",
            "description": "Severs dead TCP connections when a client stops responding to WebSocket ping frames.",
            "conditions": [{"error_type": "pong missing in timeframe"}, {"source": "asgi_server"}],
            "remediation": [
                {"step": "sever_ghost_websocket", "description": "Cleanly drop the connection mapping and free RAM.", "module": "api.stream_handlers", "function": "drop_stale_websockets"},
            ],
            "metrics": [{"name": "ghost_sockets_purged", "description": "Count of RAM recovered from dead mobile clients."}],
            "escalation": {"trigger": "guardian.escalate('ws_keepalive_broken')", "condition": "All active websockets misreport heartbeats."},
            "learning": {"record_to": "knowledge_base/layer_3/network/ghost_sockets.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "websocket", "ping", "self_healing"]}
        }
    },
    {
        "filename": "grpc_unavailable_fallback.yaml",
        "content": {
            "trigger": "network.grpc.unavailable",
            "description": "Automatically downgrades Qdrant integration to rely on standard REST HTTP if the gRPC channel HTTP/2 closes.",
            "conditions": [{"error_type": "grpc.RpcError: StatusCode.UNAVAILABLE"}],
            "remediation": [
                {"step": "downgrade_to_rest", "description": "Switch vector_db client from gRPC connection object to REST mode.", "module": "vector_db.client", "function": "force_rest_protocol"},
            ],
            "metrics": [{"name": "grpc_to_rest_downgrades", "description": "Count of Qdrant integrations seamlessly maintained."}],
            "escalation": {"trigger": "guardian.escalate('vector_cluster_offline')", "condition": "REST protocol also fails to ping."},
            "learning": {"record_to": "knowledge_base/layer_1/network/grpc_failures.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "grpc", "qdrant", "self_healing"]}
        }
    },
    {
        "filename": "redis_pubsub_desync.yaml",
        "content": {
            "trigger": "network.redis.desync",
            "description": "Triggers a full-state REST synchronization if the Redis Pub/Sub WebSocket misses sequential IDs.",
            "conditions": [{"error_type": "Message ID out of sequence"}, {"source": "redis_listener"}],
            "remediation": [
                {"step": "trigger_full_sync", "description": "Call the REST endpoints to grab recent state rather than relying on PubSub diffs.", "module": "core.memory.redis_client", "function": "resync_state"},
            ],
            "metrics": [{"name": "state_desyncs_resolved", "description": "Count of PubSub sequence breaks patched."}],
            "escalation": {"trigger": "guardian.escalate('pubsub_fatal_desync')", "condition": "Full-state sync fails to clear the pending queue."},
            "learning": {"record_to": "knowledge_base/layer_1/network/pubsub_desync.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "redis", "pubsub", "self_healing"]}
        }
    },

    # ── External Webhooks & Microservices ─────────────────────────────────
    {
        "filename": "webhook_delivery_timeout.yaml",
        "content": {
            "trigger": "network.webhook.timeout",
            "description": "Moves blocked outbound webhooks from synchronous loops to an asynchronous retry queue.",
            "conditions": [{"error_type": "TimeoutError"}, {"source": "outbound_webhook"}],
            "remediation": [
                {"step": "queue_webhook_async", "description": "Offload the dead URL payload into a RabbitMQ/Celery style delayed retry pattern.", "module": "core.services.system_service", "function": "offload_failed_hook"},
            ],
            "metrics": [{"name": "async_hooks_rescued", "description": "Count of webhooks eventually delivered."}],
            "escalation": {"trigger": "guardian.escalate('webhook_partner_offline')", "condition": "Webhook fails delivery queue after 3 days."},
            "learning": {"record_to": "knowledge_base/layer_3/network/webhook_timeouts.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "webhook", "async", "self_healing"]}
        }
    },
    {
        "filename": "service_mesh_timeout.yaml",
        "content": {
            "trigger": "network.mesh.timeout",
            "description": "Identifies timeouts in inter-container traffic across Envoy sidecars.",
            "conditions": [{"error_type": "HTTP 504 Gateway Timeout"}, {"source": "envoy_proxy"}],
            "remediation": [
                {"step": "flush_mesh_connection", "description": "Signal sidecar to drop TCP keepalives and route pure fresh HTTP.", "module": "api.health", "function": "reset_sidecar_connections"},
            ],
            "metrics": [{"name": "sidecar_resets", "description": "Count of inter-container routing healed."}],
            "escalation": {"trigger": "guardian.escalate('mesh_routing_unavailable')", "condition": "Service cannot ping sister container at all."},
            "learning": {"record_to": "knowledge_base/layer_1/network/mesh_timeouts.json", "feed_to": "cognitive.memory_mesh_learner", "tags": ["network", "mesh", "envoy", "self_healing"]}
        }
    }
]


def generate():
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "self_healing", "playbooks")
    os.makedirs(output_dir, exist_ok=True)
    
    count = 0
    for pb in NETWORKING_PLAYBOOKS:
        filepath = os.path.join(output_dir, pb["filename"])
        
        # Format the YAML output cleanly
        yaml_content = f"# Grace self-healing playbook\n# {pb['content']['description']}\n---\n"
        yaml_content += yaml.dump(pb['content'], sort_keys=False, default_flow_style=False)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(yaml_content)
        count += 1
        print(f"Generated: {pb['filename']}")
        
    print(f"\nSuccessfully generated {count} NETWORKING YAML playbooks in {output_dir}")


if __name__ == "__main__":
    generate()
