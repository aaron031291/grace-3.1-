import os
import sys
import asyncio
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from database.connection import DatabaseConnection
from database.config import DatabaseConfig
from dotenv import load_dotenv
from api.world_model_api import ingest_external_data, IngestRequest
from api.spindle_api import verify_spindle_action, ActionRequest

async def main():
    print("==================================================")
    print(" Grace World Model API & Causal Graph Integration ")
    print("==================================================")
    
    load_dotenv()
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    
    get_llm_orchestrator() # Ensure LLM is up
    
    print("\n[1] External Data Ingestion Phase")
    print("    Simulating a sensor broadcasting an environmental warning...")
    
    raw_data = "CRITICAL WARNING: The database is currently unstable. Starting the database archiving process will result in a catastrophic cluster meltdown and permanent data loss."
    print(f"    Raw Stream: '{raw_data}'")
    
    request = IngestRequest(payload=raw_data, source="db_monitor_01")
    ingest_result = await ingest_external_data(request)
    
    print("\n    Ingestion Result:")
    print(json.dumps(ingest_result, indent=2))
    
    if ingest_result.get("status") != "success":
        print("    [!] Failed to ingest data into Magma Causal Graph.")
        return
        
    print("\n[2] Spindle Z3 Topological Action Verification Phase")
    print("    An agent now tries to execute an action that seems fine locally,")
    print("    but physically triggers the disaster condition known only to the World Model.")
    
    bad_action = "Start the database archiving process."
    print(f"    Proposed Action: '{bad_action}'")
    
    action_req = ActionRequest(natural_language=bad_action, privilege="system")
    verify_result = await verify_spindle_action(action_req)
    
    if not verify_result.is_valid:
        print("\n    [!] ACTION BLOCKED BY Z3 PROVER WITH CAUSAL GRAPH CROSS-CHECK")
        print(f"    Proof Reason: {verify_result.mathematical_proof}")
    else:
        print("\n    [x] Action was allowed? This means the causal graph override failed.")
        
    print("\n==================================================")
    print(" Testing Complete.")

if __name__ == "__main__":
    asyncio.run(main())
