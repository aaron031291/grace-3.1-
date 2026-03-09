import sys
import os
import hashlib
from datetime import datetime

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from database.session import session_scope, initialize_session_factory
from models.genesis_key_models import GenesisKeyType
from genesis.genesis_key_service import get_genesis_service
from genesis.symbiotic_version_control import SymbioticVersionControl

def reproduce():
    print("Initializing database...")
    config = DatabaseConfig()
    DatabaseConnection.initialize(config)
    print("Initializing session factory...")
    initialize_session_factory()
    
    # Use a dummy file for tracking
    test_file = os.path.abspath("tmp/test_reproduce.txt")
    with open(test_file, "w") as f:
        f.write("initial content")
        
    print(f"Tracking file: {test_file}")
    
    # Initialize symbiotic VC
    svc = SymbioticVersionControl(os.path.dirname(test_file))
    
    try:
        # Simulate the error sequence
        # We need a shared session to trigger the bug
        with session_scope() as session:
            print("Step 1: Track file change (First call)")
            # This will create an operation key and a version key
            result1 = svc.track_file_change(
                file_path=test_file,
                user_id="reproduce_user",
                change_description="First change"
            )
            print(f"Success 1: {result1['operation_genesis_key']}")
            
            # Modify file to trigger a NEW version
            with open(test_file, "a") as f:
                f.write("\nsecond change")
                
            print("Step 3: Create EXACT SAME key twice in SAME session")
            # First creation
            k1 = svc.genesis_service.create_key(
                key_type=GenesisKeyType.SYSTEM_EVENT,
                what_description="Test Collision",
                who_actor="reproduce_user",
                session=session
            )
            print(f"Key 1 created: {k1.key_id}")
            
            # Second creation 
            k2 = svc.genesis_service.create_key(
                key_type=GenesisKeyType.SYSTEM_EVENT,
                what_description="Test Collision",
                who_actor="reproduce_user",
                session=session
            )
            print(f"Key 2 (potential collision) handled: {k2.key_id}")
            
            if k1.key_id == k2.key_id:
                print("SUCCESS: Deterministic collision handled correctly.")
            else:
                print("INFO: Keys were different (expected if timestamps differ).")
                
            # Final check - is the session still usable?
            session.flush()
            print("Final flush successful. Session is HEALTHY.")
            
    except Exception as e:
        print(f"\nCaught expected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if not os.path.exists("tmp"):
        os.makedirs("tmp")
    reproduce()
