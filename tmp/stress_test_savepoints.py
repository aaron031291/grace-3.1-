
import threading
import time
import os
import sys
from datetime import datetime, timezone

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from database.config import DatabaseConfig, DatabaseType
from database.connection import DatabaseConnection
from database.session import session_scope, initialize_session_factory
from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKeyType

def stress_test_thread(thread_id, count):
    print(f"Thread {thread_id} starting...")
    for i in range(count):
        try:
            with session_scope() as session:
                service = get_genesis_service(session)
                # Create a mix of deterministic and random keys
                key_type = GenesisKeyType.FILE_OPERATION
                what = f"Stress test {thread_id} - {i}"
                
                # Deterministic key to force collisions
                service.create_key(
                    key_type=key_type,
                    what_description=what,
                    who_actor=f"stress_{thread_id}",
                    where_location="stress_test",
                    why_reason="Verification of pool fix",
                    how_method="Multi-threaded test",
                    user_id="tester",
                    session=session
                )
                
                # Nested call
                service.create_key(
                    key_type=key_type,
                    what_description=f"{what} - Nested",
                    who_actor=f"stress_{thread_id}",
                    where_location="stress_test",
                    why_reason="Verification of nested savepoints",
                    how_method="Multi-threaded test",
                    user_id="tester",
                    session=session
                )
            if i % 5 == 0:
                print(f"Thread {thread_id} completed {i}/{count}")
        except Exception as e:
            print(f"ERROR in Thread {thread_id}: {e}")
            # Do not exit, continue to see if others fail

if __name__ == "__main__":
    # Initialize DB
    config = DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        database_path="./data/grace.db"
    )
    DatabaseConnection.initialize(config)
    initialize_session_factory()
    
    print("Starting stress test with 5 threads, 20 iterations each...")
    threads = []
    for i in range(5):
        t = threading.Thread(target=stress_test_thread, args=(i, 20))
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()
    
    print("Stress test COMPLETED.")
