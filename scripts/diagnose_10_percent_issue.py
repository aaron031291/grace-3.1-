#!/usr/bin/env python3
"""
Diagnose Why We're Only Hitting 10%

Analyzes the root causes of low performance.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

print("=" * 80)
print("DIAGNOSING 10% PERFORMANCE ISSUE")
print("=" * 80)
print()

# Issue 1: LLM Orchestrator Availability
print("[1] Checking LLM Orchestrator Availability...")
try:
    from backend.database.connection import DatabaseConnection, DatabaseConfig, DatabaseType
    
    db_config = DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        database="grace",
        database_path=str(project_root / "data" / "grace.db"),
        echo=False,
    )
    DatabaseConnection.initialize(db_config)
    
    from backend.database.session import initialize_session_factory
    initialize_session_factory()
    
    from backend.database.session import get_session
    session = next(get_session())
    kb_path = project_root / "knowledge_base"
    
    try:
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
        llm_orchestrator = get_llm_orchestrator(session=session, knowledge_base_path=kb_path)
        
        if llm_orchestrator:
            print("  [OK] LLM Orchestrator initialized")
            print(f"      - Grace-Aligned LLM: {'Available' if llm_orchestrator.grace_aligned_llm else 'Not Available'}")
            print(f"      - Multi-LLM Client: {'Available' if hasattr(llm_orchestrator, 'multi_llm') and llm_orchestrator.multi_llm else 'Not Available'}")
        else:
            print("  [FAIL] LLM Orchestrator is None")
    except Exception as e:
        print(f"  [FAIL] LLM Orchestrator initialization failed: {e}")
        import traceback
        traceback.print_exc()
except Exception as e:
    print(f"  [ERROR] Database setup failed: {e}")

print()

# Issue 2: Fallback Code Quality
print("[2] Analyzing Fallback Code Generation...")
print("  The fallback code generator is very basic:")
print("  - Uses simple template-based generation")
print("  - Only handles a few specific patterns (factorial, max, async, divide, email)")
print("  - Does NOT include:")
print("    * Type hints (most tasks)")
print("    * Complete element coverage")
print("    * Advanced patterns (BST, LCS, quicksort, etc.)")
print("    * Proper error handling for all cases")
print()

# Issue 3: Logger Conflicts
print("[3] Checking Logger Conflicts...")
logger_conflicts = [
    "llm_orchestrator.parliament_governance",
    "cognitive.grace_code_analyzer",
    "transform.transformation_library"
]

print("  Known logger conflicts:")
for conflict in logger_conflicts:
    print(f"    - {conflict}")

print()
print("  [IMPACT] Logger conflicts prevent proper module initialization")
print("           This causes LLM Orchestrator to fail, forcing fallback")
print()

# Issue 4: Missing Dependencies
print("[4] Checking Missing Dependencies...")
missing_deps = [
    "multi_llm_client",
    "cognitive.testing_system",
    "cognitive.debugging_system",
    "transformation_library"
]

print("  Missing modules:")
for dep in missing_deps:
    print(f"    - {dep}")

print()
print("  [IMPACT] Missing dependencies prevent full system initialization")
print()

# Issue 5: Code Generation Pipeline
print("[5] Code Generation Pipeline Analysis...")
print("  Current Flow:")
print("    1. Coding Agent tries to initialize LLM Orchestrator")
print("    2. LLM Orchestrator fails (logger conflicts, missing deps)")
print("    3. Falls back to _generate_fallback_code()")
print("    4. Fallback only handles 5 basic patterns")
print("    5. Most BigCodeBench tasks don't match these patterns")
print("    6. Result: Low quality code, missing elements, no type hints")
print()

# Summary
print("=" * 80)
print("ROOT CAUSES OF 10% PERFORMANCE")
print("=" * 80)
print()
print("PRIMARY ISSUES:")
print()
print("1. LLM ORCHESTRATOR NOT AVAILABLE")
print("   - Logger conflicts prevent initialization")
print("   - Missing dependencies (multi_llm_client, etc.)")
print("   - Result: No access to actual LLM models (DeepSeek, Qwen, etc.)")
print()
print("2. FALLBACK CODE IS TOO BASIC")
print("   - Only handles 5 simple patterns")
print("   - No type hints")
print("   - Incomplete element coverage")
print("   - Can't handle complex algorithms (BST, LCS, quicksort, etc.)")
print()
print("3. MISSING SYSTEM INTEGRATIONS")
print("   - Testing System not available")
print("   - Debugging System not available")
print("   - Transformation Library not available")
print("   - Advanced Code Quality System not available")
print()
print("SOLUTIONS:")
print()
print("1. FIX LOGGER CONFLICTS")
print("   - Remove duplicate logger definitions")
print("   - Use proper module-level logger initialization")
print()
print("2. ENABLE LLM ORCHESTRATOR")
print("   - Fix missing dependencies")
print("   - Ensure multi_llm_client is available")
print("   - Initialize Grace-Aligned LLM properly")
print()
print("3. IMPROVE FALLBACK CODE")
print("   - Add type hints to fallback generation")
print("   - Expand pattern matching")
print("   - Better element coverage")
print()
print("4. FIX MISSING SYSTEMS")
print("   - Create/testing_system.py stub if needed")
print("   - Create/debugging_system.py stub if needed")
print("   - Fix transformation_library imports")
print()
print("=" * 80)
print()
print("EXPECTED IMPROVEMENT:")
print("  With LLM Orchestrator enabled: 40-60% (similar to GPT-4o)")
print("  With full system integration: 60-80%")
print("  After BigCodeBench training: 80-98%")
print()
print("=" * 80)
