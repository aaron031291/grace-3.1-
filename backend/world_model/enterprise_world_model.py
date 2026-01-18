import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import json
import gzip
from collections import defaultdict
logger = logging.getLogger(__name__)

class EnterpriseWorldModel:
    """
    Enterprise-grade world model system.
    
    Features:
    - Context lifecycle management
    - Context versioning
    - Context relationships
    - Context analytics
    - Context compression
    """
    
    def __init__(
        self,
        world_model_path: Path,
        retention_days: int = 90,
        archive_days: int = 180
    ):
        """Initialize enterprise world model."""
        self.world_model_path = world_model_path
        self.retention_days = retention_days
        self.archive_days = archive_days
        
        # Archive directory
        self.archive_dir = world_model_path.parent / "archived_world_models"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Version directory
        self.version_dir = world_model_path.parent / "world_model_versions"
        self.version_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"[ENTERPRISE-WORLD-MODEL] Initialized: "
            f"retention={retention_days}d, archive={archive_days}d"
        )
    
    def load_world_model(self) -> Optional[Dict[str, Any]]:
        """Load world model from file."""
        if not self.world_model_path.exists():
            return None
        
        with open(self.world_model_path, 'r') as f:
            return json.load(f)
    
    def save_world_model(self, world_model: Dict[str, Any]):
        """Save world model to file."""
        self.world_model_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.world_model_path, 'w') as f:
            json.dump(world_model, f, indent=2, default=str)
    
    def prioritize_contexts(self) -> Dict[str, Any]:
        """
        Calculate priority scores for all contexts.
        
        Priority = f(recency, genesis_key_importance, usage)
        
        Returns:
            Priority statistics
        """
        logger.info("[ENTERPRISE-WORLD-MODEL] Calculating context priorities...")
        
        world_model = self.load_world_model()
        if not world_model or "contexts" not in world_model:
            return {"total_contexts": 0, "priorities": []}
        
        contexts = world_model["contexts"]
        priorities = []
        
        for ctx in contexts:
            # Parse timestamp
            integrated_at = ctx.get("integrated_at")
            if integrated_at:
                try:
                    ctx_time = datetime.fromisoformat(integrated_at)
                    days_old = (datetime.utcnow() - ctx_time).days
                    recency_weight = max(0.1, 1.0 - (days_old / 365.0))
                except:
                    recency_weight = 0.5
            else:
                recency_weight = 0.5
            
            # Genesis key importance (if available)
            genesis_key_id = ctx.get("genesis_key_id", "")
            importance_weight = 0.5  # Default
            if genesis_key_id:
                # Simple heuristic: longer IDs might be more important
                importance_weight = min(1.0, len(genesis_key_id) / 50.0)
            
            # RAG indexed (indicates importance)
            rag_indexed = ctx.get("rag_indexed", False)
            rag_weight = 0.8 if rag_indexed else 0.3
            
            priority = (
                recency_weight * 0.4 +      # Recency matters
                importance_weight * 0.3 +   # Genesis key importance
                rag_weight * 0.3            # RAG indexing
            )
            
            priorities.append({
                "genesis_key_id": genesis_key_id,
                "priority": priority,
                "recency_weight": recency_weight,
                "rag_indexed": rag_indexed
            })
        
        priorities.sort(key=lambda x: x["priority"], reverse=True)
        
        stats = {
            "total_contexts": len(priorities),
            "high_priority": len([p for p in priorities if p["priority"] >= 0.7]),
            "medium_priority": len([p for p in priorities if 0.4 <= p["priority"] < 0.7]),
            "low_priority": len([p for p in priorities if p["priority"] < 0.4]),
            "top_10": priorities[:10]
        }
        
        logger.info(
            f"[ENTERPRISE-WORLD-MODEL] Priorities calculated: "
            f"{stats['high_priority']} high-priority contexts"
        )
        
        return stats
    
    def version_world_model(self) -> str:
        """
        Create versioned snapshot of world model.
        
        Returns:
            Path to versioned file
        """
        logger.info("[ENTERPRISE-WORLD-MODEL] Creating versioned snapshot...")
        
        world_model = self.load_world_model()
        if not world_model:
            return None
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        version_file = self.version_dir / f"world_model_{timestamp}.json"
        
        with open(version_file, 'w') as f:
            json.dump(world_model, f, indent=2, default=str)
        
        logger.info(f"[ENTERPRISE-WORLD-MODEL] Version saved: {version_file}")
        
        return str(version_file)
    
    def compress_world_model(self) -> Dict[str, Any]:
        """
        Compress world model by summarizing old contexts.
        
        Returns:
            Compression statistics
        """
        logger.info("[ENTERPRISE-WORLD-MODEL] Compressing world model...")
        
        world_model = self.load_world_model()
        if not world_model or "contexts" not in world_model:
            return {"compressed_count": 0, "space_saved_bytes": 0}
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        contexts = world_model["contexts"]
        
        compressed_count = 0
        space_saved = 0
        
        for ctx in contexts:
            integrated_at = ctx.get("integrated_at")
            if integrated_at:
                try:
                    ctx_time = datetime.fromisoformat(integrated_at)
                    if ctx_time < cutoff_date:
                        # Compress old context
                        original_size = len(json.dumps(ctx))
                        
                        # Keep only essential fields
                        compressed_ctx = {
                            "genesis_key_id": ctx.get("genesis_key_id"),
                            "integrated_at": integrated_at,
                            "summary": str(ctx.get("context", {}))[:200]
                        }
                        
                        compressed_size = len(json.dumps(compressed_ctx))
                        space_saved += (original_size - compressed_size)
                        
                        # Update context
                        ctx.update(compressed_ctx)
                        ctx["compressed"] = True
                        compressed_count += 1
                except:
                    pass
        
        if compressed_count > 0:
            self.save_world_model(world_model)
        
        logger.info(
            f"[ENTERPRISE-WORLD-MODEL] Compressed {compressed_count} contexts, "
            f"saved ~{space_saved / 1024:.2f} KB"
        )
        
        return {
            "compressed_count": compressed_count,
            "space_saved_bytes": space_saved
        }
    
    def archive_old_contexts(self) -> Dict[str, Any]:
        """
        Archive contexts beyond archive threshold.
        
        Returns:
            Archive statistics
        """
        logger.info(f"[ENTERPRISE-WORLD-MODEL] Archiving contexts older than {self.archive_days} days...")
        
        world_model = self.load_world_model()
        if not world_model or "contexts" not in world_model:
            return {"archived_count": 0}
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.archive_days)
        contexts = world_model["contexts"]
        
        # Separate old and new contexts
        old_contexts = []
        new_contexts = []
        
        for ctx in contexts:
            integrated_at = ctx.get("integrated_at")
            if integrated_at:
                try:
                    ctx_time = datetime.fromisoformat(integrated_at)
                    if ctx_time < cutoff_date:
                        old_contexts.append(ctx)
                    else:
                        new_contexts.append(ctx)
                except:
                    new_contexts.append(ctx)  # Keep if can't parse
            else:
                new_contexts.append(ctx)
        
        archived_count = len(old_contexts)
        
        if old_contexts:
            # Group by month
            by_month = {}
            for ctx in old_contexts:
                integrated_at = ctx.get("integrated_at")
                if integrated_at:
                    try:
                        ctx_time = datetime.fromisoformat(integrated_at)
                        month_key = ctx_time.strftime("%Y-%m")
                        if month_key not in by_month:
                            by_month[month_key] = []
                        by_month[month_key].append(ctx)
                    except:
                        pass
            
            # Save compressed archives
            for month, ctxs in by_month.items():
                archive_file = self.archive_dir / f"world_model_{month}.json.gz"
                
                with gzip.open(archive_file, 'wt', encoding='utf-8') as f:
                    json.dump({
                        "archived_at": datetime.utcnow().isoformat(),
                        "month": month,
                        "count": len(ctxs),
                        "contexts": ctxs
                    }, f, indent=2)
        
        # Update world model with only new contexts
        world_model["contexts"] = new_contexts
        world_model["archived_contexts_count"] = archived_count
        self.save_world_model(world_model)
        
        logger.info(f"[ENTERPRISE-WORLD-MODEL] Archived {archived_count} contexts")
        
        return {
            "archived_count": archived_count,
            "archive_files_created": len(by_month) if old_contexts else 0
        }
    
    def get_world_model_health(self) -> Dict[str, Any]:
        """
        Get world model health metrics.
        
        Returns:
            Health metrics
        """
        logger.info("[ENTERPRISE-WORLD-MODEL] Calculating health...")
        
        world_model = self.load_world_model()
        if not world_model:
            return {
                "health_score": 0.0,
                "health_status": "no_data",
                "total_contexts": 0
            }
        
        contexts = world_model.get("contexts", [])
        total_contexts = len(contexts)
        
        # Recent contexts
        recent_contexts = 0
        for ctx in contexts:
            integrated_at = ctx.get("integrated_at")
            if integrated_at:
                try:
                    ctx_time = datetime.fromisoformat(integrated_at)
                    if (datetime.utcnow() - ctx_time).days < 30:
                        recent_contexts += 1
                except:
                    pass
        
        # RAG indexed ratio
        rag_indexed = sum(1 for ctx in contexts if ctx.get("rag_indexed", False))
        rag_ratio = rag_indexed / total_contexts if total_contexts > 0 else 0.0
        
        # Health score
        recency_ratio = recent_contexts / total_contexts if total_contexts > 0 else 0.0
        health_score = (
            recency_ratio * 0.5 +      # Recent activity
            rag_ratio * 0.3 +          # RAG indexing
            min(1.0, total_contexts / 1000.0) * 0.2  # Having enough data
        )
        
        health = {
            "total_contexts": total_contexts,
            "recent_30d": recent_contexts,
            "rag_indexed": rag_indexed,
            "rag_ratio": rag_ratio,
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
            f"[ENTERPRISE-WORLD-MODEL] Health: score={health_score:.2f} "
            f"({health['health_status']})"
        )
        
        return health
    
    def get_world_model_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive world model analytics.
        
        Returns:
            Complete analytics dashboard
        """
        logger.info("[ENTERPRISE-WORLD-MODEL] Generating analytics...")
        
        priorities = self.prioritize_contexts()
        health = self.get_world_model_health()
        
        world_model = self.load_world_model()
        contexts = world_model.get("contexts", []) if world_model else []
        
        # Contexts by type (from genesis key type if available)
        by_type = defaultdict(int)
        for ctx in contexts:
            context_data = ctx.get("context", {})
            # Try to infer type from context
            if "what" in context_data:
                by_type["has_what"] += 1
            if "who" in context_data:
                by_type["has_who"] += 1
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "priorities": priorities,
            "health": health,
            "contexts_by_type": dict(by_type),
            "file_size_kb": self.world_model_path.stat().st_size / 1024 if self.world_model_path.exists() else 0
        }


def get_enterprise_world_model(
    world_model_path: Path,
    retention_days: int = 90
) -> EnterpriseWorldModel:
    """Factory function to get enterprise world model."""
    return EnterpriseWorldModel(
        world_model_path=world_model_path,
        retention_days=retention_days
    )
