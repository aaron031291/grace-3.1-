"""
Training Knowledge API

API endpoints to view what Grace has learned from self-healing training.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

from cognitive.training_knowledge_tracker import (
    get_training_knowledge_tracker,
    LearnedTopic,
    LearningProgress
)

router = APIRouter(prefix="/training-knowledge", tags=["training-knowledge"])


# ==================== Request/Response Models ====================

class TopicSummaryResponse(BaseModel):
    """Response with topic summary."""
    total_topics: int
    topics_by_category: Dict[str, List[Dict[str, Any]]]
    category_counts: Dict[str, int]
    average_trust_score: float
    total_practice_sessions: int
    mastery_levels: Dict[str, str]
    recently_learned: List[str]
    improving_skills: List[str]


class TopicDetailResponse(BaseModel):
    """Response with detailed topic information."""
    topic_id: str
    topic_name: str
    category: str
    practice_count: int
    success_rate: float
    trust_score: float
    first_learned: datetime
    last_practiced: datetime
    examples: List[str]


# ==================== API Endpoints ====================

@router.get("/topics", response_model=TopicSummaryResponse)
async def get_learned_topics():
    """Get all learned topics from training."""
    try:
        from database.session import get_session
        from pathlib import Path
        
        session = next(get_session())
        kb_path = Path("knowledge_base")
        
        # Import training system if available
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
            training_system = None
        
        tracker = get_training_knowledge_tracker(
            session=session,
            knowledge_base_path=kb_path,
            training_system=training_system
        )
        
        summary = tracker.get_learned_topics_summary()
        
        return TopicSummaryResponse(**summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting learned topics: {str(e)}")


@router.get("/topics/{category}")
async def get_topics_by_category(category: str):
    """Get topics for a specific category."""
    try:
        from database.session import get_session
        from pathlib import Path
        
        session = next(get_session())
        kb_path = Path("knowledge_base")
        
        try:
            from cognitive.self_healing_training_system import get_self_healing_training_system
            # ... (same as above)
            training_system = None
        except:
            training_system = None
        
        tracker = get_training_knowledge_tracker(
            session=session,
            knowledge_base_path=kb_path,
            training_system=training_system
        )
        
        summary = tracker.get_learned_topics_summary()
        category_topics = summary["topics_by_category"].get(category, [])
        
        return {
            "category": category,
            "topics": category_topics,
            "count": len(category_topics),
            "mastery_level": summary["mastery_levels"].get(category, "Novice")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting category topics: {str(e)}")


@router.get("/progress")
async def get_learning_progress():
    """Get learning progress summary."""
    try:
        from database.session import get_session
        from pathlib import Path
        
        session = next(get_session())
        kb_path = Path("knowledge_base")
        
        try:
            from cognitive.self_healing_training_system import get_self_healing_training_system
            training_system = None
        except:
            training_system = None
        
        tracker = get_training_knowledge_tracker(
            session=session,
            knowledge_base_path=kb_path,
            training_system=training_system
        )
        
        progress = tracker.get_learning_progress()
        
        return {
            "total_topics": progress.total_topics,
            "topics_by_category": progress.topics_by_category,
            "average_trust_score": progress.average_trust_score,
            "total_practice_sessions": progress.total_practice_sessions,
            "mastery_levels": progress.mastery_levels,
            "recently_learned": progress.recently_learned,
            "improving_skills": progress.improving_skills
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting learning progress: {str(e)}")


@router.get("/display")
async def display_learned_topics():
    """Display learned topics in human-readable format."""
    try:
        from database.session import get_session
        from pathlib import Path
        
        session = next(get_session())
        kb_path = Path("knowledge_base")
        
        try:
            from cognitive.self_healing_training_system import get_self_healing_training_system
            training_system = None
        except:
            training_system = None
        
        tracker = get_training_knowledge_tracker(
            session=session,
            knowledge_base_path=kb_path,
            training_system=training_system
        )
        
        display_text = tracker.display_learned_topics()
        
        return {
            "display": display_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error displaying topics: {str(e)}")


@router.get("/exceptional-projection")
async def get_exceptional_projection():
    """Get TimeSense projections for reaching exceptional mastery levels."""
    try:
        from pathlib import Path
        
        kb_path = Path("knowledge_base")
        
        # Get TimeSense engine
        try:
            from timesense.engine import get_timesense_engine
            timesense = get_timesense_engine()
        except:
            timesense = None
        
        # Get training system (optional, can work without it)
        training_system = None
        try:
            from database.session import get_session
            from cognitive.self_healing_training_system import get_self_healing_training_system
            
            session = next(get_session())
            # Try to get training system, but don't fail if unavailable
            try:
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
            except:
                pass
        except:
            pass
        
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
        except:
            pass
        
        # Get learning projection
        from cognitive.learning_projection_timesense import get_learning_projection_timesense
        
        projection_system = get_learning_projection_timesense(
            timesense_engine=timesense,
            training_system=training_system,
            knowledge_tracker=knowledge_tracker
        )
        
        # Get cycles and knowledge summary
        cycles = training_system.cycles_completed if training_system else []
        knowledge_summary = knowledge_tracker.get_learned_topics_summary() if knowledge_tracker else {"topics_by_category": {}, "mastery_levels": {}}
        
        # Analyze trajectory
        trajectories = projection_system.analyze_learning_trajectory(cycles)
        
        # Get projections
        projections = projection_system.get_exceptional_level_projections(
            trajectories=trajectories,
            knowledge_summary=knowledge_summary
        )
        
        return {
            "projections": projections,
            "display": projection_system.display_exceptional_projections(projections)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting exceptional projections: {str(e)}")
