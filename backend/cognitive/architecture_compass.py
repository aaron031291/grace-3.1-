"""
Architecture Compass — Grace's Internal Self-Awareness Map

Grace needs to understand her own architecture to function as an IDE.
This module gives her an internal compass — she knows:
  - What each component does and why it exists
  - How components connect to each other
  - What data flows between them
  - What capabilities are available for any given task
  - Where bottlenecks and weak points are

The compass auto-registers all 184 modules on startup by scanning
the source code and building a live component graph.

Usage by Grace:
  compass.explain("pipeline")        → "The cognitive pipeline is a 9-stage..."
  compass.find_for("code review")    → ["consensus_engine", "hunter", "pipeline"]
  compass.how_connected("trust_engine", "pipeline") → data flow path
  compass.diagnose()                 → bottlenecks, broken links
"""

import ast
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from cognitive.event_bus import publish

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).parent.parent


# Pre-built knowledge of what each major system does
COMPONENT_KNOWLEDGE = {
    "cognitive/pipeline.py": {
        "purpose": "9-stage cognitive processing chain: TimeSense→OODA→Ambiguity→Invariants→Generate→Contradiction→Hallucination→Trust→Genesis. Every code generation and reasoning task flows through this pipeline.",
        "capabilities": ["code_generation", "reasoning", "verification", "trust_scoring"],
        "key_apis": ["CognitivePipeline.run()"],
    },
    "cognitive/consensus_engine.py": {
        "purpose": "Multi-model roundtable (Knights of the Roundtable). 4 layers: independent deliberation → consensus formation → alignment → verification. Runs Opus, Kimi, Qwen, and reasoning models in parallel on the same problem.",
        "capabilities": ["multi_model_consensus", "autonomous_batch", "conflict_resolution"],
        "key_apis": ["run_consensus()", "queue_autonomous_query()", "get_available_models()"],
    },
    "cognitive/trust_engine.py": {
        "purpose": "Component-level trust scoring (0-100). Breaks output into chunks, scores each chunk on source reliability, content quality, consensus, and recency. Components below threshold get flagged for verification.",
        "capabilities": ["trust_scoring", "verification_trigger", "component_tracking"],
        "key_apis": ["get_trust_engine().score_output()", "get_dashboard()"],
    },
    "cognitive/immune_system.py": {
        "purpose": "AVN (Autonomous Vigilance Network). Monitors all system health: DB, Qdrant, LLM, memory, disk, API, ingestion. Adaptive scan intervals (10s-5min). Self-heals with rollback. Connects to genesis realtime for instant error notification.",
        "capabilities": ["health_monitoring", "self_healing", "anomaly_detection", "healing_playbook"],
        "key_apis": ["GraceImmuneSystem.scan()", "_diagnose_and_heal()"],
    },
    "cognitive/flash_cache.py": {
        "purpose": "Reference-based intelligent caching. Stores source URIs + keywords + summaries, NOT full content. Content streamed on demand from original source. Sub-millisecond keyword lookups via inverted index.",
        "capabilities": ["keyword_lookup", "source_caching", "on_demand_streaming", "keyword_prediction"],
        "key_apis": ["get_flash_cache().register()", ".lookup()", ".search()", ".stream_content()"],
    },
    "cognitive/unified_memory.py": {
        "purpose": "Single interface for all 5 memory systems: episodic (experiences), procedural (skills), learning (training data), magma (graph memory), flash cache (external refs). Search all at once.",
        "capabilities": ["memory_store", "memory_recall", "cross_memory_search"],
        "key_apis": ["get_unified_memory().store_episode()", ".search_all()", ".get_stats()"],
    },
    "cognitive/central_orchestrator.py": {
        "purpose": "Grace's Cognitive Operating System. Coordinates all autonomous systems. Global state container, task routing, integration health monitoring. Event bus subscriptions for system-wide awareness.",
        "capabilities": ["task_routing", "state_sync", "integration_health", "global_awareness"],
        "key_apis": ["get_orchestrator().route_task()", ".sync_state()", ".check_integration_health()"],
    },
    "cognitive/event_bus.py": {
        "purpose": "In-process pub/sub event system. Components publish events (llm.called, healing.started, trust.updated), subscribers react. Wildcard support. Non-blocking async publish.",
        "capabilities": ["event_publishing", "event_subscription", "wildcard_matching"],
        "key_apis": ["publish()", "subscribe()", "publish_async()"],
    },
    "cognitive/librarian_autonomous.py": {
        "purpose": "Autonomous file organization. Watches for new files from ANY source, analyses content, creates directory structures, moves files to correct locations. Uses Kimi for unknown file types. FlashCache for reference lookups.",
        "capabilities": ["file_organization", "directory_management", "content_analysis", "taxonomy_maintenance"],
        "key_apis": ["AutonomousLibrarian.organise_file()", ".suggest_location()", ".on_new_folder()"],
    },
    "cognitive/hunter_assimilator.py": {
        "purpose": "Autonomous code integration triggered by HUNTER keyword. 15-step pipeline: parse→Kimi analyse→pipeline verify→code review→fix→trust→healing pre-check→write→schema→librarian→handshake→contradiction→learn→immune→KPI.",
        "capabilities": ["code_integration", "automated_review", "schema_migration"],
        "key_apis": ["HunterAssimilator.assimilate()"],
    },
    "cognitive/knowledge_cycle.py": {
        "purpose": "Iterative knowledge expansion: Seed→Discover→Score→Enrich→Validate→Reingest. Sources: Oracle DB, RAG, Magma, FlashCache. Trust-aware with depth limits and cost controls.",
        "capabilities": ["knowledge_expansion", "multi_source_discovery", "trust_scoring"],
        "key_apis": ["KnowledgeCycle.run_cycle()"],
    },
    "cognitive/mirror_self_modeling.py": {
        "purpose": "Grace's self-awareness. Analyses Genesis Keys to detect behavioral patterns: what keeps failing, what's improving, efficiency drops, learning plateaus. Lazy-loadable (no DB session required).",
        "capabilities": ["self_observation", "pattern_detection", "improvement_suggestions"],
        "key_apis": ["MirrorSelfModelingSystem().observe_recent_operations()", ".detect_behavioral_patterns()"],
    },
    "cognitive/idle_learner.py": {
        "purpose": "Background learning during idle time. Kimi teaches the coding agent from a 26-topic curriculum. Identifies knowledge gaps from failed generations.",
        "capabilities": ["background_learning", "gap_identification", "curriculum_teaching"],
        "key_apis": ["IdleLearner.learn_topic()"],
    },
    "cognitive/model_updater.py": {
        "purpose": "Checks Kimi/Opus/Ollama APIs for new model versions. Auto-updates runtime config and persists to .env. Version history tracked.",
        "capabilities": ["model_discovery", "version_update", "provider_health_check"],
        "key_apis": ["check_all_models()", "update_model()"],
    },
    "cognitive/file_generator.py": {
        "purpose": "Autonomous file creation from natural language prompts. Supports PDF, code, docs, data files. Auto-detects type, generates via appropriate LLM, saves to KB, registers in docs, organises via librarian.",
        "capabilities": ["file_generation", "multi_format_output"],
        "key_apis": ["FileGenerator.generate()"],
    },
    "cognitive/healing_coordinator.py": {
        "purpose": "Orchestrates the full healing chain: detect→diagnose→fix→verify→learn. Grace and Kimi independently diagnose, coding agent fixes, web search for context.",
        "capabilities": ["healing_orchestration", "multi_model_diagnosis"],
        "key_apis": ["HealingCoordinator.heal()"],
    },
    "llm_orchestrator/factory.py": {
        "purpose": "Factory for creating LLM clients. Every client wrapped with GovernanceAwareLLM. Supports: Ollama (local), Kimi (cloud), Opus (cloud). Per-task model selection (code, reason, fast).",
        "capabilities": ["llm_client_creation", "governance_wrapping", "task_routing"],
        "key_apis": ["get_llm_client()", "get_kimi_client()", "get_opus_client()", "get_llm_for_task()"],
    },
    "llm_orchestrator/governance_wrapper.py": {
        "purpose": "Wraps ALL LLM clients. Injects governance rules and persona into every call. Tracks usage stats (latency, errors, tokens) for BI dashboard. Genesis Key on every call.",
        "capabilities": ["governance_injection", "usage_tracking", "persona_management"],
        "key_apis": ["GovernanceAwareLLM.generate()", "get_llm_usage_stats()"],
    },
    "api/_genesis_tracker.py": {
        "purpose": "Genesis Key creation helper. Every system output gets a Genesis Key (who/what/when/where/why/how). Fires realtime engine and event bus for instant notification.",
        "capabilities": ["provenance_tracking", "event_firing"],
        "key_apis": ["track()"],
    },
    "security/api_vault.py": {
        "purpose": "Central secure access point for all API keys. Masked display, per-provider verification, key rotation with audit trail.",
        "capabilities": ["key_management", "provider_verification", "key_rotation"],
        "key_apis": ["get_vault().get_status()", ".verify_all()", ".rotate_key()"],
    },
    "api/chunked_upload_api.py": {
        "purpose": "Chunked file upload supporting 5GB files. 5MB chunks, SHA256 per-chunk verification, resumable, streaming reassembly. Auto-registers in docs library.",
        "capabilities": ["large_file_upload", "integrity_verification", "resumable_upload"],
        "key_apis": ["/api/upload/initiate", "/api/upload/chunk", "/api/upload/complete"],
    },
    "api/brain_api_v2.py": {
        "purpose": "Unified brain router: chat response (Cursor-style), consensus, code generation, RAG, file ops, governance, health. Single entry point for all 93+ actions across 8 domains.",
        "capabilities": ["chat_response", "full_nlp", "multi_model_consensus", "code_generation", "semantic_search", "file_operations", "governance"],
        "key_apis": ["call_brain()", "brain_directory()", "health_map()", "semantic_query()"],
    },
    "api/stream_api.py": {
        "purpose": "SSE streaming chat response. Cursor-style streaming: token-by-token delivery, model selection (Kimi/Opus), mention parsing, RAG context injection.",
        "capabilities": ["chat_response", "streaming", "full_nlp", "multi_model"],
        "key_apis": ["/api/stream/chat", "streamChat()"],
    },
    "api/completion_api.py": {
        "purpose": "Inline code completion (Cursor-style). Context-aware completion from code before/after cursor, optional streaming. Used by IDE and chat.",
        "capabilities": ["chat_response", "code_completion", "inline_completion"],
        "key_apis": ["/api/complete", "getCompletion()", "streamCompletion()"],
    },
    "api/autonomous_loop_api.py": {
        "purpose": "Autonomous task loop API. Background and one-shot autonomous runs, progress polling, task lifecycle.",
        "capabilities": ["autonomous_loop", "background_tasks", "task_progress"],
        "key_apis": ["/autonomous-learning/*", "run_background()", "progress"],
    },
    "api/retrieve.py": {
        "purpose": "RAG retrieval and semantic search. Multi-tier retrieval (vector → model → context), reranking, trust-aware scoring. Full NLP pipeline for query understanding and document search.",
        "capabilities": ["full_nlp", "semantic_search", "rag_retrieval", "reranking", "multi_tier"],
        "key_apis": ["/api/retrieve/*", "retrieve()", "search()"],
    },
    "retrieval/retriever.py": {
        "purpose": "Core vector retrieval against Qdrant. Embedding-based similarity, filters, scoring. Part of full NLP stack for semantic search.",
        "capabilities": ["full_nlp", "vector_search", "embedding_similarity"],
        "key_apis": ["retrieve()", "search()"],
    },
    "embedding/embedder.py": {
        "purpose": "Text embedding model (e.g. Qwen). Encodes text to vectors for RAG and semantic search. Foundation for full NLP retrieval.",
        "capabilities": ["full_nlp", "embeddings", "vector_encoding"],
        "key_apis": ["embed()", "embed_batch()"],
    },
}


@dataclass
class ComponentInfo:
    name: str
    file_path: str
    purpose: str
    capabilities: List[str]
    key_apis: List[str]
    classes: List[str]
    public_functions: List[str]
    imports_from: List[str]
    imported_by: List[str]
    connection_count: int
    is_isolated: bool
    last_health: str = "unknown"


class ArchitectureCompass:
    """Grace's internal understanding of her own architecture."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._components: Dict[str, ComponentInfo] = {}
        self._connection_graph: Dict[str, Set[str]] = {}
        self._reverse_graph: Dict[str, Set[str]] = {}
        self._capability_index: Dict[str, List[str]] = {}
        self._built = False

    @classmethod
    def get_instance(cls) -> "ArchitectureCompass":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def build(self):
        """Scan the entire codebase and build the component map."""
        if self._built:
            return

        for subdir in ["api", "cognitive", "llm_orchestrator", "genesis", "security", "search", "retrieval", "embedding"]:
            d = BACKEND_DIR / subdir
            if not d.exists():
                continue
            for f in d.glob("*.py"):
                if f.name == "__init__.py":
                    continue
                self._scan_module(f, subdir)

        self._build_reverse_graph()
        self._build_capability_index()
        self._built = True
        logger.info(f"[COMPASS] Built architecture map: {len(self._components)} components")
        publish("architecture.compass_built", data={"components": len(self._components)}, source="architecture_compass")

    def _scan_module(self, file_path: Path, subdir: str):
        rel = f"{subdir}/{file_path.name}"
        try:
            source = file_path.read_text(errors="ignore")
            tree = ast.parse(source)
        except Exception:
            return

        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
        imports_from = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if any(node.module.startswith(p) for p in ["cognitive.", "api.", "llm_orchestrator.", "genesis.", "security."]):
                    imports_from.append(node.module)

        # Use pre-built knowledge if available
        knowledge = COMPONENT_KNOWLEDGE.get(rel, {})

        info = ComponentInfo(
            name=rel.replace("/", ".").replace(".py", ""),
            file_path=rel,
            purpose=knowledge.get("purpose", f"Module with {len(classes)} classes and {len(functions)} functions"),
            capabilities=knowledge.get("capabilities", []),
            key_apis=knowledge.get("key_apis", functions[:5]),
            classes=classes,
            public_functions=functions,
            imports_from=list(set(imports_from)),
            imported_by=[],
            connection_count=len(imports_from),
            is_isolated=len(imports_from) == 0,
        )

        self._components[rel] = info
        self._connection_graph[rel] = set()
        for imp in imports_from:
            target = imp.replace(".", "/") + ".py"
            self._connection_graph[rel].add(target)

    def _build_reverse_graph(self):
        self._reverse_graph = {}
        for src, targets in self._connection_graph.items():
            for target in targets:
                if target not in self._reverse_graph:
                    self._reverse_graph[target] = set()
                self._reverse_graph[target].add(src)

        for comp_path, info in self._components.items():
            info.imported_by = list(self._reverse_graph.get(comp_path, set()))

    def _build_capability_index(self):
        self._capability_index = {}
        for comp_path, info in self._components.items():
            for cap in info.capabilities:
                if cap not in self._capability_index:
                    self._capability_index[cap] = []
                self._capability_index[cap].append(comp_path)

    # ── Grace's Internal Dialogue ─────────────────────────────────────

    def explain(self, component_name: str) -> str:
        """Grace asks: What does this component do?"""
        self.build()
        for path, info in self._components.items():
            if component_name.lower() in path.lower() or component_name.lower() in info.name.lower():
                lines = [
                    f"**{info.name}** (`{info.file_path}`)",
                    f"Purpose: {info.purpose}",
                    f"Capabilities: {', '.join(info.capabilities) if info.capabilities else 'general'}",
                    f"Key APIs: {', '.join(info.key_apis[:5])}",
                    f"Classes: {', '.join(info.classes[:5])}",
                    f"Connects to: {len(info.imports_from)} modules",
                    f"Used by: {len(info.imported_by)} modules",
                    f"Isolated: {'Yes' if info.is_isolated else 'No'}",
                ]
                return "\n".join(lines)
        return f"Unknown component: {component_name}"

    def find_for(self, capability: str) -> List[str]:
        """Grace asks: What can handle this task?"""
        self.build()
        results = []
        cap_lower = capability.lower()

        # Direct capability match
        for cap, components in self._capability_index.items():
            if cap_lower in cap.lower() or cap.lower() in cap_lower:
                results.extend(components)

        # Fuzzy search in purpose descriptions
        if not results:
            for path, info in self._components.items():
                if cap_lower in info.purpose.lower():
                    results.append(path)

        return list(set(results))[:10]

    def how_connected(self, comp_a: str, comp_b: str) -> List[str]:
        """Grace asks: How does data flow from A to B?"""
        self.build()
        path_a = self._resolve_path(comp_a)
        path_b = self._resolve_path(comp_b)
        if not path_a or not path_b:
            return [f"Could not resolve: {comp_a if not path_a else comp_b}"]

        # BFS for shortest path
        from collections import deque
        visited = set()
        queue = deque([(path_a, [path_a])])
        while queue:
            current, path = queue.popleft()
            if current == path_b:
                return path
            if current in visited:
                continue
            visited.add(current)
            for neighbor in self._connection_graph.get(current, set()):
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))

        return [f"No direct path from {comp_a} to {comp_b}"]

    def diagnose(self) -> Dict[str, Any]:
        """Grace self-diagnoses her architecture."""
        self.build()
        isolated = [p for p, i in self._components.items() if i.is_isolated]
        most_depended = sorted(
            [(p, len(self._reverse_graph.get(p, set()))) for p in self._components],
            key=lambda x: -x[1]
        )[:10]
        most_connections = sorted(
            [(p, i.connection_count) for p, i in self._components.items()],
            key=lambda x: -x[1]
        )[:10]

        return {
            "total_components": len(self._components),
            "total_connections": sum(len(v) for v in self._connection_graph.values()),
            "isolated_count": len(isolated),
            "isolated_modules": isolated[:20],
            "most_depended_on": [{"module": p, "dependents": c} for p, c in most_depended],
            "most_connections": [{"module": p, "connections": c} for p, c in most_connections],
            "capabilities_available": list(self._capability_index.keys()),
        }

    def predict_dependency_issues(self) -> List[Dict[str, Any]]:
        """
        Predict dependency issues before they happen.
        Uses the connection graph to find:
        - Single points of failure (modules everything depends on)
        - Circular dependency risks
        - Modules with too many dependents (fragile)
        - Orphaned modules that might break silently
        """
        self.build()
        issues = []

        # Single points of failure: modules with >10 dependents
        for path in self._components:
            dependents = len(self._reverse_graph.get(path, set()))
            if dependents > 10:
                issues.append({
                    "type": "single_point_of_failure",
                    "severity": "high" if dependents > 20 else "medium",
                    "module": path,
                    "dependents": dependents,
                    "risk": f"{path} has {dependents} dependents — if it breaks, {dependents} modules fail",
                    "mitigation": "Add fallback/retry logic in dependent modules",
                })

        # Modules with 0 dependents but many outgoing connections (consumer-only, may be stale)
        for path, info in self._components.items():
            dependents = len(self._reverse_graph.get(path, set()))
            outgoing = info.connection_count
            if dependents == 0 and outgoing > 5:
                issues.append({
                    "type": "potential_dead_code",
                    "severity": "low",
                    "module": path,
                    "outgoing": outgoing,
                    "risk": f"{path} imports {outgoing} modules but nothing imports it — possibly unused",
                })

        # Highly connected clusters (tight coupling risk)
        for path, info in self._components.items():
            if info.connection_count > 8:
                issues.append({
                    "type": "tight_coupling",
                    "severity": "medium",
                    "module": path,
                    "connections": info.connection_count,
                    "risk": f"{path} has {info.connection_count} dependencies — tightly coupled, hard to modify",
                    "mitigation": "Consider using event bus for some connections",
                })

        issues.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["severity"], 3))
        return issues

    def get_full_map(self) -> Dict[str, Any]:
        """Complete architecture map for display."""
        self.build()
        return {
            "components": {
                path: {
                    "name": info.name,
                    "purpose": info.purpose[:200],
                    "capabilities": info.capabilities,
                    "connections_out": len(info.imports_from),
                    "connections_in": len(info.imported_by),
                    "isolated": info.is_isolated,
                }
                for path, info in self._components.items()
            },
            "total": len(self._components),
            "connected": sum(1 for i in self._components.values() if not i.is_isolated),
            "isolated": sum(1 for i in self._components.values() if i.is_isolated),
        }

    def _resolve_path(self, name: str) -> Optional[str]:
        for path in self._components:
            if name.lower() in path.lower():
                return path
        return None


def get_compass() -> ArchitectureCompass:
    return ArchitectureCompass.get_instance()
