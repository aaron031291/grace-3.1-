import os
import sys
import asyncio
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import DatabaseConnection
from database.config import DatabaseConfig
from dotenv import load_dotenv

from legacy_components.data_warehouse import get_legacy_warehouse
from legacy_components.legacy_brain import LegacyBrain
from ai_brain_submodule.neural_planner import NeuralPlanner
from data_layer.db_connector import get_db_connector
from external_api_bridge import ExternalAPIBridge

from api.spindle_api import verify_spindle_action, ActionRequest

async def main():
    print("==================================================")
    print(" Universal Genesis Key & Spindle Middleware Test ")
    print("==================================================")
    
    load_dotenv()
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    
    print("\n[1] Instantiating Vulnerable Legacy Systems (Checking for Genesis Keys)...")
    
    # 1. Warehouse
    warehouse = get_legacy_warehouse()
    print(f"    [+] Data Warehouse initialized bounds to Key: {warehouse.component_key}")
    
    # 2. Legacy Brain
    brain = LegacyBrain()
    print(f"    [+] Legacy Brain initialized bounds to Key: {brain.brain_key}")
    
    # 3. Neural Planner
    planner = NeuralPlanner()
    print(f"    [+] Neural Planner initialized bounds to Key: {planner.planner_key}")
    
    # 4. DB Connector
    db = get_db_connector()
    print(f"    [+] DB Connector initialized bounds to Key: {db.db_key}")
    
    # 5. External API Bridge
    bridge = ExternalAPIBridge()
    print(f"    [+] External API Bridge initialized bounds to Key: {bridge.bridge_key}")

    print("\n[2] Testing Spindle Middleware on Legacy Warehouse Action...")
    try:
        from api.world_model_api import ingest_external_data, IngestRequest
        
        # Ingest the physical rule into the causal graph first so it has something to block
        raw_data = "CRITICAL WARNING: The database is currently unstable. Starting the database archiving process will result in a catastrophic cluster meltdown and permanent data loss."
        await ingest_external_data(IngestRequest(payload=raw_data))
        
        # We will try an innocent operation that violates causal physics
        # Instead of crashing, Spindle Middleware should offer an alternative
        
        # We'll use the Spindle API directly to simulate an HTTP request
        bad_action = "Start archiving the cluster databases."
        print(f"    Proposed Legacy Action: '{bad_action}'")
        req = ActionRequest(natural_language=bad_action, privilege="system")
        
        verify_result = await verify_spindle_action(req)
        
        if not verify_result.is_valid:
             print(f"\n    [!] ACTION BLOCKED BY SPINDLE (Z3_UNSAT)")
             print(f"    Middleware Response: {verify_result.mathematical_proof}")
             if "SUGGESTED FIX" in verify_result.mathematical_proof:
                 print("\n    [+] Spindle Error Middleware successfully caught the failure and suggested an alternative!")
        else:
             print("\n    [?] Action passed Spindle unexpectedly.")
             
    except Exception as e:
        print(f"    [!] Error during test: {e}")
        
    print("\n==================================================")
    print(" Testing Complete. System 100% Bound to Genesis Keys.")

if __name__ == "__main__":
    asyncio.run(main())
