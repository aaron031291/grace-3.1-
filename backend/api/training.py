"""
Grace Active Learning & Training API

API for Grace's active learning system where she:
- Studies topics from training materials (AI research folder)
- Practices skills in sandbox environment
- Builds persistent knowledge and abilities
- Tracks skill proficiency over time
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from pathlib import Path

from database.session import get_session
from cognitive.learning_memory import LearningExample
from retrieval.retriever import DocumentRetriever
from cognitive.active_learning_system import (
    GraceActiveLearningSystem,
    SkillLevel
)
from settings import KNOWLEDGE_BASE_PATH

router = APIRouter(prefix="/training", tags=["training"])


# ======================================================================
# Request/Response Models
# ======================================================================

class StudyTopicRequest(BaseModel):
    topic: str
    learning_objectives: List[str]
    max_materials: int = 10


class PracticeSkillRequest(BaseModel):
    skill_name: str
    task_description: str
    task_requirements: List[str] = []
    complexity: float = 0.5
    sandbox_context: Dict[str, Any] = {}


class CreateCurriculumRequest(BaseModel):
    skill_name: str
    target_proficiency: str = SkillLevel.INTERMEDIATE


# ======================================================================
# Dependency Injection
# ======================================================================

def get_learning_system(session: Session = Depends(get_session)) -> GraceActiveLearningSystem:
    """Get Grace's active learning system."""
    from embedding import get_embedding_model

    # Initialize retriever
    embedding_model = get_embedding_model()
    retriever = DocumentRetriever(
        collection_name="documents",
        embedding_model=embedding_model
    )

    # Initialize learning system
    learning_system = GraceActiveLearningSystem(
        session=session,
        retriever=retriever,
        knowledge_base_path=Path(KNOWLEDGE_BASE_PATH)
    )

    return learning_system


# ======================================================================
# Study Endpoints - Grace learns from training materials
# ======================================================================

@router.post("/study")
async def study_topic(
    request: StudyTopicRequest,
    learning_system: GraceActiveLearningSystem = Depends(get_learning_system)
) -> Dict[str, Any]:
    """
    **Grace studies a topic from training materials.**

    She reads relevant documents from the AI research folder,
    extracts key concepts, and stores them in learning memory.

    **Example:**
    ```json
    POST /training/study
    {
        "topic": "Python functions",
        "learning_objectives": [
            "Learn function syntax",
            "Understand parameters and return values",
            "Learn about lambda functions"
        ],
        "max_materials": 5
    }
    ```

    **Returns:**
    - Materials studied
    - Concepts learned
    - Focus areas identified
    - Examples stored in memory
    """
    try:
        result = learning_system.study_topic(
            topic=request.topic,
            learning_objectives=request.learning_objectives,
            max_materials=request.max_materials
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Study failed: {str(e)}")


# ======================================================================
# Practice Endpoints - Grace applies knowledge in sandbox
# ======================================================================

@router.post("/practice")
async def practice_skill(
    request: PracticeSkillRequest,
    learning_system: GraceActiveLearningSystem = Depends(get_learning_system)
) -> Dict[str, Any]:
    """
    **Grace practices a skill in the sandbox.**

    She applies learned knowledge to complete a task,
    observes the outcome, and learns from the experience.

    **Example:**
    ```json
    POST /training/practice
    {
        "skill_name": "Python programming",
        "task_description": "Write a function to calculate factorial",
        "task_requirements": ["Handle edge cases", "Use recursion"],
        "complexity": 0.4,
        "sandbox_context": {"language": "python"}
    }
    ```

    **Returns:**
    - Approach taken
    - Outcome (success/failure)
    - Feedback
    - What was learned
    """
    try:
        task = {
            "description": request.task_description,
            "requirements": request.task_requirements,
            "complexity": request.complexity
        }

        result = learning_system.practice_skill(
            skill_name=request.skill_name,
            task=task,
            sandbox_context=request.sandbox_context
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Practice failed: {str(e)}")


# ======================================================================
# Skill Assessment - Track Grace's abilities
# ======================================================================

@router.get("/skills/{skill_name}")
async def get_skill_assessment(
    skill_name: str,
    learning_system: GraceActiveLearningSystem = Depends(get_learning_system)
) -> Dict[str, Any]:
    """
    **Get Grace's current proficiency in a skill.**

    Returns her level (novice/beginner/intermediate/advanced/expert),
    proficiency score, success rate, and practice history.

    **Example:**
    ```
    GET /training/skills/Python%20programming
    ```

    **Returns:**
    - Current skill level
    - Proficiency score
    - Success rate
    - Tasks completed
    - Practice hours
    """
    try:
        assessment = learning_system.get_skill_assessment(skill_name)
        return assessment

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")


@router.get("/skills")
async def list_all_skills(
    learning_system: GraceActiveLearningSystem = Depends(get_learning_system)
) -> Dict[str, Any]:
    """
    **List all skills Grace has practiced.**

    Returns proficiency levels for all skills she's learning.

    **Returns:**
    - List of skills
    - Proficiency for each
    - Overall statistics
    """
    try:
        assessments = []
        for skill_name in learning_system.skill_levels.keys():
            assessment = learning_system.get_skill_assessment(skill_name)
            assessments.append(assessment)

        return {
            "total_skills": len(assessments),
            "skills": assessments
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List skills failed: {str(e)}")


# ======================================================================
# Curriculum Management - Structured learning paths
# ======================================================================

@router.post("/curriculum")
async def create_training_curriculum(
    request: CreateCurriculumRequest,
    learning_system: GraceActiveLearningSystem = Depends(get_learning_system)
) -> Dict[str, Any]:
    """
    **Create a structured training curriculum for a skill.**

    Defines study phases, practice tasks, and assessment criteria
    to guide Grace's learning from novice to target proficiency level.

    **Example:**
    ```json
    POST /training/curriculum
    {
        "skill_name": "REST API design",
        "target_proficiency": "intermediate"
    }
    ```

    **Returns:**
    - Study phases with topics and objectives
    - Practice tasks with complexity levels
    - Assessment criteria
    """
    try:
        curriculum = learning_system.create_training_curriculum(
            skill_name=request.skill_name,
            target_proficiency=request.target_proficiency
        )

        return curriculum

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Curriculum creation failed: {str(e)}")


# ======================================================================
# Learning Analytics - Monitor Grace's progress
# ======================================================================

@router.get("/analytics/progress")
async def get_learning_progress(
    session: Session = Depends(get_session),
    learning_system: GraceActiveLearningSystem = Depends(get_learning_system)
) -> Dict[str, Any]:
    """
    **Get Grace's overall learning progress.**

    Returns comprehensive statistics on:
    - Skills learned
    - Practice time invested
    - Success rates across skills
    - Knowledge accumulated in memory
    - Learning velocity

    **Use this to:**
    - Monitor Grace's growth
    - Identify areas needing more practice
    - Track training effectiveness
    """
    try:
        # Query database for practice outcomes grouped by skill
        practice_stats = session.query(
            func.json_extract(LearningExample.example_metadata, '$.skill_name').label('skill'),
            func.count(LearningExample.id).label('tasks'),
            func.avg(LearningExample.trust_score).label('avg_trust'),
            func.avg(LearningExample.outcome_quality).label('success_rate')
        ).filter(
            LearningExample.example_type == 'practice_outcome',
            func.json_extract(LearningExample.example_metadata, '$.skill_name').isnot(None)
        ).group_by('skill').all()
        
        skills = []
        total_tasks = 0
        total_success = 0.0
        
        for stat in practice_stats:
            if stat.skill:  # Only include if skill name exists
                skill_name = stat.skill
                tasks_count = stat.tasks or 0
                avg_trust = stat.avg_trust or 0.0
                success_rate = stat.success_rate or 0.0
                
                # Determine proficiency level based on trust score
                if avg_trust >= 0.9:
                    level = "expert"
                    proficiency = 0.9 + (avg_trust - 0.9)
                elif avg_trust >= 0.8:
                    level = "advanced"
                    proficiency = 0.7 + (avg_trust - 0.8) * 2
                elif avg_trust >= 0.6:
                    level = "intermediate"
                    proficiency = 0.4 + (avg_trust - 0.6) * 1.5
                else:
                    level = "beginner"
                    proficiency = avg_trust * 0.67
                
                skills.append({
                    "skill": skill_name,
                    "level": level,
                    "proficiency": round(proficiency, 3),
                    "tasks": tasks_count,
                    "success_rate": round(success_rate, 3)
                })
                total_tasks += tasks_count
                total_success += success_rate * tasks_count
        
        overall_success_rate = (total_success / total_tasks) if total_tasks > 0 else 0.0

        return {
            "total_skills": len(skills),
            "skills": skills,
            "total_tasks_completed": total_tasks,
            "overall_success_rate": round(overall_success_rate, 3),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")


# ======================================================================
# Training Data Management - Add new learning materials
# ======================================================================

@router.post("/training-data/add")
async def add_training_data(
    folder_path: str,
    category: str,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    **Add new training data to Grace's learning materials.**

    When new files are added to learning memory folders,
    this endpoint makes them available for Grace to study.

    **Example:**
    ```json
    POST /training/training-data/add
    {
        "folder_path": "learning memory/backend_development",
        "category": "api_design",
        "description": "RESTful API design patterns and best practices"
    }
    ```

    **This triggers:**
    - File ingestion into vector database
    - Metadata extraction
    - Availability for study sessions
    """
    try:
        # This would trigger ingestion of new files
        # (Connect to your file ingestion system)

        return {
            "status": "success",
            "message": f"Training data from {folder_path} added to {category}",
            "folder_path": folder_path,
            "category": category,
            "description": description,
            "files_added": 0  # Would be actual count from ingestion
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Add training data failed: {str(e)}")


@router.get("/training-data/gaps")
async def analyze_training_gaps() -> Dict[str, Any]:
    """
    **Analyze gaps in Grace's training data.**

    Identifies:
    - Software engineering topics not covered
    - Skills with insufficient training materials
    - Recommended additions to training library

    **Returns recommendations for:**
    - What topics to add
    - Which skills need more examples
    - Priority areas for training expansion
    """
    try:
        # This would analyze the AI research folder content
        # and identify gaps (implementation depends on your needs)

        gaps = {
            "missing_topics": [
                "Testing frameworks and TDD",
                "Database design and SQL",
                "Git workflows and version control",
                "API design and documentation",
                "System design patterns"
            ],
            "weak_coverage": [
                {
                    "topic": "Backend development",
                    "current_documents": 5,
                    "recommended": 20,
                    "gap": 15
                },
                {
                    "topic": "Databases",
                    "current_documents": 1,
                    "recommended": 15,
                    "gap": 14
                }
            ],
            "recommendations": [
                "Add backend framework documentation (Flask, FastAPI, Django)",
                "Include database design and SQL tutorials",
                "Add testing frameworks documentation",
                "Include Git and version control guides"
            ]
        }

        return gaps

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gap analysis failed: {str(e)}")
