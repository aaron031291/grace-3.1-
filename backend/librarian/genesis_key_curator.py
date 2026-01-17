import os
import logging
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from database.session import get_session
from genesis.daily_organizer import get_daily_organizer
class GenesisKeyCurator:
    logger = logging.getLogger(__name__)
    """
    Librarian curator for Genesis Keys.

    Responsibilities:
    - Export Genesis Keys to Layer 1 every 24 hours
    - Organize keys by type and date
    - Generate daily metadata summaries
    - Track curation history
    - Run autonomously in background
    """

    def __init__(self):
        self.organizer = get_daily_organizer()
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.last_curation: Optional[datetime] = None

    def curate_today(self, session: Optional[Session] = None) -> dict:
        """
        Curate Genesis Keys for today.

        This is the main function called every 24 hours.
        """
        sess = session or next(get_session())
        close_session = session is None

        try:
            logger.info("[LIBRARIAN-CURATOR] Starting daily Genesis Key curation")

            # Export today's Genesis Keys
            result = self.organizer.export_daily_keys(session=sess)

            if result['exported']:
                logger.info(
                    f"[LIBRARIAN-CURATOR] ✅ Curated {result['total_keys']} Genesis Keys for {result['date']}"
                )

                self.last_curation = datetime.utcnow()

                return {
                    "success": True,
                    "curated": True,
                    "keys_count": result['total_keys'],
                    "date": result['date'],
                    "summary": result['metadata']['summary']
                }
            else:
                logger.info(f"[LIBRARIAN-CURATOR] No Genesis Keys to curate for {result['date']}")

                return {
                    "success": True,
                    "curated": False,
                    "keys_count": 0,
                    "date": result['date']
                }

        except Exception as e:
            logger.error(f"[LIBRARIAN-CURATOR] ❌ Curation failed: {e}")

            return {
                "success": False,
                "error": str(e)
            }

        finally:
            if close_session:
                sess.close()

    def curate_yesterday(self, session: Optional[Session] = None) -> dict:
        """Curate Genesis Keys for yesterday (useful for missed days)."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        result = self.organizer.export_daily_keys(target_date=yesterday, session=session)

        if result['exported']:
            logger.info(f"[LIBRARIAN-CURATOR] ✅ Curated yesterday's keys: {result['total_keys']}")
            return {
                "success": True,
                "curated": True,
                "keys_count": result['total_keys'],
                "date": result['date']
            }
        else:
            return {
                "success": True,
                "curated": False,
                "keys_count": 0,
                "date": result['date']
            }

    def backfill_missing_days(self, days_back: int = 7, session: Optional[Session] = None) -> dict:
        """
        Backfill curation for missing days.

        Useful when the curator was not running for some period.
        """
        logger.info(f"[LIBRARIAN-CURATOR] Backfilling {days_back} days")

        results = self.organizer.organize_past_days(days_back=days_back, session=session)

        total_curated = sum(r['total_keys'] for r in results if r['exported'])
        days_curated = sum(1 for r in results if r['exported'])

        logger.info(f"[LIBRARIAN-CURATOR] ✅ Backfilled {days_curated} days, {total_curated} total keys")

        return {
            "success": True,
            "days_backfilled": days_curated,
            "total_keys_curated": total_curated,
            "results": results
        }

    def schedule_daily_curation(self):
        """
        Schedule daily curation to run every 24 hours at midnight.

        This runs in a background thread.
        """
        if self.is_running:
            logger.warning("[LIBRARIAN-CURATOR] Scheduler already running")
            return

        logger.info("[LIBRARIAN-CURATOR] Scheduling daily curation at midnight")

        # Schedule for midnight every day
        schedule.every().day.at("00:00").do(self._run_curation_job)

        # Also schedule a check every hour to see if we missed a run
        schedule.every().hour.do(self._check_missed_curation)

        self.is_running = True

        # Run scheduler in background thread
        def run_scheduler():
            logger.info("[LIBRARIAN-CURATOR] Scheduler thread started")
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            logger.info("[LIBRARIAN-CURATOR] Scheduler thread stopped")

        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()

        logger.info("[LIBRARIAN-CURATOR] ✅ Daily curation scheduler started")

    def _run_curation_job(self):
        """Internal method to run curation job."""
        logger.info("[LIBRARIAN-CURATOR] Running scheduled curation")
        try:
            result = self.curate_today()
            if result['success'] and result.get('curated'):
                logger.info(f"[LIBRARIAN-CURATOR] ✅ Scheduled curation complete: {result['keys_count']} keys")
            else:
                logger.info(f"[LIBRARIAN-CURATOR] Scheduled curation complete: no keys to curate")
        except Exception as e:
            logger.error(f"[LIBRARIAN-CURATOR] ❌ Scheduled curation failed: {e}")

    def _check_missed_curation(self):
        """Check if we missed a curation and run it if needed."""
        if self.last_curation is None:
            # First run, do yesterday to catch up
            logger.info("[LIBRARIAN-CURATOR] First run detected, curating yesterday")
            self.curate_yesterday()
            return

        # Check if more than 25 hours since last curation
        time_since_last = datetime.utcnow() - self.last_curation
        if time_since_last > timedelta(hours=25):
            logger.warning("[LIBRARIAN-CURATOR] Missed curation detected, running now")
            self._run_curation_job()

    def stop_scheduler(self):
        """Stop the background scheduler."""
        if not self.is_running:
            return

        logger.info("[LIBRARIAN-CURATOR] Stopping scheduler")
        self.is_running = False
        schedule.clear()

        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)

        logger.info("[LIBRARIAN-CURATOR] ✅ Scheduler stopped")

    def get_curation_status(self) -> dict:
        """Get current curation status."""
        # Get list of organized days
        organized_days = self.organizer.list_organized_days()

        return {
            "scheduler_running": self.is_running,
            "last_curation": self.last_curation.isoformat() if self.last_curation else None,
            "organized_days_count": len(organized_days),
            "latest_organized_day": organized_days[0] if organized_days else None,
            "organized_days": organized_days[:10]  # Last 10 days
        }


# Global curator instance
_genesis_key_curator: Optional[GenesisKeyCurator] = None


def get_genesis_key_curator() -> GenesisKeyCurator:
    """Get or create the global Genesis Key curator instance."""
    global _genesis_key_curator
    if _genesis_key_curator is None:
        _genesis_key_curator = GenesisKeyCurator()
    return _genesis_key_curator


def start_daily_curation():
    """Start the daily curation scheduler (call this on app startup)."""
    curator = get_genesis_key_curator()
    curator.schedule_daily_curation()
    logger.info("[LIBRARIAN] Genesis Key daily curation activated")


def stop_daily_curation():
    """Stop the daily curation scheduler (call this on app shutdown)."""
    curator = get_genesis_key_curator()
    curator.stop_scheduler()
    logger.info("[LIBRARIAN] Genesis Key daily curation deactivated")
