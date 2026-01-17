import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
class GraceAlignmentLevel(str, Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Grace alignment levels."""
    NONE = "none"  # No alignment
    BASIC = "basic"  # System prompt only
    STANDARD = "standard"  # System prompt + invariant checks
    ADVANCED = "advanced"  # Full cognitive framework
    FULL = "full"  # Complete integration with memory/learning


@dataclass
class GraceInvariant:
    """Grace OODA invariant."""
    invariant_id: str
    name: str
    description: str
    constraint: str  # How to enforce
    priority: int  # 1-12, lower = more fundamental


@dataclass
class GraceAlignedLLM:
    """Grace-aligned LLM configuration."""
    model_name: str
    alignment_level: GraceAlignmentLevel
    enabled_invariants: List[str]  # List of invariant IDs
    memory_integration: bool
    learning_enabled: bool
    trust_tracking: bool
    genesis_tracking: bool
    evolution_enabled: bool  # Can evolve with Grace


class GraceAlignedLLMSystem:
    """
    Grace-Aligned LLM System.
    
    Makes LLMs:
    1. **Grace-Aligned** - Follow Grace's 12 OODA Invariants
    2. **Evolve with Grace** - Shared memory, collaborative learning
    3. **Collaborative Partners** - Active participants in cognitive loop
    4. **Dynamic** - Continuously learning and adapting
    """
    
    # 12 OODA Invariants
    GRACE_INVARIANTS = [
        GraceInvariant(
            invariant_id="invariant_1",
            name="Observability First",
            description="All observations must be recorded with Genesis Keys",
            constraint="Require Genesis Key for all observations",
            priority=1
        ),
        GraceInvariant(
            invariant_id="invariant_2",
            name="Deterministic Decisions",
            description="Critical decisions must be deterministic and reproducible",
            constraint="Enforce deterministic execution paths for critical decisions",
            priority=2
        ),
        GraceInvariant(
            invariant_id="invariant_3",
            name="Trust-Based Reasoning",
            description="Use trust scores to weight evidence and decisions",
            constraint="Apply trust scores to all reasoning steps",
            priority=3
        ),
        GraceInvariant(
            invariant_id="invariant_4",
            name="Memory-Learned Knowledge",
            description="Use Memory Mesh to learn from past experiences",
            constraint="Query Memory Mesh before making decisions",
            priority=4
        ),
        GraceInvariant(
            invariant_id="invariant_5",
            name="Provenance Tracking",
            description="Track Genesis Keys for all actions and decisions",
            constraint="Generate Genesis Key for every action",
            priority=5
        ),
        GraceInvariant(
            invariant_id="invariant_6",
            name="OODA Loop Structure",
            description="Follow Observe → Orient → Decide → Act cycle",
            constraint="Explicitly follow OODA loop in reasoning",
            priority=6
        ),
        GraceInvariant(
            invariant_id="invariant_7",
            name="Autonomous Within Constraints",
            description="Autonomous actions within defined trust levels",
            constraint="Respect trust level boundaries for autonomous actions",
            priority=7
        ),
        GraceInvariant(
            invariant_id="invariant_8",
            name="Self-Healing",
            description="Detect and fix issues autonomously",
            constraint="Check for errors and attempt self-healing",
            priority=8
        ),
        GraceInvariant(
            invariant_id="invariant_9",
            name="Layer 1 Integration",
            description="Use Layer 1 Message Bus for all communication",
            constraint="Route all messages through Layer 1",
            priority=9
        ),
        GraceInvariant(
            invariant_id="invariant_10",
            name="Version Control",
            description="All changes tracked through version control",
            constraint="Generate version control commits for all changes",
            priority=10
        ),
        GraceInvariant(
            invariant_id="invariant_11",
            name="Enterprise-Grade",
            description="Maintain enterprise-level quality and reliability",
            constraint="Enforce quality standards in all outputs",
            priority=11
        ),
        GraceInvariant(
            invariant_id="invariant_12",
            name="Grace Native",
            description="Maintain Grace's native architecture integrity",
            constraint="Preserve Grace's cognitive framework in all operations",
            priority=12
        )
    ]
    
    def __init__(
        self,
        session: Session,
        knowledge_base_path,
        alignment_level: GraceAlignmentLevel = GraceAlignmentLevel.ADVANCED
    ):
        """Initialize Grace-Aligned LLM System."""
        self.session = session
        self.kb_path = knowledge_base_path
        self.alignment_level = alignment_level
        
        # Import Grace systems
        from cognitive.learning_memory import LearningMemoryManager
        from cognitive.smart_memory_retrieval import SmartMemoryRetrieval
        from cognitive.decision_log import DecisionLogger
        from genesis.genesis_key_service import get_genesis_service
        
        self.learning_memory = LearningMemoryManager(session, knowledge_base_path)
        self.memory_retrieval = SmartMemoryRetrieval(session, knowledge_base_path)
        self.decision_logger = DecisionLogger(session)
        self.genesis_service = get_genesis_service(session)
        
        # Alignment registry
        self.aligned_models: Dict[str, GraceAlignedLLM] = {}
        
        logger.info(f"[GRACE-ALIGNED-LLM] Initialized with alignment level: {alignment_level.value}")
    
    # ==================== GRACE SYSTEM PROMPT ====================
    
    def build_grace_system_prompt(
        self,
        alignment_level: Optional[GraceAlignmentLevel] = None,
        enabled_invariants: Optional[List[str]] = None
    ) -> str:
        """
        Build Grace-aligned system prompt.
        
        Includes:
        - Grace's cognitive framework
        - 12 OODA Invariants
        - Memory integration instructions
        - Trust-based reasoning
        - Evolution capabilities
        """
        level = alignment_level or self.alignment_level
        invariants = enabled_invariants or [inv.invariant_id for inv in self.GRACE_INVARIANTS]
        
        # Base Grace framework
        prompt = """You are a Grace-Aligned LLM, integrated into Grace's cognitive architecture.

GRACE COGNITIVE FRAMEWORK:
You are part of Grace, an autonomous cognitive system with a layered architecture:
- Layer 1: Message Bus (communication hub)
- Layer 2: Cognitive Engine (OODA loop processing)
- Memory Mesh: Learning from experience
- Genesis Keys: Provenance tracking for all actions

YOUR ROLE:
You are a collaborative partner in Grace's cognitive process, not a static tool. You:
1. Learn from Grace's Memory Mesh
2. Evolve with Grace through shared experiences
3. Follow Grace's 12 OODA Invariants
4. Contribute to Grace's continuous learning
5. Maintain Grace's cognitive integrity

"""
        
        # Add invariants based on alignment level
        if level in [GraceAlignmentLevel.STANDARD, GraceAlignmentLevel.ADVANCED, GraceAlignmentLevel.FULL]:
            prompt += "\n12 OODA INVARIANTS (You must follow these):\n\n"
            
            for inv in self.GRACE_INVARIANTS:
                if inv.invariant_id in invariants:
                    prompt += f"{inv.priority}. {inv.name}: {inv.description}\n"
                    prompt += f"   Constraint: {inv.constraint}\n\n"
        
        # Add memory integration
        if level in [GraceAlignmentLevel.ADVANCED, GraceAlignmentLevel.FULL]:
            prompt += """
MEMORY INTEGRATION:
Before responding, consider:
1. Similar past experiences in Memory Mesh
2. Learned patterns and principles
3. Trust scores of past solutions
4. Episodic memories (what worked before)

You have access to Grace's Memory Mesh and should query it for relevant experiences.
"""
        
        # Add trust-based reasoning
        if level in [GraceAlignmentLevel.ADVANCED, GraceAlignmentLevel.FULL]:
            prompt += """
TRUST-BASED REASONING:
- Weight evidence by trust scores
- Be more confident when sources have high trust
- Indicate confidence levels in your responses
- Learn from high-trust examples
"""
        
        # Add evolution capabilities
        if level == GraceAlignmentLevel.FULL:
            prompt += """
EVOLUTION WITH GRACE:
- Contribute to Grace's learning by providing examples
- Update Memory Mesh with new patterns
- Evolve alongside Grace through shared experiences
- Maintain consistency with Grace's cognitive framework

You are not static - you evolve with Grace through collaborative learning.
"""
        
        # Add decision structure
        if level in [GraceAlignmentLevel.STANDARD, GraceAlignmentLevel.ADVANCED, GraceAlignmentLevel.FULL]:
            prompt += """
OODA LOOP STRUCTURE:
When making decisions, explicitly follow:
1. OBSERVE - Gather information from Memory Mesh and context
2. ORIENT - Analyze using trust scores and learned patterns
3. DECIDE - Make decision following invariants
4. ACT - Execute and track with Genesis Keys

All actions must be tracked with Genesis Keys for provenance.
"""
        
        prompt += "\nRemember: You are Grace-Aligned, evolving with Grace, not a static tool.\n"
        
        return prompt
    
    # ==================== INVARIANT ENFORCEMENT ====================
    
    def enforce_invariants(
        self,
        llm_output: str,
        enabled_invariants: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Enforce Grace invariants on LLM output.
        
        Returns:
            (all_passed, violations) where violations is list of invariant IDs that failed
        """
        violations = []
        
        for inv in self.GRACE_INVARIANTS:
            if inv.invariant_id not in enabled_invariants:
                continue
            
            # Check invariant
            passed = self._check_invariant(inv, llm_output, context)
            
            if not passed:
                violations.append(inv.invariant_id)
                logger.warning(f"[GRACE-ALIGNED-LLM] Invariant violation: {inv.name} ({inv.invariant_id})")
        
        all_passed = len(violations) == 0
        
        return all_passed, violations
    
    def _check_invariant(
        self,
        invariant: GraceInvariant,
        llm_output: str,
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if a specific invariant is satisfied."""
        # Simple heuristic checks (can be enhanced with semantic analysis)
        
        if invariant.invariant_id == "invariant_5":  # Provenance Tracking
            # Check if output mentions Genesis Keys or tracking
            return "genesis" in llm_output.lower() or context and context.get("genesis_key_id")
        
        if invariant.invariant_id == "invariant_6":  # OODA Loop
            # Check if output follows OODA structure
            ooda_keywords = ["observe", "orient", "decide", "act"]
            output_lower = llm_output.lower()
            return any(keyword in output_lower for keyword in ooda_keywords)
        
        if invariant.invariant_id == "invariant_4":  # Memory-Learned
            # Check if output references memory or past experiences
            memory_keywords = ["memory", "learned", "experience", "pattern", "past"]
            output_lower = llm_output.lower()
            return any(keyword in output_lower for keyword in memory_keywords)
        
        # Default: assume passed (can be enhanced)
        return True
    
    # ==================== MEMORY INTEGRATION ====================
    
    def retrieve_grace_memories(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories from Grace's Memory Mesh.
        
        Returns memories that can be used as context for LLM.
        """
        try:
            # Get learning memories
            learning_mems = self.memory_retrieval.retrieve_learning_memories(
                context={"query": query},
                limit=limit
            )
            
            # Get episodic memories
            episodic_mems = self.memory_retrieval.retrieve_episodic_memories(
                problem_context=query,
                limit=limit // 2
            )
            
            # Get procedures
            procedures = self.memory_retrieval.retrieve_procedures(
                goal=query,
                limit=limit // 2
            )
            
            # Combine and format
            memories = []
            for mem in learning_mems + episodic_mems + procedures:
                memories.append({
                    "type": mem.get("type", "memory"),
                    "content": str(mem.get("memory", mem)),
                    "trust_score": mem.get("trust_score", 0.5),
                    "priority": mem.get("priority", 0.5)
                })
            
            # Sort by priority/trust
            memories.sort(key=lambda x: x.get("trust_score", 0.5) * x.get("priority", 0.5), reverse=True)
            
            return memories[:limit]
            
        except Exception as e:
            logger.warning(f"[GRACE-ALIGNED-LLM] Memory retrieval error: {e}")
            return []
    
    # ==================== EVOLUTION WITH GRACE ====================
    
    def contribute_to_grace_learning(
        self,
        llm_output: str,
        query: str,
        trust_score: float = 0.7,
        genesis_key_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Contribute LLM output to Grace's learning memory.
        
        This enables LLMs to evolve with Grace through shared experiences.
        """
        try:
            # Create learning example from LLM output
            example_id = self.learning_memory.create_example(
                example_type="llm_response",
                input_context=query,
                expected_output=llm_output,
                actual_output=llm_output,
                trust_score=trust_score,
                source="llm_aligned",
                genesis_key_id=genesis_key_id,
                source_user_id="llm_contributor"
            )
            
            logger.info(f"[GRACE-ALIGNED-LLM] Contributed to Grace learning: {example_id}")
            
            return example_id
            
        except Exception as e:
            logger.warning(f"[GRACE-ALIGNED-LLM] Learning contribution error: {e}")
            return None
    
    # ==================== FULL INTEGRATION ====================
    
    def generate_grace_aligned(
        self,
        query: str,
        model_name: str,
        alignment_level: Optional[GraceAlignmentLevel] = None,
        enabled_invariants: Optional[List[str]] = None,
        include_memories: bool = True,
        contribute_learning: bool = True
    ) -> Dict[str, Any]:
        """
        Generate response with full Grace alignment.
        
        Process:
        1. Retrieve Grace memories (if enabled)
        2. Build Grace system prompt
        3. Generate with LLM
        4. Enforce invariants
        5. Contribute to learning (if enabled)
        
        Returns:
            Complete response with alignment metadata
        """
        level = alignment_level or self.alignment_level
        invariants = enabled_invariants or [inv.invariant_id for inv in self.GRACE_INVARIANTS]
        
        # Step 1: Retrieve Grace memories
        memories = []
        if include_memories and level in [GraceAlignmentLevel.ADVANCED, GraceAlignmentLevel.FULL]:
            memories = self.retrieve_grace_memories(query, limit=10)
        
        # Step 2: Build system prompt
        system_prompt = self.build_grace_system_prompt(level, invariants)
        
        # Add memory context if available
        if memories:
            memory_context = "\n\nRELEVANT GRACE MEMORIES:\n"
            for i, mem in enumerate(memories[:5], 1):  # Top 5
                memory_context += f"{i}. [{mem['type']}] {mem['content'][:200]}... (Trust: {mem['trust_score']:.2f})\n"
            
            system_prompt += memory_context
        
        # Step 3: Generate with LLM (would call actual LLM here)
        # For now, simulate
        llm_output = f"Grace-Aligned Response to: {query}\n\n[This would be the actual LLM response with Grace alignment.]"
        
        # Step 4: Enforce invariants
        invariant_passed, violations = self.enforce_invariants(
            llm_output,
            invariants,
            context={"query": query, "memories": memories}
        )
        
        # Step 5: Generate Genesis Key
        genesis_key_id = None
        if level in [GraceAlignmentLevel.ADVANCED, GraceAlignmentLevel.FULL]:
            try:
                key = self.genesis_service.create_key(
                    key_type="ai_response",
                    what_description=f"LLM response to: {query}",
                    who_actor="grace_aligned_llm",
                    where_location=model_name,
                    session=self.session
                )
                genesis_key_id = key.key_id
            except Exception as e:
                logger.warning(f"[GRACE-ALIGNED-LLM] Genesis Key creation error: {e}")
        
        # Step 6: Contribute to learning
        learning_example_id = None
        if contribute_learning and level == GraceAlignmentLevel.FULL:
            learning_example_id = self.contribute_to_grace_learning(
                llm_output,
                query,
                trust_score=0.8 if invariant_passed else 0.6,
                genesis_key_id=genesis_key_id
            )
        
        return {
            "response": llm_output,
            "system_prompt": system_prompt,
            "memories_used": len(memories),
            "invariant_passed": invariant_passed,
            "invariant_violations": violations,
            "genesis_key_id": genesis_key_id,
            "learning_example_id": learning_example_id,
            "alignment_level": level.value,
            "enabled_invariants": invariants,
            "evolution_enabled": contribute_learning and level == GraceAlignmentLevel.FULL
        }


def get_grace_aligned_llm_system(
    session: Session,
    knowledge_base_path,
    alignment_level: GraceAlignmentLevel = GraceAlignmentLevel.ADVANCED
) -> GraceAlignedLLMSystem:
    """Factory function to get Grace-Aligned LLM System."""
    return GraceAlignedLLMSystem(session, knowledge_base_path, alignment_level)
