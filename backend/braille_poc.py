import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("BrailleCompiler")

# ==============================================================================
# SECTION 1: THE BRAILLE DICTIONARY (16-bit Proof of Concept)
# ==============================================================================
# We define a strict 16-bit spatial grid. 
# 
# Bits 0-3: Target Domain
# Bits 4-7: Action Intent
# Bits 8-11: Target State
# Bits 12-15: Privilege Level

class BrailleDictionary:
    # DOMAIN (Bits 0-3)
    DOMAIN_DATABASE = 0b0000_0000_0000_0001
    DOMAIN_API      = 0b0000_0000_0000_0010
    DOMAIN_MEMORY   = 0b0000_0000_0000_0100
    
    # INTENT (Bits 4-7)
    INTENT_START    = 0b0000_0000_0001_0000
    INTENT_DELETE   = 0b0000_0000_0010_0000
    INTENT_QUERY    = 0b0000_0000_0100_0000
    
    # STATE (Bits 8-11)
    STATE_FAILED    = 0b0000_0001_0000_0000
    STATE_IMMUTABLE = 0b0000_0010_0000_0000
    STATE_ACTIVE    = 0b0000_0100_0000_0000
    
    # PRIVILEGE (Bits 12-15)
    PRIV_ADMIN      = 0b0001_0000_0000_0000
    PRIV_USER       = 0b0010_0000_0000_0000

    @classmethod
    def compile_schema(cls, json_intent: dict) -> int:
        """
        Takes structured JSON from the NLP wrapper and strictly compiles it 
        into a deterministic bitmask.
        """
        bitmask = 0b0000_0000_0000_0000
        
        # Parse Domain
        domain = json_intent.get("domain", "").lower()
        if domain == "database": bitmask |= cls.DOMAIN_DATABASE
        elif domain == "api": bitmask |= cls.DOMAIN_API
        elif domain == "memory": bitmask |= cls.DOMAIN_MEMORY
        else: raise ValueError(f"Unknown domain hallucinated: {domain}")
            
        # Parse Intent
        intent = json_intent.get("intent", "").lower()
        if intent == "start": bitmask |= cls.INTENT_START
        elif intent == "delete": bitmask |= cls.INTENT_DELETE
        elif intent == "query": bitmask |= cls.INTENT_QUERY
        else: raise ValueError(f"Unknown intent hallucinated: {intent}")
            
        # Parse State
        state = json_intent.get("target_state", "").lower()
        if state == "failed": bitmask |= cls.STATE_FAILED
        elif state == "immutable": bitmask |= cls.STATE_IMMUTABLE
        elif state == "active": bitmask |= cls.STATE_ACTIVE
        else: raise ValueError(f"Unknown state hallucinated: {state}")
            
        # Parse Privilege
        priv = json_intent.get("privilege", "").lower()
        if priv == "admin": bitmask |= cls.PRIV_ADMIN
        elif priv == "user": bitmask |= cls.PRIV_USER
        else: raise ValueError(f"Unknown privilege hallucinated: {priv}")
            
        return bitmask


# ==============================================================================
# SECTION 2: THE DETERMINISTIC TOPOLOGICAL GUARD
# ==============================================================================

class DeterministicTopologyGuard:
    """
    Replaces neural-network based contradiction detectors.
    Runs classical bitwise math to prove if an action is topologically permitted.
    """
    
    @staticmethod
    def validate_action(compiled_bitmask: int) -> bool:
        """
        Runs topological rules against the bitmask using geometric operations (AND/XOR).
        If ANY rule yields a collision/violation, the system halts.
        """
        # RULE 1: You cannot DELETE an IMMUTABLE target.
        # Math: (Bitmask AND (INTENT_DELETE | STATE_IMMUTABLE)) == (INTENT_DELETE | STATE_IMMUTABLE)
        forbidden_delete_immutable = BrailleDictionary.INTENT_DELETE | BrailleDictionary.STATE_IMMUTABLE
        if (compiled_bitmask & forbidden_delete_immutable) == forbidden_delete_immutable:
            logger.error(f"TOPOLOGY VIOLATED [Rule 1]: Cannot mathematical compose DELETE and IMMUTABLE. Token rejected.")
            return False
            
        # RULE 2: A USER cannot START or DELETE a DATABASE.
        # Math: (Bitmask AND USER) AND (Bitmask AND DATABASE) AND (Bitmask AND (START | DELETE))
        forbidden_user_db_modify = BrailleDictionary.PRIV_USER | BrailleDictionary.DOMAIN_DATABASE
        action_bits = BrailleDictionary.INTENT_START | BrailleDictionary.INTENT_DELETE
        
        has_user_db = (compiled_bitmask & forbidden_user_db_modify) == forbidden_user_db_modify
        has_modify_action = (compiled_bitmask & action_bits) > 0
        
        if has_user_db and has_modify_action:
            logger.error(f"TOPOLOGY VIOLATED [Rule 2]: Mathematical collision between USER permission, DATABASE domain, and State Mutation.")
            return False
            
        logger.info(f"Topology Validated via Bitwise Geometry. Bitmask is executable: {bin(compiled_bitmask)}")
        return True


# ==============================================================================
# SECTION 3: NEURO-SYMBOLIC EXECUTION
# ==============================================================================

if __name__ == "__main__":
    print("==================================================")
    print(" BRAILLE DETERMINISTIC ENGINE - POC")
    print("==================================================\n")
    
    # -------------------------------------------------------------------------
    # Scenario A: Valid Autonomous Request (e.g. "Admin wants to restart a failed database")
    # -------------------------------------------------------------------------
    llm_json_output_A = {
        "domain": "database",
        "intent": "start",
        "target_state": "failed",
        "privilege": "admin"
    }
    
    print("--- SCENARIO A: Valid Action ---")
    print(f"LLM JSON Edge Input: {llm_json_output_A}")
    
    mask_A = BrailleDictionary.compile_schema(llm_json_output_A)
    print(f"Compiled Spatial Bitmask: {bin(mask_A)}")
    
    is_valid_A = DeterministicTopologyGuard.validate_action(mask_A)
    if is_valid_A:
        print("-> ENGINE INSTRUCTION: [EXECUTE PROCEDURE]\n")
    
    # -------------------------------------------------------------------------
    # Scenario B: LLM Hallucinated an Invalid Topological Sequence
    # (e.g. LLM parsed user request to "Delete the immutable memory log")
    # -------------------------------------------------------------------------
    llm_json_output_B = {
        "domain": "memory",
        "intent": "delete",
        "target_state": "immutable",
        "privilege": "admin"  # Even as admin, this breaks the laws of physics.
    }
    
    print("--- SCENARIO B: LLM Hallucination/Invalid Physics ---")
    print(f"LLM JSON Edge Input: {llm_json_output_B}")
    
    mask_B = BrailleDictionary.compile_schema(llm_json_output_B)
    print(f"Compiled Spatial Bitmask: {bin(mask_B)}")
    
    is_valid_B = DeterministicTopologyGuard.validate_action(mask_B)
    if not is_valid_B:
        print("-> ENGINE INSTRUCTION: [HARD HALT - REJECT HALLUCINATION]\n")

    # -------------------------------------------------------------------------
    # Scenario C: Privilege Escalation Attempt / Permission Boundary
    # -------------------------------------------------------------------------
    llm_json_output_C = {
        "domain": "database",
        "intent": "delete",
        "target_state": "failed",
        "privilege": "user"
    }

    print("--- SCENARIO C: Privilege Mathematics ---")
    print(f"LLM JSON Edge Input: {llm_json_output_C}")
    
    mask_C = BrailleDictionary.compile_schema(llm_json_output_C)
    print(f"Compiled Spatial Bitmask: {bin(mask_C)}")
    
    is_valid_C = DeterministicTopologyGuard.validate_action(mask_C)
    if not is_valid_C:
        print("-> ENGINE INSTRUCTION: [HARD HALT - NEURO-SYMBOLIC REJECT]\n")
