"""
Genesis Key Archival Service.

Collects keys every 24 hours, generates reports, and organizes them by date.
"""
import uuid
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.genesis_key_models import (
    GenesisKey, GenesisKeyArchive, UserProfile, FixSuggestion,
    GenesisKeyType, GenesisKeyStatus
)
from database.session import get_session

logger = logging.getLogger(__name__)


class ArchivalService:
    """
    Service for archiving Genesis Keys and generating reports.

    Every 24 hours:
    1. Collects all keys from the previous day
    2. Generates comprehensive report
    3. Archives keys with metadata
    4. Stores in organized folder structure
    """

    def __init__(
        self,
        archive_base_path: Optional[str] = None,
        session: Optional[Session] = None
    ):
        self.session = session
        self.archive_base_path = archive_base_path or self._get_default_archive_path()
        self._ensure_archive_directory()

    def _get_default_archive_path(self) -> str:
        """Get default archive path."""
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(backend_dir, "genesis_archives")

    def _ensure_archive_directory(self):
        """Ensure archive directory exists."""
        Path(self.archive_base_path).mkdir(parents=True, exist_ok=True)

    def archive_daily_keys(
        self,
        target_date: Optional[datetime] = None,
        session: Optional[Session] = None
    ) -> GenesisKeyArchive:
        """
        Archive all Genesis Keys for a specific date.

        Args:
            target_date: Date to archive (defaults to yesterday)
            session: Database session

        Returns:
            GenesisKeyArchive record
        """
        sess = session or self.session or next(get_session())
        close_session = session is None and self.session is None

        try:
            # Default to yesterday
            if target_date is None:
                target_date = datetime.now(timezone.utc) - timedelta(days=1)

            # Get start and end of day
            day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            logger.info(f"Archiving Genesis Keys for {day_start.strftime('%Y-%m-%d')}")

            # Get all keys for the day
            keys = sess.query(GenesisKey).filter(
                GenesisKey.when_timestamp >= day_start,
                GenesisKey.when_timestamp < day_end,
                GenesisKey.status != GenesisKeyStatus.ARCHIVED
            ).all()

            if not keys:
                logger.info("No keys to archive for this date")
                return None

            # Generate statistics
            stats = self._generate_statistics(keys, sess)

            # Generate report
            report_summary, report_data = self._generate_report(keys, stats, day_start)

            # Create archive directory for this date
            date_str = day_start.strftime('%Y-%m-%d')
            archive_dir = os.path.join(self.archive_base_path, date_str)
            Path(archive_dir).mkdir(parents=True, exist_ok=True)

            # Save keys to JSON file
            keys_file = os.path.join(archive_dir, f"genesis_keys_{date_str}.json")
            self._save_keys_to_file(keys, keys_file)

            # Save report
            report_file = os.path.join(archive_dir, f"report_{date_str}.txt")
            self._save_report_to_file(report_summary, report_file)

            # Save detailed data
            data_file = os.path.join(archive_dir, f"data_{date_str}.json")
            with open(data_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)

            # Create archive record
            archive = GenesisKeyArchive(
                archive_id=f"GA-{uuid.uuid4().hex[:16]}",
                archive_date=day_start,
                key_count=len(keys),
                error_count=stats['error_count'],
                fix_count=stats['fix_count'],
                user_count=stats['user_count'],
                most_active_user=stats.get('most_active_user'),
                most_changed_file=stats.get('most_changed_file'),
                most_common_error=stats.get('most_common_error'),
                report_summary=report_summary,
                report_data=report_data,
                archive_file_path=keys_file,
                report_file_path=report_file
            )

            sess.add(archive)

            # Mark keys as archived
            for key in keys:
                key.status = GenesisKeyStatus.ARCHIVED
                key.archived_at = datetime.now(timezone.utc)
                key.archive_path = keys_file

            sess.commit()

            logger.info(
                f"Archived {len(keys)} keys for {date_str}. "
                f"Archive ID: {archive.archive_id}"
            )

            return archive

        except Exception as e:
            logger.error(f"Failed to archive keys: {e}")
            sess.rollback()
            raise
        finally:
            if close_session:
                sess.close()

    def _generate_statistics(
        self,
        keys: List[GenesisKey],
        session: Session
    ) -> Dict:
        """Generate statistics from keys."""
        stats = {
            'total_keys': len(keys),
            'error_count': 0,
            'fix_count': 0,
            'user_count': 0,
            'type_breakdown': {},
            'file_changes': {},
            'error_types': {},
            'users': set()
        }

        for key in keys:
            # Count by type
            key_type = key.key_type.value
            stats['type_breakdown'][key_type] = stats['type_breakdown'].get(key_type, 0) + 1

            # Count errors
            if key.is_error:
                stats['error_count'] += 1
                if key.error_type:
                    stats['error_types'][key.error_type] = stats['error_types'].get(key.error_type, 0) + 1

            # Count fixes
            if key.key_type == GenesisKeyType.FIX:
                stats['fix_count'] += 1

            # Track file changes
            if key.file_path:
                stats['file_changes'][key.file_path] = stats['file_changes'].get(key.file_path, 0) + 1

            # Track users
            if key.user_id:
                stats['users'].add(key.user_id)

        stats['user_count'] = len(stats['users'])

        # Find most active user
        if keys:
            user_counts = {}
            for key in keys:
                if key.user_id:
                    user_counts[key.user_id] = user_counts.get(key.user_id, 0) + 1

            if user_counts:
                stats['most_active_user'] = max(user_counts, key=user_counts.get)

        # Find most changed file
        if stats['file_changes']:
            stats['most_changed_file'] = max(stats['file_changes'], key=stats['file_changes'].get)

        # Find most common error
        if stats['error_types']:
            stats['most_common_error'] = max(stats['error_types'], key=stats['error_types'].get)

        return stats

    def _generate_report(
        self,
        keys: List[GenesisKey],
        stats: Dict,
        date: datetime
    ) -> tuple[str, Dict]:
        """Generate human-readable report and structured data."""
        # Human-readable summary
        report_lines = [
            "=" * 80,
            f"GENESIS KEY DAILY REPORT",
            f"Date: {date.strftime('%Y-%m-%d')}",
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "=" * 80,
            "",
            "SUMMARY",
            "-" * 80,
            f"Total Genesis Keys: {stats['total_keys']}",
            f"Errors Detected: {stats['error_count']}",
            f"Fixes Applied: {stats['fix_count']}",
            f"Active Users: {stats['user_count']}",
            ""
        ]

        # Most active user
        if stats.get('most_active_user'):
            report_lines.append(f"Most Active User: {stats['most_active_user']}")

        # Most changed file
        if stats.get('most_changed_file'):
            report_lines.append(f"Most Changed File: {stats['most_changed_file']}")

        # Most common error
        if stats.get('most_common_error'):
            report_lines.append(f"Most Common Error: {stats['most_common_error']}")

        report_lines.extend([
            "",
            "KEY TYPE BREAKDOWN",
            "-" * 80
        ])

        for key_type, count in sorted(stats['type_breakdown'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / stats['total_keys']) * 100
            report_lines.append(f"  {key_type:25} {count:5} ({percentage:5.1f}%)")

        if stats['error_types']:
            report_lines.extend([
                "",
                "ERROR TYPES",
                "-" * 80
            ])
            for error_type, count in sorted(stats['error_types'].items(), key=lambda x: x[1], reverse=True):
                report_lines.append(f"  {error_type:40} {count:5}")

        if stats['file_changes']:
            report_lines.extend([
                "",
                "TOP 10 MODIFIED FILES",
                "-" * 80
            ])
            top_files = sorted(stats['file_changes'].items(), key=lambda x: x[1], reverse=True)[:10]
            for file_path, count in top_files:
                report_lines.append(f"  {file_path:60} {count:5} changes")

        # What, Where, When, Why, Who, How tracking summary
        report_lines.extend([
            "",
            "TRACKING SUMMARY (What, Where, When, Why, Who, How)",
            "-" * 80
        ])

        # Unique actors
        actors = set(key.who_actor for key in keys if key.who_actor)
        report_lines.append(f"WHO: {len(actors)} unique actors")

        # Unique locations
        locations = set(key.where_location for key in keys if key.where_location)
        report_lines.append(f"WHERE: {len(locations)} unique locations")

        # Time range
        if keys:
            earliest = min(key.when_timestamp for key in keys)
            latest = max(key.when_timestamp for key in keys)
            report_lines.append(f"WHEN: {earliest.strftime('%H:%M:%S')} - {latest.strftime('%H:%M:%S')}")

        # Keys with reasons
        with_reasons = sum(1 for key in keys if key.why_reason)
        report_lines.append(f"WHY: {with_reasons} keys have documented reasons")

        # Keys with methods
        with_methods = sum(1 for key in keys if key.how_method)
        report_lines.append(f"HOW: {with_methods} keys have documented methods")

        report_lines.extend([
            "",
            "=" * 80,
            "End of Report",
            "=" * 80
        ])

        report_summary = "\n".join(report_lines)

        # Structured data
        report_data = {
            "date": date.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "statistics": stats,
            "tracking_summary": {
                "unique_actors": len(actors),
                "unique_locations": len(locations),
                "keys_with_reasons": with_reasons,
                "keys_with_methods": with_methods
            }
        }

        return report_summary, report_data

    def _save_keys_to_file(self, keys: List[GenesisKey], file_path: str):
        """Save keys to JSON file."""
        keys_data = []

        for key in keys:
            key_dict = {
                "key_id": key.key_id,
                "key_type": key.key_type.value,
                "status": key.status.value,
                "what": key.what_description,
                "where": key.where_location,
                "when": key.when_timestamp.isoformat(),
                "why": key.why_reason,
                "who": key.who_actor,
                "how": key.how_method,
                "file_path": key.file_path,
                "line_number": key.line_number,
                "is_error": key.is_error,
                "error_type": key.error_type,
                "error_message": key.error_message,
                "metadata_human": key.metadata_human,
                "metadata_ai": key.metadata_ai
            }
            keys_data.append(key_dict)

        with open(file_path, 'w') as f:
            json.dump(keys_data, f, indent=2, default=str)

    def _save_report_to_file(self, report: str, file_path: str):
        """Save report to text file."""
        with open(file_path, 'w') as f:
            f.write(report)

    def get_archive_for_date(
        self,
        date: datetime,
        session: Optional[Session] = None
    ) -> Optional[GenesisKeyArchive]:
        """Get archive for a specific date."""
        sess = session or self.session or next(get_session())
        close_session = session is None and self.session is None

        try:
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            archive = sess.query(GenesisKeyArchive).filter(
                GenesisKeyArchive.archive_date >= day_start,
                GenesisKeyArchive.archive_date < day_end
            ).first()

            return archive
        finally:
            if close_session:
                sess.close()

    def list_archives(
        self,
        limit: int = 30,
        session: Optional[Session] = None
    ) -> List[GenesisKeyArchive]:
        """List recent archives."""
        sess = session or self.session or next(get_session())
        close_session = session is None and self.session is None

        try:
            archives = sess.query(GenesisKeyArchive).order_by(
                GenesisKeyArchive.archive_date.desc()
            ).limit(limit).all()

            return archives
        finally:
            if close_session:
                sess.close()


# Global archival service instance
_archival_service: Optional[ArchivalService] = None


def get_archival_service(session: Optional[Session] = None) -> ArchivalService:
    """Get or create the global archival service instance."""
    global _archival_service
    if _archival_service is None or session is not None:
        _archival_service = ArchivalService(session=session)
    return _archival_service


def schedule_daily_archival():
    """
    Schedule daily archival task.

    This should be called on application startup to set up the archival schedule.
    """
    import schedule
    import time
    import threading

    def run_archival():
        """Run archival task."""
        try:
            logger.info("Running scheduled Genesis Key archival")
            service = get_archival_service()
            service.archive_daily_keys()
        except Exception as e:
            logger.error(f"Scheduled archival failed: {e}")

    # Schedule to run every day at 2 AM
    schedule.every().day.at("02:00").do(run_archival)

    def run_scheduler():
        """Run scheduler in background thread."""
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    logger.info("Genesis Key daily archival scheduled for 2:00 AM daily")
