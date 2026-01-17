import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from models.genesis_key_models import GenesisKey, GenesisKeyType
from genesis.genesis_key_service import get_genesis_service
from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
from cognitive.mirror_self_modeling import get_mirror_system
from genesis.autonomous_triggers import get_genesis_trigger_pipeline
from cognitive.learning_subagent_system import LearningOrchestrator
class IngestionSelfHealingIntegration:
    logger = logging.getLogger(__name__)
    """
    Unified system connecting ingestion, learning, and self-healing.

    Complete Flow:
    1. File ingested → Genesis Key created (tracks what/where/when/who/how/why)
    2. Genesis Key triggers autonomous learning (study the content)
    3. Learning outcome → Genesis Key created (success/failure)
    4. Self-healing monitors for issues → Heals if needed
    5. Mirror observes patterns → Suggests improvements
    6. Iterate and improve continuously
    """

    def __init__(
        self,
        session: Session,
        knowledge_base_path: Path,
        learning_orchestrator: Optional[LearningOrchestrator] = None,
        enable_healing: bool = True,
        enable_mirror: bool = True
    ):
        self.session = session
        self.knowledge_base_path = knowledge_base_path
        self.learning_orchestrator = learning_orchestrator
        self.enable_healing = enable_healing
        self.enable_mirror = enable_mirror

        # Initialize services
        self.genesis_service = get_genesis_service()

        # Initialize trigger pipeline
        self.trigger_pipeline = get_genesis_trigger_pipeline(
            session=session,
            knowledge_base_path=knowledge_base_path,
            orchestrator=learning_orchestrator
        )

        # Initialize healing system
        if enable_healing:
            self.healing_system = get_autonomous_healing(
                session=session,
                repo_path=knowledge_base_path,
                trust_level=TrustLevel.MEDIUM_RISK_AUTO,
                enable_learning=True
            )
        else:
            self.healing_system = None

        # Initialize mirror system
        if enable_mirror:
            self.mirror_system = get_mirror_system(
                session=session,
                observation_window_hours=24,
                min_pattern_occurrences=3
            )
        else:
            self.mirror_system = None

        # Statistics
        self.total_ingestions = 0
        self.total_learning_tasks = 0
        self.total_healings = 0
        self.total_improvements = 0

        logger.info("[INGESTION-INTEGRATION] System initialized with complete autonomous loop")

    # ======================================================================
    # COMPLETE INGESTION FLOW WITH GENESIS KEYS
    # ======================================================================

    def ingest_file_with_tracking(
        self,
        file_path: Path,
        user_id: str = "system",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Ingest file with complete Genesis Key tracking.

        This is the main entry point that starts the complete cycle:
        1. Create FILE_INGESTION Genesis Key (what/where/when/who/how/why)
        2. Actually ingest the file
        3. Trigger autonomous learning
        4. Monitor for issues
        5. Heal if needed
        6. Learn from outcome

        Returns complete tracking of the entire process.
        """
        logger.info(f"[INGESTION-INTEGRATION] Starting tracked ingestion: {file_path}")

        self.total_ingestions += 1

        # Step 1: Create Genesis Key BEFORE ingestion (track the attempt)
        ingestion_key = self.genesis_service.create_key(
            key_type=GenesisKeyType.FILE_INGESTION,
            what_description=f"Ingesting file: {file_path.name}",
            who_actor=user_id,
            where_location=str(file_path),
            why_reason="Autonomous knowledge base expansion",
            how_method="file_ingestion_with_tracking",
            file_path=str(file_path),
            context_data={
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size if file_path.exists() else 0,
                "file_type": file_path.suffix,
                "metadata": metadata or {}
            }
        )

        logger.info(f"[INGESTION-INTEGRATION] Genesis Key created: {ingestion_key.key_id}")

        result = {
            "ingestion_key_id": ingestion_key.key_id,
            "file_path": str(file_path),
            "timestamp": datetime.utcnow().isoformat(),
            "steps": []
        }

        try:
            # Step 2: Actually ingest the file
            ingestion_result = self._perform_ingestion(file_path)
            result["steps"].append({
                "step": "ingestion",
                "status": "success" if ingestion_result["success"] else "failed",
                "details": ingestion_result
            })

            if not ingestion_result["success"]:
                # Ingestion failed - create ERROR Genesis Key
                error_key = self._create_error_key(
                    parent_key=ingestion_key,
                    error_type="ingestion_failure",
                    error_message=ingestion_result.get("error", "Unknown error"),
                    file_path=file_path
                )

                result["error_key_id"] = error_key.key_id

                # Trigger self-healing for ingestion failure
                if self.enable_healing:
                    healing_result = self._trigger_healing_for_error(error_key)
                    result["steps"].append({
                        "step": "self_healing",
                        "status": "triggered",
                        "details": healing_result
                    })

                return result

            # Step 3: Trigger autonomous learning
            if self.learning_orchestrator:
                learning_result = self._trigger_autonomous_learning(
                    ingestion_key=ingestion_key,
                    file_path=file_path,
                    ingestion_data=ingestion_result
                )
                result["steps"].append({
                    "step": "autonomous_learning",
                    "status": "triggered",
                    "details": learning_result
                })
                self.total_learning_tasks += 1

            # Step 4: Monitor system health after ingestion
            if self.enable_healing:
                health_check = self.healing_system.assess_system_health()
                result["steps"].append({
                    "step": "health_check",
                    "status": health_check["health_status"],
                    "anomalies": health_check["anomalies_detected"]
                })

                # If health degraded, trigger healing
                if health_check["health_status"] != "healthy":
                    cycle_result = self.healing_system.run_monitoring_cycle()
                    result["steps"].append({
                        "step": "healing_cycle",
                        "status": "executed",
                        "actions": cycle_result["actions_executed"]
                    })
                    self.total_healings += cycle_result["actions_executed"]

            # Step 5: Mirror observation (periodic)
            if self.enable_mirror and self.total_ingestions % 10 == 0:
                mirror_result = self._trigger_mirror_observation()
                result["steps"].append({
                    "step": "mirror_observation",
                    "status": "analyzed",
                    "details": mirror_result
                })
                self.total_improvements += len(mirror_result.get("improvements_triggered", []))

            result["status"] = "success"
            result["complete_cycle"] = True

            logger.info(
                f"[INGESTION-INTEGRATION] Complete cycle finished: {len(result['steps'])} steps"
            )

            return result

        except Exception as e:
            logger.error(f"[INGESTION-INTEGRATION] Error in ingestion cycle: {e}")

            # Create ERROR Genesis Key
            error_key = self._create_error_key(
                parent_key=ingestion_key,
                error_type="cycle_failure",
                error_message=str(e),
                file_path=file_path
            )

            result["error_key_id"] = error_key.key_id
            result["status"] = "failed"
            result["error"] = str(e)

            return result

    def _perform_ingestion(self, file_path: Path) -> Dict[str, Any]:
        """
        Actually ingest the file using the ingestion service.

        This would call your existing ingestion code.
        """
        try:
            from ingestion.service import ingest_file

            # Call existing ingestion
            result = ingest_file(file_path)

            return {
                "success": True,
                "chunks": result.get("chunks", 0),
                "vectors": result.get("vectors", 0)
            }

        except Exception as e:
            logger.error(f"[INGESTION-INTEGRATION] Ingestion failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _trigger_autonomous_learning(
        self,
        ingestion_key: GenesisKey,
        file_path: Path,
        ingestion_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trigger autonomous learning after successful ingestion.

        Creates LEARNING_COMPLETE Genesis Key and triggers study task.
        """
        # Infer topic from file path
        topic = self._infer_topic_from_path(file_path)

        # Submit study task
        task_id = self.learning_orchestrator.submit_study_task(
            topic=topic,
            learning_objectives=[
                f"Learn from ingested file: {file_path.name}",
                "Extract key concepts and patterns",
                "Integrate with existing knowledge"
            ],
            priority=2
        )

        # Create LEARNING_COMPLETE Genesis Key (will be updated when done)
        learning_key = self.genesis_service.create_key(
            key_type=GenesisKeyType.SYSTEM_EVENT,
            what_description=f"Autonomous learning triggered for: {topic}",
            who_actor="learning_orchestrator",
            where_location=str(file_path),
            why_reason=f"Learn from ingested file: {ingestion_key.key_id}",
            how_method="autonomous_study_task",
            context_data={
                "task_id": task_id,
                "topic": topic,
                "parent_ingestion_key": ingestion_key.key_id,
                "chunks_to_study": ingestion_data.get("chunks", 0)
            }
        )

        logger.info(
            f"[INGESTION-INTEGRATION] Learning triggered: task_id={task_id}, "
            f"genesis_key={learning_key.key_id}"
        )

        return {
            "task_id": task_id,
            "learning_key_id": learning_key.key_id,
            "topic": topic
        }

    def _create_error_key(
        self,
        parent_key: GenesisKey,
        error_type: str,
        error_message: str,
        file_path: Path
    ) -> GenesisKey:
        """Create ERROR Genesis Key for tracking failures."""
        error_key = self.genesis_service.create_key(
            key_type=GenesisKeyType.ERROR,
            what_description=f"Error during ingestion: {error_type}",
            who_actor="ingestion_system",
            where_location=str(file_path),
            why_reason=f"Failed ingestion tracked from: {parent_key.key_id}",
            how_method="error_tracking",
            is_error=True,
            error_type=error_type,
            error_message=error_message,
            file_path=str(file_path),
            context_data={
                "parent_key_id": parent_key.key_id,
                "error_type": error_type,
                "file_path": str(file_path)
            }
        )

        logger.warning(
            f"[INGESTION-INTEGRATION] Error tracked: {error_key.key_id} "
            f"(type={error_type})"
        )

        return error_key

    def _trigger_healing_for_error(self, error_key: GenesisKey) -> Dict[str, Any]:
        """Trigger self-healing for an error."""
        # Trigger autonomous actions (healing will be triggered by pipeline)
        trigger_result = self.trigger_pipeline.on_genesis_key_created(error_key)

        # Run healing cycle
        cycle_result = self.healing_system.run_monitoring_cycle()

        return {
            "triggers_fired": len(trigger_result.get("actions_triggered", [])),
            "healing_actions": cycle_result["actions_executed"],
            "health_status": cycle_result["health_status"]
        }

    def _trigger_mirror_observation(self) -> Dict[str, Any]:
        """Trigger mirror self-modeling observation."""
        # Build self-model
        self_model = self.mirror_system.build_self_model()

        # Trigger improvement actions
        if self.learning_orchestrator:
            improvements = self.mirror_system.trigger_improvement_actions(
                self.learning_orchestrator
            )
        else:
            improvements = {"actions_triggered": 0}

        return {
            "patterns_detected": self_model["behavioral_patterns"]["total_detected"],
            "self_awareness_score": self_model["self_awareness_score"],
            "improvements_triggered": improvements.get("actions_triggered", 0),
            "suggestions": len(self_model["improvement_suggestions"])
        }

    def _infer_topic_from_path(self, file_path: Path) -> str:
        """Infer learning topic from file path."""
        # Use parent directory or filename as topic
        if file_path.parent.name and file_path.parent.name != "knowledge_base":
            return file_path.parent.name
        else:
            return file_path.stem.replace("_", " ").replace("-", " ")

    # ======================================================================
    # BATCH INGESTION WITH COMPLETE TRACKING
    # ======================================================================

    def ingest_directory_with_tracking(
        self,
        directory_path: Path,
        user_id: str = "system",
        recursive: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest entire directory with complete tracking.

        Each file gets its own Genesis Key and complete cycle.
        """
        logger.info(
            f"[INGESTION-INTEGRATION] Batch ingestion started: {directory_path} "
            f"(recursive={recursive})"
        )

        results = {
            "directory": str(directory_path),
            "total_files": 0,
            "successful": 0,
            "failed": 0,
            "file_results": []
        }

        # Find all files
        if recursive:
            files = list(directory_path.rglob("*.*"))
        else:
            files = list(directory_path.glob("*.*"))

        # Filter to supported file types
        supported_extensions = {".txt", ".md", ".pdf", ".py", ".js", ".json", ".csv"}
        files = [f for f in files if f.suffix.lower() in supported_extensions]

        results["total_files"] = len(files)

        logger.info(f"[INGESTION-INTEGRATION] Found {len(files)} files to ingest")

        # Ingest each file with complete tracking
        for file_path in files:
            try:
                file_result = self.ingest_file_with_tracking(
                    file_path=file_path,
                    user_id=user_id
                )

                if file_result.get("status") == "success":
                    results["successful"] += 1
                else:
                    results["failed"] += 1

                results["file_results"].append(file_result)

            except Exception as e:
                logger.error(f"[INGESTION-INTEGRATION] Failed to ingest {file_path}: {e}")
                results["failed"] += 1
                results["file_results"].append({
                    "file_path": str(file_path),
                    "status": "failed",
                    "error": str(e)
                })

        logger.info(
            f"[INGESTION-INTEGRATION] Batch complete: "
            f"{results['successful']}/{results['total_files']} successful"
        )

        return results

    # ======================================================================
    # ITERATION & IMPROVEMENT IN SANDBOX
    # ======================================================================

    def run_improvement_cycle(self) -> Dict[str, Any]:
        """
        Run one complete improvement cycle.

        This is what you'd run periodically in the sandbox to iterate and improve:
        1. Observe recent Genesis Keys
        2. Detect patterns (what's failing? what's succeeding?)
        3. Generate improvements
        4. Apply improvements (trigger learning/healing)
        5. Measure results
        """
        logger.info("[INGESTION-INTEGRATION] Running improvement cycle...")

        cycle_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "observations": {},
            "improvements": []
        }

        # 1. Mirror observation
        if self.enable_mirror:
            self_model = self.mirror_system.build_self_model()
            cycle_results["observations"]["mirror"] = {
                "patterns": self_model["behavioral_patterns"]["total_detected"],
                "self_awareness": self_model["self_awareness_score"],
                "suggestions": len(self_model["improvement_suggestions"])
            }

            # Trigger improvements
            if self.learning_orchestrator:
                improvements = self.mirror_system.trigger_improvement_actions(
                    self.learning_orchestrator
                )
                cycle_results["improvements"].extend(
                    improvements.get("details", [])
                )

        # 2. Health check
        if self.enable_healing:
            health = self.healing_system.assess_system_health()
            cycle_results["observations"]["health"] = {
                "status": health["health_status"],
                "anomalies": health["anomalies_detected"],
                "issues": health["code_issues"]
            }

            # Heal if needed
            if health["health_status"] != "healthy":
                healing_cycle = self.healing_system.run_monitoring_cycle()
                cycle_results["improvements"].append({
                    "type": "healing",
                    "actions": healing_cycle["actions_executed"]
                })

        # 3. Learning status
        if self.learning_orchestrator:
            learning_status = self.learning_orchestrator.get_status()
            cycle_results["observations"]["learning"] = {
                "total_subagents": learning_status["total_subagents"],
                "study_queue": learning_status["study_queue_size"],
                "practice_queue": learning_status["practice_queue_size"],
                "completed": learning_status["total_tasks_completed"]
            }

        logger.info(
            f"[INGESTION-INTEGRATION] Improvement cycle complete: "
            f"{len(cycle_results['improvements'])} improvements triggered"
        )

        return cycle_results

    # ======================================================================
    # STATUS & REPORTING
    # ======================================================================

    def get_complete_status(self) -> Dict[str, Any]:
        """Get complete status of the integrated system."""
        status = {
            "statistics": {
                "total_ingestions": self.total_ingestions,
                "total_learning_tasks": self.total_learning_tasks,
                "total_healings": self.total_healings,
                "total_improvements": self.total_improvements
            },
            "components": {}
        }

        # Healing status
        if self.enable_healing:
            status["components"]["healing"] = self.healing_system.get_system_status()

        # Mirror status
        if self.enable_mirror:
            status["components"]["mirror"] = self.mirror_system.get_mirror_status()

        # Learning status
        if self.learning_orchestrator:
            status["components"]["learning"] = self.learning_orchestrator.get_status()

        # Trigger pipeline status
        status["components"]["triggers"] = self.trigger_pipeline.get_status()

        return status


# ======================================================================
# GLOBAL INSTANCE
# ======================================================================

_ingestion_integration: Optional[IngestionSelfHealingIntegration] = None


def get_ingestion_integration(
    session: Session,
    knowledge_base_path: Path,
    learning_orchestrator: Optional[LearningOrchestrator] = None,
    enable_healing: bool = True,
    enable_mirror: bool = True
) -> IngestionSelfHealingIntegration:
    """Get or create global ingestion integration instance."""
    global _ingestion_integration

    if _ingestion_integration is None:
        _ingestion_integration = IngestionSelfHealingIntegration(
            session=session,
            knowledge_base_path=knowledge_base_path,
            learning_orchestrator=learning_orchestrator,
            enable_healing=enable_healing,
            enable_mirror=enable_mirror
        )

    return _ingestion_integration
