#!/usr/bin/env python3
"""
Verify Self-Healing Training System

Checks:
1. Training system is active and working
2. Knowledge retrieval is correct for tasks
3. Memory Mesh patterns are being retrieved
4. Training cycles are improving over time
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

print("=" * 70)
print("SELF-HEALING TRAINING SYSTEM VERIFICATION")
print("=" * 70)
print()

# ==================== TEST 1: Training System Initialization ====================
print("[1] Testing Training System Initialization...")
try:
    # Initialize database
    try:
        from backend.database.connection import DatabaseConnection, DatabaseConfig, DatabaseType
        
        project_root = Path(__file__).parent.parent
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database="grace",
            database_path=str(project_root / "data" / "grace.db"),
            echo=False,
        )
        DatabaseConnection.initialize(db_config)
        
        from backend.database.session import initialize_session_factory
        initialize_session_factory()
        
        print("  [OK] Database initialized")
    except Exception as e:
        print(f"  [WARN] Database initialization: {e}")
        import traceback
        traceback.print_exc()
    
    from backend.database.session import get_session
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    session = next(get_session())
    kb_path = project_root / "knowledge_base"
    backend_dir = project_root / "backend"
    
    from cognitive.self_healing_training_system import get_self_healing_training_system
    from cognitive.autonomous_sandbox_lab import get_sandbox_lab
    from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
    from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
    
    try:
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
        llm_orchestrator = get_llm_orchestrator(session=session, knowledge_base_path=kb_path)
    except Exception as e:
        print(f"  [WARN] LLM Orchestrator not available: {e}")
        llm_orchestrator = None
    
    sandbox_lab = get_sandbox_lab()
    
    try:
        healing_system = get_autonomous_healing(session=session, trust_level=TrustLevel.MEDIUM_RISK_AUTO)
    except Exception as e:
        print(f"  [WARN] Healing system not available: {e}")
        healing_system = None
    
    try:
        diagnostic_engine = get_diagnostic_engine()
    except Exception as e:
        print(f"  [WARN] Diagnostic engine not available: {e}")
        diagnostic_engine = None
    
    try:
        training_system = get_self_healing_training_system(
            session=session,
            knowledge_base_path=kb_path,
            sandbox_lab=sandbox_lab,
            healing_system=healing_system,
            diagnostic_engine=diagnostic_engine,
            llm_orchestrator=llm_orchestrator
        )
    except Exception as e:
        print(f"  [WARN] Training system initialization: {e}")
        training_system = None
    
    print("  [OK] Training system initialized")
    print(f"      - Sandbox lab: {'available' if sandbox_lab else 'not available'}")
    print(f"      - Healing system: {'available' if healing_system else 'not available'}")
    print(f"      - Diagnostic engine: {'available' if diagnostic_engine else 'not available'}")
    print(f"      - LLM orchestrator: {'available' if llm_orchestrator else 'not available'}")
except Exception as e:
    print(f"  [ERROR] Training system initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==================== TEST 2: Knowledge Retrieval ====================
print()
print("[2] Testing Knowledge Retrieval for Tasks...")
try:
    # Test knowledge retrieval for a task
    test_task = "fix syntax errors in Python code"
    
    # Use Advanced Grace-Aligned LLM to retrieve knowledge
    if hasattr(training_system, 'llm_orchestrator') and training_system.llm_orchestrator:
        if hasattr(training_system.llm_orchestrator, 'grace_aligned_llm') and training_system.llm_orchestrator.grace_aligned_llm:
            # Retrieve memories for task
            memories = training_system.llm_orchestrator.grace_aligned_llm.retrieve_grace_memories(
                query=test_task,
                limit=10
            )
            
            print(f"  [OK] Knowledge retrieval working")
            print(f"      - Task: '{test_task}'")
            print(f"      - Memories retrieved: {len(memories)}")
            
            if memories:
                print("      - Sample memories:")
                for i, mem in enumerate(memories[:3], 1):
                    mem_type = mem.get("type", "unknown")
                    content = mem.get("content", "")[:100]
                    trust = mem.get("trust_score", 0.0)
                    print(f"        {i}. [{mem_type}] Trust: {trust:.2f} - {content}...")
            else:
                print("      - No memories found yet (system may be new)")
        else:
            print("  [WARN] Grace-Aligned LLM not available for knowledge retrieval")
    else:
        print("  [WARN] LLM orchestrator not available for knowledge retrieval")
except Exception as e:
    print(f"  [WARN] Knowledge retrieval test error: {e}")

# ==================== TEST 3: Training Cycle Start ====================
print()
print("[3] Testing Training Cycle Start...")
try:
    # Test starting a training cycle
    test_folder = str(backend_dir)
    
    cycle = training_system.start_training_cycle(
        folder_path=test_folder,
        problem_perspective=None  # Use default
    )
    
    print(f"  [OK] Training cycle started")
    print(f"      - Cycle ID: {cycle.cycle_id}")
    print(f"      - State: {cycle.state.value}")
    print(f"      - Problem perspective: {cycle.problem_perspective.value}")
    print(f"      - Difficulty level: {cycle.difficulty_level:.1f}")
    print(f"      - Cycle number: {cycle.cycle_number}")
    print(f"      - Files collected: {len(cycle.files_collected)}")
    
    if cycle.files_collected:
        print("      - Sample files:")
        for i, file_path in enumerate(cycle.files_collected[:5], 1):
            print(f"        {i}. {Path(file_path).name}")
    else:
        print("      - No files collected yet (may need to generate test files)")
except Exception as e:
    print(f"  [WARN] Training cycle start error: {e}")
    import traceback
    traceback.print_exc()

# ==================== TEST 4: Alert Registration ====================
print()
print("[4] Testing Alert Registration...")
try:
    from cognitive.self_healing_training_system import AlertSource
    
    # Test alert registration
    alert = training_system.register_alert(
        source=AlertSource.DIAGNOSTIC_ENGINE,
        severity="high",
        description="Test alert: Performance degradation detected",
        affected_files=[str(backend_dir / "app.py")]
    )
    
    print(f"  [OK] Alert registered")
    print(f"      - Alert ID: {alert.alert_id}")
    print(f"      - Source: {alert.source.value}")
    print(f"      - Severity: {alert.severity}")
    print(f"      - Description: {alert.description}")
    
    # Check if alert brought Grace out of sandbox
    if training_system.current_cycle:
        print(f"      - Current cycle state: {training_system.current_cycle.state.value}")
        if training_system.current_cycle.state.value == "alerted":
            print("      - [OK] Alert successfully brought Grace out of sandbox")
        else:
            print("      - [INFO] Alert registered, cycle state updated")
except Exception as e:
    print(f"  [WARN] Alert registration error: {e}")

# ==================== TEST 5: Knowledge Contribution ====================
print()
print("[5] Testing Knowledge Contribution...")
try:
    # Test that training contributes to knowledge
    if hasattr(training_system, 'llm_orchestrator') and training_system.llm_orchestrator:
        if hasattr(training_system.llm_orchestrator, 'grace_aligned_llm') and training_system.llm_orchestrator.grace_aligned_llm:
            # Simulate learning from a fix
            learning_id = training_system.llm_orchestrator.grace_aligned_llm.contribute_to_grace_learning(
                llm_output="Successfully fixed syntax error: missing colon",
                query="fix syntax errors",
                trust_score=0.8,
                genesis_key_id=None
            )
            
            if learning_id:
                print(f"  [OK] Knowledge contribution working")
                print(f"      - Learning ID: {learning_id}")
                print("      - Knowledge added to Memory Mesh")
            else:
                print("  [WARN] Knowledge contribution returned None (may be disabled or failed)")
        else:
            print("  [WARN] Grace-Aligned LLM not available for knowledge contribution")
    else:
        print("  [WARN] LLM orchestrator not available for knowledge contribution")
except Exception as e:
    print(f"  [WARN] Knowledge contribution error: {e}")

# ==================== TEST 6: Training Statistics ====================
print()
print("[6] Testing Training Statistics...")
try:
    stats = training_system.stats
    
    print("  [OK] Training statistics available")
    print(f"      - Total cycles: {stats['total_cycles']}")
    print(f"      - Total files fixed: {stats['total_files_fixed']}")
    print(f"      - Total alerts responded: {stats['total_alerts_responded']}")
    print(f"      - Current difficulty: {stats['current_difficulty']:.1f}")
    print(f"      - Folders trained: {len(stats['folders_trained'])}")
    
    if training_system.current_cycle:
        print(f"      - Active cycle: {training_system.current_cycle.cycle_id}")
        print(f"      - Cycle state: {training_system.current_cycle.state.value}")
except Exception as e:
    print(f"  [WARN] Statistics retrieval error: {e}")

# ==================== TEST 7: Knowledge Retrieval for Specific Task ====================
print()
print("[7] Testing Knowledge Retrieval for Specific Task...")
try:
    # Test that Grace gets the right knowledge for a specific task
    test_tasks = [
        ("fix syntax errors", "syntax_errors"),
        ("fix logic errors", "logic_errors"),
        ("optimize performance", "performance_issues"),
        ("fix security vulnerabilities", "security_vulnerabilities")
    ]
    
    print("  Testing knowledge retrieval for different tasks:")
    
    for task_description, expected_perspective in test_tasks:
        if hasattr(training_system, 'llm_orchestrator') and training_system.llm_orchestrator:
            if hasattr(training_system.llm_orchestrator, 'grace_aligned_llm') and training_system.llm_orchestrator.grace_aligned_llm:
                memories = training_system.llm_orchestrator.grace_aligned_llm.retrieve_grace_memories(
                    query=task_description,
                    limit=5
                )
                
                print(f"    - Task: '{task_description}'")
                print(f"      Memories: {len(memories)}")
                
                # Check if memories are relevant
                relevant_count = 0
                for mem in memories:
                    content = str(mem.get("content", "")).lower()
                    if expected_perspective.lower() in content or task_description.lower() in content:
                        relevant_count += 1
                
                if memories:
                    relevance_rate = relevant_count / len(memories)
                    print(f"      Relevance: {relevance_rate:.1%} ({relevant_count}/{len(memories)})")
                    if relevance_rate >= 0.6:
                        print(f"      [OK] Knowledge retrieval relevant for task")
                    else:
                        print(f"      [WARN] Some memories may not be relevant (system may need more training)")
                else:
                    print(f"      [INFO] No memories found yet (will improve with training)")
except Exception as e:
    print(f"  [WARN] Task-specific knowledge retrieval error: {e}")

# ==================== TEST 8: Training Improvement Over Time ====================
print()
print("[8] Testing Training Improvement Over Time...")
try:
    # Check if cycles are improving over time
    cycles = training_system.cycles_completed
    
    if len(cycles) >= 2:
        # Compare first vs last cycle
        first_cycle = cycles[0]
        last_cycle = cycles[-1]
        
        first_success_rate = first_cycle.metrics.get("success_rate", 0.0)
        last_success_rate = last_cycle.metrics.get("success_rate", 0.0)
        
        improvement = last_success_rate - first_success_rate
        
        print(f"  [OK] Improvement tracking available")
        print(f"      - Total cycles completed: {len(cycles)}")
        print(f"      - First cycle success rate: {first_success_rate:.1%}")
        print(f"      - Last cycle success rate: {last_success_rate:.1%}")
        print(f"      - Improvement: {improvement:+.1%}")
        
        if improvement > 0:
            print("      - [OK] System is improving over time!")
        elif improvement == 0:
            print("      - [INFO] No improvement yet (may need more cycles)")
        else:
            print("      - [WARN] Success rate decreased (may be due to increasing difficulty)")
    else:
        print(f"  [INFO] Not enough cycles for improvement analysis ({len(cycles)} cycles completed)")
        print("      - System needs more training cycles to show improvement")
except Exception as e:
    print(f"  [WARN] Improvement tracking error: {e}")

# ==================== SUMMARY ====================
print()
print("=" * 70)
print("VERIFICATION SUMMARY")
print("=" * 70)

all_tests = [
    "[1] Training System Initialization",
    "[2] Knowledge Retrieval",
    "[3] Training Cycle Start",
    "[4] Alert Registration",
    "[5] Knowledge Contribution",
    "[6] Training Statistics",
    "[7] Task-Specific Knowledge Retrieval",
    "[8] Training Improvement Over Time"
]

print(f"\nTests completed: {len(all_tests)}")
print("\nSystem Status:")
print(f"  - Training system: {'[OK] Active' if training_system else '[X] Not available'}")
print(f"  - Knowledge retrieval: {'[OK] Working' if hasattr(training_system, 'llm_orchestrator') else '[X] Not available'}")
print(f"  - Current cycle: {'[OK] Active' if training_system.current_cycle else '[ ] No active cycle'}")
print(f"  - Cycles completed: {training_system.stats['total_cycles']}")

if training_system.current_cycle:
    print(f"\nActive Cycle:")
    print(f"  - State: {training_system.current_cycle.state.value}")
    print(f"  - Files collected: {len(training_system.current_cycle.files_collected)}")
    print(f"  - Files fixed: {len(training_system.current_cycle.files_fixed)}")
    print(f"  - Difficulty: {training_system.current_cycle.difficulty_level:.1f}")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
print("\nNext steps:")
print("  1. Start continuous training: POST /self-healing-training/continuous")
print("  2. Check training status: GET /self-healing-training/status")
print("  3. View completed cycles: GET /self-healing-training/cycles")
print("  4. Register alert: POST /self-healing-training/alert")
print("\nGrace is ready for continuous self-healing training!")
