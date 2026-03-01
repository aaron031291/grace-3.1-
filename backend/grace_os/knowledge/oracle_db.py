"""
Grace OS — Oracle Database (Knowledge Store)

Persistent memory across sessions. Stores past task results,
file dependency graphs, trust score history, and successful approaches.
Dict-backed, serializable to/from JSON for persistence.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OracleDB:
    """
    In-memory knowledge store with JSON serialization.
    Categories: task_results, error_patterns, conventions, trust_history, file_deps
    """

    def __init__(self, persist_path: Optional[str] = None):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._persist_path = persist_path

        # Auto-load if persist path exists
        if persist_path and os.path.exists(persist_path):
            self.import_from_json(persist_path)

    def store(self, category: str, key: str, value: Any, metadata: Optional[Dict] = None):
        """Store a value under category/key with optional metadata."""
        if category not in self._store:
            self._store[category] = {}

        self._store[category][key] = {
            "value": value,
            "metadata": metadata or {},
            "timestamp": time.time(),
            "version": self._store[category].get(key, {}).get("version", 0) + 1,
        }

        logger.debug(f"[OracleDB] Stored: {category}/{key}")

    def query(self, category: str, key: str) -> Optional[Any]:
        """Query a specific value by category/key."""
        entry = self._store.get(category, {}).get(key)
        if entry:
            return entry["value"]
        return None

    def query_all(self, category: str) -> Dict[str, Any]:
        """Get all entries in a category."""
        entries = self._store.get(category, {})
        return {k: v["value"] for k, v in entries.items()}

    def query_recent(self, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent entries in a category."""
        entries = self._store.get(category, {})
        sorted_entries = sorted(
            entries.items(),
            key=lambda x: x[1].get("timestamp", 0),
            reverse=True,
        )
        return [
            {"key": k, "value": v["value"], "timestamp": v["timestamp"]}
            for k, v in sorted_entries[:limit]
        ]

    def delete(self, category: str, key: str) -> bool:
        """Delete a specific entry."""
        if category in self._store and key in self._store[category]:
            del self._store[category][key]
            return True
        return False

    def get_categories(self) -> List[str]:
        """List all categories."""
        return list(self._store.keys())

    def get_stats(self) -> Dict[str, int]:
        """Get count of entries per category."""
        return {cat: len(entries) for cat, entries in self._store.items()}

    def export_to_json(self, path: Optional[str] = None) -> str:
        """Serialize the entire store to JSON."""
        target = path or self._persist_path
        data = json.dumps(self._store, indent=2, default=str)
        if target:
            os.makedirs(os.path.dirname(target) if os.path.dirname(target) else ".", exist_ok=True)
            with open(target, "w") as f:
                f.write(data)
            logger.info(f"[OracleDB] Exported to {target}")
        return data

    def import_from_json(self, path: str):
        """Load store from a JSON file."""
        try:
            with open(path, "r") as f:
                self._store = json.load(f)
            logger.info(f"[OracleDB] Imported from {path} ({len(self._store)} categories)")
        except Exception as e:
            logger.error(f"[OracleDB] Import failed: {e}")

    def clear(self):
        """Clear all data."""
        self._store.clear()
