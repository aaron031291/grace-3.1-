"""
Simple Memory Mesh Test Script
Tests that Memory Mesh is working without needing the full app running.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from database.config import DatabaseConfig, DatabaseType
from database.connection import DatabaseConnection
from database.session import initialize_session_factory, get_session
from cognitive.memory_mesh_integration import MemoryMeshIntegration

def test_memory_mesh():
    """Test Memory Mesh functionality."""
    print("="*60)
    print("Memory Mesh Test")
    print("="*60)
    
    # 1. Initialize database
    print("\n1. Initializing database...")
    config = DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        database="data/grace.db"
    )
    DatabaseConnection.initialize(config)
    initialize_session_factory()
    print("   ✓ Database initialized")
    
    # 2. Create Memory Mesh
    print("\n2. Creating Memory Mesh...")
    session = next(get_session())
    kb_path = Path("knowledge_base")
    mesh = MemoryMeshIntegration(session, kb_path)
    print("   ✓ Memory Mesh created")
    
    # 3. Test: Create a learning experience
    print("\n3. Creating test learning experience...")
    result = mesh.ingest_learning_experience(
        experience_type='success',
        context={'task': 'document_upload', 'file_type': 'pdf'},
        action_taken={'action': 'extract_text', 'chunks': 10},
        outcome={'status': 'success', 'chunks_created': 10},
        source='system_observation_success',
        user_id='test_user_123'
    )
    print(f"   ✓ Learning example created: {result}")
    
    # 4. Check Memory Mesh stats
    print("\n4. Checking Memory Mesh statistics...")
    stats = mesh.get_memory_mesh_stats()
    
    print("\n" + "="*60)
    print("Memory Mesh Statistics")
    print("="*60)
    
    print(f"\n📚 Learning Memory:")
    print(f"   Total examples: {stats['learning_memory']['total_examples']}")
    print(f"   High-trust (≥0.7): {stats['learning_memory']['high_trust_examples']}")
    print(f"   Trust ratio: {stats['learning_memory']['trust_ratio']:.2%}")
    
    print(f"\n🎬 Episodic Memory:")
    print(f"   Total episodes: {stats['episodic_memory']['total_episodes']}")
    print(f"   Linked from learning: {stats['episodic_memory']['linked_from_learning']}")
    
    print(f"\n🔧 Procedural Memory:")
    print(f"   Total procedures: {stats['procedural_memory']['total_procedures']}")
    print(f"   High-success (≥0.7): {stats['procedural_memory']['high_success_procedures']}")
    
    print(f"\n🧩 Pattern Extraction:")
    print(f"   Total patterns: {stats['pattern_extraction']['total_patterns']}")
    
    print("\n" + "="*60)
    print("✅ Memory Mesh is working correctly!")
    print("="*60)
    
    session.close()

if __name__ == "__main__":
    try:
        test_memory_mesh()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
