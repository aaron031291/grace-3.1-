#!/usr/bin/env python3
"""
Show Exceptional Projection with TimeSense

Displays TimeSense projections for when Grace will reach exceptional mastery levels.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

print("=" * 80)
print("GRACE'S PATH TO EXCEPTIONAL MASTERY (TimeSense Projections)")
print("=" * 80)
print()

try:
    from pathlib import Path
    
    kb_path = Path("knowledge_base")
    
    # Try to get TimeSense engine
    timesense = None
    try:
        from timesense.engine import get_timesense_engine
        timesense = get_timesense_engine()
        print("[INFO] TimeSense engine connected")
    except Exception as e:
        print(f"[INFO] TimeSense engine not available: {e}")
        print("[INFO] Using default cycle duration estimates")
    
    # Try to get training system (optional)
    training_system = None
    try:
        from database.session import get_session
        from cognitive.self_healing_training_system import get_self_healing_training_system
        from cognitive.autonomous_sandbox_lab import get_sandbox_lab
        from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
        
        session = next(get_session())
        sandbox_lab = get_sandbox_lab()
        healing_system = get_autonomous_healing(session=session, trust_level=TrustLevel.MEDIUM_RISK_AUTO)
        diagnostic_engine = get_diagnostic_engine()
        llm_orchestrator = get_llm_orchestrator(session=session, knowledge_base_path=kb_path)
        
        training_system = get_self_healing_training_system(
            session=session,
            knowledge_base_path=kb_path,
            sandbox_lab=sandbox_lab,
            healing_system=healing_system,
            diagnostic_engine=diagnostic_engine,
            llm_orchestrator=llm_orchestrator
        )
    except Exception as e:
        print(f"[INFO] Training system not available: {e}")
    
    # Get knowledge tracker (optional)
    knowledge_tracker = None
    try:
        from database.session import get_session
        from cognitive.training_knowledge_tracker import get_training_knowledge_tracker
        
        session = next(get_session())
        knowledge_tracker = get_training_knowledge_tracker(
            session=session,
            knowledge_base_path=kb_path,
            training_system=training_system
        )
    except Exception as e:
        print(f"[INFO] Knowledge tracker not available: {e}")
    
    # Get learning projection
    from cognitive.learning_projection_timesense import get_learning_projection_timesense
    
    projection_system = get_learning_projection_timesense(
        timesense_engine=timesense,
        training_system=training_system,
        knowledge_tracker=knowledge_tracker
    )
    
    print()
    print("-" * 80)
    print("EXCEPTIONAL LEVEL PROJECTIONS")
    print("-" * 80)
    print()
    
    # Get cycles and knowledge summary
    if training_system and knowledge_tracker:
        cycles = training_system.cycles_completed or []
        knowledge_summary = knowledge_tracker.get_learned_topics_summary()
        
        # Analyze trajectory
        trajectories = projection_system.analyze_learning_trajectory(cycles)
        
        # Get projections
        projections = projection_system.get_exceptional_level_projections(
            trajectories=trajectories,
            knowledge_summary=knowledge_summary
        )
        
        # Display
        display_text = projection_system.display_exceptional_projections(projections)
        print(display_text)
    else:
        print("[INFO] No training cycles found yet.")
        print()
        print("Grace needs to complete training cycles to generate projections.")
        print()
        print("Once cycles are completed, TimeSense will project:")
        print("  - When Grace will reach 90% success rate")
        print("  - When Grace will reach Expert mastery")
        print("  - Learning velocity and acceleration")
        print()
        print("Projections use:")
        print("  - TimeSense cost models for cycle duration")
        print("  - Learning trajectory analysis (velocity, acceleration)")
        print("  - Diminishing returns curve (learning gets harder)")
        print()
        print("=" * 80)
        print("API Endpoint: GET /training-knowledge/exceptional-projection")
        print("=" * 80)
    
except Exception as e:
    print(f"[ERROR] Failed to generate projections: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
