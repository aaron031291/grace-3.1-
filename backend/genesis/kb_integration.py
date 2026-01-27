"""
Genesis Key Knowledge Base Integration.

Auto-populates Genesis Keys in knowledge_base/layer_1/genesis_key folder.
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

from models.genesis_key_models import GenesisKey
from filelock import FileLock

logger = logging.getLogger(__name__)


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

    def save_genesis_key(self, key: GenesisKey) -> str:
        """
        Save Genesis Key to knowledge base.

        Args:
            key: GenesisKey to save

        Returns:
            Path to saved file
        """
        try:
            # Organize by user
            user_folder = os.path.join(
                self.genesis_key_path,
                key.user_id or "system"
            )
            Path(user_folder).mkdir(parents=True, exist_ok=True)

            # Group by session if available
            if key.session_id:
                filename = f"session_{key.session_id}.json"
            else:
                # Use date-based filename
                date_str = key.when_timestamp.strftime('%Y-%m-%d')
                filename = f"keys_{date_str}.json"

            file_path = os.path.join(user_folder, filename)
            lock_path = f"{file_path}.lock"
            lock = FileLock(lock_path, timeout=10)

            with lock:
                # Load existing keys or create new list
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        try:
                            keys_data = json.load(f)
                        except json.JSONDecodeError as e:
                            # Handle corrupted file by backing up and creating new
                            backup_path = f"{file_path}.corrupt.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                            try:
                                import shutil
                                shutil.copy2(file_path, backup_path)
                                logger.warning(f"Corrupted KB file backed up to: {backup_path}")
                            except Exception as backup_err:
                                logger.error(f"Failed to backup corrupted file: {backup_err}")
                            
                            logger.error(f"JSON decode error in {file_path}: {e}")
                            keys_data = {
                                "user_id": key.user_id,
                                "session_id": key.session_id,
                                "created_at": datetime.utcnow().isoformat(),
                                "keys": []
                            }
                else:
                    keys_data = {
                        "user_id": key.user_id,
                        "session_id": key.session_id,
                        "created_at": datetime.utcnow().isoformat(),
                        "keys": []
                    }

                # Add this key
                key_dict = {
                    "key_id": key.key_id,
                    "key_type": key.key_type.value,
                    "status": key.status.value,
                    "timestamp": key.when_timestamp.isoformat(),

                    # What, Where, When, Why, Who, How
                    "what": key.what_description,
                    "where": key.where_location,
                    "when": key.when_timestamp.isoformat(),
                    "why": key.why_reason,
                    "who": key.who_actor,
                    "how": key.how_method,

                    # Code tracking
                    "file_path": key.file_path,
                    "line_number": key.line_number,
                    "function_name": key.function_name,
                    "code_before": key.code_before,
                    "code_after": key.code_after,

                    # Error tracking
                    "is_error": key.is_error,
                    "error_type": key.error_type,
                    "error_message": key.error_message,
                    "has_fix_suggestion": key.has_fix_suggestion,
                    "fix_applied": key.fix_applied,

                    # Metadata
                    "metadata_human": key.metadata_human,
                    "metadata_ai": key.metadata_ai,

                    # Input/Output tracking
                    "input_data": key.input_data,
                    "output_data": key.output_data,
                    "context_data": key.context_data,

                    # Version control
                    "commit_sha": key.commit_sha,
                    "branch_name": key.branch_name,

                    # Tags
                    "tags": key.tags
                }

                keys_data["keys"].append(key_dict)
                keys_data["last_updated"] = datetime.utcnow().isoformat()
                keys_data["total_keys"] = len(keys_data["keys"])

                # Save to file
                with open(file_path, 'w') as f:
                    json.dump(keys_data, f, indent=2, default=str)

            logger.info(f"Genesis Key saved to KB: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to save Genesis Key to KB: {e}")
            return None

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
