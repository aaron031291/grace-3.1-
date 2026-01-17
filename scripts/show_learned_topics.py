#!/usr/bin/env python3
"""
Show Learned Topics

Displays what Grace has learned from self-healing training practice.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

print("=" * 70)
print("GRACE'S LEARNED TOPICS FROM SELF-HEALING TRAINING")
print("=" * 70)
print()

try:
    from database.session import get_session
    from pathlib import Path
    
    # Try to initialize database
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.initialize()
    except:
        pass
    
    session = next(get_session())
    kb_path = Path("knowledge_base")
    
    # Import training knowledge tracker
    from cognitive.training_knowledge_tracker import get_training_knowledge_tracker
    
    # Try to get training system
    training_system = None
    try:
        from cognitive.self_healing_training_system import get_self_healing_training_system
        from cognitive.autonomous_sandbox_lab import get_sandbox_lab
        from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
        
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
    
    # Get tracker
    tracker = get_training_knowledge_tracker(
        session=session,
        knowledge_base_path=kb_path,
        training_system=training_system
    )
    
    # Display learned topics
    display_text = tracker.display_learned_topics()
    print(display_text)
    
    # Get detailed summary
    print()
    print("=" * 70)
    print("DETAILED SUMMARY")
    print("=" * 70)
    print()
    
    summary = tracker.get_learned_topics_summary()
    
    print(f"Total Topics: {summary['total_topics']}")
    print(f"Average Trust Score: {summary['average_trust_score']:.2f}")
    print(f"Total Practice Sessions: {summary['total_practice_sessions']}")
    print()
    
    print("Category Breakdown:")
    for category, count in summary["category_counts"].items():
        mastery = summary["mastery_levels"].get(category, "Novice")
        print(f"  - {category.title()}: {count} topics ({mastery} mastery)")
    
    if summary["recently_learned"]:
        print()
        print("Recently Learned (Last 7 Days):")
        for i, topic in enumerate(summary["recently_learned"][:10], 1):
            print(f"  {i}. {topic}")
    
    if summary["improving_skills"]:
        print()
        print("Improving Skills:")
        for skill in summary["improving_skills"]:
            print(f"  - {skill.title()} (success rate improving)")
    
except Exception as e:
    print(f"[ERROR] Failed to display learned topics: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 70)
print("Use API endpoint: GET /training-knowledge/topics")
print("Or visit: http://localhost:8000/training-knowledge/display")
print("=" * 70)
