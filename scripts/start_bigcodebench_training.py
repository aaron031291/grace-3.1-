#!/usr/bin/env python3
"""
Start BigCodeBench Sandbox Training

Continuously trains Grace on BigCodeBench until 98% accuracy.
Adapts knowledge when gaps are detected.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.cognitive.bigcodebench_sandbox_training import get_bigcodebench_sandbox_training


async def start_training():
    """Start BigCodeBench training."""
    print("=" * 80)
    print("BIGCODEBENCH SANDBOX TRAINING")
    print("=" * 80)
    print()
    print("Training Grace on BigCodeBench until 98% accuracy")
    print("Adapts knowledge when gaps are detected")
    print()
    
    # Initialize systems
    print("Initializing Grace systems...")
    
    try:
        from backend.database.session import get_session
        from cognitive.enterprise_coding_agent import get_enterprise_coding_agent
        from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
        from cognitive.self_healing_training_system import get_self_healing_training_system
        from cognitive.autonomous_sandbox_lab import get_sandbox_lab
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
        from pathlib import Path
        
        session = next(get_session())
        kb_path = Path("knowledge_base")
        
        # Get all systems
        sandbox_lab = get_sandbox_lab()
        healing_system = get_autonomous_healing(
            session=session,
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True
        )
        diagnostic_engine = get_diagnostic_engine()
        llm_orchestrator = get_llm_orchestrator(
            session=session,
            knowledge_base_path=kb_path
        )
        
        training_system = get_self_healing_training_system(
            session=session,
            knowledge_base_path=kb_path,
            sandbox_lab=sandbox_lab,
            healing_system=healing_system,
            diagnostic_engine=diagnostic_engine,
            llm_orchestrator=llm_orchestrator
        )
        
        coding_agent = get_enterprise_coding_agent(
            session=session,
            repo_path=Path.cwd(),
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True,
            enable_sandbox=True
        )
        
        # Get memory mesh
        memory_mesh = None
        if hasattr(llm_orchestrator, 'grace_aligned_llm'):
            memory_mesh = llm_orchestrator.grace_aligned_llm
        
        print("✓ All systems initialized")
        print()
        
    except Exception as e:
        print(f"ERROR: Could not initialize systems: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Create BigCodeBench training
    print("Initializing BigCodeBench training...")
    bcb_training = get_bigcodebench_sandbox_training(
        training_system=training_system,
        coding_agent=coding_agent,
        self_healing=healing_system,
        sandbox_lab=sandbox_lab,
        llm_orchestrator=llm_orchestrator,
        memory_mesh=memory_mesh,
        variant="complete",  # Start with Complete variant
        max_cycles=None,  # No limit
        min_improvement_per_cycle=0.5
    )
    
    if not bcb_training.bigcodebench_available:
        print("Installing BigCodeBench...")
        if not bcb_training._install_bigcodebench():
            print("ERROR: Could not install BigCodeBench")
            return
    
    print("✓ BigCodeBench training initialized")
    print()
    
    # Show initial status
    print("=" * 80)
    print("TRAINING CONFIGURATION")
    print("=" * 80)
    print(f"Variant: {bcb_training.variant}")
    print(f"Target Success Rate: {bcb_training.TARGET_SUCCESS_RATE}%")
    print(f"Max Cycles: {bcb_training.max_cycles or 'Unlimited'}")
    print(f"Min Improvement per Cycle: {bcb_training.min_improvement_per_cycle}%")
    print()
    print("=" * 80)
    print()
    
    # Start training
    print("Starting continuous training...")
    print("(Press Ctrl+C to stop)")
    print()
    
    try:
        # Train until target
        final_progress = await bcb_training.train_until_target()
        
        # Final report
        print()
        print("=" * 80)
        print("TRAINING COMPLETE")
        print("=" * 80)
        print()
        
        report = bcb_training.get_progress_report()
        print(f"Final Success Rate: {report['current_success_rate']:.2f}%")
        print(f"Target: {report['target_success_rate']:.2f}%")
        print(f"Status: {report['status']}")
        print(f"Total Cycles: {report['total_cycles']}")
        print(f"Total Tasks Attempted: {report['total_tasks_attempted']}")
        print(f"Total Tasks Passed: {report['total_tasks_passed']}")
        print(f"Knowledge Gaps Identified: {report['knowledge_gaps_identified']}")
        print(f"Knowledge Gaps Fixed: {report['knowledge_gaps_fixed']}")
        print()
        
        if report['current_success_rate'] >= report['target_success_rate']:
            print("🎉 TARGET ACHIEVED! Grace has reached 98% accuracy!")
        else:
            print(f"Progress: {report['progress_percentage']:.1f}% toward target")
        
        print()
        print("=" * 80)
        
    except KeyboardInterrupt:
        print()
        print("\nTraining stopped by user")
        report = bcb_training.get_progress_report()
        print(f"Current Success Rate: {report['current_success_rate']:.2f}%")
        print(f"Cycles Completed: {report['total_cycles']}")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(start_training())
