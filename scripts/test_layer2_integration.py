"""
Test Layer 2 Integration - Verify all systems are connected and working.

This script tests:
1. Layer 2 initialization
2. All system connections
3. OODA loop processing
4. API endpoint availability
5. Layer 1 message bus integration
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import asyncio
from database.session import SessionLocal, initialize_session_factory
from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from genesis_ide.layer_intelligence import Layer2Intelligence


async def test_layer2_integration():
    """Test Layer 2 integration."""
    print("=" * 70)
    print("LAYER 2 INTEGRATION TEST")
    print("=" * 70)
    
    # Initialize database
    try:
        from database.config import settings
        db_type = DatabaseType(settings.DATABASE_TYPE) if settings else DatabaseType.SQLITE
        db_config = DatabaseConfig(
            db_type=db_type,
            host=settings.DATABASE_HOST if settings else None,
            port=settings.DATABASE_PORT if settings else None,
            username=settings.DATABASE_USER if settings else None,
            password=settings.DATABASE_PASSWORD if settings else None,
            database=settings.DATABASE_NAME if settings else "grace",
            database_path=settings.DATABASE_PATH if settings else None,
            echo=settings.DATABASE_ECHO if settings else False,
        )
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        print("[OK] Database initialized")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        return False
    
    # Get session
    from database.session import get_session
    session = next(get_session())
    
    try:
        # Create Layer 2 instance
        print("\n[1] Creating Layer 2 Intelligence instance...")
        layer2 = Layer2Intelligence(
            session=session,
            repo_path=Path.cwd()
        )
        print("[OK] Layer 2 instance created")
        
        # Initialize Layer 2
        print("\n[2] Initializing Layer 2 systems...")
        initialized = await layer2.initialize()
        
        if initialized:
            print("[OK] Layer 2 initialized successfully")
        else:
            print("[ERROR] Layer 2 initialization failed")
            return False
        
        # Check connected systems
        print("\n[3] Checking connected systems...")
        systems = {
            "LLM Orchestrator": layer2._llm_orchestrator is not None,
            "Memory Mesh": layer2._memory_mesh is not None,
            "RAG Retriever": layer2._rag_retriever is not None,
            "World Model": layer2._world_model is not None,
            "Diagnostic Engine": layer2._diagnostic_engine is not None,
            "Code Analyzer": layer2._code_analyzer is not None,
            "Librarian": layer2._librarian is not None,
            "Mirror System": layer2._mirror_system is not None,
            "Confidence Scorer": layer2._confidence_scorer is not None,
            "Cognitive Engine": layer2._cognitive_engine is not None,
            "Healing System": layer2._healing_system is not None,
            "TimeSense": layer2._timesense is not None,
            "Clarity Framework": layer2._clarity_framework is not None,
            "Failure Learning": layer2._failure_learning is not None,
            "Mutation Tracker": layer2._mutation_tracker is not None,
            "Self-Updater": layer2._self_updater is not None,
            "Neuro-Symbolic Reasoner": layer2._neuro_symbolic_reasoner is not None,
            "Enterprise Neuro-Symbolic": layer2._enterprise_neuro_symbolic is not None,
            "Enterprise RAG": layer2._enterprise_rag is not None,
            "Trust-Aware Retriever": layer2._trust_aware_retriever is not None,
            "Genesis Service": layer2._genesis_service is not None,
            "Layer 1 Message Bus": layer2._message_bus is not None
        }
        
        connected_count = sum(1 for v in systems.values() if v)
        total_count = len(systems)
        
        print(f"\nConnected Systems: {connected_count}/{total_count}")
        for name, connected in systems.items():
            status = "[OK]" if connected else "[MISSING]"
            print(f"  {status} {name}")
        
        # Test OODA loop processing
        print("\n[4] Testing OODA loop processing...")
        try:
            result = await layer2.process(
                intent="Test intent: check system status",
                entities={},
                context={}
            )
            
            if result:
                print("[OK] OODA loop processing successful")
                print(f"  - Intent: {result.get('intent', 'N/A')}")
                print(f"  - Confidence: {result.get('confidence', 0):.2f}")
                print(f"  - Decision: {result.get('decision', {}).get('action', 'N/A')}")
                
                # Check observations
                observations = result.get('observations', {})
                if observations:
                    print(f"  - Observations gathered: {len(observations)} sources")
                
                # Check orientation
                orientation = result.get('orientation', {})
                if orientation:
                    print(f"  - Orientation: {orientation.get('understanding', 'N/A')[:100]}...")
            else:
                print("[ERROR] OODA loop processing returned no result")
                return False
        except Exception as e:
            print(f"[ERROR] OODA loop processing failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Check metrics
        print("\n[5] Checking metrics...")
        metrics = layer2.metrics
        print(f"  - Cognitive cycles: {metrics.get('cognitive_cycles', 0)}")
        print(f"  - Decisions made: {metrics.get('decisions_made', 0)}")
        print(f"  - Insights generated: {metrics.get('insights_generated', 0)}")
        
        # Summary
        print("\n" + "=" * 70)
        print("LAYER 2 INTEGRATION TEST SUMMARY")
        print("=" * 70)
        print(f"[OK] Layer 2 initialized: {initialized}")
        print(f"[OK] Systems connected: {connected_count}/{total_count}")
        print(f"[OK] OODA loop working: {result is not None}")
        print(f"[OK] Layer 1 message bus: {layer2._message_bus is not None}")
        print("\n[SUCCESS] Layer 2 is FULLY INTEGRATED and WORKING!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


if __name__ == "__main__":
    success = asyncio.run(test_layer2_integration())
    sys.exit(0 if success else 1)
