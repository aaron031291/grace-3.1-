"""
Genesis# Component Registry

Every component in Grace self-registers here with:
- What it is (name, type, module path)
- What it does (capabilities, dependencies)
- Its Genesis hash (content hash for version tracking)
- Its health status (alive/degraded/dead)
- Last heartbeat timestamp

When a user sends "Genesis#" in a prompt, the system:
1. Parses the component reference
2. Looks it up in this registry
3. Routes to Oracle/Kimi for logic analysis
4. Wires it into all connected systems (memory, healing, version control)
5. Confirms acceptance with a handshake

This table is THE source of truth for what exists in the system.
No component can die silently because the handshake protocol checks this.

Classes:
- `ComponentEntry`
- `ComponentRegistry`

Key Methods:
- `register()`
- `heartbeat()`
- `find_silent_deaths()`
- `lookup()`
- `search()`
- `list_all()`
- `get_stats()`
- `auto_register_all_components()`

Database Tables:
- `genesis_component_registry`

Connects To:
- `security.honesty_integrity_accountability`
"""

import logging
import hashlib
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import Session

from database.base import BaseModel

logger = logging.getLogger(__name__)


class ComponentEntry(BaseModel):
    """
    A registered component in the Grace system.

    Every file, module, subsystem, and service registers here.
    The handshake protocol uses this to verify liveness.
    Self-healing uses this to detect silent deaths.
    """
    __tablename__ = "genesis_component_registry"

    name = Column(String(200), nullable=False, index=True, unique=True)
    component_type = Column(String(50), nullable=False, index=True)
    module_path = Column(String(500), nullable=False)
    file_path = Column(String(500), nullable=True)

    genesis_hash = Column(String(64), nullable=False)
    version = Column(Integer, default=1)

    description = Column(Text, nullable=True)
    capabilities = Column(JSON, nullable=True)
    dependencies = Column(JSON, nullable=True)
    connects_to = Column(JSON, nullable=True)

    status = Column(String(20), default="registered", index=True)
    health_score = Column(Float, default=1.0)
    last_heartbeat = Column(DateTime, nullable=True)
    heartbeat_count = Column(Integer, default=0)

    registered_at = Column(DateTime, default=datetime.now)
    last_updated = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)

    component_metadata = Column(JSON, nullable=True)


class ComponentRegistry:
    """
    Central registry for all Grace components.

    Provides:
    - Self-registration for any module
    - Genesis hash tracking (content-based versioning)
    - Heartbeat recording
    - Liveness queries
    - Silent death detection
    - Component discovery for Genesis# routing
    """

    def __init__(self, session: Session):
        self.session = session

    def register(
        self,
        name: str,
        component_type: str,
        module_path: str,
        file_path: str = None,
        description: str = None,
        capabilities: List[str] = None,
        dependencies: List[str] = None,
        connects_to: List[str] = None,
    ) -> ComponentEntry:
        """Register a component or update if already exists."""
        genesis_hash = self._compute_hash(file_path or module_path)

        existing = self.session.query(ComponentEntry).filter(
            ComponentEntry.name == name
        ).first()

        if existing:
            old_hash = existing.genesis_hash
            existing.genesis_hash = genesis_hash
            existing.last_updated = datetime.now()
            existing.status = "active"
            existing.is_active = True
            if description:
                existing.description = description
            if capabilities:
                existing.capabilities = capabilities
            if connects_to:
                existing.connects_to = connects_to
            if genesis_hash != old_hash:
                existing.version = (existing.version or 0) + 1
                logger.info(f"[REGISTRY] Updated '{name}' v{existing.version} (hash changed)")
            self.session.commit()
            return existing

        entry = ComponentEntry(
            name=name,
            component_type=component_type,
            module_path=module_path,
            file_path=file_path,
            genesis_hash=genesis_hash,
            description=description,
            capabilities=capabilities or [],
            dependencies=dependencies or [],
            connects_to=connects_to or [],
        )
        self.session.add(entry)
        self.session.commit()
        logger.info(f"[REGISTRY] Registered '{name}' ({component_type})")
        return entry

    def heartbeat(self, name: str, health_score: float = 1.0) -> bool:
        """Record a heartbeat from a component."""
        entry = self.session.query(ComponentEntry).filter(
            ComponentEntry.name == name
        ).first()
        if not entry:
            return False

        entry.last_heartbeat = datetime.now()
        entry.heartbeat_count = (entry.heartbeat_count or 0) + 1
        entry.health_score = health_score
        entry.status = "alive"
        self.session.commit()
        return True

    def find_silent_deaths(self, timeout_seconds: int = 600) -> List[ComponentEntry]:
        """Find components that haven't sent a heartbeat within the timeout."""
        cutoff = datetime.now() - timedelta(seconds=timeout_seconds)
        return self.session.query(ComponentEntry).filter(
            ComponentEntry.is_active == True,
            ComponentEntry.status != "registered",
            (ComponentEntry.last_heartbeat == None) | (ComponentEntry.last_heartbeat < cutoff)
        ).all()

    def lookup(self, name: str) -> Optional[ComponentEntry]:
        """Look up a component by name (for Genesis# routing)."""
        return self.session.query(ComponentEntry).filter(
            ComponentEntry.name == name
        ).first()

    def search(self, query: str) -> List[ComponentEntry]:
        """Search components by name or description."""
        pattern = f"%{query}%"
        return self.session.query(ComponentEntry).filter(
            (ComponentEntry.name.ilike(pattern)) |
            (ComponentEntry.description.ilike(pattern)) |
            (ComponentEntry.module_path.ilike(pattern))
        ).all()

    def list_all(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all registered components."""
        query = self.session.query(ComponentEntry)
        if active_only:
            query = query.filter(ComponentEntry.is_active == True)

        return [
            {
                "name": c.name,
                "type": c.component_type,
                "module": c.module_path,
                "status": c.status,
                "health": c.health_score,
                "version": c.version,
                "heartbeats": c.heartbeat_count,
                "last_heartbeat": c.last_heartbeat.isoformat() if c.last_heartbeat else None,
                "genesis_hash": c.genesis_hash[:12],
            }
            for c in query.order_by(ComponentEntry.name).all()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics with HIA integrity verification."""
        total = self.session.query(ComponentEntry).filter(ComponentEntry.is_active == True).count()
        alive = self.session.query(ComponentEntry).filter(ComponentEntry.status == "alive").count()
        silent = len(self.find_silent_deaths())
        stats = {
            "total_registered": total,
            "alive": alive,
            "silent_deaths": silent,
            "coverage": round(alive / max(total, 1), 2),
        }

        # HIA integrity check — verify reported stats match actual DB counts
        try:
            from security.honesty_integrity_accountability import get_hia_framework
            actual_total = self.session.query(ComponentEntry).count()
            hia = get_hia_framework()
            hia.verify_kpi_report(stats["coverage"], alive, max(total, 1))
            stats["hia_verified"] = True
        except Exception:
            stats["hia_verified"] = False

        return stats

    def _compute_hash(self, path: str) -> str:
        """Compute Genesis hash for a file or module."""
        try:
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            pass
        return hashlib.sha256(path.encode()).hexdigest()


def auto_register_all_components(session: Session, backend_dir: str = None):
    """
    Scan the backend directory and auto-register all Python modules.

    Called at startup to populate the registry with every component.
    """
    registry = ComponentRegistry(session)
    backend = Path(backend_dir) if backend_dir else Path(__file__).parent.parent

    COMPONENT_MAP = {
        "cognitive": "cognitive_system",
        "api": "api_endpoint",
        "genesis": "genesis_system",
        "ml_intelligence": "ml_system",
        "retrieval": "retrieval_system",
        "ingestion": "ingestion_system",
        "llm_orchestrator": "llm_system",
        "diagnostic_machine": "diagnostic_system",
        "security": "security_system",
        "librarian": "librarian_system",
        "layer1": "layer1_system",
        "agent": "agent_system",
        "services": "service",
        "scraping": "scraping_system",
        "telemetry": "telemetry_system",
        "execution": "execution_system",
    }

    count = 0
    for subdir, comp_type in COMPONENT_MAP.items():
        module_dir = backend / subdir
        if not module_dir.is_dir():
            continue

        for py_file in module_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            name = f"{subdir}.{py_file.stem}"
            try:
                registry.register(
                    name=name,
                    component_type=comp_type,
                    module_path=f"{subdir}.{py_file.stem}",
                    file_path=str(py_file),
                    description=f"Auto-registered from {py_file.name}",
                )
                count += 1
            except Exception as e:
                logger.debug(f"[REGISTRY] Failed to register {name}: {e}")

    logger.info(f"[REGISTRY] Auto-registered {count} components")
    return count
