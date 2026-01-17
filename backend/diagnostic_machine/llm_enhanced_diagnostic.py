"""
LLM-Enhanced Diagnostic Engine

Enhances the diagnostic engine with:
1. Advanced Grace-Aligned LLM - Pattern-based diagnosis from Memory Mesh
2. Transformation Library - Deterministic fixes for known issues
3. Magma Hierarchical Memory - Issue patterns (Surface→Mantle→Core)
4. OODA Structured Diagnosis - Observe → Orient → Decide → Act
5. Bidirectional LLM Integration - LLMs trigger healing, healing uses LLMs

This makes diagnostics MORE capable than rule-based systems alone.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session
from pathlib import Path

logger = logging.getLogger(__name__)


class LLMIntegrationMode(str, Enum):
    """LLM integration modes for diagnostics."""
    NONE = "none"  # No LLM integration
    PATTERN_MATCHING = "pattern_matching"  # LLM for pattern recognition
    FULL_BIDIRECTIONAL = "full_bidirectional"  # Full bidirectional integration


@dataclass
class LLMDiagnosticResult:
    """LLM-enhanced diagnostic result."""
    anomaly_type: str
    confidence: float
    memory_pattern_matched: Optional[str] = None
    magma_layer: Optional[str] = None  # Surface, Mantle, or Core
    suggested_fix: Optional[str] = None
    deterministic_fix_available: bool = False
    transform_rule_id: Optional[str] = None
    ooda_reasoning: Dict[str, Any] = field(default_factory=dict)


class LLMEnhancedDiagnostic:
    """
    LLM-Enhanced Diagnostic System.
    
    Enhances diagnostics with:
    1. Advanced Grace-Aligned LLM - Pattern-based diagnosis
    2. Transformation Library - Deterministic fixes
    3. Magma Hierarchical Memory - Issue patterns
    4. OODA Structured Diagnosis - Structured reasoning
    5. Bidirectional Integration - LLMs ↔ Healing
    """
    
    def __init__(
        self,
        session: Session,
        knowledge_base_path: Path,
        diagnostic_engine=None,  # Original diagnostic engine
        healing_system=None,  # Self-healing system
        llm_mode: LLMIntegrationMode = LLMIntegrationMode.FULL_BIDIRECTIONAL
    ):
        """Initialize LLM-Enhanced Diagnostic System."""
        self.session = session
        self.kb_path = knowledge_base_path
        self.diagnostic_engine = diagnostic_engine
        self.healing_system = healing_system
        self.llm_mode = llm_mode
        
        # Import Grace systems
        try:
            from backend.llm_orchestrator.advanced_grace_aligned_llm import get_advanced_grace_aligned_llm
            from backend.transform.transformation_library import get_transformation_library
            from cognitive.magma_memory_system import MagmaMemorySystem
            from backend.cognitive.ooda import OODALoop
            
            self.grace_llm = get_advanced_grace_aligned_llm(
                session=session,
                knowledge_base_path=knowledge_base_path,
                max_context_tokens=4096
            )
            self.transform_library = get_transformation_library(session, knowledge_base_path)
            self.magma_system = MagmaMemorySystem(session, knowledge_base_path)
            self.ooda_loop = OODALoop()
            
            logger.info("[LLM-DIAGNOSTIC] Initialized with Grace LLM + Transform Library + Magma")
        except Exception as e:
            logger.warning(f"[LLM-DIAGNOSTIC] Could not initialize all systems: {e}")
            self.grace_llm = None
            self.transform_library = None
            self.magma_system = None
            self.ooda_loop = None
        
        # Issue pattern cache
        self.issue_pattern_cache: Dict[str, Dict] = {}
        
        logger.info(f"[LLM-DIAGNOSTIC] Initialized with llm_mode={llm_mode.value}")
    
    # ==================== BIDIRECTIONAL LLM DIAGNOSIS ====================
    
    def diagnose_with_llm(
        self,
        anomaly_data: Dict[str, Any],
        sensor_data: Optional[Dict] = None,
        use_ooda: bool = True,
        use_magma: bool = True
    ) -> LLMDiagnosticResult:
        """
        Diagnose anomaly using Advanced Grace-Aligned LLM.
        
        Process:
        1. OBSERVE: Gather anomaly data and patterns from Memory Mesh
        2. ORIENT: Analyze with trust-weighted patterns
        3. DECIDE: Match to known patterns or generate diagnosis
        4. ACT: Apply deterministic fixes if available
        
        This enables LLMs → Diagnosis → Healing flow.
        """
        anomaly_type = anomaly_data.get("type", "unknown")
        anomaly_details = anomaly_data.get("details", "")
        
        # OODA: OBSERVE - Gather patterns from Memory Mesh
        memory_patterns = {}
        if use_magma and self.magma_system:
            try:
                # Retrieve issue patterns from Magma
                issue_patterns = self.magma_system.get_memories_by_layer(
                    layer="mantle",  # Patterns layer
                    query=f"{anomaly_type} {anomaly_details}",
                    limit=5
                )
                
                # Get principles from Core layer
                core_principles = self.magma_system.get_memories_by_layer(
                    layer="core",
                    query=f"diagnostic principles {anomaly_type}",
                    limit=3
                )
                
                memory_patterns["mantle"] = issue_patterns
                memory_patterns["core"] = core_principles
                
                logger.info(f"[LLM-DIAGNOSTIC] Retrieved {len(issue_patterns)} patterns from Magma")
            except Exception as e:
                logger.warning(f"[LLM-DIAGNOSTIC] Magma retrieval error: {e}")
        
        # OODA: ORIENT - Analyze with patterns
        if use_ooda and self.ooda_loop:
            try:
                self.ooda_loop.reset()
                self.ooda_loop.observe({
                    "anomaly_type": anomaly_type,
                    "anomaly_details": anomaly_details,
                    "patterns_found": len(memory_patterns.get("mantle", []))
                })
            except Exception as e:
                logger.warning(f"[LLM-DIAGNOSTIC] OODA observe error: {e}")
        
        # Check for deterministic fixes (Transformation Library)
        deterministic_fix = None
        transform_rule_id = None
        if self.transform_library:
            try:
                # Check if anomaly matches a transform rule
                for rule_id, rule in self.transform_library.rules.items():
                    if anomaly_type.lower() in rule.description.lower() or \
                       any(keyword in anomaly_type.lower() for keyword in rule.rule_name.lower().split("_")):
                        
                        # Try to match and fix
                        # (In practice, would check code/state against rule patterns)
                        deterministic_fix = rule.description
                        transform_rule_id = rule_id
                        break
            except Exception as e:
                logger.warning(f"[LLM-DIAGNOSTIC] Transform check error: {e}")
        
        # OODA: DECIDE - Generate diagnosis with LLM if no deterministic match
        llm_diagnosis = None
        confidence = 0.5
        memory_pattern_matched = None
        magma_layer = None
        
        if self.grace_llm and self.llm_mode != LLMIntegrationMode.NONE:
            try:
                # Build diagnostic query
                query = f"Diagnose {anomaly_type} issue: {anomaly_details}"
                
                # Add pattern context
                if memory_patterns:
                    pattern_context = "\n\n=== SIMILAR ISSUES FROM MEMORY ===\n"
                    for layer, patterns in memory_patterns.items():
                        pattern_context += f"\n[{layer.upper()}]:\n"
                        for p in patterns[:3]:
                            pattern_context += f"- {p.get('content', '')[:200]}...\n"
                    query += pattern_context
                
                # Generate diagnosis with Grace LLM
                if use_ooda:
                    result = self.grace_llm.generate_with_grace_cognition(
                        query=query,
                        enable_ooda_structure=True,
                        enable_compression=True
                    )
                else:
                    result = self.grace_llm.generate_with_grace_cognition(query=query)
                
                llm_diagnosis = result.get("response", "")
                
                # Extract matched pattern if any
                if memory_patterns:
                    # Use highest trust pattern
                    all_patterns = memory_patterns.get("mantle", []) + memory_patterns.get("core", [])
                    if all_patterns:
                        best_pattern = max(all_patterns, key=lambda p: p.get("trust_score", 0.5))
                        memory_pattern_matched = best_pattern.get("content", "")[:200]
                        magma_layer = "core" if best_pattern in memory_patterns.get("core", []) else "mantle"
                        confidence = best_pattern.get("trust_score", 0.7)
                
                logger.info(f"[LLM-DIAGNOSTIC] Generated LLM diagnosis with confidence {confidence:.2f}")
            except Exception as e:
                logger.warning(f"[LLM-DIAGNOSTIC] LLM diagnosis error: {e}")
        
        # OODA: ACT - Prepare action
        if use_ooda and self.ooda_loop:
            try:
                self.ooda_loop.decide({
                    "anomaly_type": anomaly_type,
                    "diagnosis": llm_diagnosis or deterministic_fix,
                    "fix_available": deterministic_fix is not None,
                    "confidence": confidence
                })
                self.ooda_loop.act(lambda: None)  # Placeholder action
            except Exception as e:
                logger.warning(f"[LLM-DIAGNOSTIC] OODA act error: {e}")
        
        # Build result
        result = LLMDiagnosticResult(
            anomaly_type=anomaly_type,
            confidence=confidence,
            memory_pattern_matched=memory_pattern_matched,
            magma_layer=magma_layer,
            suggested_fix=llm_diagnosis or deterministic_fix,
            deterministic_fix_available=deterministic_fix is not None,
            transform_rule_id=transform_rule_id,
            ooda_reasoning={
                "observe": {"patterns_found": len(memory_patterns.get("mantle", []))},
                "orient": {"confidence": confidence},
                "decide": {"fix_available": deterministic_fix is not None},
                "act": {"ready": True}
            } if use_ooda else {}
        )
        
        logger.info(
            f"[LLM-DIAGNOSTIC] Diagnosis complete: {anomaly_type}, "
            f"confidence={confidence:.2f}, fix_available={deterministic_fix is not None}"
        )
        
        return result
    
    # ==================== LLM → HEALING TRIGGER ====================
    
    def trigger_healing_from_llm(
        self,
        diagnostic_result: LLMDiagnosticResult,
        anomaly_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trigger self-healing from LLM diagnosis.
        
        This enables: LLMs → Diagnosis → Healing
        """
        if not self.healing_system:
            logger.warning("[LLM-DIAGNOSTIC] No healing system available")
            return {"success": False, "reason": "no_healing_system"}
        
        try:
            # Check if deterministic fix available
            if diagnostic_result.deterministic_fix_available and diagnostic_result.transform_rule_id:
                # Use deterministic fix
                logger.info(f"[LLM-DIAGNOSTIC] Using deterministic fix: {diagnostic_result.transform_rule_id}")
                
                # Apply transform (would need code/state context)
                # This would be integrated with healing system's fix application
                healing_result = {
                    "action": "apply_deterministic_fix",
                    "rule_id": diagnostic_result.transform_rule_id,
                    "confidence": diagnostic_result.confidence,
                    "llm_triggered": True
                }
                
            elif diagnostic_result.suggested_fix:
                # Use LLM-suggested fix
                logger.info(f"[LLM-DIAGNOSTIC] Using LLM-suggested fix")
                
                # Trigger healing with LLM suggestion
                healing_result = self.healing_system.execute_healing(
                    anomaly_type=diagnostic_result.anomaly_type,
                    anomaly_details=anomaly_data.get("details", ""),
                    suggested_fix=diagnostic_result.suggested_fix,
                    confidence=diagnostic_result.confidence,
                    llm_guided=True
                )
                
            else:
                # No fix available
                healing_result = {
                    "action": "no_fix_available",
                    "anomaly_type": diagnostic_result.anomaly_type,
                    "confidence": diagnostic_result.confidence
                }
            
            logger.info(f"[LLM-DIAGNOSTIC] Healing triggered from LLM diagnosis")
            return healing_result
            
        except Exception as e:
            logger.error(f"[LLM-DIAGNOSTIC] Healing trigger error: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== HEALING → LLM LEARNING ====================
    
    def learn_from_healing_outcome(
        self,
        healing_result: Dict[str, Any],
        diagnostic_result: LLMDiagnosticResult,
        anomaly_data: Dict[str, Any]
    ):
        """
        Learn from healing outcome and update Memory Mesh.
        
        This enables: Healing → Learning → LLM Memory → Better Future Diagnosis
        """
        try:
            if not self.grace_llm or not self.grace_llm.base_grace_llm:
                return
            
            # Build learning context
            learning_context = f"""
Anomaly Type: {diagnostic_result.anomaly_type}
Anomaly Details: {anomaly_data.get('details', '')}
Diagnosis: {diagnostic_result.suggested_fix or 'N/A'}
Healing Action: {healing_result.get('action', 'N/A')}
Success: {healing_result.get('success', False)}
"""
            
            # Contribute to Grace's learning
            if healing_result.get("success"):
                trust_score = diagnostic_result.confidence
            else:
                trust_score = 0.3  # Lower trust for failed fixes
            
            learning_id = self.grace_llm.base_grace_llm.contribute_to_grace_learning(
                llm_output=learning_context,
                query=f"Diagnostic pattern: {diagnostic_result.anomaly_type}",
                trust_score=trust_score,
                genesis_key_id=healing_result.get("genesis_key_id")
            )
            
            logger.info(f"[LLM-DIAGNOSTIC] Learned from healing outcome: {learning_id}")
            
        except Exception as e:
            logger.warning(f"[LLM-DIAGNOSTIC] Learning from outcome error: {e}")
    
    # ==================== FULL BIDIRECTIONAL CYCLE ====================
    
    def diagnose_and_heal_bidirectional(
        self,
        anomaly_data: Dict[str, Any],
        sensor_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Complete bidirectional cycle: LLM Diagnosis → Healing → Learning → LLM Memory.
        
        Flow:
        1. LLM diagnoses anomaly (using Memory Mesh patterns)
        2. Healing system fixes issue (guided by LLM diagnosis)
        3. Outcome contributes to Memory Mesh (for future LLM diagnosis)
        4. Cycle repeats with better memory patterns
        
        This creates compounding improvement: More healing → More learning → Better diagnosis
        """
        # Step 1: LLM Diagnosis
        diagnostic_result = self.diagnose_with_llm(
            anomaly_data=anomaly_data,
            sensor_data=sensor_data,
            use_ooda=True,
            use_magma=True
        )
        
        # Step 2: Trigger Healing from LLM Diagnosis
        healing_result = self.trigger_healing_from_llm(
            diagnostic_result=diagnostic_result,
            anomaly_data=anomaly_data
        )
        
        # Step 3: Learn from Outcome
        if healing_result.get("success") or "action" in healing_result:
            self.learn_from_healing_outcome(
                healing_result=healing_result,
                diagnostic_result=diagnostic_result,
                anomaly_data=anomaly_data
            )
        
        # Build complete result
        result = {
            "diagnosis": {
                "anomaly_type": diagnostic_result.anomaly_type,
                "confidence": diagnostic_result.confidence,
                "memory_pattern_matched": diagnostic_result.memory_pattern_matched,
                "magma_layer": diagnostic_result.magma_layer,
                "deterministic_fix_available": diagnostic_result.deterministic_fix_available
            },
            "healing": healing_result,
            "learning": {
                "contributed_to_memory": healing_result.get("success", False) or "action" in healing_result,
                "trust_score": diagnostic_result.confidence
            },
            "bidirectional": True,
            "cycle_complete": True
        }
        
        logger.info(
            f"[LLM-DIAGNOSTIC] Bidirectional cycle complete: "
            f"diagnosis={diagnostic_result.anomaly_type}, "
            f"healing={healing_result.get('action', 'none')}, "
            f"learning={'yes' if result['learning']['contributed_to_memory'] else 'no'}"
        )
        
        return result


def get_llm_enhanced_diagnostic(
    session: Session,
    knowledge_base_path: Path,
    diagnostic_engine=None,
    healing_system=None,
    llm_mode: LLMIntegrationMode = LLMIntegrationMode.FULL_BIDIRECTIONAL
) -> LLMEnhancedDiagnostic:
    """Factory function to get LLM-Enhanced Diagnostic System."""
    return LLMEnhancedDiagnostic(
        session=session,
        knowledge_base_path=knowledge_base_path,
        diagnostic_engine=diagnostic_engine,
        healing_system=healing_system,
        llm_mode=llm_mode
    )
