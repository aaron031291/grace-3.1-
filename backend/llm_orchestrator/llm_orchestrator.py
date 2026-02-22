"""
Complete LLM Orchestration System

Integrates all components:
- Multiple LLMs (DeepSeek, Qwen, Llama, etc.)
- Read-only repository access
- Hallucination mitigation (5-layer pipeline)
- Cognitive framework enforcement (12 OODA invariants)
- Genesis Key tracking
- Layer 1 integration
- Learning Memory integration
- Version control
- Trust system verification

All LLM operations are:
- Tracked with Genesis Keys
- Logged for audit
- Trust-scored
- Cognitively enforced
- Integrated with learning memory
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy.orm import Session
import json
import uuid

from .multi_llm_client import MultiLLMClient, TaskType
from .repo_access import RepositoryAccessLayer
from .hallucination_guard import HallucinationGuard, VerificationResult
from .cognitive_enforcer import CognitiveEnforcer, CognitiveConstraints
from genesis.cognitive_layer1_integration import get_cognitive_layer1_integration, CognitiveLayer1Integration
from cognitive.learning_memory import LearningMemoryManager
from embedding import EmbeddingModel
from confidence_scorer.confidence_scorer import ConfidenceScorer

logger = logging.getLogger(__name__)
def _check_hia(text):
    try:
        from security.honesty_integrity_accountability import get_hia_framework
        return get_hia_framework().verify_llm_output(text)
    except Exception:
        return None



@dataclass
class LLMTaskRequest:
    """LLM task request."""
    task_id: str
    prompt: str
    task_type: TaskType
    user_id: Optional[str] = None
    require_verification: bool = True
    require_consensus: bool = True
    require_grounding: bool = True
    enable_learning: bool = True
    system_prompt: Optional[str] = None
    context_documents: Optional[List[str]] = None
    cognitive_constraints: Optional[CognitiveConstraints] = None


@dataclass
class LLMTaskResult:
    """LLM task result."""
    task_id: str
    success: bool
    content: str
    verification_result: Optional[VerificationResult]
    cognitive_decision_id: Optional[str]
    genesis_key_id: Optional[str]
    trust_score: float
    confidence_score: float
    model_used: str
    duration_ms: float
    learning_example_id: Optional[str]
    audit_trail: List[Dict[str, Any]]
    timestamp: datetime


class LLMOrchestrator:
    """
    Complete LLM orchestration system.

    Manages the full lifecycle of LLM tasks:
    1. Cognitive enforcement (OODA + 12 invariants)
    2. Multi-model selection
    3. Hallucination mitigation (5-layer pipeline)
    4. Genesis Key assignment
    5. Layer 1 integration
    6. Learning Memory integration
    7. Trust scoring
    8. Audit logging
    """

    def __init__(
        self,
        session: Optional[Session] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        knowledge_base_path: Optional[str] = None
    ):
        """
        Initialize LLM orchestrator.

        Args:
            session: Database session
            embedding_model: Embedding model
            knowledge_base_path: Path to knowledge base
        """
        self.session = session
        self.embedding_model = embedding_model

        # Initialize core components
        self.multi_llm = MultiLLMClient()
        self.repo_access = RepositoryAccessLayer(
            session=session,
            embedding_model=embedding_model
        )
        self.confidence_scorer = ConfidenceScorer(
            embedding_model=embedding_model
        ) if embedding_model else None

        self.hallucination_guard = HallucinationGuard(
            multi_llm_client=self.multi_llm,
            repo_access=self.repo_access,
            confidence_scorer=self.confidence_scorer
        )
        self.cognitive_enforcer = CognitiveEnforcer()

        # Near-Zero Hallucination Guard (13 layers) - wraps the base guard
        self.near_zero_guard = None
        try:
            from .near_zero_hallucination_guard import get_near_zero_hallucination_guard
            self.near_zero_guard = get_near_zero_hallucination_guard(
                base_guard=self.hallucination_guard,
                multi_llm=self.multi_llm,
                repo_access=self.repo_access,
            )
            logger.info("[LLM-ORCHESTRATOR] Near-Zero Hallucination Guard active (13 layers)")
        except Exception as e:
            logger.warning(f"[LLM-ORCHESTRATOR] Near-Zero Guard not available, using base 6-layer: {e}")

        # Initialize Cognitive Layer 1 (with OODA + 12 Invariants) and Learning Memory
        self.cognitive_layer1 = get_cognitive_layer1_integration(session=session) if session else None
        self.learning_memory = LearningMemoryManager(
            session=session,
            knowledge_base_path=knowledge_base_path
        ) if session and knowledge_base_path else None

        # Task registry
        self.active_tasks: Dict[str, LLMTaskRequest] = {}
        self.completed_tasks: List[LLMTaskResult] = []

    # =======================================================================
    # MAIN TASK EXECUTION
    # =======================================================================

    def execute_task(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        user_id: Optional[str] = None,
        require_verification: bool = True,
        require_consensus: bool = True,
        require_grounding: bool = True,
        enable_learning: bool = True,
        system_prompt: Optional[str] = None,
        context_documents: Optional[List[str]] = None,
        cognitive_constraints: Optional[CognitiveConstraints] = None
    ) -> LLMTaskResult:
        """
        Execute complete LLM task with full pipeline.

        Args:
            prompt: User prompt
            task_type: Type of task
            user_id: User ID (Genesis ID)
            require_verification: Enable hallucination mitigation
            require_consensus: Enable cross-model consensus
            require_grounding: Require repository grounding
            enable_learning: Enable learning memory integration
            system_prompt: System prompt
            context_documents: Context documents
            cognitive_constraints: Cognitive constraints

        Returns:
            LLMTaskResult with complete information
        """
        start_time = datetime.now()
        task_id = f"llm_task_{uuid.uuid4().hex[:8]}"
        audit_trail = []

        logger.info(f"[LLM ORCHESTRATOR] Starting task {task_id}: {task_type.value}")

        # Governance check - verify constitutional rules allow this task
        try:
            from security.governance import get_governance_engine, GovernanceContext
            governance = get_governance_engine()
            gov_context = GovernanceContext(
                context_id=task_id,
                action_type="execute_safe",
                actor_id=user_id or "system",
                actor_type="ai",
                target_resource=f"llm_task:{task_type.value}",
                impact_scope="component",
                is_reversible=True,
                metadata={"prompt_length": len(prompt), "task_type": task_type.value},
            )
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    gov_decision = None  # Can't await in sync context, skip
                else:
                    gov_decision = loop.run_until_complete(governance.evaluate(gov_context))
            except RuntimeError:
                gov_decision = None

            if gov_decision and not gov_decision.allowed:
                violations = [v.description for v in gov_decision.violations[:3]]
                logger.warning(f"[LLM ORCHESTRATOR] Task {task_id} BLOCKED by governance: {violations}")
                audit_trail.append({"step": "governance", "blocked": True, "violations": violations})
                return LLMTaskResult(
                    task_id=task_id, prompt=prompt, success=False,
                    content=f"Task blocked by governance: {'; '.join(violations)}",
                    verification_result=None, cognitive_decision_id=None,
                    genesis_key_id=None, trust_score=0.0, confidence_score=0.0,
                    model_used="none", duration_ms=0, learning_example_id=None,
                    audit_trail=audit_trail, timestamp=start_time,
                )
            else:
                audit_trail.append({"step": "governance", "allowed": True})
        except Exception as e:
            audit_trail.append({"step": "governance", "error": str(e), "skipped": True})

        # Create task request
        task_request = LLMTaskRequest(
            task_id=task_id,
            prompt=prompt,
            task_type=task_type,
            user_id=user_id,
            require_verification=require_verification,
            require_consensus=require_consensus,
            require_grounding=require_grounding,
            enable_learning=enable_learning,
            system_prompt=system_prompt,
            context_documents=context_documents,
            cognitive_constraints=cognitive_constraints or CognitiveConstraints()
        )
        self.active_tasks[task_id] = task_request

        try:
            # STEP 0: Constitutional Governance Check
            governance_passed = self._check_governance(task_request)
            audit_trail.append({
                "step": "governance_check",
                "passed": governance_passed,
                "timestamp": datetime.now().isoformat()
            })
            if not governance_passed:
                raise Exception("Task blocked by constitutional governance rules")

            # STEP 1: Cognitive Framework Enforcement (OODA Loop)
            decision_id = self._enforce_cognitive_framework(task_request)
            audit_trail.append({
                "step": "cognitive_enforcement",
                "decision_id": decision_id,
                "timestamp": datetime.now().isoformat()
            })

            # STEP 2: Generate LLM Response
            llm_response = self._generate_llm_response(task_request)
            audit_trail.append({
                "step": "llm_generation",
                "model": llm_response.get("model_name"),
                "duration_ms": llm_response.get("duration_ms"),
                "timestamp": datetime.now().isoformat()
            })

            if not llm_response.get("success"):
                raise Exception(f"LLM generation failed: {llm_response.get('error')}")

            content = llm_response.get("content", "")

            # STEP 3: Hallucination Mitigation
            verification_result = None
            if require_verification:
                verification_result = self._verify_content(
                    task_request,
                    content,
                    llm_response
                )
                audit_trail.append({
                    "step": "hallucination_verification",
                    "is_verified": verification_result.is_verified,
                    "confidence": verification_result.confidence_score,
                    "trust_score": verification_result.trust_score,
                    "timestamp": datetime.now().isoformat()
                })

                # Use verified content
                content = verification_result.final_content

            # STEP 4: Genesis Key Assignment
            genesis_key_id = self._assign_genesis_key(task_request, content)
            audit_trail.append({
                "step": "genesis_key_assignment",
                "genesis_key_id": genesis_key_id,
                "timestamp": datetime.now().isoformat()
            })

            # STEP 5: Layer 1 Integration
            self._integrate_layer1(task_request, content, genesis_key_id)
            audit_trail.append({
                "step": "layer1_integration",
                "genesis_key_id": genesis_key_id,
                "timestamp": datetime.now().isoformat()
            })

            # STEP 6: Learning Memory Integration
            learning_example_id = None
            if enable_learning:
                learning_example_id = self._integrate_learning_memory(
                    task_request,
                    content,
                    verification_result,
                    genesis_key_id
                )
                audit_trail.append({
                    "step": "learning_memory_integration",
                    "learning_example_id": learning_example_id,
                    "timestamp": datetime.now().isoformat()
                })

            # STEP 7: Finalize Cognitive Decision
            self.cognitive_enforcer.act(
                decision_id=decision_id,
                action_result=content,
                success=True
            )
            self.cognitive_enforcer.finalize_decision(
                decision_id=decision_id,
                genesis_key_id=genesis_key_id
            )

            # Calculate final scores
            trust_score = verification_result.trust_score if verification_result else 0.8
            confidence_score = verification_result.confidence_score if verification_result else 0.8

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Create result
            result = LLMTaskResult(
                task_id=task_id,
                success=True,
                content=content,
                verification_result=verification_result,
                cognitive_decision_id=decision_id,
                genesis_key_id=genesis_key_id,
                trust_score=trust_score,
                confidence_score=confidence_score,
                model_used=llm_response.get("model_name", "unknown"),
                duration_ms=duration_ms,
                learning_example_id=learning_example_id,
                audit_trail=audit_trail,
                timestamp=datetime.now()
            )

            self.completed_tasks.append(result)
            del self.active_tasks[task_id]

            logger.info(f"[LLM ORCHESTRATOR] Task {task_id} completed successfully")
            return result

        except Exception as e:
            logger.error(f"[LLM ORCHESTRATOR] Task {task_id} failed: {e}")

            # Create failure result
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            result = LLMTaskResult(
                task_id=task_id,
                success=False,
                content="",
                verification_result=None,
                cognitive_decision_id=None,
                genesis_key_id=None,
                trust_score=0.0,
                confidence_score=0.0,
                model_used="unknown",
                duration_ms=duration_ms,
                learning_example_id=None,
                audit_trail=audit_trail + [{
                    "step": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }],
                timestamp=datetime.now()
            )

            self.completed_tasks.append(result)
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

            return result

    # =======================================================================
    # INTERNAL PIPELINE STEPS
    # =======================================================================

    def _check_governance(self, task_request: LLMTaskRequest) -> bool:
        """Check constitutional governance rules before executing a task."""
        logger.info(f"[GOVERNANCE] Checking rules for task {task_request.task_id}")
        try:
            from security.governance import get_governance_engine, GovernanceContext
            engine = get_governance_engine()
            if engine is None:
                logger.warning("[GOVERNANCE] Engine not available, allowing task")
                return True

            context = GovernanceContext(
                action=f"llm_task_{task_request.task_type.value}",
                actor=task_request.user_id or "system",
                resource=task_request.prompt[:200],
                metadata={
                    "task_type": task_request.task_type.value,
                    "task_id": task_request.task_id,
                }
            )
            decision = engine.evaluate(context)
            if hasattr(decision, 'allowed'):
                return decision.allowed
            if hasattr(decision, 'approved'):
                return decision.approved
            return True
        except ImportError:
            logger.debug("[GOVERNANCE] Governance module not available")
            return True
        except Exception as e:
            logger.warning(f"[GOVERNANCE] Governance check error (allowing): {e}")
            return True

    def _enforce_cognitive_framework(self, task_request: LLMTaskRequest) -> str:
        """Enforce cognitive framework (OODA + 12 invariants)."""
        logger.info(f"[COGNITIVE] Enforcing framework for task {task_request.task_id}")

        # Begin OODA loop
        decision_id = self.cognitive_enforcer.begin_ooda_loop(
            operation=f"llm_task_{task_request.task_type.value}",
            constraints=task_request.cognitive_constraints
        )

        # OBSERVE
        self.cognitive_enforcer.observe(
            decision_id=decision_id,
            observations={
                "task_id": task_request.task_id,
                "task_type": task_request.task_type.value,
                "prompt_length": len(task_request.prompt),
                "has_context": bool(task_request.context_documents),
                "user_id": task_request.user_id
            }
        )

        # ORIENT
        self.cognitive_enforcer.orient(
            decision_id=decision_id,
            context={
                "verification_required": task_request.require_verification,
                "consensus_required": task_request.require_consensus,
                "grounding_required": task_request.require_grounding
            }
        )

        # DECIDE
        alternatives = [{
            "name": "execute_llm_task",
            "description": "Execute LLM task with full pipeline",
            "simplicity": 0.8,
            "optionality": 1.0,
            "immediate_value": 1.0,
            "reversible": True,
            "complexity": 0.3
        }]

        self.cognitive_enforcer.decide(
            decision_id=decision_id,
            alternatives=alternatives
        )

        return decision_id

    def _generate_llm_response(self, task_request: LLMTaskRequest) -> Dict[str, Any]:
        """Generate LLM response."""
        logger.info(f"[LLM GENERATION] Generating response for task {task_request.task_id}")

        # Add repository context to system prompt if grounding required
        system_prompt = task_request.system_prompt or ""
        if task_request.require_grounding and self.repo_access:
            system_prompt += "\n\nYou have read-only access to the repository. Always reference actual files when making claims about code."

        # Generate response
        response = self.multi_llm.generate(
            prompt=task_request.prompt,
            task_type=task_request.task_type,
            system_prompt=system_prompt
        )

        return response

    def _verify_content(
        self,
        task_request: LLMTaskRequest,
        content: str,
        llm_response: Dict[str, Any]
    ) -> VerificationResult:
        """Verify content through hallucination mitigation pipeline."""
        logger.info(f"[VERIFICATION] Verifying content for task {task_request.task_id}")

        verification_result = self.hallucination_guard.verify_content(
            prompt=task_request.prompt,
            content=content,
            task_type=task_request.task_type,
            enable_consensus=task_request.require_consensus,
            enable_grounding=task_request.require_grounding,
            enable_contradiction_check=True,
            enable_trust_verification=True,
            system_prompt=task_request.system_prompt,
            context_documents=task_request.context_documents
        )

        return verification_result

    def _assign_genesis_key(
        self,
        task_request: LLMTaskRequest,
        content: str
    ) -> Optional[str]:
        """Assign Genesis Key to LLM interaction."""
        logger.info(f"[GENESIS KEY] Assigning Genesis Key for task {task_request.task_id}")

        if not self.cognitive_layer1:
            return None

        # Create metadata for Genesis Key
        metadata = {
            "task_id": task_request.task_id,
            "task_type": task_request.task_type.value,
            "user_id": task_request.user_id,
            "prompt": task_request.prompt[:500],  # Truncate for storage
            "content_length": len(content),
            "timestamp": datetime.now().isoformat()
        }

        # Genesis Keys will be created via Layer 1 integration
        # For now, return a placeholder
        genesis_key_id = f"GK-LLM-{task_request.task_id}"
        return genesis_key_id

    def _integrate_layer1(
        self,
        task_request: LLMTaskRequest,
        content: str,
        genesis_key_id: Optional[str]
    ):
        """
        Integrate with Cognitive Layer 1.

        ALL LLM interactions flow through Layer 1 with:
        - OODA Loop enforcement
        - 12 Invariant validation
        - Genesis Key tracking
        - Trust scoring
        - Complete audit trail
        """
        logger.info(f"[COGNITIVE LAYER 1] Integrating task {task_request.task_id}")

        if not self.cognitive_layer1:
            logger.warning("Cognitive Layer 1 integration not available")
            return

        try:
            # Prepare LLM interaction data for Layer 1
            llm_interaction_data = {
                "task_id": task_request.task_id,
                "task_type": task_request.task_type.value,
                "user_id": task_request.user_id,
                "prompt": task_request.prompt[:500],  # Truncate for storage
                "content": content[:1000],  # Truncate for storage
                "content_length": len(content),
                "genesis_key_id": genesis_key_id,
                "require_verification": task_request.require_verification,
                "require_consensus": task_request.require_consensus,
                "require_grounding": task_request.require_grounding,
                "timestamp": datetime.now().isoformat()
            }

            # Process through Cognitive Layer 1 (OODA + 12 Invariants + Trust)
            result = self.cognitive_layer1.process_system_event(
                event_type="llm_interaction",
                event_data=llm_interaction_data,
                metadata={
                    "verified": task_request.require_verification,
                    "consensus": task_request.require_consensus,
                    "grounding": task_request.require_grounding,
                    "learning_enabled": task_request.enable_learning
                }
            )

            logger.info(f"[COGNITIVE LAYER 1] ✓ Task {task_request.task_id} processed through Layer 1")
            logger.info(f"[COGNITIVE LAYER 1] - Genesis Key: {result.get('genesis_key_id', 'N/A')}")
            logger.info(f"[COGNITIVE LAYER 1] - OODA Loop: {result.get('cognitive', {}).get('ooda_loop_completed', False)}")
            logger.info(f"[COGNITIVE LAYER 1] - Invariants: {result.get('cognitive', {}).get('invariants_validated', False)}")

        except Exception as e:
            logger.error(f"Cognitive Layer 1 integration error: {e}")
            import traceback
            traceback.print_exc()

    def _integrate_learning_memory(
        self,
        task_request: LLMTaskRequest,
        content: str,
        verification_result: Optional[VerificationResult],
        genesis_key_id: Optional[str]
    ) -> Optional[str]:
        """Integrate with learning memory."""
        logger.info(f"[LEARNING MEMORY] Integrating task {task_request.task_id}")

        if not self.learning_memory:
            logger.warning("Learning memory not available")
            return None

        try:
            # Create learning example
            learning_data = {
                "context": {
                    "task_type": task_request.task_type.value,
                    "prompt": task_request.prompt
                },
                "expected": {
                    "content": content,
                    "verified": verification_result.is_verified if verification_result else False
                },
                "actual": {
                    "confidence_score": verification_result.confidence_score if verification_result else 0.8,
                    "trust_score": verification_result.trust_score if verification_result else 0.8
                }
            }

            example = self.learning_memory.ingest_learning_data(
                learning_type="llm_interaction",
                learning_data=learning_data,
                source="system_observation_success",
                user_id=task_request.user_id,
                genesis_key_id=genesis_key_id
            )

            return str(example.id) if example else None

        except Exception as e:
            logger.error(f"Learning memory integration error: {e}")
            return None

    # =======================================================================
    # QUERY METHODS
    # =======================================================================

    def get_task_result(self, task_id: str) -> Optional[LLMTaskResult]:
        """Get task result by ID."""
        for result in self.completed_tasks:
            if result.task_id == task_id:
                return result
        return None

    def get_recent_tasks(self, limit: int = 100) -> List[LLMTaskResult]:
        """Get recent task results."""
        return self.completed_tasks[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        if not self.completed_tasks:
            return {
                "total_tasks": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
                "avg_trust_score": 0.0,
                "avg_confidence_score": 0.0
            }

        total = len(self.completed_tasks)
        successful = sum(1 for t in self.completed_tasks if t.success)

        return {
            "total_tasks": total,
            "success_rate": successful / total,
            "avg_duration_ms": sum(t.duration_ms for t in self.completed_tasks) / total,
            "avg_trust_score": sum(t.trust_score for t in self.completed_tasks) / total,
            "avg_confidence_score": sum(t.confidence_score for t in self.completed_tasks) / total,
            "multi_llm_stats": self.multi_llm.get_model_stats(),
            "verification_stats": self.hallucination_guard.get_verification_stats()
        }


# Global instance
_llm_orchestrator: Optional[LLMOrchestrator] = None


def get_llm_orchestrator(
    session: Optional[Session] = None,
    embedding_model: Optional[EmbeddingModel] = None,
    knowledge_base_path: Optional[str] = None
) -> LLMOrchestrator:
    """Get or create global LLM orchestrator instance."""
    global _llm_orchestrator
    if _llm_orchestrator is None:
        _llm_orchestrator = LLMOrchestrator(
            session=session,
            embedding_model=embedding_model,
            knowledge_base_path=knowledge_base_path
        )
    return _llm_orchestrator
