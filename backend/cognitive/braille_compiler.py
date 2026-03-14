import json
import logging
from typing import Dict, Any, Optional, Tuple
import datetime

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType

logger = logging.getLogger(__name__)

# ==============================================================================
# SECTION 1: THE BRAILLE DICTIONARY (Iteration 3: 64-bit Production Ready)
# ==============================================================================
# Bits 0-7: Target Domain
# Bits 8-15: Action Intent
# Bits 16-23: Target State
# Bits 24-31: Privilege Role
# Bits 32-39: Contextual Session Modifiers (Tokens, Windows, Escalations)

class BrailleDictionary:
    # DOMAIN (Bits 0-7)
    DOMAIN_DATABASE = 1 << 0
    DOMAIN_API      = 1 << 1
    DOMAIN_MEMORY   = 1 << 2
    DOMAIN_NETWORK  = 1 << 3
    DOMAIN_SYS_CONF = 1 << 4
    
    # INTENT (Bits 8-15)
    INTENT_START    = 1 << 8
    INTENT_STOP     = 1 << 9
    INTENT_DELETE   = 1 << 10
    INTENT_QUERY    = 1 << 11
    INTENT_GRANT    = 1 << 12
    INTENT_REPAIR   = 1 << 13
    
    # STATE (Bits 16-23)
    STATE_FAILED    = 1 << 16
    STATE_IMMUTABLE = 1 << 17
    STATE_ACTIVE    = 1 << 18
    STATE_UNKNOWN   = 1 << 19
    STATE_STOPPED   = 1 << 20
    
    # PRIVILEGE ROLE (Bits 24-31)
    PRIV_ADMIN      = 1 << 24
    PRIV_USER       = 1 << 25
    PRIV_SYSTEM     = 1 << 26
    PRIV_GUEST      = 1 << 27

    # SESSION CONTEXT (Bits 32-39)
    CTX_MAINTENANCE = 1 << 32
    CTX_EMERGENCY   = 1 << 33
    CTX_ELEVATED    = 1 << 34
    CTX_NORMAL      = 1 << 35

    @classmethod
    def compile_schema(cls, json_intent: dict, session_context: dict) -> int:
        """
        Takes structured JSON and current environment context and compiles into a 64-bit mask.
        """
        domain_mask = 0
        intent_mask = 0
        state_mask = 0
        priv_mask = 0
        
        # Domain mapping
        domain = json_intent.get("domain", "").lower()
        if domain == "database": domain_mask |= cls.DOMAIN_DATABASE
        elif domain == "api": domain_mask |= cls.DOMAIN_API
        elif domain == "memory": domain_mask |= cls.DOMAIN_MEMORY
        elif domain == "network": domain_mask |= cls.DOMAIN_NETWORK
        elif domain == "sys_conf": domain_mask |= cls.DOMAIN_SYS_CONF
        else: raise ValueError(f"Unknown domain hallucinated: {domain}")
            
        # Intent mapping
        intent = json_intent.get("intent", "").lower()
        if intent == "start": intent_mask |= cls.INTENT_START
        elif intent == "stop": intent_mask |= cls.INTENT_STOP
        elif intent == "delete": intent_mask |= cls.INTENT_DELETE
        elif intent == "query": intent_mask |= cls.INTENT_QUERY
        elif intent == "grant": intent_mask |= cls.INTENT_GRANT
        elif intent == "repair": intent_mask |= cls.INTENT_REPAIR
        else: raise ValueError(f"Unknown intent hallucinated: {intent}")
            
        # State mapping
        state = json_intent.get("target_state", "").lower()
        if state == "failed": state_mask |= cls.STATE_FAILED
        elif state == "immutable": state_mask |= cls.STATE_IMMUTABLE
        elif state == "active": state_mask |= cls.STATE_ACTIVE
        elif state == "unknown": state_mask |= cls.STATE_UNKNOWN
        elif state == "stopped": state_mask |= cls.STATE_STOPPED
        else: raise ValueError(f"Unknown state hallucinated: {state}")
            
        # Role mapping
        priv = json_intent.get("privilege", "").lower()
        if priv == "admin": priv_mask |= cls.PRIV_ADMIN
        elif priv == "user": priv_mask |= cls.PRIV_USER
        elif priv == "system": priv_mask |= cls.PRIV_SYSTEM
        elif priv == "guest": priv_mask |= cls.PRIV_GUEST
        else: raise ValueError(f"Unknown privilege hallucinated: {priv}")

        # Context mapping (Injected safely from environment, NOT user/LLM text)
        is_maintenance = session_context.get("is_maintenance_window", False)
        is_emergency = session_context.get("is_emergency", False)
        is_elevated = session_context.get("has_elevation_token", False)

        ctx_mask = 0
        if is_maintenance: ctx_mask |= cls.CTX_MAINTENANCE
        if is_emergency: ctx_mask |= cls.CTX_EMERGENCY
        if is_elevated: ctx_mask |= cls.CTX_ELEVATED
        
        # Move Privilege into ctx_mask for 256-bit simplification in Z3 Model
        ctx_mask |= priv_mask
            
        return (domain_mask, intent_mask, state_mask, ctx_mask)


# ==============================================================================
# SECTION 2: THE DETERMINISTIC TOPOLOGICAL GUARD (Iteration 4: Z3 SMT Prover)
# ==============================================================================
# Manual rules migrated to Z3 Formal Constraints in `cognitive.physics.bitmask_geometry`

# ==============================================================================
# SECTION 3: THE NLP-TO-BRAILLE COMPILER EDGE
# ==============================================================================

from cognitive.physics.bitmask_geometry import HierarchicalZ3Geometry

class NLPCompilerEdge:
    def __init__(self):
        self.orchestrator = get_llm_orchestrator()
        self.z3_geometry = HierarchicalZ3Geometry()
        
    def translate_to_json(self, natural_language: str, privilege: str = "user") -> Optional[Dict[str, Any]]:
        prompt = f"""
        Translate the user command into a STRICT JSON schema. 
        Focus on semantic intent for the deterministic engine.
        
        Allowed values:
        - domain: ["database", "api", "memory", "network", "sys_conf"]
        - intent: ["start", "stop", "delete", "query", "grant", "repair"]
        - target_state: ["failed", "immutable", "active", "unknown", "stopped"] (What is the CURRENT state of the resource before the action?)
        - privilege: ["admin", "user", "system", "guest"]
        
        User Privilege: {privilege}
        User Command: "{natural_language}"
        
        Output format:
        {{
            "domain": "...",
            "intent": "...",
            "target_state": "...",
            "privilege": "{privilege}"
        }}
        """
        
        try:
            result = self.orchestrator.execute_task(
                prompt=prompt,
                task_type=TaskType.GENERAL,
                require_consensus=False,
                require_verification=False,
                require_grounding=False
            )
            
            if result.success:
                content = result.content.strip()
                if "{" in content and "}" in content:
                    json_str = content[content.find("{"):content.rfind("}")+1]
                    return json.loads(json_str)
            return None
                
        except Exception:
            return None

    def process_command(self, natural_language: str, privilege: str, session_context: dict,
                        use_gate: bool = False) -> Tuple[Optional[tuple], str]:
        json_schema = self.translate_to_json(natural_language, privilege)
        if not json_schema:
            return None, "COMPILE_ERROR_NLP"
            
        try:
            d_val, i_val, s_val, c_val = BrailleDictionary.compile_schema(json_schema, session_context)
        except ValueError as e:
            return None, f"COMPILE_ERROR_HALLUCINATION: {e}"

        if use_gate:
            from cognitive.physics.spindle_gate import get_spindle_gate
            gate = get_spindle_gate()
            verdict = gate.verify(d_val, i_val, s_val, c_val, context=session_context)
            self._last_proof = verdict.proof
            self._last_verdict = verdict
            if verdict.passed and verdict.proof:
                return (d_val, i_val, s_val, c_val), verdict.proof.reason
            else:
                reasons = [r.reason for r in verdict.validator_results if not r.passed]
                return None, f"GATE_REJECTED: {'; '.join(reasons)}"

        proof = self.z3_geometry.verify_action(d_val, i_val, s_val, c_val)
        self._last_proof = proof
        if proof.is_valid:
            return (d_val, i_val, s_val, c_val), proof.reason
        else:
            return None, proof.reason

