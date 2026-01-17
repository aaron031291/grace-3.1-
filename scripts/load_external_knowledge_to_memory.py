#!/usr/bin/env python3
"""
Load External Knowledge to Memory Mesh

Loads the extracted external knowledge from JSON into Grace's Memory Mesh
so it's immediately available to the Coding Agent and other systems.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

import json
from backend.database.connection import DatabaseConnection, DatabaseConfig, DatabaseType
from backend.database.session import get_session
from cognitive.memory_mesh_integration import MemoryMeshIntegration
from cognitive.learning_memory import LearningMemoryManager


def load_knowledge_to_memory():
    """Load external knowledge into Memory Mesh."""
    print("=" * 80)
    print("LOADING EXTERNAL KNOWLEDGE TO MEMORY MESH")
    print("=" * 80)
    print()
    
    # Initialize database
    print("Initializing database...")
    try:
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database="grace",
            database_path=str(project_root / "data" / "grace.db"),
            echo=False,
        )
        DatabaseConnection.initialize(db_config)
        
        from backend.database.session import initialize_session_factory
        initialize_session_factory()
        
        print("[OK] Database initialized")
    except Exception as e:
        print(f"ERROR: Database initialization: {e}")
        return
    
    # Load external knowledge JSON
    knowledge_file = project_root / "data" / "external_knowledge.json"
    
    if not knowledge_file.exists():
        print(f"ERROR: Knowledge file not found: {knowledge_file}")
        print("Please run extract_external_knowledge_simple.py first")
        return
    
    print(f"Loading knowledge from: {knowledge_file}")
    
    with open(knowledge_file, "r", encoding="utf-8") as f:
        knowledge_data = json.load(f)
    
    sources = knowledge_data.get("sources", [])
    print(f"Found {len(sources)} knowledge sources")
    print()
    
    # Initialize Memory Mesh
    print("Initializing Memory Mesh...")
    try:
        session = next(get_session())
        kb_path = project_root / "knowledge_base"
        memory_mesh = MemoryMeshIntegration(session=session, knowledge_base_path=kb_path)
        
        print("[OK] Memory Mesh initialized")
    except Exception as e:
        print(f"ERROR: Memory Mesh initialization: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Load each source into Memory Mesh
    print()
    print("=" * 80)
    print("LOADING KNOWLEDGE TO MEMORY MESH")
    print("=" * 80)
    print()
    
    loaded = 0
    failed = 0
    
    for i, source in enumerate(sources, 1):
        try:
            source_type = source.get("source_type", "unknown")
            title = source.get("title", "")
            url = source.get("url", "")
            
            print(f"[{i}/{len(sources)}] Loading: {source_type} - {title[:60]}...")
            
            # Create learning example from external knowledge
            experience_data = {
                "source_type": source_type,
                "title": title,
                "url": url,
                "query": source.get("query", ""),
                "score": source.get("score", 0),
                "is_accepted": source.get("is_accepted", False)
            }
            
            # Ingest into Memory Mesh
            example_id = memory_mesh.ingest_learning_experience(
                experience_type="external_knowledge",
                context={
                    "source": source_type,
                    "title": title,
                    "url": url,
                    "query": source.get("query", ""),
                    "metadata": source
                },
                action_taken={
                    "action": "extract_knowledge",
                    "source_type": source_type
                },
                outcome={
                    "success": True,
                    "knowledge_extracted": True,
                    "quality_score": min(1.0, (source.get("score", 0) / 100.0) + 0.5) if source.get("score") else 0.7
                },
                source="external_extraction",
                genesis_key_id=None
            )
            
            loaded += 1
            print(f"  [OK] Loaded (ID: {example_id})")
            
        except Exception as e:
            failed += 1
            print(f"  [FAIL] Error: {e}")
    
    print()
    print("=" * 80)
    print("LOADING SUMMARY")
    print("=" * 80)
    print()
    print(f"Total sources: {len(sources)}")
    print(f"Successfully loaded: {loaded}")
    print(f"Failed: {failed}")
    print()
    
    if loaded > 0:
        print("=" * 80)
        print("KNOWLEDGE NOW AVAILABLE")
        print("=" * 80)
        print()
        print("The external knowledge is now in Grace's Memory Mesh!")
        print("It's immediately available to:")
        print("  - Coding Agent (for code generation)")
        print("  - Self-Healing System (for fix patterns)")
        print("  - LLM Orchestrator (for AI research insights)")
        print("  - All Grace learning systems")
        print()
    
    print("=" * 80)


if __name__ == "__main__":
    load_knowledge_to_memory()
