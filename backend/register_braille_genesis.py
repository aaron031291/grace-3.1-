import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from database.session import get_session
from genesis.genesis_key_service import GenesisKeyService
from core.clarity_framework import ClarityFramework
from database.connection import DatabaseConnection
from database.config import DatabaseConfig
from dotenv import load_dotenv
from models.genesis_key_models import GenesisKeyType

def register_braille_engine():
    load_dotenv()
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    # We create a Genesis Key to track the Braille Deterministic Compiler
    # This acts as our version control loop for the engine itself.
    session_gen = get_session()
    session = next(session_gen)
    
    try:
        service = GenesisKeyService(session)
        
        print("Registering Braille Deterministic Engine with Genesis...")
        
        # Create a Genesis Key for the Component
        key = service.create_key(
            key_type=GenesisKeyType.SYSTEM_EVENT,
            what_description="Braille Deterministic Toplogical Guard (NLPCompilerEdge)",
            where_location="backend.cognitive.braille_compiler",
            who_actor="grace_architect",
            why_reason="Eliminate LLM Hallucinations and enforce deterministic physics constraints on autonomous actions.",
            how_method="Spatial Bitmask Compilation",
            context_data={
                "version": "1.0.0",
                "capabilities": ["nlp_to_bitmask", "deterministic_validation", "privilege_enforcement"],
                "repository": "grace-3.1"
            }
        )
        
        print(f"[SUCCESS] Issued Genesis Key for Braille Engine: {key.key_id}")
        
        # Record the decision in Clarity
        decision = ClarityFramework().record_decision(
            what="Deployed Braille Deterministic Engine horizontally across Grace",
            why="To prevent LLM hallucinations from executing destructive actions in the wild.",
            who={"actor": "grace_architect", "system": "backend installation"},
            where={"components": ["action_router.py", "action_gate.py", "cognitive_framework.py"]},
            how={"method": "Injecting NLPCompilerEdge to intercept fuzzy language and convert to bitmasks."},
            risk_score=0.1,  # Lower risk because it acts as a safety shield
            related_ids=[str(key.key_id)]
        )
        
        print(f"[SUCCESS] Clarity Framework Logged Decision: {decision.id}")
        
        session.commit()
    except Exception as e:
        print(f"Failed to register Braille Engine: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    register_braille_engine()
