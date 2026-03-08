"""
Grace System Registry — Living map of every component in the system.

Connected to Genesis Keys, Auto-Updater, and Handshake Protocol.
Shows every component (old code and new code) with live status:
  🟢 Green = working
  🟡 Amber = degraded or partially working
  🔴 Red = broken or not responding

The registry:
1. Auto-discovers components on startup by scanning the codebase
2. Listens to HUNTER handshakes to register new components
3. Reads genesis keys to track last activity per component
4. Pings components to check health status
5. Persists to disk so nothing is ever lost
6. Human-readable display — you see the full system, not a black box
"""

import logging
import os
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

REGISTRY_FILE = Path(__file__).parent.parent / "data" / "system_registry.json"


@dataclass
class Component:
    """A registered component in Grace."""
    id: str
    name: str
    category: str  # cognitive, api, frontend, intelligence, infrastructure, data
    module_path: str
    description: str = ""
    status: str = "unknown"  # green, amber, red, unknown
    last_seen: str = ""
    last_genesis_key: str = ""
    health_score: float = 0
    dependencies: List[str] = field(default_factory=list)
    registered_at: str = ""
    source: str = "auto_discovery"  # auto_discovery, hunter_handshake, manual
    file_count: int = 0
    is_new: bool = False


class SystemRegistry:
    """
    Living registry of every component in Grace.
    Auto-discovers, tracks health, persists, and displays.
    """

    def __init__(self):
        self._components: Dict[str, Component] = {}
        self._load()
        self._auto_discover()
        self._connect_to_realtime()

    # ── Auto-discovery ─────────────────────────────────────────────────

    def _auto_discover(self):
        """Scan the codebase and register every module."""
        backend = Path(__file__).parent.parent
        skip = {'venv', 'node_modules', '__pycache__', 'mcp_repos', '.git', 'tests', 'data', 'logs', 'knowledge_base'}

        categories = {
            'cognitive': 'cognitive',
            'api': 'api',
            'llm_orchestrator': 'intelligence',
            'ml_intelligence': 'intelligence',
            'genesis': 'tracking',
            'retrieval': 'data',
            'ingestion': 'data',
            'vector_db': 'data',
            'database': 'infrastructure',
            'security': 'infrastructure',
            'diagnostic_machine': 'infrastructure',
            'grace_os': 'core',
            'agent': 'intelligence',
            'execution': 'intelligence',
            'confidence_scorer': 'intelligence',
            'scraping': 'data',
            'search': 'data',
            'librarian': 'data',
            'file_manager': 'data',
            'telemetry': 'infrastructure',
            'models': 'infrastructure',
            'services': 'core',
            'layer1': 'core',
            'cache': 'infrastructure',
            'core': 'core',
            'embedding': 'intelligence',
            'version_control': 'infrastructure',
        }

        for d in sorted(backend.iterdir()):
            if d.name in skip or not d.is_dir() or d.name.startswith('.'):
                continue

            py_files = [f for f in d.rglob('*.py') if '__pycache__' not in str(f)]
            if not py_files:
                continue

            comp_id = f"module_{d.name}"
            if comp_id not in self._components:
                category = categories.get(d.name, 'other')

                # Check if module is importable
                status = "unknown"
                try:
                    __import__(d.name)
                    status = "green"
                except Exception:
                    status = "amber"

                self._components[comp_id] = Component(
                    id=comp_id,
                    name=d.name,
                    category=category,
                    module_path=str(d.relative_to(backend)),
                    description=self._get_module_description(d),
                    status=status,
                    registered_at=datetime.utcnow().isoformat(),
                    source="auto_discovery",
                    file_count=len(py_files),
                )

        # Register frontend tabs
        frontend_tabs = Path(__file__).parent.parent.parent / "frontend" / "src" / "components"
        if frontend_tabs.exists():
            for f in frontend_tabs.iterdir():
                if f.name.endswith('Tab.jsx'):
                    comp_id = f"frontend_{f.stem}"
                    if comp_id not in self._components:
                        self._components[comp_id] = Component(
                            id=comp_id,
                            name=f.stem,
                            category="frontend",
                            module_path=f"frontend/src/components/{f.name}",
                            description=f"Frontend tab: {f.stem}",
                            status="green",
                            registered_at=datetime.utcnow().isoformat(),
                            source="auto_discovery",
                            file_count=1,
                        )

        # Register key individual components
        key_components = [
            ("cognitive_pipeline", "Cognitive Pipeline", "cognitive", "cognitive/pipeline.py", "9-stage cognitive processing chain"),
            ("trust_engine", "Trust Engine", "intelligence", "cognitive/trust_engine.py", "Component-level trust scoring 0-100"),
            ("immune_system", "Immune System", "cognitive", "cognitive/immune_system.py", "Autonomous health monitoring and healing"),
            ("healing_coordinator", "Healing Coordinator", "cognitive", "cognitive/healing_coordinator.py", "Intelligent problem resolution chain"),
            ("magma_memory", "Magma Memory", "cognitive", "cognitive/magma/", "4-graph relation memory system"),
            ("genesis_realtime", "Genesis Realtime", "tracking", "genesis/realtime.py", "Instant event firing and alerting"),
            ("governance_wrapper", "Governance Wrapper", "intelligence", "llm_orchestrator/governance_wrapper.py", "Law docs enforced on every LLM call"),
            ("kimi_enhanced", "Kimi Enhanced", "intelligence", "llm_orchestrator/kimi_enhanced.py", "8 tool-like Kimi capabilities"),
            ("hunter_assimilator", "HUNTER Assimilator", "intelligence", "cognitive/hunter_assimilator.py", "Autonomous code integration"),
            ("idle_learner", "Idle Learner", "intelligence", "cognitive/idle_learner.py", "Kimi teaches during idle time"),
            ("knowledge_cycle", "Knowledge Cycle", "intelligence", "cognitive/knowledge_cycle.py", "Seed→discover→score→enrich→reingest"),
            ("autonomous_librarian", "Autonomous Librarian", "data", "cognitive/librarian_autonomous.py", "Auto-organise files system-wide"),
            ("time_sense", "TimeSense", "cognitive", "cognitive/time_sense.py", "Temporal awareness and urgency"),
            ("self_healing", "Self-Healing", "infrastructure", "cognitive/self_healing.py", "Service recovery and fallback"),
            ("feedback_loop", "Feedback Loop", "intelligence", "cognitive/pipeline.py", "Learn from outcomes"),
            ("magma_bridge", "Magma Bridge", "cognitive", "cognitive/magma_bridge.py", "Connects Magma to all systems"),
        ]

        for comp_id, name, category, path, desc in key_components:
            if comp_id not in self._components:
                status = "green"
                try:
                    full_path = backend / path
                    if not full_path.exists():
                        status = "red"
                except Exception:
                    status = "red"

                self._components[comp_id] = Component(
                    id=comp_id, name=name, category=category,
                    module_path=path, description=desc,
                    status=status,
                    registered_at=datetime.utcnow().isoformat(),
                    source="auto_discovery",
                )

        self._save()

    def _get_module_description(self, module_dir: Path) -> str:
        init = module_dir / "__init__.py"
        if init.exists():
            try:
                content = init.read_text(errors="ignore")
                for line in content.split('\n'):
                    line = line.strip().strip('"').strip("'")
                    if line and not line.startswith('#') and not line.startswith('from') and not line.startswith('import') and len(line) > 10:
                        return line[:200]
            except Exception:
                pass
        return f"Backend module: {module_dir.name}"

    # ── Realtime connection ────────────────────────────────────────────

    def _connect_to_realtime(self):
        try:
            from genesis.realtime import get_realtime_engine
            rt = get_realtime_engine()
            rt.watch("__all__", self._on_genesis_event)
            logger.info("[REGISTRY] Connected to genesis realtime")
        except Exception:
            pass

    def _on_genesis_event(self, event):
        """Update last_seen for components based on genesis key activity. Accepts Event or dict."""
        data = getattr(event, "data", event) if event is not None else {}
        if not isinstance(data, dict):
            data = {}
        where = data.get("where", "")
        key_type = data.get("key_type", "")

        for comp in self._components.values():
            if comp.module_path and comp.module_path in where:
                comp.last_seen = data.get("timestamp", "")
                comp.last_genesis_key = (data.get("what", "") or "")[:100]

    # ── HUNTER handshake registration ──────────────────────────────────

    def register_from_handshake(self, announcement: Dict):
        """Register a new component from HUNTER handshake."""
        files = announcement.get("files", [])
        request_id = announcement.get("request_id", "")
        trust = announcement.get("trust_score", 0)

        comp_id = f"hunter_{request_id}"
        self._components[comp_id] = Component(
            id=comp_id,
            name=f"HUNTER: {request_id}",
            category="intelligence",
            module_path=", ".join(files[:5]),
            description=f"HUNTER assimilated component (trust: {trust:.0f})",
            status="green" if trust >= 60 else "amber" if trust >= 40 else "red",
            health_score=trust,
            registered_at=datetime.utcnow().isoformat(),
            source="hunter_handshake",
            file_count=len(files),
            is_new=True,
        )
        self._save()

    # ── Health check ───────────────────────────────────────────────────

    def check_health(self) -> Dict[str, Any]:
        """Check health of all registered components."""
        for comp in self._components.values():
            if comp.source == "auto_discovery" and comp.category != "frontend":
                try:
                    module_name = comp.module_path.replace('/', '.').replace('.py', '')
                    if '.' in module_name:
                        module_name = module_name.split('.')[0]
                    __import__(module_name)
                    comp.status = "green"
                    comp.health_score = 90
                except Exception:
                    if comp.status == "green":
                        comp.status = "amber"
                        comp.health_score = 50
                    else:
                        comp.status = "red"
                        comp.health_score = 0

        self._save()

        green = sum(1 for c in self._components.values() if c.status == "green")
        amber = sum(1 for c in self._components.values() if c.status == "amber")
        red = sum(1 for c in self._components.values() if c.status == "red")
        unknown = sum(1 for c in self._components.values() if c.status == "unknown")

        return {
            "total": len(self._components),
            "green": green, "amber": amber, "red": red, "unknown": unknown,
            "health_pct": round(green / max(len(self._components), 1) * 100, 1),
        }

    # ── Query ──────────────────────────────────────────────────────────

    def get_all(self) -> List[Dict]:
        """Get all components as human-readable list."""
        return sorted([
            {
                "id": c.id, "name": c.name, "category": c.category,
                "module": c.module_path, "description": c.description,
                "status": c.status, "health": c.health_score,
                "last_seen": c.last_seen, "last_key": c.last_genesis_key,
                "registered": c.registered_at, "source": c.source,
                "files": c.file_count, "is_new": c.is_new,
                "dependencies": c.dependencies,
            }
            for c in self._components.values()
        ], key=lambda x: ({"green": 0, "amber": 1, "red": 2, "unknown": 3}.get(x["status"], 4), x["category"], x["name"]))

    def get_by_category(self) -> Dict[str, List[Dict]]:
        """Get components grouped by category."""
        all_comps = self.get_all()
        categories = {}
        for c in all_comps:
            cat = c["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(c)
        return categories

    def get_by_status(self, status: str) -> List[Dict]:
        return [c for c in self.get_all() if c["status"] == status]

    # ── Persistence ────────────────────────────────────────────────────

    def _save(self):
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for comp_id, comp in self._components.items():
            data[comp_id] = {
                "id": comp.id, "name": comp.name, "category": comp.category,
                "module_path": comp.module_path, "description": comp.description,
                "status": comp.status, "health_score": comp.health_score,
                "last_seen": comp.last_seen, "last_genesis_key": comp.last_genesis_key,
                "registered_at": comp.registered_at, "source": comp.source,
                "file_count": comp.file_count, "is_new": comp.is_new,
                "dependencies": comp.dependencies,
            }
        REGISTRY_FILE.write_text(json.dumps(data, indent=2, default=str))

    def _load(self):
        if REGISTRY_FILE.exists():
            try:
                data = json.loads(REGISTRY_FILE.read_text())
                for comp_id, comp_data in data.items():
                    self._components[comp_id] = Component(**comp_data)
            except Exception:
                pass


_registry = None

def get_system_registry() -> SystemRegistry:
    global _registry
    if _registry is None:
        _registry = SystemRegistry()
    return _registry
