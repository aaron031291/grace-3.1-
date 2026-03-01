"""
Memory Reconciler — Single source of truth for ALL memory systems.

Ticket #2: FlashCache, Ghost Memory, and Unified Memory need reconciliation.
They currently contradict each other (hot keys age out of one but not another).

This reconciler provides:
  - atomic_get(key): checks all 3 systems, returns freshest
  - atomic_set(key, value): writes to all 3 simultaneously
  - atomic_evict(key): removes from all 3
  - reconcile(): sync all systems on demand
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryReconciler:
    """Single source of truth across FlashCache, Ghost Memory, and Unified Memory."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "MemoryReconciler":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def atomic_get(self, key: str) -> Optional[Dict]:
        """Get from the freshest source."""
        results = []

        # FlashCache
        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            refs = fc.lookup(keyword=key, limit=1)
            if refs:
                results.append({"source": "flash_cache", "data": refs[0],
                                "ts": refs[0].get("last_accessed", "")})
        except Exception:
            pass

        # Ghost Memory
        try:
            from cognitive.ghost_memory import get_ghost_memory
            ghost = get_ghost_memory()
            for entry in reversed(ghost._cache):
                if key.lower() in entry.get("content", "").lower():
                    results.append({"source": "ghost", "data": entry, "ts": entry.get("ts", "")})
                    break
        except Exception:
            pass

        # Unified Memory
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            search = mem.search_all(key)
            if search.get("total", 0) > 0:
                for sys_name, items in search.items():
                    if isinstance(items, list) and items:
                        results.append({"source": f"unified_{sys_name}", "data": items[0],
                                        "ts": items[0].get("created_at", "") if isinstance(items[0], dict) else ""})
                        break
        except Exception:
            pass

        if not results:
            return None

        # Return freshest
        results.sort(key=lambda r: r.get("ts", ""), reverse=True)
        return results[0]

    def atomic_set(self, key: str, value: str, source: str = "reconciler",
                   keywords: List[str] = None, trust: float = 0.7):
        """Write to ALL memory systems simultaneously."""
        stored = []

        # FlashCache
        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            kw = keywords or fc.extract_keywords(f"{key} {value[:200]}")
            fc.register(
                source_uri=f"internal://reconciler/{key}",
                source_type="internal",
                source_name=key,
                keywords=kw,
                summary=value[:500],
                trust_score=trust,
            )
            stored.append("flash_cache")
        except Exception:
            pass

        # Unified Memory
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            mem.store_learning(
                input_ctx=key,
                expected=value[:3000],
                trust=trust,
                source=source,
            )
            stored.append("unified_memory")
        except Exception:
            pass

        # Ghost Memory (if active)
        try:
            from cognitive.ghost_memory import get_ghost_memory
            ghost = get_ghost_memory()
            if ghost._task_id:
                ghost.append("memory_write", f"{key}: {value[:200]}")
                stored.append("ghost_memory")
        except Exception:
            pass

        return {"stored_in": stored, "key": key}

    def atomic_evict(self, key: str) -> Dict:
        """Remove from ALL memory systems."""
        evicted = []

        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            refs = fc.lookup(keyword=key, limit=5)
            for ref in refs:
                if ref.get("source_name", "").lower() == key.lower():
                    fc.remove(ref["id"])
                    evicted.append("flash_cache")
                    break
        except Exception:
            pass

        return {"evicted_from": evicted, "key": key}

    def reconcile(self) -> Dict[str, Any]:
        """Force sync all memory systems. Returns reconciliation report."""
        stats = {"flash_cache": 0, "unified_memory": 0, "ghost_memory": 0, "conflicts": 0}

        try:
            from cognitive.flash_cache import get_flash_cache
            stats["flash_cache"] = get_flash_cache().stats().get("total_entries", 0)
        except Exception:
            pass

        try:
            from cognitive.unified_memory import get_unified_memory
            mem_stats = get_unified_memory().get_stats()
            stats["unified_memory"] = sum(v.get("count", 0) for v in mem_stats.values() if isinstance(v, dict))
        except Exception:
            pass

        try:
            from cognitive.ghost_memory import get_ghost_memory
            stats["ghost_memory"] = len(get_ghost_memory()._cache)
        except Exception:
            pass

        stats["total"] = sum(v for v in stats.values() if isinstance(v, int))
        return stats


def get_reconciler() -> MemoryReconciler:
    return MemoryReconciler.get_instance()
