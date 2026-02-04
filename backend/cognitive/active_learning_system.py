"""
Grace Active Learning System

Transforms passive RAG into active learning where Grace:
1. Studies training materials from AI research folder
2. Practices skills in the sandbox environment
3. Learns from successes and failures
4. Builds persistent knowledge and abilities

Architecture:
- AI Research Folder = Curriculum (what to learn)
- Cognitive Framework = How to think and learn
- Learning Memory = What has been learned
- Sandbox = Practice environment
- File Manager = Her world to interact with
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.orm import Session
import json
import logging

from cognitive.engine import CognitiveEngine, DecisionContext
from cognitive.learning_memory import LearningMemoryManager, TrustScorer, LearningExample, LearningPattern
from cognitive.predictive_context_loader import PredictiveContextLoader
from retrieval.retriever import DocumentRetriever
from database.session import get_session

logger = logging.getLogger(__name__)


class TrainingSession:
    """
    Represents a focused training session where Grace learns a specific skill.
    """
    def __init__(
        self,
        session_id: str,
        skill_name: str,
        learning_objectives: List[str],
        training_materials: List[str],  # Document IDs from AI research
        practice_tasks: List[Dict[str, Any]],
        success_criteria: Dict[str, Any]
    ):
        self.session_id = session_id
        self.skill_name = skill_name
        self.learning_objectives = learning_objectives
        self.training_materials = training_materials
        self.practice_tasks = practice_tasks
        self.success_criteria = success_criteria

        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.examples_learned: List[str] = []
        self.tasks_completed: List[Dict] = []
        self.performance_metrics: Dict = {}


class SkillLevel:
    """Tracks Grace's proficiency in a specific skill."""

    NOVICE = "novice"           # Just learning
    BEGINNER = "beginner"       # Basic understanding
    INTERMEDIATE = "intermediate"  # Can apply with guidance
    ADVANCED = "advanced"       # Can apply independently
    EXPERT = "expert"           # Can teach others

    def __init__(
        self,
        skill_name: str,
        current_level: str = NOVICE,
        proficiency_score: float = 0.0,
        practice_hours: float = 0.0,
        success_rate: float = 0.0,
        tasks_completed: int = 0
    ):
        self.skill_name = skill_name
        self.current_level = current_level
        self.proficiency_score = proficiency_score
        self.practice_hours = practice_hours
        self.success_rate = success_rate
        self.tasks_completed = tasks_completed


class GraceActiveLearningSystem:
    """
    Active learning system that trains Grace using cognitive framework.

    Core capabilities:
    1. **Study**: Extract knowledge from training materials
    2. **Practice**: Apply knowledge in sandbox
    3. **Learn**: Build persistent skills from experience
    4. **Adapt**: Improve based on outcomes
    """

    def __init__(
        self,
        session: Session,
        retriever: DocumentRetriever,
        knowledge_base_path: Path
    ):
        self.session = session
        self.retriever = retriever
        self.knowledge_base_path = knowledge_base_path

        # Initialize cognitive components
        self.cognitive_engine = CognitiveEngine(enable_strict_mode=False)
        self.learning_manager = LearningMemoryManager(
            session=session,
            knowledge_base_path=knowledge_base_path
        )
        self.trust_scorer = TrustScorer()

        # Initialize predictive context loader (proactive fetching)
        self.predictive_loader = PredictiveContextLoader(
            session=session,
            retriever=retriever,
            cache_ttl_minutes=30
        )

        # Training state
        self.current_session: Optional[TrainingSession] = None
        self.skill_levels: Dict[str, SkillLevel] = {}

    # ======================================================================
    # PHASE 1: STUDY - Extract knowledge from training materials
    # ======================================================================

    def study_topic(
        self,
        topic: str,
        learning_objectives: List[str],
        max_materials: int = 10
    ) -> Dict[str, Any]:
        """
        Study a topic from training materials WITH PREDICTIVE FETCHING.

        Grace reads relevant documents, extracts key concepts,
        builds internal knowledge representation, AND proactively
        pre-fetches related topics she'll likely need next.

        Args:
            topic: What to study (e.g., "Python functions", "REST APIs")
            learning_objectives: What Grace should learn
            max_materials: Max training documents to study

        Returns:
            Study results with extracted concepts, examples, AND prefetched contexts
        """
        logger.info(f"Grace studying topic: {topic}")

        # Use cognitive engine to analyze learning objectives
        context = DecisionContext(
            problem_statement=f"Study {topic}: {', '.join(learning_objectives)}",
            goal="Extract concepts, patterns, and examples for long-term learning",
            complexity_score=0.7,
            metadata={
                "task_type": "learning",
                "time_pressure": 0.0,
                "user_intent": "skill_building"
            }
        )

        # 🔮 PREDICTIVE FETCHING: Pre-load related topics
        predictive_result = self.predictive_loader.process_query(
            query=topic,
            context={
                "task_type": "learning",
                "complexity": 0.7
            }
        )

        # OODA Loop: Observe - What materials are available?
        study_materials = self._find_relevant_training_materials(topic, max_materials)

        # OODA Loop: Orient - What are the key concepts?
        concepts = self._extract_key_concepts(study_materials, learning_objectives)

        # OODA Loop: Decide - What should Grace focus on?
        focus_areas = self._prioritize_learning_focus(concepts, learning_objectives)

        # OODA Loop: Act - Store learned concepts in memory
        examples_created = self._store_learning_examples(
            topic=topic,
            concepts=concepts,
            materials=study_materials
        )

        # Get prefetched contexts
        prefetched_topics = predictive_result.get('ready_topics', [])
        prefetch_stats = predictive_result.get('statistics', {})

        return {
            "topic": topic,
            "materials_studied": len(study_materials),
            "concepts_learned": len(concepts),
            "focus_areas": focus_areas,
            "examples_stored": len(examples_created),
            "prefetched_topics": prefetched_topics,  # Topics ready for next query
            "prefetch_statistics": prefetch_stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _find_relevant_training_materials(
        self,
        topic: str,
        max_materials: int
    ) -> List[Dict[str, Any]]:
        """Find documents from AI research folder relevant to topic."""
        # Use retriever to find relevant chunks
        results = self.retriever.retrieve(
            query=topic,
            limit=max_materials * 5,  # Get more chunks, consolidate to documents
            score_threshold=0.4
        )

        # Group by document
        materials_by_doc = {}
        # Results is a list of chunks, not a dict
        for chunk in results:
            doc_id = chunk.get('document_id')
            if doc_id not in materials_by_doc:
                materials_by_doc[doc_id] = {
                    'document_id': doc_id,
                    'source': chunk.get('metadata', {}).get('source', ''),
                    'chunks': [],
                    'relevance_score': 0.0
                }
            materials_by_doc[doc_id]['chunks'].append(chunk)
            materials_by_doc[doc_id]['relevance_score'] = max(
                materials_by_doc[doc_id]['relevance_score'],
                chunk.get('score', 0.0)
            )

        # Sort by relevance and take top materials
        materials = sorted(
            materials_by_doc.values(),
            key=lambda x: x['relevance_score'],
            reverse=True
        )[:max_materials]

        return materials

    def _extract_key_concepts(
        self,
        materials: List[Dict[str, Any]],
        learning_objectives: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Extract key concepts from training materials.

        This is where Grace identifies:
        - Definitions and terminology
        - Code patterns and examples
        - Best practices and anti-patterns
        - Prerequisites and dependencies
        """
        concepts = []

        for material in materials:
            for chunk in material['chunks']:
                text = chunk.get('text', '')

                # Extract concepts relevant to learning objectives
                # (In production, this would use NLP/LLM to extract structured concepts)
                concept = {
                    'text': text,
                    'source_document': material['document_id'],
                    'source_file': material['source'],
                    'relevance_score': chunk.get('score', 0.0),
                    'extracted_at': datetime.utcnow().isoformat(),
                    'learning_objectives': learning_objectives
                }
                concepts.append(concept)

        return concepts

    def _prioritize_learning_focus(
        self,
        concepts: List[Dict[str, Any]],
        learning_objectives: List[str]
    ) -> List[str]:
        """
        Determine what Grace should focus on first.

        Uses cognitive engine to prioritize based on:
        - Learning objectives
        - Current skill level
        - Concept dependencies
        """
        # Sort concepts by relevance
        sorted_concepts = sorted(
            concepts,
            key=lambda x: x['relevance_score'],
            reverse=True
        )

        # Extract focus areas (simplified - would use NLP in production)
        focus_areas = []
        for objective in learning_objectives[:3]:  # Top 3 objectives
            focus_areas.append(objective)

        return focus_areas

    def _store_learning_examples(
        self,
        topic: str,
        concepts: List[Dict[str, Any]],
        materials: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Store learned concepts as learning examples in memory WITH TRUST SCORES.

        Trust scoring includes:
        1. **Source Reliability** - Quality of training material
        2. **Data Confidence** - How accurate/relevant the content is
        3. **Operational Confidence** - Grace's ability to apply this knowledge
        4. **Consistency** - Alignment with existing knowledge
        """
        example_ids = []

        for concept in concepts[:20]:  # Store top 20 concepts
            # 1. Source Reliability (based on document type/source)
            source_reliability = self._assess_source_reliability(concept['source_file'])

            # 2. Data Confidence (relevance from retrieval)
            data_confidence = concept['relevance_score']

            # 3. Operational Confidence (starts low, increases with practice)
            operational_confidence = 0.3  # Grace hasn't practiced this yet

            # 4. Consistency with existing knowledge
            consistency_score = self._assess_consistency(topic, concept['text'])

            # Calculate overall trust score
            trust_score = self.trust_scorer.calculate_trust_score(
                source="training_material",
                outcome_quality=data_confidence,
                consistency_score=consistency_score,
                validation_history={'validated': 0, 'invalidated': 0},
                age_days=0.0
            )

            example = LearningExample(
                example_type="knowledge_extraction",
                input_context={
                    "topic": topic,
                    "source": concept['source_file'],
                    "learning_objective": concept.get('learning_objectives', [])
                },
                expected_output={
                    "concept": concept['text'],
                    "relevance": concept['relevance_score'],
                    "operational_confidence": operational_confidence,
                    "data_confidence": data_confidence
                },
                trust_score=trust_score,
                source_reliability=source_reliability,
                outcome_quality=data_confidence,
                consistency_score=consistency_score,
                source="training_material",
                file_path=concept['source_file'],
                example_metadata={
                    "operational_confidence": operational_confidence,
                    "data_confidence": data_confidence,
                    "requires_practice": True
                }
            )

            self.session.add(example)
            self.session.commit()
            example_ids.append(str(example.id))

        return example_ids

    def _assess_source_reliability(self, source_file: str) -> float:
        """
        Assess reliability of training material source.

        **Scoring:**
        - Academic papers / peer-reviewed: 0.9-1.0
        - Technical books: 0.8-0.9
        - Official documentation: 0.8-0.9
        - Tutorials / guides: 0.6-0.7
        - Unknown source: 0.5
        """
        source_lower = source_file.lower()

        # Peer-reviewed research papers
        if any(x in source_lower for x in ['ieee', 'acm', 'arxiv', 'journal', 'conference', 'research', 'paper']):
            return 0.95

        # Technical books from reputable publishers
        if any(x in source_lower for x in ['oreilly', 'manning', 'apress', 'packt', 'cambridge', 'mit']):
            return 0.90

        # General PDF books
        if '.pdf' in source_lower and any(x in source_lower for x in ['book', 'guide', 'textbook']):
            return 0.85

        # Official documentation
        if any(x in source_lower for x in ['docs', 'documentation', 'official', 'reference']):
            return 0.80

        # Tutorials and educational content
        if any(x in source_lower for x in ['tutorial', 'course', 'learn', 'training', 'beginner']):
            return 0.70

        # Default for AI research folder (assume good quality)
        return 0.75

    def _assess_consistency(self, topic: str, concept_text: str) -> float:
        """
        Assess how consistent new concept is with existing knowledge.

        **Checks:**
        - Does it contradict existing examples?
        - Does it align with established patterns?
        - Is it mainstream or outlier knowledge?
        """
        # Get existing examples for this topic
        existing = self.session.query(LearningExample).filter(
            LearningExample.input_context.contains({"topic": topic})
        ).limit(10).all()

        if not existing:
            return 0.6  # No existing knowledge, moderate trust

        # Use semantic similarity to compare concepts
        try:
            # Get embedding for new concept
            if hasattr(self.retriever, 'embedding_model') and self.retriever.embedding_model:
                new_embedding = self.retriever.embedding_model.embed(concept_text)

                similarities = []
                for example in existing:
                    # Extract text from existing example
                    existing_text = ""
                    if example.input_context:
                        existing_text = json.dumps(example.input_context)
                    if example.expected_output:
                        existing_text += " " + json.dumps(example.expected_output)

                    if existing_text.strip():
                        existing_embedding = self.retriever.embedding_model.embed(existing_text)

                        # Calculate cosine similarity
                        similarity = self._cosine_similarity(new_embedding, existing_embedding)
                        similarities.append(similarity)

                if similarities:
                    avg_similarity = sum(similarities) / len(similarities)
                    # High similarity = consistent with existing knowledge
                    # Map similarity (0-1) to trust score (0.5-0.9)
                    return 0.5 + (avg_similarity * 0.4)

        except Exception as e:
            logger.debug(f"Semantic similarity assessment failed: {e}")

        # Fallback: assume reasonable consistency
        return 0.7

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    # ======================================================================
    # PHASE 2: PRACTICE - Apply knowledge in sandbox
    # ======================================================================

    def practice_skill(
        self,
        skill_name: str,
        task: Dict[str, Any],
        sandbox_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Practice a skill in the sandbox environment.

        Grace attempts a task using learned knowledge.
        Records outcome for learning.

        Args:
            skill_name: Skill being practiced
            task: Task description and requirements
            sandbox_context: Sandbox state (files, environment, etc.)

        Returns:
            Practice result with outcome and feedback
        """
        logger.info(f"Grace practicing skill: {skill_name}")

        # Use cognitive engine for decision-making
        context = DecisionContext(
            problem_statement=task.get('description', ''),
            goal="Practice skill and validate learning through execution",
            complexity_score=task.get('complexity', 0.5),
            metadata={
                "task_type": "skill_practice",
                "time_pressure": 0.3,
                "user_intent": "skill_building"
            }
        )

        # OODA Loop: Observe - What is the task?
        task_analysis = self._analyze_practice_task(task, sandbox_context)

        # OODA Loop: Orient - What knowledge applies?
        relevant_knowledge = self._retrieve_applicable_knowledge(skill_name, task_analysis)

        # OODA Loop: Decide - What approach to take?
        approach = self._decide_practice_approach(task_analysis, relevant_knowledge)

        # OODA Loop: Act - Execute in sandbox (simulated here)
        outcome = self._execute_practice_task(task, approach, sandbox_context)

        # Learn from the outcome
        self._learn_from_practice(skill_name, task, approach, outcome)

        return {
            "skill": skill_name,
            "task": task.get('description'),
            "approach": approach,
            "outcome": outcome,
            "success": outcome.get('success', False),
            "feedback": outcome.get('feedback', ''),
            "timestamp": datetime.utcnow().isoformat()
        }

    def _analyze_practice_task(
        self,
        task: Dict[str, Any],
        sandbox_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze what the task requires."""
        return {
            "description": task.get('description', ''),
            "requirements": task.get('requirements', []),
            "complexity": task.get('complexity', 0.5),
            "sandbox_state": sandbox_context
        }

    def _retrieve_applicable_knowledge(
        self,
        skill_name: str,
        task_analysis: Dict[str, Any]
    ) -> List[LearningExample]:
        """
        Retrieve learned knowledge applicable to this task.

        Queries learning memory for relevant examples.
        """
        # Query learning examples
        examples = self.session.query(LearningExample).filter(
            LearningExample.example_type == "knowledge_extraction"
        ).order_by(
            LearningExample.trust_score.desc()
        ).limit(10).all()

        return examples

    def _decide_practice_approach(
        self,
        task_analysis: Dict[str, Any],
        knowledge: List[LearningExample]
    ) -> Dict[str, Any]:
        """
        Decide how to approach the practice task.

        Based on learned knowledge and task requirements.
        """
        return {
            "strategy": "apply_learned_patterns",
            "knowledge_used": [str(ex.id) for ex in knowledge[:5]],
            "estimated_success_rate": 0.6
        }

    def _execute_practice_task(
        self,
        task: Dict[str, Any],
        approach: Dict[str, Any],
        sandbox_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the practice task in sandbox.

        NOTE: This is a simulation. In production, this would:
        - Execute code in isolated sandbox
        - Interact with file manager
        - Observe results
        - Compare to expected outcome
        """
        # Simulated execution
        simulated_success = approach.get('estimated_success_rate', 0.5) > 0.5

        return {
            "success": simulated_success,
            "output": "Task executed in sandbox",
            "feedback": "Good attempt" if simulated_success else "Needs improvement",
            "execution_time": 1.5
        }

    def _learn_from_practice(
        self,
        skill_name: str,
        task: Dict[str, Any],
        approach: Dict[str, Any],
        outcome: Dict[str, Any]
    ):
        """
        Learn from practice outcome WITH TRUST SCORE UPDATES.

        Updates:
        1. **Operational Confidence** - Grace's ability to apply knowledge increases with practice
        2. **Data Confidence** - Validates accuracy of training materials
        3. **Trust Score** - Overall confidence in this knowledge
        4. **Skill Proficiency** - Tracks improvement over time
        """
        success = outcome.get('success', False)

        # Calculate operational confidence based on outcome
        operational_confidence = 0.8 if success else 0.4

        # Calculate trust score
        trust_score = self.trust_scorer.calculate_trust_score(
            source="system_observation_success" if success else "system_observation_failure",
            outcome_quality=1.0 if success else 0.3,
            consistency_score=0.7,  # Practice validates theoretical knowledge
            validation_history={'validated': 1 if success else 0, 'invalidated': 0 if success else 1},
            age_days=0.0
        )

        # Create learning example from practice
        example = LearningExample(
            example_type="practice_outcome",
            input_context={
                "skill": skill_name,
                "task": task.get('description'),
                "approach": approach,
                "complexity": task.get('complexity', 0.5)
            },
            expected_output={
                "success": True,
                "requirements_met": task.get('requirements', [])
            },
            actual_output=outcome,
            trust_score=trust_score,
            source_reliability=1.0,  # Direct observation is most reliable
            outcome_quality=1.0 if success else 0.3,
            consistency_score=0.7,
            source="system_observation_success" if success else "system_observation_failure",
            example_metadata={
                "operational_confidence": operational_confidence,
                "data_confidence": 0.9,  # Practice validates data
                "skill_level": self.skill_levels.get(skill_name, SkillLevel(skill_name)).current_level,
                "practice_iteration": self.skill_levels.get(skill_name, SkillLevel(skill_name)).tasks_completed + 1
            }
        )

        self.session.add(example)
        self.session.commit()

        # Update operational confidence for related knowledge examples
        self._update_related_knowledge_confidence(skill_name, operational_confidence)

        # Update skill proficiency
        self._update_skill_level(skill_name, success)

    def _update_related_knowledge_confidence(self, skill_name: str, operational_confidence: float):
        """
        Update operational confidence for knowledge examples related to this skill.

        When Grace successfully practices a skill, the operational confidence
        for related theoretical knowledge increases.
        """
        # Find knowledge examples for this skill
        knowledge_examples = self.session.query(LearningExample).filter(
            LearningExample.example_type == "knowledge_extraction",
            LearningExample.input_context.contains({"topic": skill_name})
        ).all()

        for example in knowledge_examples:
            # Update metadata with new operational confidence
            if example.example_metadata:
                metadata = example.example_metadata.copy()
            else:
                metadata = {}

            old_confidence = metadata.get('operational_confidence', 0.3)
            # Gradually increase operational confidence with practice
            new_confidence = min(0.95, (old_confidence + operational_confidence) / 2)

            metadata['operational_confidence'] = new_confidence
            metadata['last_practiced'] = datetime.utcnow().isoformat()

            example.example_metadata = metadata

            # Recalculate trust score with updated operational confidence
            example.outcome_quality = new_confidence
            example.trust_score = self.trust_scorer.calculate_trust_score(
                source=example.source,
                outcome_quality=new_confidence,
                consistency_score=example.consistency_score,
                validation_history={
                    'validated': example.times_validated,
                    'invalidated': example.times_invalidated
                },
                age_days=(datetime.utcnow() - example.created_at).days if example.created_at else 0
            )

        self.session.commit()

    def _update_skill_level(self, skill_name: str, success: bool):
        """Update Grace's proficiency in a skill."""
        if skill_name not in self.skill_levels:
            self.skill_levels[skill_name] = SkillLevel(skill_name)

        skill = self.skill_levels[skill_name]
        skill.tasks_completed += 1

        # Update success rate
        total_successes = (skill.success_rate * (skill.tasks_completed - 1))
        if success:
            total_successes += 1
        skill.success_rate = total_successes / skill.tasks_completed

        # Update proficiency score
        skill.proficiency_score = skill.success_rate * (1 + (skill.tasks_completed / 100))

        # Level up if proficiency threshold met
        if skill.proficiency_score > 0.8 and skill.current_level == SkillLevel.NOVICE:
            skill.current_level = SkillLevel.BEGINNER
        elif skill.proficiency_score > 1.5 and skill.current_level == SkillLevel.BEGINNER:
            skill.current_level = SkillLevel.INTERMEDIATE
        # etc...

    # ======================================================================
    # PHASE 3: ADAPTIVE LEARNING - Improve based on patterns
    # ======================================================================

    def extract_learning_patterns(self) -> List[LearningPattern]:
        """
        Extract patterns from accumulated learning examples.

        Identifies:
        - What approaches work best
        - Common mistakes to avoid
        - Prerequisites for success
        - Optimal learning sequences
        """
        # Get all learning examples
        examples = self.session.query(LearningExample).filter(
            LearningExample.example_type == "practice_outcome"
        ).all()

        if len(examples) < 10:
            logger.info("Not enough examples to extract patterns yet")
            return []

        # Group by skill and analyze
        # (Simplified - would use ML clustering in production)
        patterns = []

        return patterns

    # ======================================================================
    # TRAINING CURRICULUM MANAGEMENT
    # ======================================================================

    def create_training_curriculum(
        self,
        skill_name: str,
        target_proficiency: str = SkillLevel.INTERMEDIATE
    ) -> Dict[str, Any]:
        """
        Create a structured training curriculum for a skill.

        Args:
            skill_name: Skill to train (e.g., "Python programming", "API design")
            target_proficiency: Desired skill level

        Returns:
            Curriculum with study materials and practice tasks
        """
        curriculum = {
            "skill_name": skill_name,
            "target_proficiency": target_proficiency,
            "study_phases": [],
            "practice_tasks": [],
            "assessment_criteria": {}
        }

        # Phase 1: Foundational knowledge
        curriculum["study_phases"].append({
            "phase": "foundations",
            "topics": [f"{skill_name} basics", f"{skill_name} core concepts"],
            "learning_objectives": [
                f"Understand {skill_name} fundamentals",
                f"Learn {skill_name} syntax and structure",
                f"Identify {skill_name} use cases"
            ]
        })

        # Phase 2: Practical application
        curriculum["practice_tasks"].append({
            "phase": "application",
            "tasks": [
                {"description": f"Simple {skill_name} exercise", "complexity": 0.3},
                {"description": f"Moderate {skill_name} project", "complexity": 0.6},
                {"description": f"Complex {skill_name} challenge", "complexity": 0.9}
            ]
        })

        return curriculum

    def get_skill_assessment(self, skill_name: str) -> Dict[str, Any]:
        """Get Grace's current proficiency in a skill."""
        if skill_name not in self.skill_levels:
            return {
                "skill": skill_name,
                "level": SkillLevel.NOVICE,
                "proficiency_score": 0.0,
                "status": "not_started"
            }

        skill = self.skill_levels[skill_name]
        return {
            "skill": skill_name,
            "level": skill.current_level,
            "proficiency_score": skill.proficiency_score,
            "success_rate": skill.success_rate,
            "tasks_completed": skill.tasks_completed,
            "practice_hours": skill.practice_hours
        }
