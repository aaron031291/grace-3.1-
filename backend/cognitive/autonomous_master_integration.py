import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime
from genesis.layer1_integration import get_layer1_integration
from genesis.autonomous_triggers import get_genesis_trigger_pipeline
from cognitive.learning_subagent_system import LearningOrchestrator
from cognitive.memory_mesh_learner import get_memory_mesh_learner
from database.session import initialize_session_factory
from models.genesis_key_models import GenesisKey, GenesisKeyType
class AutonomousMasterIntegration:
    logger = logging.getLogger(__name__)
    """
    Master Integration Layer - Connects ALL systems.

    This is Grace's central nervous system that orchestrates:
    1. Input reception (Layer 1)
    2. Genesis Key creation
    3. Autonomous trigger evaluation
    4. Multi-process learning execution
    5. Memory pattern analysis
    6. Multi-LLM verification
    7. Recursive self-improvement

    ALL systems are connected and trigger each other autonomously.
    """

    def __init__(
        self,
        session: Session,
        knowledge_base_path: Path,
        enable_learning: bool = True,
        enable_multi_llm: bool = True
    ):
        self.session = session
        self.knowledge_base_path = knowledge_base_path
        self.enable_learning = enable_learning
        self.enable_multi_llm = enable_multi_llm

        # System components
        self.layer1 = None
        self.trigger_pipeline = None
        self.learning_orchestrator = None
        self.memory_learner = None

        # Statistics
        self.total_inputs_processed = 0
        self.total_triggers_fired = 0
        self.total_learning_tasks = 0
        self.total_verifications = 0

        logger.info("[MASTER-INTEGRATION] Initializing autonomous master integration...")

    def initialize(self):
        """
        Initialize ALL systems and connect them together.

        Order matters:
        1. Layer 1 (foundation)
        2. Learning Orchestrator (must exist before triggers)
        3. Trigger Pipeline (references orchestrator)
        4. Memory Learner (analyzes patterns)
        """
        logger.info("[MASTER-INTEGRATION] Starting system initialization...")

        # 1. Initialize Layer 1 Integration
        logger.info("[MASTER-INTEGRATION] → Initializing Layer 1...")
        self.layer1 = get_layer1_integration(session=self.session)

        # 2. Initialize Learning Orchestrator (if enabled)
        if self.enable_learning:
            logger.info("[MASTER-INTEGRATION] → Initializing Learning Orchestrator (8 processes)...")
            self.learning_orchestrator = LearningOrchestrator(
                knowledge_base_path=self.knowledge_base_path,
                num_study_agents=3,
                num_practice_agents=2
            )
            self.learning_orchestrator.start()
            logger.info("[MASTER-INTEGRATION] → Learning Orchestrator ACTIVE")

        # 3. Initialize Genesis Trigger Pipeline
        logger.info("[MASTER-INTEGRATION] → Initializing Genesis Trigger Pipeline...")
        self.trigger_pipeline = get_genesis_trigger_pipeline(
            session=self.session,
            knowledge_base_path=self.knowledge_base_path,
            orchestrator=self.learning_orchestrator
        )

        # 4. Initialize Memory Mesh Learner
        logger.info("[MASTER-INTEGRATION] → Initializing Memory Mesh Learner...")
        self.memory_learner = get_memory_mesh_learner(session=self.session)

        logger.info("[MASTER-INTEGRATION] ✅ ALL SYSTEMS INITIALIZED AND CONNECTED!")

        # Print system status
        self._print_system_status()

    # ======================================================================
    # UNIFIED INPUT PROCESSING - ALL inputs flow through here
    # ======================================================================

    def process_input(
        self,
        input_data: Any,
        input_type: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        UNIFIED INPUT PROCESSOR - ALL inputs flow through here.

        This is the SINGLE ENTRY POINT for all data:
        - User inputs
        - File uploads
        - API data
        - Web scraping results
        - Learning memory
        - System events

        Flow:
        1. Layer 1 processes input
        2. Genesis Key created
        3. Triggers evaluated
        4. Autonomous actions spawned
        5. Results fed back to Layer 1
        """
        self.total_inputs_processed += 1

        logger.info(f"[MASTER-INTEGRATION] Processing input (type={input_type})...")

        # Route to appropriate Layer 1 processor
        result = self._route_to_layer1(input_data, input_type, user_id, metadata)

        # Extract Genesis Key
        genesis_key_id = result.get('genesis_key_id')

        if genesis_key_id:
            # Trigger autonomous actions based on Genesis Key
            trigger_result = self._evaluate_and_trigger(genesis_key_id)
            result['autonomous_actions'] = trigger_result

        # Check memory mesh for learning suggestions
        if self.enable_learning and self.total_inputs_processed % 10 == 0:
            # Every 10 inputs, check if memory mesh has learning suggestions
            suggestions = self._check_memory_mesh_suggestions()
            if suggestions.get('top_priorities'):
                result['memory_suggestions'] = suggestions['top_priorities'][:3]

        return result

    def _route_to_layer1(
        self,
        input_data: Any,
        input_type: str,
        user_id: Optional[str],
        metadata: Optional[Dict]
    ) -> Dict[str, Any]:
        """Route input to appropriate Layer 1 processor."""

        if input_type == "user_input":
            return self.layer1.process_user_input(
                user_input=input_data,
                input_type="question",
                user_id=user_id,
                metadata=metadata
            )

        elif input_type == "file_upload":
            return self.layer1.process_file_upload(
                file_content=input_data.get('content'),
                file_name=input_data.get('name'),
                file_type=input_data.get('type'),
                user_id=user_id,
                metadata=metadata
            )

        elif input_type == "learning_memory":
            return self.layer1.process_learning_memory(
                learning_type=input_data.get('type', 'training'),
                learning_data=input_data.get('data', {}),
                user_id=user_id,
                metadata=metadata
            )

        elif input_type == "external_api":
            return self.layer1.process_external_api(
                api_name=input_data.get('api_name'),
                api_data=input_data.get('data'),
                user_id=user_id,
                metadata=metadata
            )

        elif input_type == "system_event":
            return self.layer1.process_system_event(
                event_type=input_data.get('event_type'),
                event_data=input_data.get('data'),
                user_id=user_id,
                metadata=metadata
            )

        else:
            logger.warning(f"[MASTER-INTEGRATION] Unknown input type: {input_type}")
            return {"error": "Unknown input type"}

    def _evaluate_and_trigger(self, genesis_key_id: str) -> Dict[str, Any]:
        """
        Evaluate Genesis Key and trigger autonomous actions.

        This is where the magic happens:
        - Trigger pipeline evaluates the Genesis Key
        - Determines what autonomous actions are needed
        - Spawns learning tasks, verifications, etc.
        - Returns what was triggered
        """
        # Get Genesis Key from database
        genesis_key = self.session.query(GenesisKey).filter_by(
            key_id=genesis_key_id
        ).first()

        if not genesis_key:
            return {"triggered": False, "reason": "Genesis Key not found"}

        # Trigger autonomous actions
        trigger_result = self.trigger_pipeline.on_genesis_key_created(genesis_key)

        self.total_triggers_fired += len(trigger_result.get('actions_triggered', []))

        return trigger_result

    def _check_memory_mesh_suggestions(self) -> Dict[str, Any]:
        """Check memory mesh for proactive learning suggestions."""
        try:
            suggestions = self.memory_learner.get_learning_suggestions()

            # If there are high-priority items, trigger learning automatically
            for priority in suggestions.get('top_priorities', [])[:2]:  # Top 2
                if priority.get('action') == 'restudy' and priority.get('priority') == 1:
                    # URGENT: Failed multiple times - trigger study immediately
                    if self.learning_orchestrator:
                        task_id = self.learning_orchestrator.submit_study_task(
                            topic=priority['topic'],
                            learning_objectives=['Urgent gap-filling study'],
                            priority=1
                        )
                        logger.info(
                            f"[MASTER-INTEGRATION] Memory mesh triggered urgent study: "
                            f"{priority['topic']} (task={task_id})"
                        )

            return suggestions

        except Exception as e:
            logger.error(f"[MASTER-INTEGRATION] Error checking memory mesh: {e}")
            return {}

    # ======================================================================
    # PROACTIVE MONITORING - Continuous autonomous operation
    # ======================================================================

    def run_proactive_cycle(self):
        """
        Run one cycle of proactive monitoring and triggering.

        This should be called periodically (e.g., every minute) to:
        1. Check for new files (proactive learning)
        2. Analyze memory patterns (proactive gap-filling)
        3. Review learning progress (proactive practice)
        4. Check for contradictions (proactive verification)
        """
        logger.info("[MASTER-INTEGRATION] Running proactive monitoring cycle...")

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "actions": []
        }

        # 1. Check memory mesh for learning gaps
        suggestions = self._check_memory_mesh_suggestions()
        if suggestions.get('knowledge_gaps'):
            logger.info(
                f"[MASTER-INTEGRATION] Found {len(suggestions['knowledge_gaps'])} "
                f"knowledge gaps"
            )
            results['actions'].append({
                "action": "gap_detection",
                "count": len(suggestions['knowledge_gaps'])
            })

        # 2. Check if any recursive loops need attention
        if self.trigger_pipeline:
            status = self.trigger_pipeline.get_status()
            if status.get('recursive_loops_active', 0) > 0:
                logger.info(
                    f"[MASTER-INTEGRATION] {status['recursive_loops_active']} "
                    f"recursive self-improvement loops active"
                )
                results['actions'].append({
                    "action": "recursive_loops",
                    "count": status['recursive_loops_active']
                })

        # 3. Check learning orchestrator status
        if self.learning_orchestrator:
            learning_status = self.learning_orchestrator.get_status()
            total_queued = (
                learning_status.get('study_queue_size', 0) +
                learning_status.get('practice_queue_size', 0)
            )
            if total_queued > 0:
                logger.info(
                    f"[MASTER-INTEGRATION] {total_queued} learning tasks in queue"
                )
                results['actions'].append({
                    "action": "learning_tasks_queued",
                    "count": total_queued
                })

        return results

    # ======================================================================
    # STATUS & MONITORING
    # ======================================================================

    def get_complete_system_status(self) -> Dict[str, Any]:
        """Get complete status of ALL integrated systems."""

        status = {
            "master_integration": {
                "inputs_processed": self.total_inputs_processed,
                "triggers_fired": self.total_triggers_fired,
                "learning_enabled": self.enable_learning,
                "multi_llm_enabled": self.enable_multi_llm
            }
        }

        # Layer 1 status
        if self.layer1:
            status['layer1'] = self.layer1.get_statistics()

        # Trigger pipeline status
        if self.trigger_pipeline:
            status['trigger_pipeline'] = self.trigger_pipeline.get_status()

        # Learning orchestrator status
        if self.learning_orchestrator:
            status['learning_orchestrator'] = self.learning_orchestrator.get_status()

        # Memory mesh suggestions
        if self.memory_learner:
            try:
                suggestions = self.memory_learner.get_learning_suggestions()
                status['memory_mesh'] = {
                    "knowledge_gaps": len(suggestions.get('knowledge_gaps', [])),
                    "high_value_topics": len(suggestions.get('high_value_topics', [])),
                    "failure_patterns": len(suggestions.get('failure_patterns', [])),
                    "top_priorities": suggestions.get('top_priorities', [])[:3]
                }
            except Exception:
                status['memory_mesh'] = {"status": "error"}

        return status

    def _print_system_status(self):
        """Print comprehensive system status."""
        logger.info("=" * 70)
        logger.info("[MASTER-INTEGRATION] COMPLETE SYSTEM STATUS")
        logger.info("=" * 70)
        logger.info(f"✅ Layer 1: CONNECTED")
        logger.info(f"✅ Genesis Keys: TRACKING")
        logger.info(f"✅ Trigger Pipeline: ACTIVE")

        if self.learning_orchestrator:
            status = self.learning_orchestrator.get_status()
            logger.info(f"✅ Learning Orchestrator: {status.get('total_subagents', 0)} agents")

        if self.memory_learner:
            logger.info(f"✅ Memory Mesh: ANALYZING")

        if self.enable_multi_llm:
            logger.info(f"✅ Multi-LLM Verification: ENABLED")

        logger.info("=" * 70)
        logger.info("[MASTER-INTEGRATION] ALL SYSTEMS OPERATIONAL")
        logger.info("=" * 70)

    def shutdown(self):
        """Gracefully shutdown all systems."""
        logger.info("[MASTER-INTEGRATION] Shutting down all systems...")

        if self.learning_orchestrator:
            self.learning_orchestrator.stop()
            logger.info("[MASTER-INTEGRATION] Learning orchestrator stopped")

        logger.info("[MASTER-INTEGRATION] Shutdown complete")


# ======================================================================
# GLOBAL INSTANCE
# ======================================================================

_master_integration: Optional[AutonomousMasterIntegration] = None


def get_master_integration(
    session: Optional[Session] = None,
    knowledge_base_path: Optional[Path] = None,
    enable_learning: bool = True,
    enable_multi_llm: bool = True,
    auto_initialize: bool = True
) -> AutonomousMasterIntegration:
    """
    Get or create the global master integration instance.

    This is the SINGLE ENTRY POINT to Grace's complete autonomous system.
    """
    global _master_integration

    if _master_integration is None:
        if session is None:
            session_factory = initialize_session_factory()
            session = session_factory()

        if knowledge_base_path is None:
            knowledge_base_path = Path("knowledge_base")

        _master_integration = AutonomousMasterIntegration(
            session=session,
            knowledge_base_path=knowledge_base_path,
            enable_learning=enable_learning,
            enable_multi_llm=enable_multi_llm
        )

        if auto_initialize:
            _master_integration.initialize()

    return _master_integration
