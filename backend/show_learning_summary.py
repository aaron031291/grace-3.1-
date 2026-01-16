"""
Show what Grace's self-learning system has learned so far.

Queries the database for learning examples, patterns, and knowledge.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent))

def check_learning_database():
    """Check what Grace has learned from the database."""
    
    print("=" * 80)
    print("GRACE SELF-LEARNING SUMMARY")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    try:
        from database.config import DatabaseConfig
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory, get_db
        from cognitive.learning_memory import LearningExample
        from sqlalchemy import func, and_
        
        # Initialize database
        db_config = DatabaseConfig()
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())
        
        # Check if learning_examples table exists
        try:
            total_examples = session.query(func.count(LearningExample.id)).scalar() or 0
            
            print(f"LEARNING STATISTICS")
            print("-" * 80)
            print(f"Total Learning Examples: {total_examples}")
            
            if total_examples == 0:
                print()
                print("[!] No learning examples found in the database yet.")
                print()
                print("This means:")
                print("  - Grace hasn't started autonomous learning yet, OR")
                print("  - The learning_examples table doesn't exist yet, OR")
                print("  - Learning data hasn't been stored yet")
                print()
                print("To start learning:")
                print("  1. Start the autonomous learning system:")
                print("     python backend/start_autonomous_learning_simple.py")
                print("  2. Ingest some files for Grace to study")
                print("  3. The system will automatically create learning examples")
                print()
                session.close()
                return
            
            # Group by example type
            type_counts = session.query(
                LearningExample.example_type,
                func.count(LearningExample.id)
            ).group_by(LearningExample.example_type).all()
            
            print()
            print("Learning Examples by Type:")
            for example_type, count in type_counts:
                print(f"  - {example_type}: {count}")
            
            # Get high-trust examples (trust_score >= 0.7)
            high_trust = session.query(func.count(LearningExample.id)).filter(
                LearningExample.trust_score >= 0.7
            ).scalar() or 0
            
            # Get validated examples
            validated = session.query(func.count(LearningExample.id)).filter(
                LearningExample.times_validated > 0
            ).scalar() or 0
            
            # Get recent examples (last 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent = session.query(func.count(LearningExample.id)).filter(
                LearningExample.created_at >= cutoff_time
            ).scalar() or 0
            
            print()
            print(f"High-Trust Examples (trust >= 0.7): {high_trust}")
            print(f"Validated Examples: {validated}")
            print(f"Recent Examples (last 24h): {recent}")
            
            # Show recent learning examples
            print()
            print("RECENT LEARNING EXAMPLES")
            print("-" * 80)
            
            recent_examples = session.query(LearningExample).order_by(
                LearningExample.created_at.desc()
            ).limit(10).all()
            
            if recent_examples:
                for i, example in enumerate(recent_examples, 1):
                    timestamp = example.created_at.strftime("%Y-%m-%d %H:%M:%S") if example.created_at else "Unknown"
                    
                    # Extract topic/context from input_context
                    context = example.input_context if example.input_context else {}
                    topic = context.get('topic', context.get('anomaly_type', example.example_type))
                    
                    print(f"\n{i}. {example.example_type}")
                    print(f"   Time: {timestamp}")
                    print(f"   Topic: {topic}")
                    print(f"   Trust Score: {example.trust_score:.2f}")
                    print(f"   Outcome Quality: {example.outcome_quality:.2f}")
                    print(f"   Validated: {example.times_validated}x | Invalidated: {example.times_invalidated}x")
                    
                    if example.actual_output:
                        if isinstance(example.actual_output, dict):
                            if example.actual_output.get('success'):
                                print(f"   Result: [SUCCESS]")
                            elif example.actual_output.get('success') is False:
                                print(f"   Result: [FAILED]")
            else:
                print("No recent examples found.")
            
            # Analyze learning topics
            print()
            print("LEARNING TOPICS ANALYSIS")
            print("-" * 80)
            
            # Get unique topics from input_context
            all_examples = session.query(LearningExample).all()
            topics = {}
            
            for ex in all_examples:
                ctx = ex.input_context if ex.input_context else {}
                topic = ctx.get('topic', ctx.get('anomaly_type', ctx.get('action_taken', ex.example_type)))
                
                if topic not in topics:
                    topics[topic] = {
                        'count': 0,
                        'avg_trust': 0.0,
                        'success_count': 0
                    }
                
                topics[topic]['count'] += 1
                topics[topic]['avg_trust'] += ex.trust_score
                
                if ex.actual_output and isinstance(ex.actual_output, dict):
                    if ex.actual_output.get('success'):
                        topics[topic]['success_count'] += 1
            
            # Calculate averages
            for topic, data in topics.items():
                if data['count'] > 0:
                    data['avg_trust'] = data['avg_trust'] / data['count']
            
            if topics:
                print(f"Topics Studied: {len(topics)}")
                print()
                print("Top Topics:")
                sorted_topics = sorted(topics.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
                for topic, data in sorted_topics:
                    success_rate = (data['success_count'] / data['count'] * 100) if data['count'] > 0 else 0
                    print(f"  - {topic}:")
                    print(f"    Examples: {data['count']} | Avg Trust: {data['avg_trust']:.2f} | Success Rate: {success_rate:.1f}%")
            
            session.close()
            
        except Exception as e:
            if "no such table" in str(e).lower():
                print("[!] Learning tables don't exist yet.")
                print()
                print("The learning_examples table hasn't been created.")
                print("To set up learning:")
                print("  1. Run the migration:")
                print("     python backend/database/migrate_add_memory_mesh.py")
                print("  2. Start the autonomous learning system")
                print()
            else:
                raise
        
    except Exception as e:
        print(f"Error querying learning data: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("Note: Learning tables may not exist yet.")
        print("      Run: python backend/database/migrate_add_memory_mesh.py")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    check_learning_database()
