import logging
import schedule
import time
import threading
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from cognitive.transformation_library.pattern_miner import TransformationPatternMiner
from cognitive.transformation_library.outcome_ledger import OutcomeLedger
from cognitive.magma_memory_system import get_magma_memory_system, MagmaMemorySystem
from cognitive.memory_mesh_integration import MemoryMeshIntegration
from database.session import get_session
from pathlib import Path
logger = logging.getLogger(__name__)

class NightlyMiner:
    """
    Scheduled pattern mining job.
    
    Runs pattern mining nightly or on beat to discover new rules
    from successful transforms.
    """

    def __init__(
        self,
        session: Optional[Session] = None,
        knowledge_base_path: Optional[Path] = None
    ):
        """
        Initialize Nightly Miner.
        
        Args:
            session: Database session (created if not provided)
            knowledge_base_path: Knowledge base path (optional)
        """
        self.session = session or get_session()
        self.kb_path = knowledge_base_path or Path("knowledge_base")
        
        # Components
        self.outcome_ledger = OutcomeLedger(self.session)
        self.magma_memory: Optional[MagmaMemorySystem] = None
        self.memory_mesh: Optional[MemoryMeshIntegration] = None
        
        # Initialize components
        try:
            from cognitive.magma_memory_system import get_magma_memory_system
            from cognitive.memory_mesh_integration import MemoryMeshIntegration
            from cognitive.memory_mesh_snapshot import MemoryMeshSnapshot
            
            snapshot = MemoryMeshSnapshot(self.session, self.kb_path)
            self.magma_memory = get_magma_memory_system(
                session=self.session,
                knowledge_base_path=self.kb_path,
                memory_mesh_snapshot=snapshot
            )
            
            self.memory_mesh = MemoryMeshIntegration(self.session, self.kb_path)
            
        except Exception as e:
            logger.warning(f"[NIGHTLY-MINER] Could not initialize all components: {e}")
        
        # Update outcome ledger with magma memory
        if self.magma_memory:
            self.outcome_ledger.magma_memory = self.magma_memory
        
        # Pattern miner
        self.pattern_miner = TransformationPatternMiner(
            session=self.session,
            outcome_ledger=self.outcome_ledger,
            magma_memory=self.magma_memory,
            memory_mesh=self.memory_mesh
        )
        
        # Scheduler state
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.last_run: Optional[datetime] = None
        self.stats = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "total_proposals": 0,
            "last_run_time": None
        }
        
        logger.info("[NIGHTLY-MINER] Initialized")

    def run_mining(self) -> dict:
        """
        Run pattern mining job.
        
        Returns:
            Mining results
        """
        logger.info("[NIGHTLY-MINER] Starting pattern mining job")
        start_time = datetime.utcnow()
        
        try:
            # Run pattern miner
            results = self.pattern_miner.mine_patterns()
            
            # Update statistics
            self.stats["total_runs"] += 1
            self.stats["successful_runs"] += 1
            self.stats["total_proposals"] += len(results.get("rule_proposals", []))
            self.stats["last_run_time"] = (datetime.utcnow() - start_time).total_seconds()
            self.last_run = datetime.utcnow()
            
            logger.info(
                f"[NIGHTLY-MINER] Mining complete: "
                f"{len(results.get('rule_proposals', []))} proposals, "
                f"{self.stats['last_run_time']:.2f}s"
            )
            
            return {
                "success": True,
                "results": results,
                "stats": self.stats.copy()
            }
        
        except Exception as e:
            logger.error(f"[NIGHTLY-MINER] Mining failed: {e}")
            
            self.stats["total_runs"] += 1
            self.stats["failed_runs"] += 1
            
            return {
                "success": False,
                "error": str(e),
                "stats": self.stats.copy()
            }

    def schedule_nightly(self, time_str: str = "02:00"):
        """
        Schedule nightly pattern mining.
        
        Args:
            time_str: Time to run (default: "02:00")
        """
        if self.is_running:
            logger.warning("[NIGHTLY-MINER] Scheduler already running")
            return
        
        logger.info(f"[NIGHTLY-MINER] Scheduling nightly mining at {time_str}")
        
        # Schedule for specified time every day
        schedule.every().day.at(time_str).do(self._run_job)
        
        # Also schedule a check every hour to see if we missed a run
        schedule.every().hour.do(self._check_missed_run)
        
        self.is_running = True
        
        # Run scheduler in background thread
        def run_scheduler():
            logger.info("[NIGHTLY-MINER] Scheduler thread started")
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            logger.info("[NIGHTLY-MINER] Scheduler thread stopped")
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("[NIGHTLY-MINER] ✅ Nightly mining scheduler started")

    def _run_job(self):
        """Internal method to run mining job."""
        logger.info("[NIGHTLY-MINER] Running scheduled mining job")
        try:
            self.run_mining()
        except Exception as e:
            logger.error(f"[NIGHTLY-MINER] Scheduled job failed: {e}")

    def _check_missed_run(self):
        """Check if we missed a run and run it if needed."""
        if self.last_run is None:
            # First run
            logger.info("[NIGHTLY-MINER] First run detected, running now")
            self._run_job()
            return
        
        # Check if more than 25 hours since last run
        time_since_last = datetime.utcnow() - self.last_run
        if time_since_last.total_seconds() > 25 * 3600:  # 25 hours
            logger.warning("[NIGHTLY-MINER] Missed run detected, running now")
            self._run_job()

    def stop_scheduler(self):
        """Stop the background scheduler."""
        if not self.is_running:
            return
        
        logger.info("[NIGHTLY-MINER] Stopping scheduler")
        self.is_running = False
        schedule.clear()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        logger.info("[NIGHTLY-MINER] ✅ Scheduler stopped")

    def get_status(self) -> dict:
        """Get current status."""
        return {
            "is_running": self.is_running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "stats": self.stats.copy()
        }


# Global Nightly Miner instance
_nightly_miner: Optional[NightlyMiner] = None


def get_nightly_miner() -> NightlyMiner:
    """Get or create global Nightly Miner instance."""
    global _nightly_miner
    if _nightly_miner is None:
        _nightly_miner = NightlyMiner()
    return _nightly_miner


def schedule_nightly_mining(time_str: str = "02:00"):
    """Schedule nightly pattern mining (convenience function)."""
    miner = get_nightly_miner()
    miner.schedule_nightly(time_str)
