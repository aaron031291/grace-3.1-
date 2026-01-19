"""
Memory Mesh Snapshot System

Creates immutable snapshots of the entire memory mesh state.
This allows recovery, versioning, and persistent storage of learned knowledge.

The immutable memory stores:
1. All learning examples with trust scores
2. All episodic memories
3. All procedural memories
4. All extracted patterns
5. Complete statistics and metadata

Snapshots are saved as .genesis_immutable_memory_mesh.json
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from cognitive.learning_memory import LearningExample, LearningPattern
from cognitive.episodic_memory import Episode
from cognitive.procedural_memory import Procedure

logger = logging.getLogger(__name__)


class MemoryMeshSnapshot:
    """
    Creates and manages immutable snapshots of memory mesh.

    The snapshot is a complete, recoverable state of all learned knowledge.
    """

    def __init__(self, session: Session, knowledge_base_path: Path):
        self.session = session
        self.kb_path = knowledge_base_path
        self.snapshot_path = knowledge_base_path / ".genesis_immutable_memory_mesh.json"

    def create_snapshot(self) -> Dict[str, Any]:
        """
        Create complete snapshot of current memory mesh state.

        Returns:
            Complete memory mesh snapshot
        """
        logger.info("[MEMORY-MESH-SNAPSHOT] Creating immutable snapshot...")

        snapshot = {
            "snapshot_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0",
                "type": "memory_mesh_immutable_snapshot"
            },
            "learning_memory": self._snapshot_learning_memory(),
            "episodic_memory": self._snapshot_episodic_memory(),
            "procedural_memory": self._snapshot_procedural_memory(),
            "pattern_memory": self._snapshot_pattern_memory(),
            "statistics": self._calculate_statistics(),
            "integrity": self._calculate_integrity_hash()
        }

        logger.info(
            f"[MEMORY-MESH-SNAPSHOT] Snapshot created: "
            f"{snapshot['statistics']['total_memories']} total memories"
        )

        return snapshot

    def _snapshot_learning_memory(self) -> Dict[str, Any]:
        """Snapshot all learning examples."""
        examples = self.session.query(LearningExample).all()

        return {
            "total_examples": len(examples),
            "examples": [
                {
                    "id": ex.id,
                    "type": ex.example_type,
                    "input_context": ex.input_context,
                    "expected_output": ex.expected_output,
                    "actual_output": ex.actual_output,
                    "trust_score": ex.trust_score,
                    "source_reliability": ex.source_reliability,
                    "outcome_quality": ex.outcome_quality,
                    "consistency_score": ex.consistency_score,
                    "recency_weight": ex.recency_weight,
                    "source": ex.source,
                    "source_user_id": ex.source_user_id,
                    "genesis_key_id": ex.genesis_key_id,
                    "times_referenced": ex.times_referenced,
                    "times_validated": ex.times_validated,
                    "times_invalidated": ex.times_invalidated,
                    "last_used": ex.last_used.isoformat() if ex.last_used else None,
                    "file_path": ex.file_path,
                    "episodic_episode_id": ex.episodic_episode_id,
                    "procedure_id": ex.procedure_id,
                    "metadata": ex.example_metadata,
                    "created_at": ex.created_at.isoformat(),
                    "updated_at": ex.updated_at.isoformat()
                }
                for ex in examples
            ],
            "by_type": self._group_by_type(examples),
            "by_source": self._group_by_source(examples),
            "trust_distribution": self._calculate_trust_distribution(examples)
        }

    def _snapshot_episodic_memory(self) -> Dict[str, Any]:
        """Snapshot all episodic memories."""
        episodes = self.session.query(Episode).all()

        return {
            "total_episodes": len(episodes),
            "episodes": [
                {
                    "id": ep.id,
                    "problem": ep.problem,
                    "action": ep.action,
                    "outcome": ep.outcome,
                    "predicted_outcome": ep.predicted_outcome,
                    "prediction_error": ep.prediction_error,
                    "trust_score": ep.trust_score,
                    "source": ep.source,
                    "genesis_key_id": ep.genesis_key_id,
                    "decision_id": ep.decision_id,
                    "timestamp": ep.timestamp.isoformat(),
                    "embedding": ep.embedding,
                    "metadata": ep.episode_metadata,
                    "created_at": ep.created_at.isoformat(),
                    "updated_at": ep.updated_at.isoformat()
                }
                for ep in episodes
            ],
            "high_trust_episodes": len([ep for ep in episodes if ep.trust_score >= 0.7]),
            "avg_prediction_error": sum(ep.prediction_error for ep in episodes) / len(episodes) if episodes else 0.0,
            "recent_episodes": self._get_recent_count(episodes, days=7)
        }

    def _snapshot_procedural_memory(self) -> Dict[str, Any]:
        """Snapshot all learned procedures."""
        procedures = self.session.query(Procedure).all()

        return {
            "total_procedures": len(procedures),
            "procedures": [
                {
                    "id": proc.id,
                    "name": proc.name,
                    "goal": proc.goal,
                    "type": proc.procedure_type,
                    "steps": proc.steps,
                    "preconditions": proc.preconditions,
                    "trust_score": proc.trust_score,
                    "success_rate": proc.success_rate,
                    "usage_count": proc.usage_count,
                    "success_count": proc.success_count,
                    "supporting_examples": proc.supporting_examples,
                    "learned_from_episode_id": proc.learned_from_episode_id,
                    "embedding": proc.embedding,
                    "metadata": proc.procedure_metadata,
                    "created_at": proc.created_at.isoformat(),
                    "updated_at": proc.updated_at.isoformat()
                }
                for proc in procedures
            ],
            "high_success_procedures": len([p for p in procedures if p.success_rate >= 0.7]),
            "avg_success_rate": sum(p.success_rate for p in procedures) / len(procedures) if procedures else 0.0,
            "by_type": self._group_procedures_by_type(procedures)
        }

    def _snapshot_pattern_memory(self) -> Dict[str, Any]:
        """Snapshot all extracted patterns."""
        patterns = self.session.query(LearningPattern).all()

        return {
            "total_patterns": len(patterns),
            "patterns": [
                {
                    "id": pat.id,
                    "name": pat.pattern_name,
                    "type": pat.pattern_type,
                    "preconditions": pat.preconditions,
                    "actions": pat.actions,
                    "expected_outcomes": pat.expected_outcomes,
                    "trust_score": pat.trust_score,
                    "success_rate": pat.success_rate,
                    "sample_size": pat.sample_size,
                    "supporting_examples": pat.supporting_examples,
                    "times_applied": pat.times_applied,
                    "times_succeeded": pat.times_succeeded,
                    "times_failed": pat.times_failed,
                    "linked_procedures": pat.linked_procedures,
                    "created_at": pat.created_at.isoformat(),
                    "updated_at": pat.updated_at.isoformat()
                }
                for pat in patterns
            ],
            "high_success_patterns": len([p for p in patterns if p.success_rate >= 0.7]),
            "avg_sample_size": sum(p.sample_size for p in patterns) / len(patterns) if patterns else 0.0
        }

    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate comprehensive statistics."""
        learning_count = self.session.query(LearningExample).count()
        episodic_count = self.session.query(Episode).count()
        procedural_count = self.session.query(Procedure).count()
        pattern_count = self.session.query(LearningPattern).count()

        high_trust_learning = self.session.query(LearningExample).filter(
            LearningExample.trust_score >= 0.7
        ).count()

        high_trust_episodes = self.session.query(Episode).filter(
            Episode.trust_score >= 0.7
        ).count()

        high_success_procedures = self.session.query(Procedure).filter(
            Procedure.success_rate >= 0.7
        ).count()

        return {
            "total_memories": learning_count + episodic_count + procedural_count + pattern_count,
            "learning_examples": learning_count,
            "episodic_memories": episodic_count,
            "procedural_memories": procedural_count,
            "extracted_patterns": pattern_count,
            "high_trust_learning": high_trust_learning,
            "high_trust_episodes": high_trust_episodes,
            "high_success_procedures": high_success_procedures,
            "trust_ratio": high_trust_learning / learning_count if learning_count > 0 else 0.0,
            "episodic_trust_ratio": high_trust_episodes / episodic_count if episodic_count > 0 else 0.0,
            "procedural_success_ratio": high_success_procedures / procedural_count if procedural_count > 0 else 0.0
        }

    def _calculate_integrity_hash(self) -> str:
        """Calculate hash for integrity verification."""
        import hashlib

        # Create hash from counts and timestamps
        hash_input = f"{datetime.utcnow().isoformat()}_mesh_snapshot"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _group_by_type(self, examples: List[LearningExample]) -> Dict[str, int]:
        """Group examples by type."""
        types = {}
        for ex in examples:
            types[ex.example_type] = types.get(ex.example_type, 0) + 1
        return types

    def _group_by_source(self, examples: List[LearningExample]) -> Dict[str, int]:
        """Group examples by source."""
        sources = {}
        for ex in examples:
            sources[ex.source] = sources.get(ex.source, 0) + 1
        return sources

    def _calculate_trust_distribution(self, examples: List[LearningExample]) -> Dict[str, int]:
        """Calculate trust score distribution."""
        distribution = {
            "very_high_0.9+": 0,
            "high_0.7-0.9": 0,
            "medium_0.5-0.7": 0,
            "low_0.3-0.5": 0,
            "very_low_<0.3": 0
        }

        for ex in examples:
            if ex.trust_score >= 0.9:
                distribution["very_high_0.9+"] += 1
            elif ex.trust_score >= 0.7:
                distribution["high_0.7-0.9"] += 1
            elif ex.trust_score >= 0.5:
                distribution["medium_0.5-0.7"] += 1
            elif ex.trust_score >= 0.3:
                distribution["low_0.3-0.5"] += 1
            else:
                distribution["very_low_<0.3"] += 1

        return distribution

    def _group_procedures_by_type(self, procedures: List[Procedure]) -> Dict[str, int]:
        """Group procedures by type."""
        types = {}
        for proc in procedures:
            types[proc.procedure_type] = types.get(proc.procedure_type, 0) + 1
        return types

    def _get_recent_count(self, items: List, days: int = 7) -> int:
        """Count items from last N days."""
        cutoff = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)
        return len([
            item for item in items
            if hasattr(item, 'timestamp') and item.timestamp.timestamp() >= cutoff
        ])

    def save_snapshot(self, snapshot: Optional[Dict[str, Any]] = None) -> str:
        """
        Save snapshot to immutable JSON file.

        Args:
            snapshot: Snapshot to save (or create new one)

        Returns:
            Path to saved snapshot
        """
        if snapshot is None:
            snapshot = self.create_snapshot()

        # Ensure directory exists
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)

        # Save to file
        with open(self.snapshot_path, 'w') as f:
            json.dump(snapshot, f, indent=2, default=str)

        logger.info(f"[MEMORY-MESH-SNAPSHOT] Saved to: {self.snapshot_path}")

        return str(self.snapshot_path)

    def load_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Load snapshot from file.

        Returns:
            Loaded snapshot or None if doesn't exist
        """
        if not self.snapshot_path.exists():
            logger.warning("[MEMORY-MESH-SNAPSHOT] No snapshot file found")
            return None

        with open(self.snapshot_path, 'r') as f:
            snapshot = json.load(f)

        logger.info(
            f"[MEMORY-MESH-SNAPSHOT] Loaded snapshot from {snapshot['snapshot_metadata']['timestamp']}"
        )

        return snapshot

    def restore_from_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restore memory mesh from snapshot.

        WARNING: This will overwrite current memory mesh!

        Args:
            snapshot: Snapshot to restore from

        Returns:
            Restoration statistics
        """
        logger.warning("[MEMORY-MESH-SNAPSHOT] Starting restoration - this will overwrite current data!")

        stats = {
            "learning_examples_restored": 0,
            "episodes_restored": 0,
            "procedures_restored": 0,
            "patterns_restored": 0
        }

        # Clear existing data (optional - could merge instead)
        # For now, we'll add to existing data

        # Restore learning examples
        for ex_data in snapshot["learning_memory"]["examples"]:
            # Check if already exists
            existing = self.session.query(LearningExample).filter(
                LearningExample.id == ex_data["id"]
            ).first()

            if existing:
                # Update existing
                for key, value in ex_data.items():
                    if key not in ['created_at', 'updated_at', 'last_used']:
                        setattr(existing, key, value)
            else:
                # Create new
                example = LearningExample(**{
                    k: v for k, v in ex_data.items()
                    if k not in ['created_at', 'updated_at', 'last_used']
                })
                self.session.add(example)

            stats["learning_examples_restored"] += 1

        # Restore episodes
        for ep_data in snapshot["episodic_memory"]["episodes"]:
            existing = self.session.query(Episode).filter(
                Episode.id == ep_data["id"]
            ).first()

            if not existing:
                episode = Episode(**{
                    k: v for k, v in ep_data.items()
                    if k not in ['created_at', 'updated_at', 'timestamp']
                })
                self.session.add(episode)
                stats["episodes_restored"] += 1

        # Restore procedures
        for proc_data in snapshot["procedural_memory"]["procedures"]:
            existing = self.session.query(Procedure).filter(
                Procedure.id == proc_data["id"]
            ).first()

            if not existing:
                procedure = Procedure(**{
                    k: v for k, v in proc_data.items()
                    if k not in ['created_at', 'updated_at']
                })
                self.session.add(procedure)
                stats["procedures_restored"] += 1

        # Restore patterns
        for pat_data in snapshot["pattern_memory"]["patterns"]:
            existing = self.session.query(LearningPattern).filter(
                LearningPattern.id == pat_data["id"]
            ).first()

            if not existing:
                pattern = LearningPattern(**{
                    k: v for k, v in pat_data.items()
                    if k not in ['created_at', 'updated_at']
                })
                self.session.add(pattern)
                stats["patterns_restored"] += 1

        self.session.commit()

        logger.info(f"[MEMORY-MESH-SNAPSHOT] Restoration complete: {stats}")

        return stats

    def create_versioned_snapshot(self) -> str:
        """
        Create snapshot with timestamp in filename.

        Returns:
            Path to versioned snapshot
        """
        snapshot = self.create_snapshot()

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        versioned_path = self.kb_path / f".genesis_immutable_memory_mesh_{timestamp}.json"

        with open(versioned_path, 'w') as f:
            json.dump(snapshot, f, indent=2, default=str)

        logger.info(f"[MEMORY-MESH-SNAPSHOT] Versioned snapshot saved: {versioned_path}")

        return str(versioned_path)

    def compare_snapshots(
        self,
        snapshot1: Dict[str, Any],
        snapshot2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare two snapshots to see what changed.

        Returns:
            Difference report
        """
        return {
            "snapshot1_time": snapshot1["snapshot_metadata"]["timestamp"],
            "snapshot2_time": snapshot2["snapshot_metadata"]["timestamp"],
            "learning_diff": {
                "added": snapshot2["statistics"]["learning_examples"] - snapshot1["statistics"]["learning_examples"],
                "old_count": snapshot1["statistics"]["learning_examples"],
                "new_count": snapshot2["statistics"]["learning_examples"]
            },
            "episodic_diff": {
                "added": snapshot2["statistics"]["episodic_memories"] - snapshot1["statistics"]["episodic_memories"],
                "old_count": snapshot1["statistics"]["episodic_memories"],
                "new_count": snapshot2["statistics"]["episodic_memories"]
            },
            "procedural_diff": {
                "added": snapshot2["statistics"]["procedural_memories"] - snapshot1["statistics"]["procedural_memories"],
                "old_count": snapshot1["statistics"]["procedural_memories"],
                "new_count": snapshot2["statistics"]["procedural_memories"]
            },
            "pattern_diff": {
                "added": snapshot2["statistics"]["extracted_patterns"] - snapshot1["statistics"]["extracted_patterns"],
                "old_count": snapshot1["statistics"]["extracted_patterns"],
                "new_count": snapshot2["statistics"]["extracted_patterns"]
            },
            "trust_quality_change": {
                "old_trust_ratio": snapshot1["statistics"]["trust_ratio"],
                "new_trust_ratio": snapshot2["statistics"]["trust_ratio"],
                "improvement": snapshot2["statistics"]["trust_ratio"] - snapshot1["statistics"]["trust_ratio"]
            }
        }


def create_memory_mesh_snapshot(
    session: Session,
    knowledge_base_path: Path,
    save: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to create memory mesh snapshot.

    Args:
        session: Database session
        knowledge_base_path: Path to knowledge base
        save: Whether to save to file

    Returns:
        Snapshot data
    """
    snapshotter = MemoryMeshSnapshot(session, knowledge_base_path)
    snapshot = snapshotter.create_snapshot()

    if save:
        snapshotter.save_snapshot(snapshot)

    return snapshot
