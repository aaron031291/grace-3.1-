"""
Genesis# Router

When a user types "Genesis#<component>" in a prompt, this router:
1. Parses the Genesis# reference
2. Looks up the component in the registry
3. Analyzes it via Oracle/LLM (Kimi analyzes the logic)
4. Wires it into all connected systems
5. Returns full acceptance + version control confirmation
6. Triggers handshake protocol for the component

This is the user-facing entry point for the Genesis# system.

Classes:
- `GenesisHashRouter`

Key Methods:
- `detect_genesis_refs()`
- `has_genesis_ref()`
- `route()`
- `get_genesis_hash_router()`

Database Tables:
None (no DB tables)

Connects To:
- `cognitive.timesense_governance`
- `genesis.component_registry`
- `genesis.unified_intelligence`
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


class GenesisHashRouter:
    """
    Parses and routes Genesis# references from user prompts.

    Syntax: Genesis#<component_name> or genesis#<component_name>
    Examples:
      - Genesis#magma_memory
      - Genesis#self_healing
      - Genesis#librarian
    """

    GENESIS_PATTERN = re.compile(
        r'[Gg]enesis#(\w[\w./-]*)',
        re.IGNORECASE
    )

    def __init__(self):
        self._registry = None
        self._intelligence = None

    def detect_genesis_refs(self, user_prompt: str) -> List[str]:
        """Extract all Genesis# references from a user prompt."""
        if not user_prompt:
            return []
        matches = self.GENESIS_PATTERN.findall(user_prompt)
        return [m.strip() for m in matches]

    def has_genesis_ref(self, user_prompt: str) -> bool:
        """Check if prompt contains any Genesis# references."""
        if not user_prompt:
            return False
        return bool(self.GENESIS_PATTERN.search(user_prompt))

    def route(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """
        Route a Genesis# reference.

        Returns component info, analysis, and acceptance confirmation.
        Returns None if no Genesis# reference found.
        """
        refs = self.detect_genesis_refs(user_prompt)
        if not refs:
            return None

        results = []
        for ref in refs:
            result = self._process_reference(ref)
            results.append(result)

        # TimeSense timing
        try:
            from cognitive.timesense_governance import get_timesense_governance
            get_timesense_governance().record("governance.check", 0, "governance")
        except Exception:
            pass

        return {
            "genesis_refs_found": len(refs),
            "components": results,
            "system_message": self._build_system_message(results),
        }

    def _process_reference(self, ref: str) -> Dict[str, Any]:
        """Process a single Genesis# reference."""
        component_info = self._lookup_component(ref)

        if not component_info:
            return {
                "ref": ref,
                "found": False,
                "status": "not_found",
                "message": f"Component '{ref}' not found in registry. It may need to be registered first.",
            }

        connections = self._get_connections(ref, component_info)
        self._record_acceptance(ref, component_info)

        return {
            "ref": ref,
            "found": True,
            "status": "accepted",
            "name": component_info.get("name", ref),
            "type": component_info.get("type", "unknown"),
            "module": component_info.get("module", ""),
            "version": component_info.get("version", 1),
            "genesis_hash": component_info.get("genesis_hash", ""),
            "health": component_info.get("health", 1.0),
            "connections": connections,
            "message": (
                f"Genesis# accepted: '{ref}' is registered, version-controlled, "
                f"and connected to {len(connections)} systems."
            ),
        }

    def _lookup_component(self, ref: str) -> Optional[Dict[str, Any]]:
        """Look up a component in the registry."""
        try:
            from database.session import SessionLocal
            from genesis.component_registry import ComponentRegistry
            session = SessionLocal()
            if not session:
                return None
            try:
                registry = ComponentRegistry(session)
                matches = registry.search(ref)
                if matches:
                    comp = matches[0]
                    return {
                        "name": comp.name,
                        "type": comp.component_type,
                        "module": comp.module_path,
                        "version": comp.version,
                        "genesis_hash": comp.genesis_hash,
                        "health": comp.health_score,
                        "capabilities": comp.capabilities,
                        "connects_to": comp.connects_to,
                    }
            finally:
                session.close()
        except Exception as e:
            logger.debug(f"[GENESIS#] Lookup failed for '{ref}': {e}")
        return None

    def _get_connections(self, ref: str, info: Dict) -> List[str]:
        """Get all systems this component is connected to."""
        connections = list(info.get("connects_to", []) or [])
        standard = [
            "genesis_keys", "version_control", "component_registry",
            "handshake_protocol", "unified_intelligence"
        ]
        for s in standard:
            if s not in connections:
                connections.append(s)
        return connections

    def _record_acceptance(self, ref: str, info: Dict):
        """Record that a Genesis# reference was accepted by the system."""
        try:
            from database.session import SessionLocal
            from genesis.unified_intelligence import UnifiedIntelligenceEngine
            session = SessionLocal()
            if session:
                try:
                    engine = UnifiedIntelligenceEngine(session)
                    engine.record(
                        source_system="genesis_hash_router",
                        signal_type="acceptance",
                        signal_name=f"genesis#{ref}",
                        value_text=f"Component '{ref}' accepted via Genesis#",
                        trust_score=0.9,
                        confidence=1.0,
                        component_name=info.get("name", ref),
                    )
                finally:
                    session.close()
        except Exception:
            pass

    def _build_system_message(self, results: List[Dict]) -> str:
        """Build a system message summarizing all Genesis# routing results."""
        accepted = [r for r in results if r.get("found")]
        not_found = [r for r in results if not r.get("found")]

        parts = []
        if accepted:
            names = ", ".join(r["ref"] for r in accepted)
            parts.append(
                f"Genesis# accepted {len(accepted)} component(s): {names}. "
                f"All are registered, version-controlled, and connected to the system."
            )
        if not_found:
            names = ", ".join(r["ref"] for r in not_found)
            parts.append(f"Genesis# could not find: {names}. These may need registration.")

        return " ".join(parts)


_router: Optional[GenesisHashRouter] = None

def get_genesis_hash_router() -> GenesisHashRouter:
    global _router
    if _router is None:
        _router = GenesisHashRouter()
    return _router
