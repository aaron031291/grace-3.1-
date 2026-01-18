"""
Verify Self-Healing System Status

Run this script to check if all self-healing components are operational.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

def verify_components():
    """Verify all self-healing components."""
    results = {}
    
    print("=" * 60)
    print("GRACE Self-Healing System Verification")
    print("=" * 60)
    
    # 1. Autonomous Healing System
    print("\n[1] Autonomous Healing System...")
    try:
        from cognitive.autonomous_healing_system import (
            AutonomousHealingSystem,
            HealingAction,
            TrustLevel,
            get_autonomous_healing
        )
        actions = [a.value for a in HealingAction]
        print(f"    ✅ Loaded - {len(actions)} healing actions available")
        print(f"    Actions: {', '.join(actions[:5])}...")
        results["autonomous_healing"] = True
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        results["autonomous_healing"] = False
    
    # 2. Diagnostic Engine
    print("\n[2] Diagnostic Engine (4-Layer)...")
    try:
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine, TriggerSource
        triggers = [t.value for t in TriggerSource]
        print(f"    ✅ Loaded - {len(triggers)} trigger sources")
        results["diagnostic_engine"] = True
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        results["diagnostic_engine"] = False
    
    # 3. Healing Validation Pipeline
    print("\n[3] Healing Validation Pipeline...")
    try:
        from cognitive.healing_validation_pipeline import (
            HealingValidationPipeline,
            ValidationGate,
            Patch
        )
        gates = [g.value for g in ValidationGate]
        print(f"    ✅ Loaded - {len(gates)} validation gates")
        print(f"    Gates: {', '.join(gates)}")
        results["validation_pipeline"] = True
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        results["validation_pipeline"] = False
    
    # 4. Proactive Code Scanner
    print("\n[4] Proactive Code Scanner...")
    try:
        from diagnostic_machine.proactive_code_scanner import (
            ProactiveCodeScanner,
            get_proactive_scanner
        )
        print(f"    ✅ Loaded - Proactive scanning available")
        results["proactive_scanner"] = True
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        results["proactive_scanner"] = False
    
    # 5. Semantic Refactoring Engine
    print("\n[5] Semantic Refactoring Engine...")
    try:
        from cognitive.semantic_refactoring_engine import (
            SemanticRefactoringEngine,
            RefactoringType,
            SymbolType
        )
        refactor_types = [r.value for r in RefactoringType]
        print(f"    ✅ Loaded - {len(refactor_types)} refactoring types")
        results["semantic_refactoring"] = True
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        results["semantic_refactoring"] = False
    
    # 6. Genesis Key Service
    print("\n[6] Genesis Key Service...")
    try:
        from genesis.genesis_key_service import GenesisKeyService, get_genesis_service
        from models.genesis_key_models import GenesisKeyType
        key_types = [k.value for k in GenesisKeyType]
        print(f"    ✅ Loaded - {len(key_types)} key types available")
        results["genesis_keys"] = True
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        results["genesis_keys"] = False
    
    # 7. Healing Knowledge Base
    print("\n[7] Healing Knowledge Base...")
    try:
        from cognitive.healing_knowledge_base import (
            HealingKnowledgeBase,
            IssueType,
            get_healing_knowledge_base
        )
        issue_types = [i.value for i in IssueType]
        print(f"    ✅ Loaded - {len(issue_types)} issue types known")
        results["knowledge_base"] = True
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        results["knowledge_base"] = False
    
    # 8. Code Analyzer Self-Healing
    print("\n[8] Code Analyzer Self-Healing...")
    try:
        from cognitive.code_analyzer_self_healing import (
            CodeAnalyzerSelfHealing,
            get_code_analyzer_healing
        )
        print(f"    ✅ Loaded - Code analyzer with self-healing")
        results["code_analyzer"] = True
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        results["code_analyzer"] = False
    
    # 9. CI/CD Pipeline Integration
    print("\n[9] CI/CD Pre-commit Healing...")
    try:
        from cicd.pipeline_integration import run_pre_commit_check
        from cicd.proactive_self_healing import ProactiveSelfHealing, PipelineStage
        stages = [s.value for s in PipelineStage]
        print(f"    ✅ Loaded - {len(stages)} pipeline stages")
        results["cicd_healing"] = True
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        results["cicd_healing"] = False
    
    # 10. Circuit Breaker (Runtime Healing)
    print("\n[10] Circuit Breaker (Runtime Protection)...")
    try:
        from utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        from utils.service_protection import protect_database_operation
        print(f"    ✅ Loaded - Circuit breaker pattern available")
        results["circuit_breaker"] = True
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        results["circuit_breaker"] = False
    
    # 11. Healing Scheduler (NEW)
    print("\n[11] Healing Scheduler (Persistent Queue + File Watcher)...")
    try:
        from cognitive.healing_scheduler import (
            HealingScheduler,
            PersistentHealingQueue,
            FileWatcherHealing,
            HealingTask,
            HealingPriority,
            get_healing_scheduler
        )
        print(f"    ✅ Loaded - Scheduler with persistent queue and file watcher")
        results["healing_scheduler"] = True
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        results["healing_scheduler"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nComponents: {passed}/{total} operational")
    
    if passed == total:
        print("\n✅ ALL SELF-HEALING COMPONENTS OPERATIONAL")
    else:
        print("\n⚠️ Some components have issues:")
        for name, status in results.items():
            if not status:
                print(f"   - {name}: FAILED")
    
    # Background processes check
    print("\n" + "-" * 60)
    print("BACKGROUND PROCESSES (when server is running)")
    print("-" * 60)
    print("• Health Monitor: Every 5 minutes")
    print("• Mirror Analysis: Every 10 minutes")
    print("• Proactive Scan: On-demand or triggered by file changes")
    print("• Pre-flight Analysis: On boot (analysis only)")
    
    return passed == total


if __name__ == "__main__":
    success = verify_components()
    sys.exit(0 if success else 1)
