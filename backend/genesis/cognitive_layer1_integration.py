import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable
from sqlalchemy.orm import Session
from genesis.layer1_integration import Layer1Integration
from cognitive.engine import CognitiveEngine, DecisionContext
from cognitive.decision_log import DecisionLogger
logger = logging.getLogger(__name__)

class CognitiveLayer1Integration:
    """
    Layer 1 Integration with Cognitive Engine enforcement.

    Every Layer 1 input flows through OODA loop and invariant validation.
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session
        self.layer1 = Layer1Integration(session)
        self.decision_logger = DecisionLogger()
        self.cognitive_engine = CognitiveEngine(
            decision_logger=self.decision_logger,
            enable_strict_mode=True
        )

    def _execute_with_cognitive_enforcement(
        self,
        operation_name: str,
        problem_statement: str,
        goal: str,
        success_criteria: List[str],
        action: Callable[[], Any],
        requires_determinism: bool = False,
        is_safety_critical: bool = False,
        impact_scope: str = "local",
        is_reversible: bool = True,
        reversibility_justification: Optional[str] = None,
        observations: Optional[Dict] = None,
        constraints: Optional[Dict] = None,
        context_info: Optional[Dict] = None,
        planning_timeout_seconds: int = 30
    ) -> tuple[Any, DecisionContext]:
        """
        Execute an operation through the complete OODA loop with invariant validation.

        Args:
            operation_name: Name of the operation
            problem_statement: Clear problem statement
            goal: What success looks like
            success_criteria: Measurable success criteria
            action: Function to execute
            requires_determinism: If True, enforces deterministic execution
            is_safety_critical: If True, marks as safety-critical
            impact_scope: Blast radius (local, component, systemic)
            is_reversible: Whether operation can be reversed
            reversibility_justification: Justification for irreversible operations
            observations: Observed facts
            constraints: Constraints on decision
            context_info: Contextual information
            planning_timeout_seconds: Planning timeout

        Returns:
            Tuple of (result, decision_context)
        """
        # BEGIN DECISION
        context = self.cognitive_engine.begin_decision(
            problem_statement=problem_statement,
            goal=goal,
            success_criteria=success_criteria,
            requires_determinism=requires_determinism,
            is_safety_critical=is_safety_critical,
            impact_scope=impact_scope,
            is_reversible=is_reversible
        )

        # Set reversibility justification for irreversible operations
        if not is_reversible and reversibility_justification:
            context.reversibility_justification = reversibility_justification

        # Set planning timeout
        context.decision_freeze_point = (
            datetime.utcnow() + timedelta(seconds=planning_timeout_seconds)
        )

        try:
            # OBSERVE: Gather information
            self.cognitive_engine.observe(
                context,
                observations or {
                    'operation': operation_name,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )

            # ORIENT: Understand context and constraints
            self.cognitive_engine.orient(
                context,
                constraints or {
                    'safety_critical': is_safety_critical,
                    'impact_scope': impact_scope
                },
                context_info or {
                    'determinism_required': requires_determinism,
                    'reversible': is_reversible
                }
            )

            # DECIDE: Choose execution path
            def generate_alternatives() -> List[Dict[str, Any]]:
                return [{
                    'name': 'execute_layer1_operation',
                    'description': f'Execute {operation_name} through Layer 1 pipeline',
                    'immediate_value': 1.0,
                    'future_options': 1.0,
                    'simplicity': 1.0,
                    'reversibility': 1.0 if is_reversible else 0.5,
                    'complexity': 0.2,
                }]

            selected_path = self.cognitive_engine.decide(context, generate_alternatives)

            # ACT: Execute the action
            result = self.cognitive_engine.act(context, action, dry_run=False)

            # Finalize decision
            self.cognitive_engine.finalize_decision(context)

            return result, context

        except Exception as e:
            # Abort decision on error
            self.cognitive_engine.abort_decision(
                context,
                reason=f"Error during {operation_name}: {str(e)}"
            )
            raise

    # ============================================================
    # COGNITIVE-ENHANCED LAYER 1 OPERATIONS
    # ============================================================

    def process_user_input(
        self,
        user_input: str,
        user_id: str,
        input_type: str = "chat",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process user input through Cognitive Layer 1.

        Flows through:
        1. Cognitive Engine (OODA + Invariants)
        2. Layer 1 → Genesis Key → Version Control → Librarian → Memory → RAG → World Model
        """
        logger.info(f"[COGNITIVE L1] Processing user input from {user_id}")

        def action():
            return self.layer1.process_user_input(
                user_input=user_input,
                user_id=user_id,
                input_type=input_type,
                metadata=metadata
            )

        result, context = self._execute_with_cognitive_enforcement(
            operation_name="process_user_input",
            problem_statement=f"Process user {input_type} from {user_id}",
            goal="Successfully process user input through complete pipeline",
            success_criteria=[
                "User input received and validated",
                "Genesis Key assigned",
                "Data indexed in RAG",
                "World model updated"
            ],
            action=action,
            requires_determinism=False,
            is_safety_critical=False,
            impact_scope="local",
            is_reversible=True,
            observations={
                'user_id': user_id,
                'input_type': input_type,
                'input_length': len(user_input),
                'has_metadata': metadata is not None
            },
            constraints={'max_input_length': 100000},
            context_info={'user_initiated': True}
        )

        # Add cognitive metadata to result
        result['cognitive'] = {
            'decision_id': context.decision_id,
            'ooda_loop_completed': True,
            'invariants_validated': True,
            'decision_logged': True
        }

        return result

    def process_file_upload(
        self,
        file_content: bytes,
        file_name: str,
        file_type: str,
        user_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process file upload through Cognitive Layer 1.

        File uploads are potentially IRREVERSIBLE (can't unlearn data),
        so we enforce higher cognitive scrutiny.
        """
        logger.info(f"[COGNITIVE L1] Processing file upload '{file_name}' from {user_id}")

        def action():
            return self.layer1.process_file_upload(
                file_content=file_content,
                file_name=file_name,
                file_type=file_type,
                user_id=user_id,
                metadata=metadata
            )

        result, context = self._execute_with_cognitive_enforcement(
            operation_name="process_file_upload",
            problem_statement=f"Ingest file '{file_name}' ({file_type}) from {user_id}",
            goal="Successfully ingest file into knowledge base with full tracking",
            success_criteria=[
                "File validated and saved",
                "Genesis Key assigned",
                "Version tracked symbiotically",
                "Librarian categorized",
                "RAG indexed",
                "World model updated"
            ],
            action=action,
            requires_determinism=True,  # File ingestion should be deterministic
            is_safety_critical=False,
            impact_scope="component",  # Affects knowledge base
            is_reversible=False,  # Cannot unlearn ingested data
            reversibility_justification="File ingestion is intentionally permanent to maintain knowledge base integrity. Data can be marked as deprecated but not fully removed.",
            observations={
                'user_id': user_id,
                'file_name': file_name,
                'file_type': file_type,
                'file_size': len(file_content),
                'has_metadata': metadata is not None
            },
            constraints={
                'max_file_size': 100 * 1024 * 1024,  # 100MB
                'allowed_file_types': ['pdf', 'txt', 'md', 'json', 'py', 'js']
            },
            context_info={'user_initiated': True, 'permanent_ingestion': True}
        )

        # Add cognitive metadata
        result['cognitive'] = {
            'decision_id': context.decision_id,
            'ooda_loop_completed': True,
            'invariants_validated': True,
            'deterministic_execution': True,
            'irreversible_operation': True,
            'decision_logged': True
        }

        return result

    def process_external_api(
        self,
        api_name: str,
        api_endpoint: str,
        api_data: Dict,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process external API data through Cognitive Layer 1.

        External data requires trust assessment (future enhancement).
        """
        logger.info(f"[COGNITIVE L1] Processing external API '{api_name}' data")

        def action():
            return self.layer1.process_external_api(
                api_name=api_name,
                api_endpoint=api_endpoint,
                api_data=api_data,
                user_id=user_id,
                metadata=metadata
            )

        result, context = self._execute_with_cognitive_enforcement(
            operation_name="process_external_api",
            problem_statement=f"Ingest data from external API '{api_name}'",
            goal="Successfully validate and ingest external API data",
            success_criteria=[
                "API data validated",
                "Trust score calculated",
                "Genesis Key assigned",
                "Data indexed in RAG"
            ],
            action=action,
            requires_determinism=True,
            is_safety_critical=False,
            impact_scope="component",
            is_reversible=False,
            reversibility_justification="API data ingestion is permanent to maintain data provenance and audit trails.",
            observations={
                'api_name': api_name,
                'api_endpoint': api_endpoint,
                'data_size': len(str(api_data)),
                'user_id': user_id
            }
        )

        result['cognitive'] = {
            'decision_id': context.decision_id,
            'ooda_loop_completed': True,
            'invariants_validated': True,
            'decision_logged': True
        }

        return result

    def process_web_scraping(
        self,
        url: str,
        html_content: str,
        parsed_data: Dict,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process web scraping data through Cognitive Layer 1.
        """
        logger.info(f"[COGNITIVE L1] Processing web scraping from {url}")

        def action():
            return self.layer1.process_web_scraping(
                url=url,
                html_content=html_content,
                parsed_data=parsed_data,
                user_id=user_id,
                metadata=metadata
            )

        result, context = self._execute_with_cognitive_enforcement(
            operation_name="process_web_scraping",
            problem_statement=f"Ingest scraped data from {url}",
            goal="Successfully validate and ingest web scraping data",
            success_criteria=[
                "Data validated",
                "Trust score calculated",
                "Genesis Key assigned",
                "Data indexed"
            ],
            action=action,
            requires_determinism=True,
            is_safety_critical=False,
            impact_scope="component",
            is_reversible=False,
            reversibility_justification="Web scraping data is permanently archived to maintain historical accuracy and source tracking.",
            observations={
                'url': url,
                'html_size': len(html_content),
                'parsed_data_size': len(str(parsed_data))
            }
        )

        result['cognitive'] = {
            'decision_id': context.decision_id,
            'ooda_loop_completed': True,
            'invariants_validated': True,
            'decision_logged': True
        }

        return result

    def process_memory_mesh(
        self,
        memory_type: str,
        memory_data: Dict,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process memory mesh data through Cognitive Layer 1.
        """
        logger.info(f"[COGNITIVE L1] Processing memory mesh ({memory_type})")

        def action():
            return self.layer1.process_memory_mesh(
                memory_type=memory_type,
                memory_data=memory_data,
                user_id=user_id,
                metadata=metadata
            )

        result, context = self._execute_with_cognitive_enforcement(
            operation_name="process_memory_mesh",
            problem_statement=f"Process memory mesh data ({memory_type})",
            goal="Successfully update memory mesh",
            success_criteria=[
                "Memory validated",
                "Genesis Key assigned",
                "Memory integrated"
            ],
            action=action,
            requires_determinism=True,
            is_safety_critical=False,
            impact_scope="component",
            is_reversible=True,
            observations={
                'memory_type': memory_type,
                'data_size': len(str(memory_data))
            }
        )

        result['cognitive'] = {
            'decision_id': context.decision_id,
            'ooda_loop_completed': True,
            'invariants_validated': True,
            'decision_logged': True
        }

        return result

    def process_learning_memory(
        self,
        learning_type: str,
        learning_data: Dict,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process learning memory through Cognitive Layer 1.

        Learning is CRITICAL - flows to episodic/procedural memory.
        """
        logger.info(f"[COGNITIVE L1] Processing learning memory ({learning_type})")

        def action():
            return self.layer1.process_learning_memory(
                learning_type=learning_type,
                learning_data=learning_data,
                user_id=user_id,
                metadata=metadata
            )

        result, context = self._execute_with_cognitive_enforcement(
            operation_name="process_learning_memory",
            problem_statement=f"Process learning memory ({learning_type})",
            goal="Successfully integrate learning into memory mesh with trust scoring",
            success_criteria=[
                "Learning validated",
                "Trust score calculated",
                "Genesis Key assigned",
                "Memory mesh updated",
                "Episodic/procedural memory updated if high trust"
            ],
            action=action,
            requires_determinism=True,  # Learning must be deterministic
            is_safety_critical=True,  # Learning affects future behavior
            impact_scope="systemic",  # Affects entire system behavior
            is_reversible=False,  # Cannot unlearn
            reversibility_justification="Learning operations permanently affect the knowledge base and model behavior. While weights can be adjusted, learned patterns cannot be fully unlearned.",
            observations={
                'learning_type': learning_type,
                'has_context': 'context' in learning_data,
                'has_outcome': 'outcome' in learning_data
            }
        )

        result['cognitive'] = {
            'decision_id': context.decision_id,
            'ooda_loop_completed': True,
            'invariants_validated': True,
            'deterministic_execution': True,
            'safety_critical': True,
            'decision_logged': True
        }

        return result

    def process_whitelist(
        self,
        whitelist_type: str,
        whitelist_data: Dict,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process whitelist operations through Cognitive Layer 1.

        Whitelist changes are SAFETY-CRITICAL and SYSTEMIC.
        """
        logger.info(f"[COGNITIVE L1] Processing whitelist ({whitelist_type})")

        def action():
            return self.layer1.process_whitelist(
                whitelist_type=whitelist_type,
                whitelist_data=whitelist_data,
                user_id=user_id,
                metadata=metadata
            )

        result, context = self._execute_with_cognitive_enforcement(
            operation_name="process_whitelist",
            problem_statement=f"Update whitelist ({whitelist_type})",
            goal="Successfully update whitelist with security validation",
            success_criteria=[
                "Whitelist change validated",
                "Security implications assessed",
                "Genesis Key assigned",
                "Whitelist updated"
            ],
            action=action,
            requires_determinism=True,
            is_safety_critical=True,  # Affects security
            impact_scope="systemic",  # Affects entire system
            is_reversible=False,
            reversibility_justification="Whitelist changes are critical security operations. While entries can be removed, the history of all security decisions must be permanently maintained for audit purposes.",
            observations={
                'whitelist_type': whitelist_type,
                'operation': whitelist_data.get('operation', 'unknown')
            }
        )

        result['cognitive'] = {
            'decision_id': context.decision_id,
            'ooda_loop_completed': True,
            'invariants_validated': True,
            'deterministic_execution': True,
            'safety_critical': True,
            'decision_logged': True
        }

        return result

    def process_system_event(
        self,
        event_type: str,
        event_data: Dict,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process system events through Cognitive Layer 1.
        """
        logger.info(f"[COGNITIVE L1] Processing system event ({event_type})")

        def action():
            return self.layer1.process_system_event(
                event_type=event_type,
                event_data=event_data,
                metadata=metadata
            )

        result, context = self._execute_with_cognitive_enforcement(
            operation_name="process_system_event",
            problem_statement=f"Process system event ({event_type})",
            goal="Successfully log and process system event",
            success_criteria=[
                "Event validated",
                "Genesis Key assigned",
                "Event logged"
            ],
            action=action,
            requires_determinism=False,
            is_safety_critical=False,
            impact_scope="local",
            is_reversible=True,
            observations={
                'event_type': event_type,
                'event_data_size': len(str(event_data))
            }
        )

        result['cognitive'] = {
            'decision_id': context.decision_id,
            'ooda_loop_completed': True,
            'invariants_validated': True,
            'decision_logged': True
        }

        return result

    # ============================================================
    # UTILITY METHODS
    # ============================================================

    def get_layer1_stats(self) -> Dict[str, Any]:
        """Get Layer 1 statistics with cognitive metadata."""
        stats = self.layer1.get_layer1_stats()
        stats['cognitive_integration'] = {
            'enabled': True,
            'ooda_loop_enforced': True,
            'invariants_validated': 12,
            'decision_logging': True
        }
        return stats

    def verify_layer1_structure(self) -> Dict[str, Any]:
        """Verify Layer 1 structure."""
        return self.layer1.verify_layer1_structure()

    def get_decision_history(self, limit: int = 100) -> List[Dict]:
        """
        Get recent decision history.

        Args:
            limit: Maximum number of decisions to return

        Returns:
            List of decision summaries
        """
        return self.decision_logger.get_recent_decisions(limit=limit)

    def get_active_decisions(self) -> List[DecisionContext]:
        """
        Get all currently active decision contexts.

        Returns:
            List of active decision contexts
        """
        return self.cognitive_engine.get_active_decisions()


# Global Cognitive Layer 1 integration instance
_cognitive_layer1: Optional[CognitiveLayer1Integration] = None


def get_cognitive_layer1_integration(session: Optional[Session] = None) -> CognitiveLayer1Integration:
    """Get or create global Cognitive Layer 1 integration instance."""
    global _cognitive_layer1
    if _cognitive_layer1 is None or session is not None:
        _cognitive_layer1 = CognitiveLayer1Integration(session=session)
    return _cognitive_layer1
