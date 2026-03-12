import os
import sys
import asyncio
import logging
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import DatabaseConnection
from database.config import DatabaseConfig
from dotenv import load_dotenv

from api.world_model_api import ingest_external_data, IngestRequest

async def main():
    print("==================================================")
    print(" TLA+ Model Checking for Causal Graph Tests       ")
    print("==================================================")
    
    load_dotenv()
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    
    print("\n[1] Attempting to Ingest a Contradictory Invariant (A -> B, B -> A)")
    
    # We feed the World Model two sentences that create a recursive deadlock
    # The TLA Validator MUST catch this and reject the update.
    contradiction_data = "WARNING: Increasing the core voltage will cause thermal throttling. NOTE: Thermal throttling will cause an increase in the core voltage."
    print(f"    Raw Stream: '{contradiction_data}'")
    
    request = IngestRequest(payload=contradiction_data, source="hardware_sensor")
    
    # This should fail model checking
    ingest_result = await ingest_external_data(request)
    
    print("\n[2] Ingestion Result:")
    print(json.dumps(ingest_result, indent=2))
    
    if ingest_result.get("status") == "error" and "TLA_VIOLATION" in ingest_result.get("reason", ""):
        print("\n    [+] SUCCESS: TLA+ Validator successfully detected the infinite cause-effect loop!")
        print(f"    [+] Generated TLA Spec File: {ingest_result.get('tla_spec')}.tla")
    else:
        print("\n    [!] FAILURE: TLA+ Validator allowed a contradictory invariant to enter Magma Memory.")

    print("\n==================================================")
    print(" Testing Complete. ")

if __name__ == "__main__":
    asyncio.run(main())
