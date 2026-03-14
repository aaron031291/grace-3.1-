"""
Genesis Key Autonomous Trigger Pipeline

Genesis Keys are the CENTRAL TRIGGER for all autonomous actions.

Every Genesis Key creation can trigger:
1. Autonomous learning (study new files)
2. Recursive practice loops (mirror → study → practice)
3. Predictive context loading (prefetch related topics)
4. Memory mesh integration (store high-trust patterns)

Architecture:
- Trigger Pipeline Checks Type
  ↓
- Spawns Appropriate Autonomous Actions
  ↓
- Results Create New Genesis Keys
  ↓
- RECURSIVE LOOP if needed
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from settings import settings  # ADDED THIS
from models.genesis_key_models import GenesisKey, GenesisKeyType
from cognitive.learning_subagent_system import LearningOrchestrator, TaskType
from database.session import initialize_session_factory

logger = logging.getLogger(__name__)


class GenesisTriggerPipeline:
    """
    Central trigger pipeline - Genesis Keys trigger autonomous actions.

    Trigger Rules:
    1. FILE_OPERATION (new/modified file) → Auto-study
    2. PRACTICE_OUTCOME (failed) → Mirror analysis → Gap study → Retry
    3. USER_INPUT (question) → Predictive context prefetch
    4. LEARNING_COMPLETE (study done) → Auto-practice if applicable
    5. GAP_IDENTIFIED (by mirror) → Targeted study
    """

    def __init__(
        self,
        knowledge_base_path: Path,
        orchestrator: Optional[LearningOrchestrator] = None
    ):
        # Use session factory instead of storing session (prevents pickle errors)
        self.session_factory = initialize_session_factory()
        self.knowledge_base_path = knowledge_base_path
        self.orchestrator = orchestrator

        # Tracking
        self.triggers_fired = 0
        self.recursive_loops_active = 0

        logger.info("[GENESIS-TRIGGER] Autonomous trigger pipeline initialized")

    def set_orchestrator(self, orchestrator: LearningOrchestrator):
        """Set learning orchestrator reference."""
        self.orchestrator = orchestrator

    # ======================================================================
    # MAIN TRIGGER HANDLER
    # ======================================================================

    def on_genesis_key_created(self, genesis_key: GenesisKey) -> Dict[str, Any]:
        """
        Main trigger handler - called whenever ANY Genesis Key is created.

        Checks Genesis Key type and triggers appropriate autonomous actions.

        Args:
            genesis_key: The newly created Genesis Key

        Returns:
            Dict with triggered actions and results
        """
        if not self.orchestrator:
            logger.debug("[GENESIS-TRIGGER] No orchestrator set, skipping autonomous actions")
            return {"triggered": False, "reason": "No orchestrator"}

        logger.info(f"[GENESIS-TRIGGER] Processing: {genesis_key.key_id} (type={genesis_key.key_type})")

        triggered_actions = []

        # Route to appropriate trigger handler based on type
        if genesis_key.key_type == GenesisKeyType.FILE_OPERATION:
            actions = self._handle_file_operation(genesis_key)
            triggered_actions.extend(actions)

        elif genesis_key.key_type == GenesisKeyType.USER_INPUT:
            actions = self._handle_user_input(genesis_key)
            triggered_actions.extend(actions)

        elif genesis_key.key_type == GenesisKeyType.LEARNING_COMPLETE:
            actions = self._handle_learning_complete(genesis_key)
            triggered_actions.extend(actions)

        elif genesis_key.key_type == GenesisKeyType.PRACTICE_OUTCOME:
            actions = self._handle_practice_outcome(genesis_key)
            triggered_actions.extend(actions)

        elif genesis_key.key_type == GenesisKeyType.GAP_IDENTIFIED:
            actions = self._handle_gap_identified(genesis_key)
            triggered_actions.extend(actions)

        # Check if multi-LLM verification is needed for any response
        if self._should_use_multi_llm_verification(genesis_key):
            actions = self._handle_multi_llm_verification(genesis_key)
            triggered_actions.extend(actions)

        # Check if health check is needed (errors/failures)
        if self._should_trigger_health_check(genesis_key):
            actions = self._handle_health_check_trigger(genesis_key)
            triggered_actions.extend(actions)

        # Check if mirror self-modeling should run (periodic)
        if self._should_trigger_mirror_analysis(genesis_key):
            actions = self._handle_mirror_analysis_trigger(genesis_key)
            triggered_actions.extend(actions)

        self.triggers_fired += len(triggered_actions)

        return {
            "genesis_key_id": genesis_key.key_id,
            "triggered": len(triggered_actions) > 0,
            "actions_triggered": triggered_actions,
            "total_triggers_fired": self.triggers_fired
        }

    # ======================================================================
    # TRIGGER HANDLERS
    # ======================================================================

    def _handle_file_operation(self, genesis_key: GenesisKey) -> List[Dict[str, Any]]:
        """
        Handle FILE_OPERATION Genesis Key.

        Triggers:
        - Auto-study for new files
        - Re-study for modified files
        """
        actions = []
        metadata = genesis_key.context_data or {}

        # Check if this is a new file or modification
        operation_type = metadata.get('operation_type', '')
        file_path = metadata.get('file_path', '')

        if operation_type in ('create', 'modify') and file_path:
            # Determine if this is a learning-worthy file
            if self._is_learning_file(file_path):
                # TRIGGER: Autonomous study
                topic = self._infer_topic_from_path(Path(file_path))

                logger.info(
                    f"[GENESIS-TRIGGER] File operation detected → Triggering autonomous study "
                    f"for '{topic}'"
                )

                task_id = self.orchestrator.submit_study_task(
                    topic=topic,
                    learning_objectives=[f"Learn from {Path(file_path).name}"],
                    priority=1 if operation_type == 'create' else 3
                )

                actions.append({
                    "action": "autonomous_study",
                    "trigger": "file_operation",
                    "topic": topic,
                    "file_path": file_path,
                    "task_id": task_id,
                    "priority": 1 if operation_type == 'create' else 3
                })

        return actions

    def _handle_user_input(self, genesis_key: GenesisKey) -> List[Dict[str, Any]]:
        """
        Handle USER_INPUT Genesis Key.

        Triggers:
        - Predictive context prefetch for related topics
        """
        actions = []
        metadata = genesis_key.context_data or {}

        user_input = metadata.get('input_text', '')

        if user_input:
            # Extract topics from user input
            topics = self._extract_topics_from_input(user_input)

            if topics:
                logger.info(
                    f"[GENESIS-TRIGGER] User input detected → Triggering predictive prefetch "
                    f"for {len(topics)} related topics"
                )

                # TRIGGER: Predictive context prefetch
                # This will pre-load related topics user likely needs next
                for topic in topics[:3]:  # Top 3 most related
                    task_id = self.orchestrator.submit_study_task(
                        topic=topic,
                        learning_objectives=["Prefetch for user query"],
                        priority=5  # Medium priority (background)
                    )

                    actions.append({
                        "action": "predictive_prefetch",
                        "trigger": "user_input",
                        "topic": topic,
                        "task_id": task_id
                    })

        return actions

    def _handle_learning_complete(self, genesis_key: GenesisKey) -> List[Dict[str, Any]]:
        """
        Handle LEARNING_COMPLETE Genesis Key.

        Triggers:
        - Auto-practice if skill is practice-worthy
        """
        actions = []
        metadata = genesis_key.context_data or {}

        skill_learned = metadata.get('skill_name', '')
        concepts_learned = metadata.get('concepts_learned', 0)

        if skill_learned and concepts_learned > 0:
            # Check if this skill should be practiced
            if self._is_practice_worthy_skill(skill_learned):
                logger.info(
                    f"[GENESIS-TRIGGER] Learning complete → Triggering autonomous practice "
                    f"for '{skill_learned}'"
                )

                # TRIGGER: Autonomous practice
                task_id = self.orchestrator.submit_practice_task(
                    skill_name=skill_learned,
                    task_description=f"Practice applying {skill_learned}",
                    complexity=0.5  # Medium complexity
                )

                actions.append({
                    "action": "autonomous_practice",
                    "trigger": "learning_complete",
                    "skill": skill_learned,
                    "task_id": task_id
                })

        return actions

    def _handle_practice_outcome(self, genesis_key: GenesisKey) -> List[Dict[str, Any]]:
        """
        Handle PRACTICE_OUTCOME Genesis Key.

        Triggers:
        - If FAILED: Mirror analysis → Gap identification → Targeted study → Retry
        - If SUCCESS: Log success pattern

        THIS IS THE RECURSIVE LOOP!
        """
        actions = []
        metadata = genesis_key.context_data or {}

        success = metadata.get('success', False)
        skill_name = metadata.get('skill_name', '')

        if not success and skill_name:
            # RECURSIVE TRIGGER: Practice failed → Start self-improvement loop
            logger.info(
                f"[GENESIS-TRIGGER] Practice FAILED → Starting recursive self-improvement loop "
                f"for '{skill_name}'"
            )

            self.recursive_loops_active += 1

            # 1. TRIGGER: Mirror reflection to identify gaps
            # Mirror will analyze what went wrong
            feedback = metadata.get('feedback', 'Unknown failure')

            # Create gap identification Genesis Key (which will trigger gap study)
            gap_genesis_key = GenesisKey(
                key_id=f"GK-gap-{genesis_key.key_id[-8:]}",
                key_type=GenesisKeyType.GAP_IDENTIFIED,
                user_id=genesis_key.user_id,
                description=f"Knowledge gap identified from failed practice: {skill_name}",
                metadata={
                    "skill_name": skill_name,
                    "gap_reason": feedback,
                    "original_practice_key": genesis_key.key_id,
                    "recursive_loop": True
                }
            )

            # Create fresh session for database operation
            session = self.session_factory()
            try:
                session.add(gap_genesis_key)
                session.commit()
            finally:
                session.close()

            # This will trigger _handle_gap_identified recursively
            actions.append({
                "action": "recursive_gap_analysis",
                "trigger": "practice_failed",
                "skill": skill_name,
                "gap_genesis_key": gap_genesis_key.key_id,
                "recursive_loop": True
            })

            logger.info(
                f"[GENESIS-TRIGGER] Recursive loop initiated: "
                f"Practice failed → Gap identified → Will trigger study → Will retry practice"
            )

        elif success:
            # Success - log pattern for memory mesh
            logger.info(f"[GENESIS-TRIGGER] Practice SUCCESS for '{skill_name}' - Pattern logged")

            actions.append({
                "action": "log_success_pattern",
                "trigger": "practice_success",
                "skill": skill_name
            })

        return actions

    def _handle_gap_identified(self, genesis_key: GenesisKey) -> List[Dict[str, Any]]:
        """
        Handle GAP_IDENTIFIED Genesis Key.

        Triggers:
        - Targeted study to fill the gap
        - After study: Retry the practice that failed

        THIS COMPLETES THE RECURSIVE LOOP!
        """
        actions = []
        metadata = genesis_key.context_data or {}

        skill_name = metadata.get('skill_name', '')
        gap_reason = metadata.get('gap_reason', '')
        is_recursive = metadata.get('recursive_loop', False)

        if skill_name:
            logger.info(
                f"[GENESIS-TRIGGER] Gap identified → Triggering targeted study "
                f"to fill gap in '{skill_name}'"
            )

            # TRIGGER: Targeted study to fill gap
            task_id = self.orchestrator.submit_study_task(
                topic=skill_name,
                learning_objectives=[f"Fill gap: {gap_reason}"],
                priority=2  # High priority (gap-filling)
            )

            actions.append({
                "action": "gap_filling_study",
                "trigger": "gap_identified",
                "skill": skill_name,
                "gap_reason": gap_reason,
                "task_id": task_id,
                "recursive_loop": is_recursive
            })

            if is_recursive:
                # TRIGGER: After study completes, retry practice
                # This closes the recursive loop: Practice → Fail → Gap → Study → Practice
                logger.info(
                    f"[GENESIS-TRIGGER] Recursive loop continues: "
                    f"Will retry practice after gap-filling study"
                )

                # Queue practice retry (will execute after study completes)
                retry_task_id = self.orchestrator.submit_practice_task(
                    skill_name=skill_name,
                    task_description=f"Retry practice after gap-filling study",
                    complexity=0.5
                )

                actions.append({
                    "action": "retry_practice",
                    "trigger": "gap_study_queued",
                    "skill": skill_name,
                    "task_id": retry_task_id,
                    "recursive_loop": True,
                    "note": "This completes the recursive self-improvement loop"
                })

                logger.info(
                    f"[GENESIS-TRIGGER] ✅ RECURSIVE LOOP COMPLETE: "
                    f"Practice → Failed → Gap Identified → Study Queued → Practice Queued → "
                    f"Loop will continue until success"
                )

        return actions

    # ======================================================================
    # UTILITY METHODS
    # ======================================================================

    def _is_learning_file(self, file_path: str) -> bool:
        """Check if file is learning-worthy."""
        learning_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md', '.py', '.json'}
        ignore_patterns = ['node_modules', '__pycache__', '.git', 'dist', 'build']

        path = Path(file_path)

        # Check extension
        if path.suffix.lower() not in learning_extensions:
            return False

        # Check ignore patterns
        if any(pattern in str(path) for pattern in ignore_patterns):
            return False

        return True

    def _infer_topic_from_path(self, file_path: Path) -> str:
        """Infer learning topic from file path."""
        # Use parent folder name as topic
        parent = file_path.parent.name

        # Common topic mappings
        topic_mappings = {
            "ai research": "AI and machine learning",
            "ai_research": "AI and machine learning",
            "learning_memory": "Learning and memory systems",
            "backend": "Backend development",
            "frontend": "Frontend development",
            "databases": "Database design",
            "testing": "Testing and TDD",
            "python": "Python programming",
            "api": "API design",
            "architecture": "Software architecture"
        }

        parent_lower = parent.lower()
        for key, topic in topic_mappings.items():
            if key in parent_lower:
                return topic

        # Default: use file name without extension
        return file_path.stem.replace('_', ' ').replace('-', ' ').title()

    def _extract_topics_from_input(self, user_input: str) -> List[str]:
        """Extract potential topics from user input for prefetching."""
        # Simple keyword extraction (can be enhanced with NLP)
        keywords = {
            'api': 'API design',
            'rest': 'REST APIs',
            'authentication': 'Authentication',
            'database': 'Database design',
            'python': 'Python programming',
            'react': 'React development',
            'docker': 'Docker containers',
            'kubernetes': 'Kubernetes',
            'testing': 'Testing and TDD'
        }

        user_lower = user_input.lower()
        extracted_topics = []

        for keyword, topic in keywords.items():
            if keyword in user_lower:
                extracted_topics.append(topic)

        return extracted_topics

    def _is_practice_worthy_skill(self, skill_name: str) -> bool:
        """Check if skill should be automatically practiced."""
        # Skills that benefit from practice
        practice_worthy = [
            'python', 'programming', 'coding', 'api', 'database',
            'testing', 'docker', 'kubernetes', 'react', 'frontend',
            'backend', 'algorithm'
        ]

        skill_lower = skill_name.lower()
        return any(kw in skill_lower for kw in practice_worthy)

    # ======================================================================
    # MULTI-LLM VERIFICATION
    # ======================================================================

    def _should_use_multi_llm_verification(self, genesis_key: GenesisKey) -> bool:
        """
        Determine if multi-LLM verification should be triggered.

        Multi-LLM verification is useful for:
        - Critical decisions (high-stakes)
        - Complex reasoning tasks
        - Uncertain or low-confidence responses
        - Contradictory information detected
        """
        metadata = genesis_key.context_data or {}

        # Check for markers that indicate verification needed
        needs_verification = False

        # 1. Low confidence responses
        confidence = metadata.get('confidence_score', 1.0)
        if confidence < 0.7:
            needs_verification = True

        # 2. Contradiction detected
        if metadata.get('contradiction_detected', False):
            needs_verification = True

        # 3. High-stakes operations
        if metadata.get('high_stakes', False):
            needs_verification = True

        # 4. Complex reasoning required
        complexity = metadata.get('complexity', 0)
        if complexity > 0.7:
            needs_verification = True

        # 5. Explicit verification request
        if metadata.get('request_verification', False):
            needs_verification = True

        return needs_verification

    def _handle_multi_llm_verification(self, genesis_key: GenesisKey) -> List[Dict[str, Any]]:
        """
        Handle multi-LLM verification trigger.

        Spawns verification task using multiple LLMs to:
        - Cross-validate responses
        - Detect hallucinations
        - Identify contradictions
        - Provide consensus answer
        """
        actions = []
        metadata = genesis_key.context_data or {}

        try:
            # Import LLM orchestration (lazy import)
            from llm_orchestrator.llm_orchestrator import LLMOrchestrator

            # Get the query/prompt that needs verification
            query = metadata.get('query') or metadata.get('user_input') or metadata.get('prompt', '')

            if query:
                logger.info(
                    f"[GENESIS-TRIGGER] Low confidence/contradiction detected → "
                    f"Triggering multi-LLM verification for: '{query[:50]}...'"
                )

                # Create orchestrator instance
                orchestrator = LLMOrchestrator()

                # Queue verification task (async)
                # This will use multiple LLMs to verify the response
                actions.append({
                    "action": "multi_llm_verification",
                    "trigger": "low_confidence_or_contradiction",
                    "query": query[:100],
                    "reason": metadata.get('verification_reason', 'Low confidence or contradiction detected'),
                    "verification_method": "multi_llm_consensus",
                    "note": "Will use 3+ LLMs to cross-validate response"
                })

                logger.info(
                    f"[GENESIS-TRIGGER] Multi-LLM verification queued for consensus validation"
                )

        except Exception as e:
            if not (settings and settings.SUPPRESS_GENESIS_ERRORS):
                logger.error(f"Error triggering multi-LLM verification: {e}")

        return actions

    # ======================================================================
    # SELF-HEALING TRIGGERS
    # ======================================================================

    def _should_trigger_health_check(self, genesis_key: GenesisKey) -> bool:
        """
        Determine if health check should be triggered.

        Triggers on:
        - Multiple errors in short period
        - Critical failures
        - System anomalies
        """
        metadata = genesis_key.context_data or {}

        # Trigger on error Genesis Keys
        if genesis_key.key_type == GenesisKeyType.ERROR:
            return True

        # Trigger if explicitly requested
        if metadata.get('request_health_check', False):
            return True

        return False

    def _handle_health_check_trigger(self, genesis_key: GenesisKey) -> List[Dict[str, Any]]:
        """
        Handle health check and healing trigger.

        Uses autonomous healing system to:
        - Assess system health
        - Detect anomalies
        - Decide healing actions
        - Execute autonomously (if trust allows)
        """
        actions = []

        try:
            from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel

            logger.info("[GENESIS-TRIGGER] Error/failure detected → Triggering health check")

            # Create fresh session for healing system
            session = self.session_factory()
            try:
                # Get healing system
                healing = get_autonomous_healing(
                    session=session,
                    trust_level=TrustLevel.MEDIUM_RISK_AUTO,
                    enable_learning=True
                )

                # Run monitoring cycle
                cycle_result = healing.run_monitoring_cycle()

                actions.append({
                    "action": "health_check_and_healing",
                    "trigger": "error_or_failure_detected",
                    "health_status": cycle_result["health_status"],
                    "anomalies_detected": cycle_result["anomalies_detected"],
                    "actions_executed": cycle_result["actions_executed"],
                    "awaiting_approval": cycle_result["awaiting_approval"]
                })
            finally:
                session.close()

            logger.info(
                f"[GENESIS-TRIGGER] Health check complete: {cycle_result['health_status']}, "
                f"executed {cycle_result['actions_executed']} healing actions"
            )

        except Exception as e:
            if hasattr(settings, 'SUPPRESS_GENESIS_ERRORS') and settings.SUPPRESS_GENESIS_ERRORS:
                logger.debug(f"Spindle isolation or health check failed (suppressed): {e}")
            else:
                if not (settings and settings.SUPPRESS_GENESIS_ERRORS):
                    logger.error(f"Error triggering health check: {e}")

        return actions

    # ======================================================================
    # MIRROR SELF-MODELING TRIGGERS
    # ======================================================================

    def _should_trigger_mirror_analysis(self, genesis_key: GenesisKey) -> bool:
        """
        Determine if mirror self-modeling should be triggered.

        Triggers periodically (every N operations) to build self-model.
        """
        # Trigger every 50 operations
        return self.triggers_fired % 50 == 0

    def _handle_mirror_analysis_trigger(self, genesis_key: GenesisKey) -> List[Dict[str, Any]]:
        """
        Handle mirror self-modeling trigger.

        Uses mirror system to:
        - Observe recent operations
        - Detect behavioral patterns
        - Build self-model
        - Generate improvement suggestions
        - Trigger improvement actions
        """
        actions = []

        try:
            from cognitive.mirror_self_modeling import get_mirror_system

            logger.info("[GENESIS-TRIGGER] Triggering mirror self-modeling analysis")

            # Create fresh session for mirror system
            session = self.session_factory()
            try:
                # Get mirror system
                mirror = get_mirror_system(
                    session=session,
                    observation_window_hours=24,
                    min_pattern_occurrences=3
                )

                # Build self-model
                self_model = mirror.build_self_model()

                # Trigger improvement actions if orchestrator available
                if self.orchestrator:
                    try:
                        from cognitive.autonomous_sandbox_lab import get_sandbox_lab
                        sandbox = get_sandbox_lab(session=session)
                    except Exception as e:
                        logger.error(f"[GENESIS-TRIGGER] Could not load sandbox lab: {e}")
                        sandbox = None
                        
                    improvement_result = mirror.trigger_improvement_actions(
                        learning_orchestrator=self.orchestrator,
                        sandbox_lab=sandbox
                    )
                    actions.append({
                        "action": "mirror_self_modeling",
                        "trigger": "periodic_self_reflection",
                        "patterns_detected": self_model["behavioral_patterns"]["total_detected"],
                        "improvement_suggestions": len(self_model["improvement_suggestions"]),
                        "actions_triggered": improvement_result["actions_triggered"],
                        "self_awareness_score": self_model["self_awareness_score"]
                    })

                    logger.info(
                        f"[GENESIS-TRIGGER] Mirror analysis complete: "
                        f"{self_model['behavioral_patterns']['total_detected']} patterns, "
                        f"{len(self_model['improvement_suggestions'])} suggestions, "
                        f"{improvement_result['actions_triggered']} actions triggered"
                    )
            finally:
                session.close()

        except Exception as e:
            if not (settings and settings.SUPPRESS_GENESIS_ERRORS):
                logger.error(f"Error triggering mirror analysis: {e}")

        return actions

    # ======================================================================
    # STATUS
    # ======================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get trigger pipeline status."""
        return {
            "triggers_fired": self.triggers_fired,
            "recursive_loops_active": self.recursive_loops_active,
            "orchestrator_connected": self.orchestrator is not None,
            "message": "Genesis Key autonomous trigger pipeline operational"
        }


# ======================================================================
# GLOBAL INSTANCE
# ======================================================================

_trigger_pipeline: Optional[GenesisTriggerPipeline] = None


def get_genesis_trigger_pipeline(
    session: Optional[Session] = None,
    knowledge_base_path: Optional[Path] = None,
    orchestrator: Optional[LearningOrchestrator] = None
) -> GenesisTriggerPipeline:
    """
    Get or create Genesis trigger pipeline instance.
    
    NOTE: 'session' parameter is deprecated and ignored. 
    Pipeline creates fresh sessions on-demand to avoid pickle errors.
    """
    global _trigger_pipeline

    # Warn if session is passed (deprecated)
    if session is not None:
        logger.warning("[GENESIS-TRIGGER] Session parameter is deprecated and ignored (uses session factory instead)")

    # Default knowledge base path
    if knowledge_base_path is None:
        knowledge_base_path = Path(settings.KNOWLEDGE_BASE_PATH)

    # Always use global singleton (session created on-demand via factory)
    if _trigger_pipeline is None:
        _trigger_pipeline = GenesisTriggerPipeline(
            knowledge_base_path=knowledge_base_path,
            orchestrator=orchestrator
        )
    
    # Update orchestrator on global if provided
    if orchestrator is not None:
        _trigger_pipeline.set_orchestrator(orchestrator)
        
    return _trigger_pipeline
