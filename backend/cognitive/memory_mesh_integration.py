"""
Memory Mesh Integration with Learning Memory

Connects learning memory to episodic and procedural memory,
creating a feedback loop for continuous improvement.

Classes:
- `MemoryMeshIntegration`

Key Methods:
- `ingest_learning_experience()`
- `feedback_loop_update()`
- `get_training_dataset()`
- `export_training_data_to_file()`
- `get_memory_mesh_stats()`
- `sync_learning_folders()`
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path

from cognitive.learning_memory import (
    LearningMemoryManager,
    LearningExample,
    LearningPattern
)
from cognitive.episodic_memory import EpisodicBuffer, Episode
from cognitive.procedural_memory import ProceduralRepository, Procedure


class MemoryMeshIntegration:
    """
    Integrates learning memory with the full memory mesh.

    Flow:
    1. Learning data comes in (from files, user feedback, system observations)
    2. Trust scores calculated and stored in learning_memory
    3. High-trust examples feed into episodic memory
    4. Patterns extracted and stored as procedures
    5. Procedures used in inference
    6. Outcomes feed back to update trust scores
    """

    def __init__(self, session: Session, knowledge_base_path: Path):
        self.session = session
        self.kb_path = knowledge_base_path

        # Memory systems
        self.learning_memory = LearningMemoryManager(session, knowledge_base_path)
        self.episodic_buffer = EpisodicBuffer(session)
        self.procedural_repo = ProceduralRepository(session)

    def ingest_learning_experience(
        self,
        experience_type: str,
        context: Dict[str, Any],
        action_taken: Dict[str, Any],
        outcome: Dict[str, Any],
        expected_outcome: Optional[Dict[str, Any]] = None,
        source: str = "system_observation",
        user_id: Optional[str] = None,
        genesis_key_id: Optional[str] = None
    ) -> str:
        """
        Ingest a learning experience into the memory mesh.

        This is the main entry point for learning data.

        Args:
            experience_type: Type of experience (success, failure, feedback, etc.)
            context: Contextual information
            action_taken: What was done
            outcome: What happened
            expected_outcome: What was expected (if different from outcome)
            source: Source of learning
            user_id: Genesis ID if user-provided
            genesis_key_id: Link to Genesis Key

        Returns:
            Learning example ID
        """
        # 1. Store in learning memory with trust scoring
        learning_data = {
            'context': context,
            'expected': expected_outcome or outcome,
            'actual': outcome
        }

        learning_example = self.learning_memory.ingest_learning_data(
            learning_type=experience_type,
            learning_data=learning_data,
            source=source,
            user_id=user_id,
            genesis_key_id=genesis_key_id
        )

        # 2. If high trust, add to episodic memory
        if learning_example.trust_score >= 0.7:
            episode = self._add_to_episodic_memory(
                learning_example,
                context,
                action_taken,
                outcome,
                expected_outcome
            )
            learning_example.episodic_episode_id = episode.id

        # 3. Check if this experience can create/update a procedure
        if learning_example.trust_score >= 0.8 and experience_type in ['success', 'pattern']:
            procedure = self._update_procedural_memory(
                learning_example,
                context,
                action_taken,
                outcome
            )
            if procedure:
                learning_example.procedure_id = procedure.id

        self.session.commit()

        return learning_example.id

    def _add_to_episodic_memory(
        self,
        learning_example: LearningExample,
        context: Dict[str, Any],
        action: Dict[str, Any],
        outcome: Dict[str, Any],
        expected_outcome: Optional[Dict[str, Any]]
    ) -> Episode:
        """
        Add high-trust learning example to episodic memory.
        """
        # Create episode from learning example
        episode = Episode(
            problem=str(context),
            action=action,
            outcome=outcome,
            predicted_outcome=expected_outcome,
            prediction_error=self._calculate_prediction_error(outcome, expected_outcome),
            trust_score=learning_example.trust_score,
            source=learning_example.source,
            genesis_key_id=learning_example.genesis_key_id,
            timestamp=datetime.now(),
            # Link back to learning example
            metadata={'learning_example_id': learning_example.id}
        )

        self.session.add(episode)
        return episode

    def _calculate_prediction_error(
        self,
        actual: Dict[str, Any],
        expected: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate error between expected and actual outcomes.
        """
        if not expected:
            return 0.0

        # Simple error calculation (can be enhanced)
        matching_keys = set(actual.keys()) & set(expected.keys())
        if not matching_keys:
            return 1.0

        errors = []
        for key in matching_keys:
            if actual[key] == expected[key]:
                errors.append(0.0)
            elif isinstance(actual[key], (int, float)) and isinstance(expected[key], (int, float)):
                # Normalized error for numeric values
                diff = abs(actual[key] - expected[key])
                max_val = max(abs(actual[key]), abs(expected[key]))
                if max_val > 0:
                    errors.append(diff / max_val)
                else:
                    errors.append(0.0)
            else:
                errors.append(1.0)

        return sum(errors) / len(errors) if errors else 0.0

    def _update_procedural_memory(
        self,
        learning_example: LearningExample,
        context: Dict[str, Any],
        action: Dict[str, Any],
        outcome: Dict[str, Any]
    ) -> Optional[Procedure]:
        """
        Update procedural memory based on learning example.
        """
        # Extract goal from context
        goal = context.get('goal', learning_example.example_type)

        # Check if procedure already exists
        existing = self.procedural_repo.find_procedure(goal, context)

        if existing:
            # Update existing procedure with new evidence
            self.procedural_repo.update_procedure_evidence(
                procedure_id=existing.id,
                new_example=learning_example,
                success=learning_example.outcome_quality > 0.7
            )
            return existing
        else:
            # Create new procedure if we have enough evidence
            similar_examples = self._find_similar_learning_examples(learning_example)

            if len(similar_examples) >= 2:  # Need at least 3 total (including current)
                procedure = self.procedural_repo.create_procedure(
                    goal=goal,
                    action_sequence=[action],
                    preconditions=context,
                    supporting_examples=[learning_example] + similar_examples
                )
                return procedure

        return None

    def _find_similar_learning_examples(
        self,
        example: LearningExample,
        min_trust: float = 0.7
    ) -> List[LearningExample]:
        """
        Find similar high-trust learning examples.
        """
        # Query similar examples
        similar = self.session.query(LearningExample).filter(
            LearningExample.example_type == example.example_type,
            LearningExample.trust_score >= min_trust,
            LearningExample.id != example.id
        ).limit(5).all()

        return similar

    def feedback_loop_update(
        self,
        learning_example_id: str,
        actual_outcome: Dict[str, Any],
        success: bool
    ):
        """
        Feedback loop: Update trust scores based on real-world outcomes.

        When a learning example is used and we observe the outcome,
        update its trust score.

        Args:
            learning_example_id: Learning example that was used
            actual_outcome: The actual outcome observed
            success: Whether it was successful
        """
        # Update learning example trust
        self.learning_memory.update_trust_on_usage(learning_example_id, success)

        # Get updated example
        example = self.session.query(LearningExample).filter(
            LearningExample.id == learning_example_id
        ).first()

        if not example:
            return

        # If trust dropped below threshold, remove from episodic memory
        if example.trust_score < 0.5 and example.episodic_episode_id:
            self._remove_from_episodic(example.episodic_episode_id)
            example.episodic_episode_id = None

        # Update associated procedure
        if example.procedure_id:
            self.procedural_repo.update_success_rate(
                example.procedure_id,
                success
            )

            # Get procedure
            procedure = self.session.query(Procedure).filter(
                Procedure.id == example.procedure_id
            ).first()

            # If procedure success rate dropped, mark for review
            if procedure and procedure.success_rate < 0.5:
                procedure.metadata = procedure.metadata or {}
                procedure.metadata['needs_review'] = True
                procedure.metadata['low_success_reason'] = 'trust_score_drop'

        self.session.commit()

    def _remove_from_episodic(self, episode_id: str):
        """
        Remove low-trust episode from episodic memory.
        """
        episode = self.session.query(Episode).filter(
            Episode.id == episode_id
        ).first()

        if episode:
            # Don't delete - just mark as low trust
            episode.trust_score = 0.3
            episode.metadata = episode.metadata or {}
            episode.metadata['deprecated'] = True

    def get_training_dataset(
        self,
        experience_type: Optional[str] = None,
        min_trust_score: float = 0.7,
        max_examples: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get high-trust training dataset for fine-tuning or learning.

        This data can be used to:
        1. Fine-tune language models
        2. Train classifiers
        3. Improve inference patterns

        Args:
            experience_type: Filter by type
            min_trust_score: Minimum trust threshold
            max_examples: Maximum examples to return

        Returns:
            List of training examples in standard format
        """
        examples = self.learning_memory.get_training_data(
            min_trust_score=min_trust_score,
            example_type=experience_type,
            limit=max_examples
        )

        # Convert to training format
        training_data = []
        for ex in examples:
            training_data.append({
                'input': ex.input_context,
                'output': ex.expected_output,
                'trust_score': ex.trust_score,
                'source': ex.source,
                'metadata': {
                    'example_id': ex.id,
                    'times_validated': ex.times_validated,
                    'times_invalidated': ex.times_invalidated,
                    'created_at': ex.created_at.isoformat()
                }
            })

        return training_data

    def export_training_data_to_file(
        self,
        output_path: Path,
        experience_type: Optional[str] = None,
        min_trust_score: float = 0.7,
        format: str = 'jsonl'
    ):
        """
        Export training data to file for external use.

        Args:
            output_path: Where to save the file
            experience_type: Filter by type
            min_trust_score: Minimum trust threshold
            format: 'jsonl' or 'json'
        """
        import json

        training_data = self.get_training_dataset(
            experience_type=experience_type,
            min_trust_score=min_trust_score
        )

        if format == 'jsonl':
            with open(output_path, 'w') as f:
                for item in training_data:
                    f.write(json.dumps(item) + '\n')
        else:  # json
            with open(output_path, 'w') as f:
                json.dump(training_data, f, indent=2)

    def get_memory_mesh_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the entire memory mesh.
        OPTIMIZED: Single aggregation query instead of 7 separate queries
        """
        from sqlalchemy import func, case

        # Single optimized query with conditional aggregations
        stats = self.session.query(
            # Learning examples counts
            func.count(LearningExample.id).label('total_learning'),
            func.sum(
                case((LearningExample.trust_score >= 0.7, 1), else_=0)
            ).label('high_trust_learning'),
            func.sum(
                case((LearningExample.episodic_episode_id.isnot(None), 1), else_=0)
            ).label('linked_episodes'),
            # Episode counts (via left join)
            func.count(Episode.id.distinct()).label('total_episodes'),
            # Procedure counts (via left join)
            func.count(Procedure.id.distinct()).label('total_procedures'),
            func.sum(
                case((Procedure.success_rate >= 0.7, 1), else_=0)
            ).label('high_success_procedures'),
        ).outerjoin(
            Episode, LearningExample.episodic_episode_id == Episode.id
        ).outerjoin(
            Procedure, LearningExample.procedure_id == Procedure.id
        ).first()

        # Pattern stats (separate lightweight query)
        total_patterns = self.session.query(func.count(LearningPattern.id)).scalar() or 0

        # Handle None values from aggregations
        total_learning = stats.total_learning or 0
        high_trust_learning = stats.high_trust_learning or 0
        linked_episodes = stats.linked_episodes or 0
        total_episodes = stats.total_episodes or 0
        total_procedures = stats.total_procedures or 0
        high_success_procedures = stats.high_success_procedures or 0

        return {
            'learning_memory': {
                'total_examples': total_learning,
                'high_trust_examples': high_trust_learning,
                'trust_ratio': high_trust_learning / total_learning if total_learning > 0 else 0
            },
            'episodic_memory': {
                'total_episodes': total_episodes,
                'linked_from_learning': linked_episodes,
                'linkage_ratio': linked_episodes / total_episodes if total_episodes > 0 else 0
            },
            'procedural_memory': {
                'total_procedures': total_procedures,
                'high_success_procedures': high_success_procedures,
                'success_ratio': high_success_procedures / total_procedures if total_procedures > 0 else 0
            },
            'pattern_extraction': {
                'total_patterns': total_patterns
            }
        }

    def sync_learning_folders(self):
        """
        Sync learning memory from file system folders.

        Reads data from knowledge_base/layer_1/learning_memory/*
        and ingests into memory mesh.
        """
        import json

        # Walk through learning memory folders
        for learning_type_dir in self.learning_memory.learning_memory_path.iterdir():
            if not learning_type_dir.is_dir():
                continue

            learning_type = learning_type_dir.name

            # Process each date folder
            for date_dir in learning_type_dir.iterdir():
                if not date_dir.is_dir():
                    continue

                # Process each learning file
                for learning_file in date_dir.glob('learning_*.json'):
                    try:
                        with open(learning_file, 'r') as f:
                            data = json.load(f)

                        # Check if already ingested
                        existing = self.session.query(LearningExample).filter(
                            LearningExample.file_path == str(learning_file)
                        ).first()

                        if existing:
                            continue  # Already ingested

                        # Ingest new learning data
                        self.ingest_learning_experience(
                            experience_type=learning_type,
                            context=data.get('context', {}),
                            action_taken=data.get('action', {}),
                            outcome=data.get('outcome', {}),
                            expected_outcome=data.get('expected_outcome'),
                            source=data.get('source', 'file_system'),
                            user_id=data.get('user_id'),
                            genesis_key_id=data.get('genesis_key_id')
                        )

                    except Exception as e:
                        print(f"Error ingesting {learning_file}: {e}")
                        continue
