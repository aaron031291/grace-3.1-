# Grace unified memory

All Grace memory is unified under a single design: **one entry point** and **one set of backends**.

## Entry points

| Use case | Import | Usage |
|----------|--------|--------|
| **Global (no session)** | `from cognitive.unified_memory import get_unified_memory` | `mem = get_unified_memory()` then `mem.store_episode(...)`, `mem.recall_*`, `mem.search_all()`, `mem.get_stats()` |
| **With session + optional KB path** | `from core.memory.unified_memory import UnifiedMemory` | `um = UnifiedMemory(session, knowledge_base_path)` then `um.ingest_experience(...)`, `um.recall_similar(...)`, `um.get_training_data()` |
| **Reconciler (FlashCache + Ghost + Unified)** | `from cognitive.memory_reconciler import get_reconciler` | `get_reconciler().atomic_get/set/evict()`, `reconcile()` |

## Backends (internal)

All storage and recall go through the same session-based modules:

- **Episodic** — `cognitive.episodic_memory.EpisodicBuffer` (episodes table)
- **Learning** — `cognitive.learning_memory.LearningMemoryManager` (learning_examples, learning_patterns)
- **Procedural** — `cognitive.procedural_memory.ProceduralRepository` (procedures table)
- **Mesh** — `cognitive.memory_mesh_integration.MemoryMeshIntegration` (orchestrates learning → episodic → procedural when KB path is set)
- **Magma** — `cognitive.magma_bridge` (graph context)
- **Flash cache** — `cognitive.flash_cache` (external references)

The global singleton (`cognitive.unified_memory.UnifiedMemory`) uses a short-lived session per call and delegates to these backends so there is **one code path** and **one schema**.

## Don’t

- Don’t bypass the unified entry points: avoid raw SQL or direct imports of EpisodicBuffer / LearningMemoryManager / ProceduralRepository for “memory” unless you’re inside the unified stack.
- Don’t add a second global memory API; extend `cognitive.unified_memory` or the sessionful `core.memory.unified_memory` instead.
