import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import json
import gzip
from pathlib import Path
logger = logging.getLogger(__name__)

class MemoryLifecycleManager:
    """
    Enterprise-grade memory lifecycle management.
    
    Automatically:
    - Prioritizes high-value memories
    - Compresses old memories
    - Archives memories beyond retention period
    - Prunes low-value memories
    - Monitors memory health
    """

    def __init__(
        self,
        session: Session,
        knowledge_base_path: Path,
        retention_days: int = 90,
        archive_days: int = 180,
        min_trust_for_retention: float = 0.3
    ):
        """
        Initialize memory lifecycle manager.
        
        Args:
            session: Database session
            knowledge_base_path: Path to knowledge base
            retention_days: Days to keep memories active (default 90)
            archive_days: Days before archiving (default 180)
            min_trust_for_retention: Minimum trust to retain (default 0.3)
        """
        self.session = session
        self.kb_path = knowledge_base_path
        self.retention_days = retention_days
        self.archive_days = archive_days
        self.min_trust_for_retention = min_trust_for_retention
        
        # Archive directory
        self.archive_dir = knowledge_base_path / "archived_memories"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"[MEMORY-LIFECYCLE] Initialized: "
            f"retention={retention_days}d, archive={archive_days}d, "
            f"min_trust={min_trust_for_retention}"
        )

    def prioritize_memories(self) -> Dict[str, Any]:
        """
        Calculate priority scores for all memories.
        
        Priority = f(trust_score, recency, usage_count, success_rate)
        
        Returns:
            Priority statistics
        """
        logger.info("[MEMORY-LIFECYCLE] Calculating memory priorities...")
        
        # Learning examples priority
        learning_examples = self.session.query(LearningExample).all()
        learning_priorities = []
        
        for ex in learning_examples:
            # Priority formula: trust * recency * usage
            days_old = (datetime.utcnow() - ex.created_at).days if ex.created_at else 365
            recency_weight = max(0.1, 1.0 - (days_old / 365.0))  # Decay over 1 year
            
            usage_weight = min(1.0, (ex.times_referenced or 0) / 10.0)  # Cap at 10 uses
            
            priority = (
                ex.trust_score * 0.5 +  # Trust is most important
                recency_weight * 0.3 +  # Recency matters
                usage_weight * 0.2      # Usage indicates value
            )
            
            learning_priorities.append({
                "id": ex.id,
                "priority": priority,
                "trust_score": ex.trust_score,
                "days_old": days_old,
                "usage_count": ex.times_referenced or 0
            })
        
        # Episodes priority
        episodes = self.session.query(Episode).all()
        episode_priorities = []
        
        for ep in episodes:
            days_old = (datetime.utcnow() - ep.timestamp).days if ep.timestamp else 365
            recency_weight = max(0.1, 1.0 - (days_old / 365.0))
            
            priority = (
                ep.trust_score * 0.6 +  # Trust is critical for episodes
                recency_weight * 0.4
            )
            
            episode_priorities.append({
                "id": ep.id,
                "priority": priority,
                "trust_score": ep.trust_score,
                "days_old": days_old
            })
        
        # Procedures priority
        procedures = self.session.query(Procedure).all()
        procedure_priorities = []
        
        for proc in procedures:
            days_old = (datetime.utcnow() - proc.created_at).days if proc.created_at else 365
            recency_weight = max(0.1, 1.0 - (days_old / 365.0))
            
            priority = (
                proc.success_rate * 0.4 +  # Success rate matters
                proc.trust_score * 0.3 +    # Trust matters
                recency_weight * 0.2 +      # Recency matters
                min(1.0, (proc.usage_count or 0) / 20.0) * 0.1  # Usage matters
            )
            
            procedure_priorities.append({
                "id": proc.id,
                "priority": priority,
                "success_rate": proc.success_rate,
                "trust_score": proc.trust_score,
                "usage_count": proc.usage_count or 0,
                "days_old": days_old
            })
        
        # Sort by priority
        learning_priorities.sort(key=lambda x: x["priority"], reverse=True)
        episode_priorities.sort(key=lambda x: x["priority"], reverse=True)
        procedure_priorities.sort(key=lambda x: x["priority"], reverse=True)
        
        stats = {
            "learning_examples": {
                "total": len(learning_priorities),
                "high_priority": len([p for p in learning_priorities if p["priority"] >= 0.7]),
                "medium_priority": len([p for p in learning_priorities if 0.4 <= p["priority"] < 0.7]),
                "low_priority": len([p for p in learning_priorities if p["priority"] < 0.4]),
                "top_10": learning_priorities[:10]
            },
            "episodes": {
                "total": len(episode_priorities),
                "high_priority": len([p for p in episode_priorities if p["priority"] >= 0.7]),
                "medium_priority": len([p for p in episode_priorities if 0.4 <= p["priority"] < 0.7]),
                "low_priority": len([p for p in episode_priorities if p["priority"] < 0.4]),
                "top_10": episode_priorities[:10]
            },
            "procedures": {
                "total": len(procedure_priorities),
                "high_priority": len([p for p in procedure_priorities if p["priority"] >= 0.7]),
                "medium_priority": len([p for p in procedure_priorities if 0.4 <= p["priority"] < 0.7]),
                "low_priority": len([p for p in procedure_priorities if p["priority"] < 0.4]),
                "top_10": procedure_priorities[:10]
            }
        }
        
        logger.info(
            f"[MEMORY-LIFECYCLE] Priorities calculated: "
            f"{stats['learning_examples']['high_priority']} high-priority learning, "
            f"{stats['episodes']['high_priority']} high-priority episodes, "
            f"{stats['procedures']['high_priority']} high-priority procedures"
        )
        
        return stats

    def compress_old_memories(self, days_old: int = 90) -> Dict[str, Any]:
        """
        Compress old, low-priority memories to save space.
        
        Compression strategy:
        - Keep full data for high-priority memories
        - Compress embeddings for old memories
        - Summarize context for very old memories
        
        Args:
            days_old: Compress memories older than this
            
        Returns:
            Compression statistics
        """
        logger.info(f"[MEMORY-LIFECYCLE] Compressing memories older than {days_old} days...")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Find old learning examples with low priority
        old_examples = self.session.query(LearningExample).filter(
            and_(
                LearningExample.created_at < cutoff_date,
                LearningExample.trust_score < 0.5,
                LearningExample.times_referenced < 3
            )
        ).all()
        
        compressed_count = 0
        space_saved = 0
        
        for ex in old_examples:
            # Compress by summarizing large fields
            if ex.input_context and isinstance(ex.input_context, dict):
                # Keep only essential fields
                compressed_context = {
                    "type": ex.input_context.get("type"),
                    "summary": str(ex.input_context)[:200]  # Truncate
                }
                
                original_size = len(json.dumps(ex.input_context))
                compressed_size = len(json.dumps(compressed_context))
                space_saved += (original_size - compressed_size)
                
                ex.input_context = compressed_context
                compressed_count += 1
        
        if compressed_count > 0:
            self.session.commit()
            logger.info(
                f"[MEMORY-LIFECYCLE] Compressed {compressed_count} memories, "
                f"saved ~{space_saved / 1024:.2f} KB"
            )
        
        return {
            "compressed_count": compressed_count,
            "space_saved_bytes": space_saved,
            "space_saved_kb": space_saved / 1024,
            "cutoff_date": cutoff_date.isoformat()
        }

    def archive_old_memories(self) -> Dict[str, Any]:
        """
        Archive memories beyond archive threshold.
        
        Archives to compressed JSON files in archive directory.
        
        Returns:
            Archive statistics
        """
        logger.info(f"[MEMORY-LIFECYCLE] Archiving memories older than {self.archive_days} days...")
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.archive_days)
        
        # Find memories to archive
        old_examples = self.session.query(LearningExample).filter(
            and_(
                LearningExample.created_at < cutoff_date,
                LearningExample.trust_score < 0.4
            )
        ).all()
        
        archived_count = 0
        
        if old_examples:
            # Group by month for organized archiving
            by_month = {}
            for ex in old_examples:
                month_key = ex.created_at.strftime("%Y-%m") if ex.created_at else "unknown"
                if month_key not in by_month:
                    by_month[month_key] = []
                by_month[month_key].append({
                    "id": ex.id,
                    "type": ex.example_type,
                    "trust_score": ex.trust_score,
                    "created_at": ex.created_at.isoformat() if ex.created_at else None,
                    "summary": str(ex.input_context)[:500] if ex.input_context else None
                })
            
            # Save compressed archives
            for month, examples in by_month.items():
                archive_file = self.archive_dir / f"learning_examples_{month}.json.gz"
                
                with gzip.open(archive_file, 'wt', encoding='utf-8') as f:
                    json.dump({
                        "archived_at": datetime.utcnow().isoformat(),
                        "month": month,
                        "count": len(examples),
                        "examples": examples
                    }, f, indent=2)
                
                archived_count += len(examples)
                
                # Mark as archived in database (soft delete)
                for ex in old_examples:
                    if ex.created_at and ex.created_at.strftime("%Y-%m") == month:
                        # Store archive path in metadata
                        if not ex.example_metadata:
                            ex.example_metadata = {}
                        ex.example_metadata["archived"] = True
                        ex.example_metadata["archive_path"] = str(archive_file)
                        ex.example_metadata["archived_at"] = datetime.utcnow().isoformat()
            
            self.session.commit()
        
        logger.info(f"[MEMORY-LIFECYCLE] Archived {archived_count} memories")
        
        return {
            "archived_count": archived_count,
            "archive_files_created": len(by_month) if old_examples else 0,
            "cutoff_date": cutoff_date.isoformat()
        }

    def prune_low_value_memories(
        self,
        min_trust: Optional[float] = None,
        max_age_days: int = 365
    ) -> Dict[str, Any]:
        """
        Prune (delete) low-value memories.
        
        Only prunes memories that are:
        - Below minimum trust threshold
        - Older than max_age_days
        - Never or rarely referenced
        
        Args:
            min_trust: Minimum trust to keep (default: self.min_trust_for_retention)
            max_age_days: Maximum age before pruning (default: 365)
            
        Returns:
            Pruning statistics
        """
        min_trust = min_trust or self.min_trust_for_retention
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        
        logger.info(
            f"[MEMORY-LIFECYCLE] Pruning memories: "
            f"trust<{min_trust}, age>{max_age_days}d"
        )
        
        # Find memories to prune
        to_prune = self.session.query(LearningExample).filter(
            and_(
                LearningExample.created_at < cutoff_date,
                LearningExample.trust_score < min_trust,
                or_(
                    LearningExample.times_referenced == 0,
                    LearningExample.times_referenced.is_(None)
                )
            )
        ).all()
        
        pruned_count = len(to_prune)
        
        if pruned_count > 0:
            # Log before deletion
            for ex in to_prune:
                logger.debug(f"[MEMORY-LIFECYCLE] Pruning: {ex.id} (trust={ex.trust_score})")
            
            # Delete
            for ex in to_prune:
                self.session.delete(ex)
            
            self.session.commit()
            logger.info(f"[MEMORY-LIFECYCLE] Pruned {pruned_count} low-value memories")
        
        return {
            "pruned_count": pruned_count,
            "min_trust": min_trust,
            "max_age_days": max_age_days,
            "cutoff_date": cutoff_date.isoformat()
        }

    def get_memory_health(self) -> Dict[str, Any]:
        """
        Get comprehensive memory system health metrics.
        
        Returns:
            Health metrics including:
            - Total memories by type
            - Trust distribution
            - Age distribution
            - Priority distribution
            - Storage usage
            - Health score (0-1)
        """
        logger.info("[MEMORY-LIFECYCLE] Calculating memory health...")
        
        # Counts
        learning_count = self.session.query(LearningExample).count()
        episodic_count = self.session.query(Episode).count()
        procedural_count = self.session.query(Procedure).count()
        pattern_count = self.session.query(LearningPattern).count()
        
        # Trust distribution
        high_trust_learning = self.session.query(LearningExample).filter(
            LearningExample.trust_score >= 0.7
        ).count()
        
        # Age distribution
        now = datetime.utcnow()
        recent_learning = self.session.query(LearningExample).filter(
            LearningExample.created_at >= now - timedelta(days=30)
        ).count()
        
        old_learning = self.session.query(LearningExample).filter(
            LearningExample.created_at < now - timedelta(days=180)
        ).count()
        
        # Calculate health score
        trust_ratio = high_trust_learning / learning_count if learning_count > 0 else 0.0
        recency_ratio = recent_learning / learning_count if learning_count > 0 else 0.0
        
        # Health score: weighted combination
        health_score = (
            trust_ratio * 0.6 +      # Trust is most important
            recency_ratio * 0.3 +     # Recency matters
            min(1.0, learning_count / 1000.0) * 0.1  # Having enough data
        )
        
        health = {
            "total_memories": learning_count + episodic_count + procedural_count + pattern_count,
            "by_type": {
                "learning_examples": learning_count,
                "episodic_memories": episodic_count,
                "procedural_memories": procedural_count,
                "patterns": pattern_count
            },
            "trust_distribution": {
                "high_trust_0.7+": high_trust_learning,
                "total": learning_count,
                "trust_ratio": trust_ratio
            },
            "age_distribution": {
                "recent_30d": recent_learning,
                "old_180d+": old_learning,
                "recency_ratio": recency_ratio
            },
            "health_score": health_score,
            "health_status": (
                "excellent" if health_score >= 0.8 else
                "good" if health_score >= 0.6 else
                "fair" if health_score >= 0.4 else
                "poor"
            ),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(
            f"[MEMORY-LIFECYCLE] Health: score={health_score:.2f} "
            f"({health['health_status']}), "
            f"{learning_count} learning, {high_trust_learning} high-trust"
        )
        
        return health

    def run_lifecycle_maintenance(self) -> Dict[str, Any]:
        """
        Run complete lifecycle maintenance.
        
        Performs:
        1. Priority calculation
        2. Compression of old memories
        3. Archiving of very old memories
        4. Pruning of low-value memories
        5. Health check
        
        Returns:
            Complete maintenance report
        """
        logger.info("[MEMORY-LIFECYCLE] Running complete lifecycle maintenance...")
        
        report = {
            "started_at": datetime.utcnow().isoformat(),
            "priorities": self.prioritize_memories(),
            "compression": self.compress_old_memories(),
            "archiving": self.archive_old_memories(),
            "pruning": self.prune_low_value_memories(),
            "health": self.get_memory_health(),
            "completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info("[MEMORY-LIFECYCLE] Lifecycle maintenance complete")
        
        return report


def get_memory_lifecycle_manager(
    session: Session,
    knowledge_base_path: Path,
    retention_days: int = 90,
    archive_days: int = 180
) -> MemoryLifecycleManager:
    """Factory function to get memory lifecycle manager."""
    return MemoryLifecycleManager(
        session=session,
        knowledge_base_path=knowledge_base_path,
        retention_days=retention_days,
        archive_days=archive_days
    )
