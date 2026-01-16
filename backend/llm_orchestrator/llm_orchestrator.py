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
import hashlib

from .multi_llm_client import MultiLLMClient, TaskType
from .repo_access import RepositoryAccessLayer
from .hallucination_guard import HallucinationGuard, VerificationResult
from .cognitive_enforcer import CognitiveEnforcer, CognitiveConstraints
from .proactive_code_intelligence import get_proactive_code_intelligence, ProactiveCodeIntelligence
from .autonomous_fine_tuning_trigger import get_autonomous_fine_tuning_trigger, AutonomousFineTuningTrigger
from .grace_system_prompts import get_grace_system_prompt, enhance_prompt_with_grace_context
from genesis.cognitive_layer1_integration import get_cognitive_layer1_integration, CognitiveLayer1Integration
from cognitive.learning_memory import LearningMemoryManager
from embedding import EmbeddingModel
from confidence_scorer.confidence_scorer import ConfidenceScorer

logger = logging.getLogger(__name__)


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

        # Initialize Cognitive Layer 1 (with OODA + 12 Invariants) and Learning Memory
        self.cognitive_layer1 = get_cognitive_layer1_integration(session=session) if session else None
        self.learning_memory = LearningMemoryManager(
            session=session,
            knowledge_base_path=knowledge_base_path
        ) if session and knowledge_base_path else None

        # Initialize proactive code intelligence (makes LLMs always code-aware)
        self.code_intelligence = get_proactive_code_intelligence(
            multi_llm_client=self.multi_llm,
            repo_access=self.repo_access,
            learning_integration=None  # Will be set after learning_integration is created
        )
        
        # Initialize autonomous fine-tuning trigger (continuous improvement)
        from .learning_integration import get_learning_integration
        learning_integration = get_learning_integration(
            multi_llm_client=self.multi_llm,
            repo_access=self.repo_access,
            learning_memory=self.learning_memory,
            cognitive_layer1=self.cognitive_layer1,
            session=session
        )
        
        from .fine_tuning import get_fine_tuning_system
        fine_tuning_system = get_fine_tuning_system(
            multi_llm_client=self.multi_llm,
            repo_access=self.repo_access,
            learning_integration=learning_integration
        )
        
        self.autonomous_fine_tuning = get_autonomous_fine_tuning_trigger(
            multi_llm_client=self.multi_llm,
            fine_tuning_system=fine_tuning_system,
            repo_access=self.repo_access,
            learning_integration=learning_integration,
            auto_approve=False  # Requires user approval for safety
        )
        
        # Start proactive monitoring
        self.code_intelligence.start_monitoring()
        self.autonomous_fine_tuning.start_monitoring()

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

        # Enhance prompt with code context (makes LLMs always code-aware)
        enhanced_prompt = self.code_intelligence.enhance_prompt_with_code_context(
            prompt=task_request.prompt,
            task_type=task_request.task_type,
            relevant_files=task_request.context_documents
        )
        
        # Always include source code access context if repo_access available
        if self.repo_access:
            # Add source code repository context
            code_context = "\n\n[SOURCE CODE ACCESS - READ-ONLY]\n"
            code_context += "You have read-only access to GRACE's source code repository.\n"
            code_context += "You can read files, search code, and understand the codebase structure.\n"
            code_context += "When discussing code, always reference actual file paths (e.g., backend/path/to/file.py).\n"
            code_context += "Available methods:\n"
            code_context += "- repo_access.read_file(file_path) - Read source files\n"
            code_context += "- repo_access.search_code(pattern) - Search for code patterns\n"
            code_context += "- repo_access.get_file_tree() - Get codebase structure\n"
            code_context += "- repo_access.get_genesis_keys() - Get related Genesis Keys\n"
            code_context += "- repo_access.get_learning_examples() - Get high-trust learning examples\n"
            code_context += "All access is logged and read-only - you cannot modify code.\n"
            
            enhanced_prompt = code_context + "\n\n" + enhanced_prompt
        
        # Enhance prompt with GRACE context (Genesis Keys, trust scores, learning examples)
        # Get relevant learning examples if available
        learning_examples = None
        if self.learning_memory and task_request.enable_learning:
            try:
                # Get high-trust learning examples from learning memory
                # Use repo_access if available, otherwise use learning_memory directly
                if self.repo_access:
                    examples = self.repo_access.get_learning_examples(
                        min_trust_score=0.8,
                        limit=5
                    )
                    learning_examples = [
                        {
                            "content": ex.get("input_context", {}).get("text", "")[:200] if isinstance(ex.get("input_context"), dict) else str(ex.get("input_context", ""))[:200],
                            "trust_score": ex.get("trust_score", 0.8),
                            "example_type": ex.get("example_type", "general")
                        }
                        for ex in examples[:3]  # Top 3
                    ]
                elif hasattr(self.learning_memory, 'get_examples'):
                    # Direct access to learning memory
                    examples = self.learning_memory.get_examples(
                        min_trust_score=0.8,
                        limit=5
                    )
                    learning_examples = [
                        {
                            "content": str(ex.input_context)[:200] if hasattr(ex, 'input_context') else "",
                            "trust_score": ex.trust_score if hasattr(ex, 'trust_score') else 0.8,
                            "example_type": ex.example_type if hasattr(ex, 'example_type') else "general"
                        }
                        for ex in examples[:3] if hasattr(ex, 'trust_score')
                    ]
            except Exception as e:
                logger.warning(f"Could not retrieve learning examples: {e}")
                learning_examples = None
        
        # Enhance with GRACE context
        enhanced_prompt = enhance_prompt_with_grace_context(
            prompt=enhanced_prompt,
            task_type=task_request.task_type.value,
            include_code=task_request.task_type in [
                TaskType.CODE_GENERATION,
                TaskType.CODE_DEBUGGING,
                TaskType.CODE_EXPLANATION,
                TaskType.CODE_REVIEW
            ],
            learning_examples=learning_examples
        )

        # Add GRACE system prompt (makes LLMs GRACE-aligned)
        grace_prompt = get_grace_system_prompt(
            task_type=task_request.task_type.value,
            include_code=task_request.task_type in [
                TaskType.CODE_GENERATION,
                TaskType.CODE_DEBUGGING,
                TaskType.CODE_EXPLANATION,
                TaskType.CODE_REVIEW
            ]
        )
        
        # Combine with user-provided system prompt
        system_prompt = task_request.system_prompt or ""
        if system_prompt:
            system_prompt = f"{grace_prompt}\n\n{system_prompt}"
        else:
            system_prompt = grace_prompt
        
        # Add repository context if grounding required
        if task_request.require_grounding and self.repo_access:
            system_prompt += "\n\nYou have read-only access to the repository. Always reference actual files when making claims about code."

        # Generate response
        response = self.multi_llm.generate(
            prompt=enhanced_prompt,
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
        """Assign Genesis Key to LLM interaction - ALL outputs tracked."""
        logger.info(f"[GENESIS KEY] Assigning Genesis Key for task {task_request.task_id}")

        if not self.cognitive_layer1:
            logger.warning("Cognitive Layer 1 not available - cannot assign Genesis Key")
            return f"GK-LLM-{task_request.task_id}"  # Fallback ID

        try:
            # Create comprehensive metadata for Genesis Key
            metadata = {
                "task_id": task_request.task_id,
                "task_type": task_request.task_type.value,
                "user_id": task_request.user_id,
                "prompt": task_request.prompt[:500],  # Truncate for storage
                "content_length": len(content),
                "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
                "model_used": "auto-selected",  # Will be updated with actual model
                "verification_required": task_request.require_verification,
                "consensus_required": task_request.require_consensus,
                "grounding_required": task_request.require_grounding,
                "timestamp": datetime.now().isoformat()
            }

            # Process through Layer 1 to create Genesis Key
            result = self.cognitive_layer1.process_system_event(
                event_type="llm_interaction",
                event_data={
                    "task_id": task_request.task_id,
                    "prompt": task_request.prompt,
                    "content": content[:2000],  # Truncate for storage
                    "task_type": task_request.task_type.value
                },
                metadata=metadata
            )
            
            genesis_key_id = result.get("genesis_key_id")
            
            if genesis_key_id:
                logger.info(f"[GENESIS KEY] ✓ Assigned: {genesis_key_id}")
                return genesis_key_id
            else:
                logger.warning(f"[GENESIS KEY] Layer 1 did not return Genesis Key ID")
                return f"GK-LLM-{task_request.task_id}"  # Fallback
                
        except Exception as e:
            logger.error(f"[GENESIS KEY] Error assigning Genesis Key: {e}")
            import traceback
            traceback.print_exc()
            return f"GK-LLM-{task_request.task_id}"  # Fallback

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
