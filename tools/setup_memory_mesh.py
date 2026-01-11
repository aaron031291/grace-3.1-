"""
Setup Script for Memory Mesh with Learning Memory

Runs all necessary migrations and initializations.
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))


def setup_memory_mesh():
    """Setup memory mesh system."""
    print("=" * 80)
    print("MEMORY MESH WITH LEARNING MEMORY - SETUP")
    print("=" * 80)

    # Step 1: Run migration
    print("\n[1/4] Running database migration...")
    try:
        from database.migrate_add_memory_mesh import migrate
        migrate()
        print("✓ Migration completed")
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False

    # Step 2: Ensure learning memory folders exist
    print("\n[2/4] Creating learning memory folder structure...")
    try:
        from settings import KNOWLEDGE_BASE_PATH
        learning_path = Path(KNOWLEDGE_BASE_PATH) / "layer_1" / "learning_memory"

        folders = [
            "feedback",
            "correction",
            "success",
            "failure",
            "pattern",
            "training",
            "optimization"
        ]

        for folder in folders:
            folder_path = learning_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created {folder}/")

        print("✓ Learning memory folders created")
    except Exception as e:
        print(f"✗ Folder creation failed: {e}")
        return False

    # Step 3: Create exports folder
    print("\n[3/4] Creating exports folder...")
    try:
        exports_path = Path(KNOWLEDGE_BASE_PATH) / "exports"
        exports_path.mkdir(parents=True, exist_ok=True)
        print("✓ Exports folder created")
    except Exception as e:
        print(f"✗ Exports folder creation failed: {e}")
        return False

    # Step 4: Test connection
    print("\n[4/4] Testing memory mesh integration...")
    try:
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory, SessionLocal
        from cognitive.memory_mesh_integration import MemoryMeshIntegration

        # Initialize database
        DatabaseConnection.initialize(
            db_type='sqlite',
            database='grace.db',
            base_path='data'
        )
        initialize_session_factory()

        # Test integration
        session = SessionLocal()
        mesh = MemoryMeshIntegration(session, Path(KNOWLEDGE_BASE_PATH))

        # Get stats
        stats = mesh.get_memory_mesh_stats()

        print("✓ Memory mesh integration working")
        print("\nInitial stats:")
        print(f"  Learning examples: {stats['learning_memory']['total_examples']}")
        print(f"  Episodes: {stats['episodic_memory']['total_episodes']}")
        print(f"  Procedures: {stats['procedural_memory']['total_procedures']}")
        print(f"  Patterns: {stats['pattern_extraction']['total_patterns']}")

        session.close()

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 80)
    print("SETUP COMPLETE!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Start the server: python backend/app.py")
    print("2. Test with: curl http://localhost:8000/learning-memory/stats")
    print("3. Read docs: MEMORY_MESH_WITH_LEARNING.md")
    print("\nAPI endpoints available at:")
    print("  POST /learning-memory/record-experience")
    print("  POST /learning-memory/user-feedback")
    print("  GET  /learning-memory/training-data")
    print("  GET  /learning-memory/stats")
    print("  POST /learning-memory/sync-folders")

    return True


if __name__ == "__main__":
    success = setup_memory_mesh()
    sys.exit(0 if success else 1)
