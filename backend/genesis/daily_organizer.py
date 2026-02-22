"""
Genesis Key Daily Organizer.

Exports Genesis Keys to Layer 1 folder and creates daily summaries.
Librarian organizes keys every 24 hours with metadata.
"""
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from database.session import get_session
from models.genesis_key_models import GenesisKey, GenesisKeyType

logger = logging.getLogger(__name__)


class GenesisKeyDailyOrganizer:
    """
    Organizes Genesis Keys daily into Layer 1 folder structure.

    Structure:
    layer_1/
        genesis_keys/
            2026-01-11/
                metadata.json (summary of the day)
                api_requests.json (all API request keys)
                user_inputs.json (all user input keys)
                file_operations.json (all file operation keys)
                errors.json (all error keys)
                all_keys.json (complete export)
    """

    def __init__(self, layer1_path: Optional[str] = None):
        if layer1_path:
            self.layer1_path = Path(layer1_path)
        else:
            backend_dir = Path(__file__).parent.parent
            self.layer1_path = backend_dir / "knowledge_base" / "layer_1"

        self.genesis_keys_path = self.layer1_path / "genesis_keys"
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure all necessary directories exist."""
        self.genesis_keys_path.mkdir(parents=True, exist_ok=True)

    def export_daily_keys(
        self,
        target_date: Optional[datetime] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Export all Genesis Keys for a specific day to Layer 1.

        Args:
            target_date: Date to export (defaults to today)
            session: Database session

        Returns:
            Export summary with statistics
        """
        sess = session or next(get_session())
        close_session = session is None

        try:
            # Default to today
            if target_date is None:
                target_date = datetime.now()

            # Get date string for folder name
            date_str = target_date.strftime("%Y-%m-%d")
            day_folder = self.genesis_keys_path / date_str
            day_folder.mkdir(parents=True, exist_ok=True)

            logger.info(f"Exporting Genesis Keys for {date_str}")

            # Query all Genesis Keys for this day
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            keys = sess.query(GenesisKey).filter(
                GenesisKey.when_timestamp >= start_of_day,
                GenesisKey.when_timestamp < end_of_day
            ).all()

            if not keys:
                logger.info(f"No Genesis Keys found for {date_str}")
                return {
                    "date": date_str,
                    "total_keys": 0,
                    "exported": False
                }

            # Organize by type
            organized_keys = self._organize_keys_by_type(keys)

            # Generate metadata summary
            metadata = self._generate_daily_metadata(keys, date_str, organized_keys)

            # Export all keys
            self._export_all_keys(day_folder, keys)

            # Export by type
            self._export_by_type(day_folder, organized_keys)

            # Save metadata
            self._save_metadata(day_folder, metadata)

            logger.info(f"✅ Exported {len(keys)} Genesis Keys to {day_folder}")

            return {
                "date": date_str,
                "folder": str(day_folder),
                "total_keys": len(keys),
                "by_type": {k: len(v) for k, v in organized_keys.items()},
                "metadata": metadata,
                "exported": True
            }

        finally:
            if close_session:
                sess.close()

    def _organize_keys_by_type(self, keys: List[GenesisKey]) -> Dict[str, List[GenesisKey]]:
        """Organize keys by type."""
        organized = {
            "api_requests": [],
            "user_inputs": [],
            "file_operations": [],
            "code_changes": [],
            "errors": [],
            "fixes": [],
            "other": []
        }

        for key in keys:
            if key.key_type == GenesisKeyType.API_REQUEST:
                organized["api_requests"].append(key)
            elif key.key_type == GenesisKeyType.USER_INPUT:
                organized["user_inputs"].append(key)
            elif key.key_type == GenesisKeyType.FILE_OPERATION:
                organized["file_operations"].append(key)
            elif key.key_type == GenesisKeyType.CODE_CHANGE:
                organized["code_changes"].append(key)
            elif key.is_error:
                organized["errors"].append(key)
            elif key.key_type == GenesisKeyType.FIX:
                organized["fixes"].append(key)
            else:
                organized["other"].append(key)

        return organized

    def _generate_daily_metadata(
        self,
        keys: List[GenesisKey],
        date_str: str,
        organized_keys: Dict[str, List[GenesisKey]]
    ) -> Dict[str, Any]:
        """
        Generate metadata summary for the day.

        Includes:
        - What happened today (high-level summary)
        - Key statistics
        - Top activities
        - Errors and fixes
        - Most active users
        """
        # Count by type
        type_counts = {k: len(v) for k, v in organized_keys.items() if v}

        # Get error count
        error_count = len([k for k in keys if k.is_error])

        # Get fix count
        fix_count = len([k for k in keys if k.key_type == GenesisKeyType.FIX])

        # Get unique users
        users = set(k.who_actor for k in keys if k.who_actor)

        # Get unique file paths
        files = set(k.file_path for k in keys if k.file_path)

        # Get most common activities (top 10 descriptions)
        activities = {}
        for key in keys:
            desc = key.what_description[:100]  # Truncate for grouping
            activities[desc] = activities.get(desc, 0) + 1

        top_activities = sorted(activities.items(), key=lambda x: x[1], reverse=True)[:10]

        # Generate natural language summary
        summary = self._generate_summary_text(
            date_str,
            len(keys),
            type_counts,
            error_count,
            fix_count,
            len(users),
            len(files),
            top_activities
        )

        # Time range
        earliest = min(k.when_timestamp for k in keys) if keys else None
        latest = max(k.when_timestamp for k in keys) if keys else None

        return {
            "date": date_str,
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "statistics": {
                "total_keys": len(keys),
                "by_type": type_counts,
                "errors": error_count,
                "fixes": fix_count,
                "unique_users": len(users),
                "unique_files": len(files),
                "time_range": {
                    "earliest": earliest.isoformat() if earliest else None,
                    "latest": latest.isoformat() if latest else None
                }
            },
            "top_activities": [
                {"description": desc, "count": count}
                for desc, count in top_activities
            ],
            "users": list(users),
            "files_touched": list(files)[:50]  # Limit to 50 files
        }

    def _generate_summary_text(
        self,
        date_str: str,
        total_keys: int,
        type_counts: Dict[str, int],
        error_count: int,
        fix_count: int,
        user_count: int,
        file_count: int,
        top_activities: List[tuple]
    ) -> str:
        """Generate natural language summary."""
        summary_parts = [
            f"On {date_str}, GRACE tracked {total_keys} activities."
        ]

        # Activity breakdown
        if type_counts:
            activity_desc = []
            if type_counts.get("api_requests"):
                activity_desc.append(f"{type_counts['api_requests']} API requests")
            if type_counts.get("user_inputs"):
                activity_desc.append(f"{type_counts['user_inputs']} user interactions")
            if type_counts.get("file_operations"):
                activity_desc.append(f"{type_counts['file_operations']} file operations")

            if activity_desc:
                summary_parts.append(f"This included {', '.join(activity_desc)}.")

        # User activity
        if user_count > 0:
            summary_parts.append(f"{user_count} unique user(s) interacted with the system.")

        # Files
        if file_count > 0:
            summary_parts.append(f"{file_count} different file(s) were accessed or modified.")

        # Errors and fixes
        if error_count > 0:
            summary_parts.append(f"{error_count} error(s) occurred.")
            if fix_count > 0:
                summary_parts.append(f"{fix_count} fix(es) were applied.")

        # Top activity
        if top_activities:
            top_desc, top_count = top_activities[0]
            summary_parts.append(f"The most common activity was: '{top_desc}' ({top_count} times).")

        return " ".join(summary_parts)

    def _export_all_keys(self, day_folder: Path, keys: List[GenesisKey]):
        """Export all keys to all_keys.json."""
        all_keys_file = day_folder / "all_keys.json"

        keys_data = [
            {
                "key_id": key.key_id,
                "key_type": key.key_type.value,
                "status": key.status.value,
                "what": key.what_description,
                "who": key.who_actor,
                "when": key.when_timestamp.isoformat(),
                "where": key.where_location,
                "why": key.why_reason,
                "how": key.how_method,
                "file_path": key.file_path,
                "is_error": key.is_error,
                "error_message": key.error_message if key.is_error else None,
                "metadata_human": key.metadata_human
            }
            for key in keys
        ]

        with open(all_keys_file, 'w') as f:
            json.dump(keys_data, f, indent=2, default=str)

    def _export_by_type(self, day_folder: Path, organized_keys: Dict[str, List[GenesisKey]]):
        """Export keys organized by type."""
        for type_name, type_keys in organized_keys.items():
            if not type_keys:
                continue

            file_name = f"{type_name}.json"
            file_path = day_folder / file_name

            keys_data = [
                {
                    "key_id": key.key_id,
                    "what": key.what_description,
                    "who": key.who_actor,
                    "when": key.when_timestamp.isoformat(),
                    "where": key.where_location,
                    "file_path": key.file_path
                }
                for key in type_keys
            ]

            with open(file_path, 'w') as f:
                json.dump(keys_data, f, indent=2, default=str)

    def _save_metadata(self, day_folder: Path, metadata: Dict[str, Any]):
        """Save metadata summary."""
        metadata_file = day_folder / "metadata.json"

        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        # Also create a human-readable summary
        summary_file = day_folder / "DAILY_SUMMARY.md"
        summary_md = self._generate_markdown_summary(metadata)

        with open(summary_file, 'w') as f:
            f.write(summary_md)

    def _generate_markdown_summary(self, metadata: Dict[str, Any]) -> str:
        """Generate Markdown summary."""
        md = f"""# Daily Genesis Key Summary

**Date:** {metadata['date']}
**Generated:** {metadata['generated_at']}

---

## Summary

{metadata['summary']}

---

## Statistics

- **Total Activities:** {metadata['statistics']['total_keys']}
- **Errors:** {metadata['statistics']['errors']}
- **Fixes Applied:** {metadata['statistics']['fixes']}
- **Unique Users:** {metadata['statistics']['unique_users']}
- **Files Touched:** {metadata['statistics']['unique_files']}

### Activity Breakdown

"""

        for type_name, count in metadata['statistics']['by_type'].items():
            md += f"- **{type_name.replace('_', ' ').title()}:** {count}\n"

        md += "\n---\n\n## Top Activities\n\n"

        for activity in metadata['top_activities'][:5]:
            md += f"- {activity['description']} ({activity['count']} times)\n"

        md += "\n---\n\n## Files\n\n"
        md += f"The following files were accessed or modified:\n\n"

        for file_path in metadata['files_touched'][:20]:
            md += f"- `{file_path}`\n"

        if len(metadata['files_touched']) > 20:
            md += f"\n...and {len(metadata['files_touched']) - 20} more files.\n"

        md += "\n---\n\n## Users\n\n"
        for user in metadata['users']:
            md += f"- {user}\n"

        md += "\n---\n\n*This summary was automatically generated by the Genesis Key Daily Organizer.*\n"

        return md

    def organize_past_days(
        self,
        days_back: int = 7,
        session: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Organize Genesis Keys for the past N days.

        Args:
            days_back: Number of days to go back
            session: Database session

        Returns:
            List of export summaries
        """
        results = []

        for i in range(days_back):
            target_date = datetime.now() - timedelta(days=i)
            result = self.export_daily_keys(target_date, session)
            results.append(result)

            if result['exported']:
                logger.info(f"✅ Organized {result['total_keys']} keys for {result['date']}")

        return results

    def get_daily_summary(self, date_str: str) -> Optional[Dict[str, Any]]:
        """Get metadata summary for a specific day."""
        day_folder = self.genesis_keys_path / date_str
        metadata_file = day_folder / "metadata.json"

        if not metadata_file.exists():
            return None

        with open(metadata_file, 'r') as f:
            return json.load(f)

    def list_organized_days(self) -> List[str]:
        """List all days that have been organized."""
        if not self.genesis_keys_path.exists():
            return []

        days = []
        for item in self.genesis_keys_path.iterdir():
            if item.is_dir() and item.name.count('-') == 2:  # YYYY-MM-DD format
                days.append(item.name)

        return sorted(days, reverse=True)


# Global organizer instance
_daily_organizer: Optional[GenesisKeyDailyOrganizer] = None


def get_daily_organizer(layer1_path: Optional[str] = None) -> GenesisKeyDailyOrganizer:
    """Get or create the global daily organizer instance."""
    global _daily_organizer
    if _daily_organizer is None or layer1_path is not None:
        _daily_organizer = GenesisKeyDailyOrganizer(layer1_path=layer1_path)
    return _daily_organizer
