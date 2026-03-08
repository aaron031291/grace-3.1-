"""
Genesis Key Knowledge Base Integration.

Auto-populates Genesis Keys in knowledge_base/layer_1/genesis_key folder.
"""
import os
import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Optional
from pathlib import Path

from models.genesis_key_models import GenesisKey
from filelock import FileLock, Timeout as FileLockTimeout

logger = logging.getLogger(__name__)

# Per-file-path locks so we serialize writes to the same JSON file within this process (reduces file lock contention)
_path_locks: dict = {}
_path_locks_mu = threading.Lock()


class GenesisKBIntegration:
    """
    Integrates Genesis Keys with Knowledge Base.

    Auto-saves all Genesis Keys to knowledge_base/layer_1/genesis_key/
    for ingestion and retrieval.
    """

    def __init__(self, kb_base_path: Optional[str] = None):
        if kb_base_path:
            self.kb_base_path = kb_base_path
        else:
            # Default to backend/knowledge_base
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.kb_base_path = os.path.join(backend_dir, "knowledge_base")

        self.genesis_key_path = os.path.join(self.kb_base_path, "layer_1", "genesis_key")
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure the genesis_key directory structure exists."""
        Path(self.genesis_key_path).mkdir(parents=True, exist_ok=True)

        # Create README in genesis_key folder
        readme_path = os.path.join(self.genesis_key_path, "README.md")
        if not os.path.exists(readme_path):
            with open(readme_path, 'w') as f:
                f.write("""# Genesis Key Knowledge Base

This folder contains all Genesis Keys tracked in the system.

## Structure

- User folders: `{user_id}/` - Keys organized by user
- Session files: `{user_id}/session_{session_id}.json` - Keys grouped by session
- Profile files: `{user_id}/profile.json` - User profile information

## Purpose

Genesis Keys are automatically ingested into the knowledge base for:
- Historical tracking and auditing
- AI-powered analysis and insights
- User behavior patterns
- Error trend analysis
- Session reconstruction

## Automatic Population

This folder is automatically populated by the Genesis Key system.
All user actions, inputs, and outputs are tracked here from the first login.
""")

    def _get_path_lock(self, file_path: str) -> threading.Lock:
        """Per-file process lock to serialize writes and reduce file lock contention."""
        with _path_locks_mu:
            if file_path not in _path_locks:
                _path_locks[file_path] = threading.Lock()
            return _path_locks[file_path]

    def save_genesis_key(self, key) -> Optional[str]:
        """
        Save Genesis Key to knowledge base.

        Accepts either a GenesisKey ORM object or a plain dict (extracted_key_data).
        This duck-typing approach avoids SQLAlchemy DetachedInstanceError when called
        after the DB session has closed.

        Args:
            key: GenesisKey ORM object OR dict with equivalent fields

        Returns:
            Path to saved file, or None on failure
        """
        try:
            # Support both ORM objects and plain dicts
            def _get(field, default=None):
                if isinstance(key, dict):
                    return key.get(field, default)
                return getattr(key, field, default)

            user_id = _get('user_id') or "system"
            session_id = _get('session_id')
            when_timestamp = _get('when_timestamp')

            # Organize by user
            user_folder = os.path.join(self.genesis_key_path, user_id)
            Path(user_folder).mkdir(parents=True, exist_ok=True)

            # Group by session if available
            if session_id:
                filename = f"session_{session_id}.json"
            else:
                ts = when_timestamp or datetime.utcnow()
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts)
                    except Exception:
                        ts = datetime.utcnow()
                date_str = ts.strftime('%Y-%m-%d')
                filename = f"keys_{date_str}.json"

            file_path = os.path.join(user_folder, filename)
            lock_path = f"{file_path}.lock"
            path_lock = self._get_path_lock(file_path)
            file_lock = FileLock(lock_path, timeout=20)

            # Serialize per-file in this process, then acquire file lock with retry
            max_retries = 4
            for attempt in range(max_retries):
                try:
                    with path_lock:
                        with file_lock:
                            return self._write_key_to_file(file_path, key)
                except FileLockTimeout:
                    if attempt < max_retries - 1:
                        time.sleep(0.3 * (attempt + 1))
                    else:
                        logger.error(
                            "Failed to save Genesis Key to KB: The file lock '%s' could not be "
                            "acquired after %s attempts.", lock_path, max_retries
                        )
                        return None
            return None

        except Exception as e:
            logger.error("Failed to save Genesis Key to KB: %s", e)
            return None

    def _write_key_to_file(self, file_path: str, key) -> str:
        """Hold file lock already; load, append key, write. Caller must hold path_lock and file_lock.
        
        Accepts both GenesisKey ORM objects and plain dicts.
        """
        # Helper to read from ORM object or dict
        def _get(field, default=None):
            if isinstance(key, dict):
                return key.get(field, default)
            return getattr(key, field, default)

        user_id = _get('user_id')
        session_id = _get('session_id')

        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                try:
                    keys_data = json.load(f)
                except json.JSONDecodeError as e:
                    backup_path = f"{file_path}.corrupt.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                    try:
                        import shutil
                        shutil.copy2(file_path, backup_path)
                        logger.warning("Corrupted KB file backed up to: %s", backup_path)
                    except Exception as backup_err:
                        logger.error("Failed to backup corrupted file: %s", backup_err)
                    logger.error("JSON decode error in %s: %s", file_path, e)
                    keys_data = {
                        "user_id": user_id,
                        "session_id": session_id,
                        "created_at": datetime.utcnow().isoformat(),
                        "keys": []
                    }
        else:
            keys_data = {
                "user_id": user_id,
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "keys": []
            }

        when_ts = _get('when_timestamp')
        if isinstance(when_ts, str):
            ts_str = when_ts
        elif when_ts is not None:
            ts_str = when_ts.isoformat()
        else:
            ts_str = datetime.utcnow().isoformat()

        # Handle key_type: may be an Enum or a string
        key_type_raw = _get('key_type', 'unknown')
        if hasattr(key_type_raw, 'value'):
            key_type_str = key_type_raw.value
        else:
            key_type_str = str(key_type_raw) if key_type_raw else 'unknown'

        # Handle status: may be an Enum or a string
        status_raw = _get('status', 'active')
        if hasattr(status_raw, 'value'):
            status_str = status_raw.value
        else:
            status_str = str(status_raw) if status_raw else 'active'

        key_dict = {
            "key_id": _get('key_id', str(uuid.uuid4())),
            "key_type": key_type_str,
            "status": status_str,
            "timestamp": ts_str,
            "what": _get('what_description', _get('what', 'No description')),
            "where": _get('where_location', _get('where', 'Unknown location')),
            "when": ts_str,
            "why": _get('why_reason', _get('why', 'Not provided')),
            "who": _get('who_actor', _get('who', 'System')),
            "how": _get('how_method', _get('how', 'Automatic')),
            "file_path": _get('file_path'),
            "line_number": _get('line_number'),
            "function_name": _get('function_name'),
            "code_before": _get('code_before'),
            "code_after": _get('code_after'),
            "is_error": _get('is_error'),
            "error_type": _get('error_type'),
            "error_message": _get('error_message'),
            "has_fix_suggestion": _get('has_fix_suggestion'),
            "fix_applied": _get('fix_applied'),
            "metadata_human": _get('metadata_human'),
            "metadata_ai": _get('metadata_ai'),
            "input_data": _get('input_data'),
            "output_data": _get('output_data'),
            "context_data": _get('context_data'),
            "commit_sha": _get('commit_sha'),
            "branch_name": _get('branch_name'),
            "tags": _get('tags'),
        }
        keys_data["keys"].append(key_dict)
        keys_data["last_updated"] = datetime.utcnow().isoformat()
        keys_data["total_keys"] = len(keys_data["keys"])

        with open(file_path, 'w') as f:
            json.dump(keys_data, f, indent=2, default=str)

        logger.info("Genesis Key saved to KB: %s", file_path)
        return file_path


    def save_user_profile(self, user_id: str, profile_data: dict) -> str:
        """
        Save user profile to knowledge base.

        Args:
            user_id: Genesis user ID
            profile_data: User profile information

        Returns:
            Path to saved profile file
        """
        try:
            user_folder = os.path.join(self.genesis_key_path, user_id)
            Path(user_folder).mkdir(parents=True, exist_ok=True)

            profile_path = os.path.join(user_folder, "profile.json")

            # Merge with existing profile if it exists
            if os.path.exists(profile_path):
                with open(profile_path, 'r') as f:
                    existing_profile = json.load(f)
                existing_profile.update(profile_data)
                profile_data = existing_profile

            profile_data["last_updated"] = datetime.utcnow().isoformat()

            with open(profile_path, 'w') as f:
                json.dump(profile_data, f, indent=2, default=str)

            logger.info(f"User profile saved to KB: {profile_path}")
            return profile_path

        except Exception as e:
            logger.error(f"Failed to save user profile to KB: {e}")
            return None

    def get_user_keys(self, user_id: str) -> list:
        """
        Get all Genesis Keys for a user from knowledge base.

        Args:
            user_id: Genesis user ID

        Returns:
            List of Genesis Keys
        """
        try:
            user_folder = os.path.join(self.genesis_key_path, user_id)
            if not os.path.exists(user_folder):
                return []

            all_keys = []

            # Read all JSON files in user folder
            for filename in os.listdir(user_folder):
                if filename.endswith('.json') and filename != 'profile.json':
                    file_path = os.path.join(user_folder, filename)
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        if 'keys' in data:
                            all_keys.extend(data['keys'])

            return all_keys

        except Exception as e:
            logger.error(f"Failed to get user keys from KB: {e}")
            return []

    def create_user_summary(self, user_id: str) -> dict:
        """
        Create a comprehensive summary of a user's activity.

        Args:
            user_id: Genesis user ID

        Returns:
            Summary dictionary
        """
        keys = self.get_user_keys(user_id)

        summary = {
            "user_id": user_id,
            "total_keys": len(keys),
            "total_errors": sum(1 for k in keys if k.get("is_error")),
            "total_fixes": sum(1 for k in keys if k.get("fix_applied")),
            "key_types": {},
            "active_sessions": set(),
            "files_modified": set(),
            "first_activity": None,
            "last_activity": None,
        }

        for key in keys:
            # Count by type
            key_type = key.get("key_type", "unknown")
            summary["key_types"][key_type] = summary["key_types"].get(key_type, 0) + 1

            # Track sessions
            if key.get("session_id"):
                summary["active_sessions"].add(key["session_id"])

            # Track files
            if key.get("file_path"):
                summary["files_modified"].add(key["file_path"])

            # Track activity times
            timestamp = key.get("timestamp")
            if timestamp:
                if not summary["first_activity"] or timestamp < summary["first_activity"]:
                    summary["first_activity"] = timestamp
                if not summary["last_activity"] or timestamp > summary["last_activity"]:
                    summary["last_activity"] = timestamp

        # Convert sets to lists for JSON serialization
        summary["active_sessions"] = list(summary["active_sessions"])
        summary["files_modified"] = list(summary["files_modified"])

        return summary


# Global KB integration instance
_kb_integration: Optional[GenesisKBIntegration] = None


def get_kb_integration() -> GenesisKBIntegration:
    """Get or create the global KB integration instance."""
    global _kb_integration
    if _kb_integration is None:
        _kb_integration = GenesisKBIntegration()
    return _kb_integration
