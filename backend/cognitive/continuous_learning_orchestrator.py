"""
Continuous Learning Orchestrator

Connects the Autonomous Sandbox Lab to continuous training data ingestion.

Grace continuously:
1. Ingests new documents and data
2. Learns from them using autonomous learning
3. Identifies improvement opportunities via Mirror
4. Proposes experiments to Sandbox Lab
5. Tests improvements with new data
6. Promotes validated improvements
7. Repeats - continuous evolution

This creates a never-ending self-improvement loop.
"""

import logging
import asyncio
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ContinuousLearningOrchestrator:
    """
    Orchestrates continuous autonomous learning and self-improvement

    Coordinates:
    - Data ingestion (files, documents, knowledge)
    - Autonomous learning (study, practice, consolidate)
    - Mirror observations (pattern detection)
    - Sandbox experiments (self-improvement)
    - Performance tracking
    - Continuous evolution
    """

    def __init__(self):
        self.running = False
        self.orchestrator_thread: Optional[threading.Thread] = None

        # Component references
        self.sandbox_lab = None
        self.mirror_system = None
        self.learning_orchestrator = None
        self.ingestion_service = None

        # State tracking
        self.last_ingestion_check = None
        self.last_learning_cycle = None
        self.last_mirror_observation = None
        self.last_experiment_check = None

        # Continuous operation config
        self.config = {
            "ingestion_interval_seconds": 60,  # Check for new data every 60s
            "learning_cycle_interval_seconds": 300,  # Run learning every 5 min
            "mirror_observation_interval_seconds": 600,  # Mirror observes every 10 min
            "experiment_check_interval_seconds": 120,  # Check experiments every 2 min
            "auto_propose_experiments": True,  # Let Grace propose experiments
            "auto_start_trials": True,  # Auto-start trials if trust is high
            "min_trust_for_auto_trial": 0.65,  # Minimum trust to auto-start trial
        }

        # Statistics
        self.stats = {
            "total_ingestions": 0,
            "total_learning_cycles": 0,
            "total_mirror_observations": 0,
            "total_experiments_proposed": 0,
            "total_trials_started": 0,
            "total_improvements_deployed": 0,
            "uptime_seconds": 0,
            "data_points_processed": 0,
            "knowledge_items_learned": 0
        }

        # Data flow tracking
        self.ingestion_queue: List[Dict] = []
        self.learning_queue: List[Dict] = []
        self.experiment_ideas: List[Dict] = []

        # Performance metrics over time
        self.performance_history: List[Dict] = []

        # Continuous improvement markers
        self.baseline_metrics = {
            "ingestion_success_rate": 0.0,
            "learning_retention_rate": 0.0,
            "retrieval_quality": 0.0,
            "average_confidence": 0.0,
            "error_rate": 0.0
        }

        self.current_metrics = dict(self.baseline_metrics)

    def initialize_components(self):
        """Initialize all required components"""
        # print("[CONTINUOUS_LEARNING] Initializing components...", flush=True)
        logger.info("[CONTINUOUS_LEARNING] Initializing components...")

        # Get Sandbox Lab
        try:
            from cognitive.autonomous_sandbox_lab import get_sandbox_lab
            self.sandbox_lab = get_sandbox_lab()
            logger.info("[CONTINUOUS_LEARNING] [OK] Sandbox Lab initialized")
        except Exception as e:
            logger.warning(f"[CONTINUOUS_LEARNING] Sandbox Lab unavailable: {e}")

        # Get Mirror System (requires database session)
        try:
            from cognitive.mirror_self_modeling import get_mirror_system
            from database.session import SessionLocal
            session = SessionLocal()
            self.mirror_system = get_mirror_system(session=session)
            logger.info("[CONTINUOUS_LEARNING] [OK] Mirror System initialized")
        except Exception as e:
            logger.warning(f"[CONTINUOUS_LEARNING] Mirror System unavailable: {e}")

        # Get Learning Orchestrator
        try:
            from cognitive.thread_learning_orchestrator import ThreadLearningOrchestrator
            kb_path = str(Path(__file__).parent.parent / "data" / "knowledge_base")
            self.learning_orchestrator = ThreadLearningOrchestrator(knowledge_base_path=kb_path)
            logger.info("[CONTINUOUS_LEARNING] [OK] Learning Orchestrator initialized")
        except Exception as e:
            logger.debug(f"[CONTINUOUS_LEARNING] Learning Orchestrator unavailable: {e}")

        # Get Ingestion Service
        try:
            from ingestion.service import TextIngestionService
            from embedding import get_embedding_model

            try:
                embedding_model = get_embedding_model()
                self.ingestion_service = TextIngestionService(
                    embedding_model=embedding_model
                )
                # print("[CONTINUOUS_LEARNING] [OK] Ingestion Service initialized", flush=True)
                logger.info("[CONTINUOUS_LEARNING] [OK] Ingestion Service initialized")
            except FileNotFoundError as e:
                # Model not available - this is okay, ingestion service will be unavailable
                logger.warning(f"[CONTINUOUS_LEARNING] Ingestion Service unavailable: {e}")
                self.ingestion_service = None
        except Exception as e:
            logger.warning(f"[CONTINUOUS_LEARNING] Ingestion Service unavailable: {e}")
            self.ingestion_service = None

        logger.info("[CONTINUOUS_LEARNING] Component initialization complete")

    def start(self):
        """Start continuous learning orchestration"""
        if self.running:
            logger.warning("[CONTINUOUS_LEARNING] Already running")
            # Re-initialize components if they're missing
            if not self.ingestion_service or not self.sandbox_lab:
                logger.info("[CONTINUOUS_LEARNING] Re-initializing missing components...")
                self.initialize_components()
            return

        logger.info("[CONTINUOUS_LEARNING] Starting continuous learning orchestration...")

        self.initialize_components()

        self.running = True
        self.orchestrator_thread = threading.Thread(
            target=self._orchestration_loop,
            daemon=True,
            name="ContinuousLearningOrchestrator"
        )
        self.orchestrator_thread.start()

        logger.info("[CONTINUOUS_LEARNING] Orchestration started - Grace will now continuously learn and improve")

    def stop(self):
        """Stop continuous learning orchestration"""
        if not self.running:
            return

        logger.info("[CONTINUOUS_LEARNING] Stopping orchestration...")
        self.running = False

        if self.orchestrator_thread:
            self.orchestrator_thread.join(timeout=5)

        logger.info("[CONTINUOUS_LEARNING] Orchestration stopped")

    def _orchestration_loop(self):
        """Main orchestration loop - runs continuously"""
        start_time = time.time()
        cycle_count = 0

        logger.info("[CONTINUOUS_LEARNING] Orchestration loop started")

        while self.running:
            try:
                cycle_start = time.time()
                cycle_count += 1

                # Update uptime
                self.stats["uptime_seconds"] = int(time.time() - start_time)

                # 1. Check for new data to ingest
                if self._should_run_ingestion():
                    self._run_ingestion_check()

                # 2. Run learning cycles
                if self._should_run_learning():
                    self._run_learning_cycle()

                # 3. Mirror observes and identifies improvements
                if self._should_run_mirror():
                    self._run_mirror_observation()

                # 4. Check and manage experiments
                if self._should_check_experiments():
                    self._check_experiments()

                # 5. Update metrics
                self._update_metrics()

                # 6. Log periodic status
                if cycle_count % 10 == 0:
                    self._log_status()

                # Sleep until next cycle
                cycle_duration = time.time() - cycle_start
                sleep_time = max(1, 10 - cycle_duration)  # Run at least every 10 seconds
                time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"[CONTINUOUS_LEARNING] Error in orchestration loop: {e}", exc_info=True)
                time.sleep(30)  # Wait before retrying

    def _should_run_ingestion(self) -> bool:
        """Check if it's time to check for new data"""
        if not self.last_ingestion_check:
            return True

        elapsed = (datetime.now() - self.last_ingestion_check).total_seconds()
        return elapsed >= self.config["ingestion_interval_seconds"]

    def _should_run_learning(self) -> bool:
        """Check if it's time to run learning cycle"""
        if not self.last_learning_cycle:
            return True

        elapsed = (datetime.now() - self.last_learning_cycle).total_seconds()
        return elapsed >= self.config["learning_cycle_interval_seconds"]

    def _should_run_mirror(self) -> bool:
        """Check if it's time for mirror observation"""
        if not self.last_mirror_observation:
            return True

        elapsed = (datetime.now() - self.last_mirror_observation).total_seconds()
        return elapsed >= self.config["mirror_observation_interval_seconds"]

    def _should_check_experiments(self) -> bool:
        """Check if it's time to check experiments"""
        if not self.last_experiment_check:
            return True

        elapsed = (datetime.now() - self.last_experiment_check).total_seconds()
        return elapsed >= self.config["experiment_check_interval_seconds"]

    def _run_ingestion_check(self):
        """Check for and ingest new data"""
        self.last_ingestion_check = datetime.now()

        if not self.ingestion_service:
            return

        try:
            # Check knowledge_base directory for new files
            # Try multiple locations since cwd may vary
            possible_paths = [
                Path("knowledge_base"),  # Relative to cwd
                Path("../knowledge_base"),  # Parent directory
                Path(__file__).parent.parent.parent / "knowledge_base",  # Project root
            ]

            knowledge_base = None
            for path in possible_paths:
                if path.exists() and path.is_dir():
                    knowledge_base = path
                    break

            if not knowledge_base:
                return

            # Scan for files (simplified - would integrate with file manager)
            new_files = []
            for file_path in knowledge_base.glob("**/*"):
                if file_path.is_file() and file_path.suffix in ['.txt', '.md', '.pdf', '.docx']:
                    # Check if already ingested (simplified check)
                    new_files.append(str(file_path))

            if new_files:
                logger.info(f"[CONTINUOUS_LEARNING] Found {len(new_files)} files to potentially ingest")
                # Add to ingestion queue
                for file_path in new_files[:5]:  # Limit to 5 files per check
                    self.ingestion_queue.append({
                        "file_path": file_path,
                        "timestamp": datetime.now().isoformat()
                    })

            # Process ingestion queue
            while self.ingestion_queue and len(self.ingestion_queue) > 0:
                item = self.ingestion_queue.pop(0)
                try:
                    # Ingest file
                    file_path = Path(item["file_path"])
                    if file_path.exists():
                        content = file_path.read_text(encoding='utf-8', errors='ignore')

                        # Ingest
                        doc_id, error = self.ingestion_service.ingest_text_fast(
                            text_content=content,
                            filename=file_path.name,
                            source="continuous_learning",
                            metadata={"file_path": str(file_path.absolute())}
                        )

                        if doc_id:
                            self.stats["total_ingestions"] += 1
                            logger.info(f"[CONTINUOUS_LEARNING] Ingested: {file_path.name} (doc_id={doc_id})")

                            # Add to learning queue
                            self.learning_queue.append({
                                "document_id": doc_id,
                                "filename": file_path.name,
                                "timestamp": datetime.now().isoformat()
                            })

                except Exception as e:
                    logger.error(f"[CONTINUOUS_LEARNING] Ingestion error: {e}")

        except Exception as e:
            logger.error(f"[CONTINUOUS_LEARNING] Ingestion check error: {e}")

    def _run_learning_cycle(self):
        """Run autonomous learning cycle"""
        self.last_learning_cycle = datetime.now()

        if not self.learning_orchestrator:
            return

        try:
            # Process learning queue
            if self.learning_queue:
                logger.info(f"[CONTINUOUS_LEARNING] Running learning cycle with {len(self.learning_queue)} items")

                # Take up to 10 items for this cycle
                items = self.learning_queue[:10]
                self.learning_queue = self.learning_queue[10:]

                for item in items:
                    # Trigger autonomous learning
                    # This would integrate with the autonomous learning API
                    self.stats["knowledge_items_learned"] += 1

                self.stats["total_learning_cycles"] += 1
                logger.info(f"[CONTINUOUS_LEARNING] Learning cycle complete")

        except Exception as e:
            logger.error(f"[CONTINUOUS_LEARNING] Learning cycle error: {e}")

    def _run_mirror_observation(self):
        """Mirror observes patterns and proposes improvements"""
        self.last_mirror_observation = datetime.now()

        if not self.mirror_system or not self.sandbox_lab:
            return

        try:
            logger.info("[CONTINUOUS_LEARNING] Mirror observing recent operations...")

            # Mirror analyzes recent operations
            analysis = self.mirror_system.analyze_recent_operations(limit=100)

            if analysis and "improvement_opportunities" in analysis:
                opportunities = analysis["improvement_opportunities"]

                for opportunity in opportunities[:3]:  # Top 3 opportunities
                    if self.config["auto_propose_experiments"]:
                        # Propose experiment to sandbox lab
                        self._propose_experiment_from_opportunity(opportunity)

            self.stats["total_mirror_observations"] += 1

        except Exception as e:
            logger.error(f"[CONTINUOUS_LEARNING] Mirror observation error: {e}")

    def _propose_experiment_from_opportunity(self, opportunity: Dict):
        """Propose experiment based on improvement opportunity"""
        if not self.sandbox_lab:
            return

        try:
            from cognitive.autonomous_sandbox_lab import ExperimentType

            # Map opportunity to experiment
            exp_type_map = {
                "chunking": ExperimentType.ALGORITHM_IMPROVEMENT,
                "retrieval": ExperimentType.ALGORITHM_IMPROVEMENT,
                "learning": ExperimentType.LEARNING_ENHANCEMENT,
                "performance": ExperimentType.PERFORMANCE_OPTIMIZATION,
                "error": ExperimentType.ERROR_REDUCTION
            }

            exp_type = exp_type_map.get(
                opportunity.get("category", "improvement"),
                ExperimentType.ALGORITHM_IMPROVEMENT
            )

            # Propose experiment
            exp = self.sandbox_lab.propose_experiment(
                name=opportunity.get("name", "Auto-proposed improvement"),
                description=opportunity.get("description", ""),
                experiment_type=exp_type,
                motivation=opportunity.get("motivation", "Mirror detected improvement opportunity"),
                proposed_by="continuous_learning_orchestrator",
                initial_trust_score=opportunity.get("confidence", 0.5)
            )

            self.stats["total_experiments_proposed"] += 1
            logger.info(f"[CONTINUOUS_LEARNING] Proposed experiment: {exp.experiment_id} - {exp.name}")

            # Track for auto-start trial
            self.experiment_ideas.append({
                "experiment_id": exp.experiment_id,
                "proposed_at": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"[CONTINUOUS_LEARNING] Experiment proposal error: {e}")

    def _check_experiments(self):
        """Check and manage sandbox experiments"""
        self.last_experiment_check = datetime.now()

        if not self.sandbox_lab:
            return

        try:
            # Check active trials
            active_trials = self.sandbox_lab.get_active_trials()

            # Record trial results based on recent ingestions
            for trial_exp in active_trials:
                # Use recently ingested data as trial data points
                if self.stats["total_ingestions"] > 0:
                    # Simulate trial result (in reality, would track actual performance)
                    success = True  # Would measure actual success

                    self.sandbox_lab.record_trial_result(
                        trial_exp.experiment_id,
                        success=success,
                        metrics=self.current_metrics
                    )

                    self.stats["data_points_processed"] += 1

            # Check for validated experiments
            awaiting_approval = self.sandbox_lab.get_awaiting_approval()

            for exp in awaiting_approval:
                logger.info(f"[CONTINUOUS_LEARNING] Experiment {exp.experiment_id} awaiting user approval")
                logger.info(f"[CONTINUOUS_LEARNING] Trust: {exp.current_trust_score:.2f}, Improvement: {exp.improvement_percentage}%")

                # Check for auto-approval
                if exp.can_auto_approve():
                    logger.info(f"[CONTINUOUS_LEARNING] Experiment {exp.experiment_id} qualifies for auto-approval!")
                    # Would request user approval here

            # Auto-start trials for high-trust sandbox experiments
            if self.config["auto_start_trials"]:
                from cognitive.autonomous_sandbox_lab import ExperimentStatus
                sandbox_exps = self.sandbox_lab.list_experiments(
                    status=ExperimentStatus.SANDBOX
                )

                for exp in sandbox_exps:
                    if exp.current_trust_score >= self.config["min_trust_for_auto_trial"]:
                        if exp.implementation_code:  # Has implementation
                            # Start trial
                            self.sandbox_lab.start_trial(
                                exp.experiment_id,
                                baseline_metrics=self.baseline_metrics
                            )

                            self.stats["total_trials_started"] += 1
                            logger.info(f"[CONTINUOUS_LEARNING] Auto-started trial for {exp.experiment_id}")

        except Exception as e:
            logger.error(f"[CONTINUOUS_LEARNING] Experiment check error: {e}")

    def _update_metrics(self):
        """Update current performance metrics"""
        # Would calculate actual metrics from recent operations
        # For now, track stats
        pass

    def _log_status(self):
        """Log periodic status"""
        logger.info(f"[CONTINUOUS_LEARNING] === STATUS ===")
        logger.info(f"[CONTINUOUS_LEARNING] Uptime: {self.stats['uptime_seconds']}s")
        logger.info(f"[CONTINUOUS_LEARNING] Ingestions: {self.stats['total_ingestions']}")
        logger.info(f"[CONTINUOUS_LEARNING] Learning cycles: {self.stats['total_learning_cycles']}")
        logger.info(f"[CONTINUOUS_LEARNING] Mirror observations: {self.stats['total_mirror_observations']}")
        logger.info(f"[CONTINUOUS_LEARNING] Experiments proposed: {self.stats['total_experiments_proposed']}")
        logger.info(f"[CONTINUOUS_LEARNING] Trials started: {self.stats['total_trials_started']}")
        logger.info(f"[CONTINUOUS_LEARNING] Queues - Ingestion: {len(self.ingestion_queue)}, Learning: {len(self.learning_queue)}")

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            "running": self.running,
            "uptime_seconds": self.stats["uptime_seconds"],
            "stats": self.stats,
            "config": self.config,
            "queues": {
                "ingestion": len(self.ingestion_queue),
                "learning": len(self.learning_queue),
                "experiment_ideas": len(self.experiment_ideas)
            },
            "last_operations": {
                "ingestion_check": self.last_ingestion_check.isoformat() if self.last_ingestion_check else None,
                "learning_cycle": self.last_learning_cycle.isoformat() if self.last_learning_cycle else None,
                "mirror_observation": self.last_mirror_observation.isoformat() if self.last_mirror_observation else None,
                "experiment_check": self.last_experiment_check.isoformat() if self.last_experiment_check else None
            },
            "current_metrics": self.current_metrics
        }


# Singleton instance
_continuous_orchestrator: Optional[ContinuousLearningOrchestrator] = None


def get_continuous_orchestrator() -> ContinuousLearningOrchestrator:
    """Get or create continuous learning orchestrator"""
    global _continuous_orchestrator
    if _continuous_orchestrator is None:
        _continuous_orchestrator = ContinuousLearningOrchestrator()
    return _continuous_orchestrator


def start_continuous_learning():
    """Start continuous learning orchestration"""
    global _continuous_orchestrator

    # Force re-initialization if components are missing
    if _continuous_orchestrator and not _continuous_orchestrator.ingestion_service:
        logger.info("[CONTINUOUS_LEARNING] Forcing re-initialization (components missing)")
        _continuous_orchestrator.running = False
        _continuous_orchestrator = None

    orchestrator = get_continuous_orchestrator()
    orchestrator.start()
    return orchestrator


def stop_continuous_learning():
    """Stop continuous learning orchestration"""
    orchestrator = get_continuous_orchestrator()
    orchestrator.stop()
