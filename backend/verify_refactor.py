"""
Complete System Verification Script
===================================
Verifies all components after the provider-agnostic refactor:
1. LLM Factory and Client
2. Librarian Engine/Analyzer
3. Health API
4. Diagnostic Sensors
"""

import sys
import os
from pathlib import Path
import logging

# Configure minimal logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY")

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_result(name, success, message=""):
    status = "[PASS]" if success else "[FAIL]"
    print(f"  {status} {name}: {message}")

def verify_llm_factory():
    print_header("1. VERIFYING LLM FACTORY & CLIENT")
    try:
        from llm_orchestrator.factory import get_llm_client
        from settings import settings
        
        provider = settings.LLM_PROVIDER
        print(f"  Configured Provider: {provider.upper()}")
        
        client = get_llm_client()
        print_result("Factory instantiation", True)
        
        is_running = client.is_running()
        print_result("Client connectivity check", is_running, f"Service {'responding' if is_running else 'unreachable'}")
        
        if is_running:
            try:
                # Test simple completion
                print("  Testing simple chat completion...")
                messages = [{"role": "user", "content": "Say 'System Ready'"}]
                response = client.chat(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    temperature=0.1,
                    stream=False
                )
                print_result("LLM Chat interaction", True, f"Response: {response[:30]}...")
            except Exception as e:
                print_result("LLM Chat interaction", False, str(e))
        
        return is_running
    except Exception as e:
        print_result("LLM Factory verify", False, str(e))
        return False

def verify_librarian():
    print_header("2. VERIFYING LIBRARIAN SYSTEM")
    try:
        from librarian.engine import LibrarianEngine
        from database.session import SessionLocal
        from embedding import get_embedding_model
        from llm_orchestrator.factory import get_llm_client
        
        # Check if embedding model factory is available
        if get_embedding_model is None:
            print_result("Embedding model check", False, "get_embedding_model is None (dependencies missing?)")
            return False
            
        db = SessionLocal()
        client = get_llm_client()
        
        embedding_model = get_embedding_model()
        if embedding_model is None:
             print_result("Embedding model load", False, "get_embedding_model() returned None")
             return False

        print("  Initializing LibrarianEngine...")
        engine = LibrarianEngine(
            db_session=db,
            embedding_model=embedding_model,
            llm_client=client,
            use_ai=True
        )
        print_result("Engine initialization", True)
        
        is_ready = engine.ai_analyzer.is_available()
        print_result("AI Analyzer availability", is_ready)
        
        db.close()
        return True
    except Exception as e:
        print_result("Librarian verify", False, str(e))
        import traceback
        traceback.print_exc()
        return False

def verify_health_api():
    print_header("3. VERIFYING HEALTH API")
    try:
        from api.health import check_llm
        import asyncio
        
        print("  Calling internal health check function...")
        # Since this is an async function, we need a simple way to run it
        result = asyncio.run(check_llm())
        print_result("Internal Health check", result.status == "healthy", result.message or "OK")
        return result.status == "healthy"
    except Exception as e:
        print_result("Health API verify", False, str(e))
        return False

def verify_sensors():
    print_header("4. VERIFYING DIAGNOSTIC SENSORS")
    try:
        from diagnostic_machine.sensors import SensorLayer
        
        sensor_layer = SensorLayer()
        print("  Collecting system metrics...")
        metrics = sensor_layer._collect_metrics()
        
        print_result("LLM Health Sensor", hasattr(metrics, 'llm_health'), f"Health: {metrics.llm_health}")
        return True
    except Exception as e:
        print_result("Sensors verify", False, str(e))
        return False

def main():
    print("\n" + "#"*70)
    print("  GRACE SYSTEM VERIFICATION POST-REFACOR")
    print("#"*70)
    
    # Initialize database once for all checks
    try:
        from database.config import DatabaseConfig, DatabaseType
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory
        from settings import settings
        
        print("\n  Initializing environment...")
        db_type = DatabaseType(settings.DATABASE_TYPE) if settings else DatabaseType.SQLITE
        db_config = DatabaseConfig(
            db_type=db_type,
            database=settings.DATABASE_NAME if settings else "grace",
            database_path=settings.DATABASE_PATH if settings else None,
        )
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        print("  [OK] Database initialized")
    except Exception as e:
        print(f"  [FAIL] Environment initialization failed: {e}")
        # Proceed anyway to see other failures
    
    v1 = verify_llm_factory()
    v2 = verify_librarian()
    v3 = verify_health_api()
    v4 = verify_sensors()
    
    print("\n" + "="*70)
    if all([v1, v2, v3, v4]):
        print("  SUCCESS: System is fully operational and provider-agnostic.")
    else:
        print("  WARNING: Some components encountered issues. See logs above.")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
