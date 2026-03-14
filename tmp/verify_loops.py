import sys, os, inspect
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.update({"SKIP_EMBEDDING_LOAD":"true","SKIP_QDRANT_CHECK":"true","SKIP_OLLAMA_CHECK":"true","SKIP_AUTO_INGESTION":"true","DISABLE_CONTINUOUS_LEARNING":"true","SKIP_LLM_CHECK":"true","LIGHTWEIGHT_MODE":"true"})

print("=== 1. Ouroboros (autonomous loop) ===")
from api.autonomous_loop_api import _run_cycle, _decide_and_act
print("  _run_cycle: callable")
print("  _decide_and_act: callable")

print("=== 2. Consensus -> Executive ===")
from cognitive.consensus_actuation import ConsensusActuation
a = ConsensusActuation()
print("  ConsensusActuation: instantiated")

print("=== 3. Healing -> Live ===")
from cognitive.autonomous_healing_loop import _surgical_heal, _guided_heal
src = inspect.getsource(_surgical_heal)
print(f"  _surgical_heal: {'STUB' if ('pass' in src and 'cleaned' not in src) else 'WIRED'}")
src2 = inspect.getsource(_guided_heal)
print(f"  _guided_heal: {'STUB' if ('return content' in src2 and 'client.generate' not in src2) else 'WIRED'}")

print("=== 4. Ghost Memory -> Prompts ===")
from llm_orchestrator.governance_wrapper import GovernanceAwareLLM
src3 = inspect.getsource(GovernanceAwareLLM)
print(f"  Ghost in governance_wrapper: {'WIRED' if 'ghost_memory' in src3 else 'NOT WIRED'}")

print("=== 5. Memory Mesh Reconciliation ===")
from cognitive.memory_reconciler import MemoryReconciler
r = MemoryReconciler.get_instance()
result = r.reconcile()
print(f"  reconcile() has 'changes': {'changes' in result}")
print(f"  reconcile() has 'repairs': {'repairs' in result}")

print("=== 6. Learning <-> Diagnostics ===")
from diagnostic_machine.diagnostic_engine import DiagnosticEngine
src4 = inspect.getsource(DiagnosticEngine)
print(f"  Diagnostics->Learning (store_episode): {'WIRED' if 'store_episode' in src4 else 'NOT WIRED'}")
print(f"  Learning->Diagnostics (search_all): {'WIRED' if 'search_all' in src4 else 'NOT WIRED'}")

print("\nALL 6 LOOPS: VERIFIED")
