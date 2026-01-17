import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from collections import defaultdict
from pathlib import Path
import json
import gzip
from models.database_models import Document, DocumentChunk
from models.librarian_models import LibrarianTag, DocumentTag
class EnterpriseLibrarian:
    logger = logging.getLogger(__name__)
    """
    Enterprise-grade librarian system.
    
    Features:
    - Document lifecycle management
    - Document clustering
    - Document prediction
    - Document analytics
    - Smart organization
    """
    
    def __init__(
        self,
        session: Session,
        knowledge_base_path: Path,
        retention_days: int = 90,
        archive_days: int = 180
    ):
        """Initialize enterprise librarian."""
        self.session = session
        self.kb_path = knowledge_base_path
        self.retention_days = retention_days
        self.archive_days = archive_days
        
        # Archive directory
        self.archive_dir = knowledge_base_path / "archived_documents"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"[ENTERPRISE-LIBRARIAN] Initialized: "
            f"retention={retention_days}d, archive={archive_days}d"
        )
    
    def prioritize_documents(self) -> Dict[str, Any]:
        """
        Calculate priority scores for all documents.
        
        Priority = f(access_count, recency, relevance, tags)
        
        Returns:
            Priority statistics
        """
        logger.info("[ENTERPRISE-LIBRARIAN] Calculating document priorities...")
        
        documents = self.session.query(Document).all()
        priorities = []
        
        for doc in documents:
            # Priority formula
            days_old = (datetime.utcnow() - doc.created_at).days if doc.created_at else 365
            recency_weight = max(0.1, 1.0 - (days_old / 365.0))
            
            # Access-based priority (if tracked)
            access_count = getattr(doc, 'access_count', 0) or 0
            access_weight = min(1.0, access_count / 10.0)
            
            # Tag-based priority (more tags = more important)
            tag_count = self.session.query(DocumentTag).filter(
                DocumentTag.document_id == doc.id
            ).count()
            tag_weight = min(1.0, tag_count / 5.0)
            
            priority = (
                recency_weight * 0.4 +  # Recency matters
                access_weight * 0.4 +    # Access indicates value
                tag_weight * 0.2         # Tags indicate organization
            )
            
            priorities.append({
                "id": doc.id,
                "filename": doc.filename,
                "priority": priority,
                "days_old": days_old,
                "access_count": access_count,
                "tag_count": tag_count
            })
        
        priorities.sort(key=lambda x: x["priority"], reverse=True)
        
        stats = {
            "total_documents": len(priorities),
            "high_priority": len([p for p in priorities if p["priority"] >= 0.7]),
            "medium_priority": len([p for p in priorities if 0.4 <= p["priority"] < 0.7]),
            "low_priority": len([p for p in priorities if p["priority"] < 0.4]),
            "top_10": priorities[:10]
        }
        
        logger.info(
            f"[ENTERPRISE-LIBRARIAN] Priorities calculated: "
            f"{stats['high_priority']} high-priority documents"
        )
        
        return stats
    
    def cluster_documents(self) -> Dict[str, Any]:
        """
        Cluster documents by category, tags, and temporal proximity.
        
        Returns:
            Cluster statistics
        """
        logger.info("[ENTERPRISE-LIBRARIAN] Clustering documents...")
        
        documents = self.session.query(Document).all()
        
        # Cluster by category (if exists)
        category_clusters = defaultdict(list)
        tag_clusters = defaultdict(list)
        temporal_clusters = defaultdict(list)
        
        for doc in documents:
            # Category clustering
            category = getattr(doc, 'category', None) or "uncategorized"
            category_clusters[category].append(doc.id)
            
            # Tag clustering
            doc_tags = self.session.query(DocumentTag).join(
                LibrarianTag
            ).filter(
                DocumentTag.document_id == doc.id
            ).all()
            for doc_tag in doc_tags:
                tag_name = doc_tag.tag.name if doc_tag.tag else None
                if tag_name:
                    tag_clusters[tag_name].append(doc.id)
            
            # Temporal clustering (by month)
            if doc.created_at:
                month_key = doc.created_at.strftime("%Y-%m")
                temporal_clusters[month_key].append(doc.id)
        
        clusters = {
            "by_category": {
                cat: len(docs) for cat, docs in category_clusters.items()
            },
            "by_tag": {
                tag: len(docs) for tag, docs in tag_clusters.items()
            },
            "by_temporal": {
                month: len(docs) for month, docs in temporal_clusters.items()
            },
            "total_clusters": (
                len(category_clusters) + len(tag_clusters) + len(temporal_clusters)
            )
        }
        
        logger.info(
            f"[ENTERPRISE-LIBRARIAN] Created clusters: "
            f"{len(category_clusters)} category, "
            f"{len(tag_clusters)} tag, "
            f"{len(temporal_clusters)} temporal"
        )
        
        return clusters
    
    def compress_old_documents(self, days_old: int = 90) -> Dict[str, Any]:
        """
        Compress old, low-priority documents.
        
        Args:
            days_old: Compress documents older than this
            
        Returns:
            Compression statistics
        """
        logger.info(f"[ENTERPRISE-LIBRARIAN] Compressing documents older than {days_old} days...")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Find old documents with low priority
        old_docs = self.session.query(Document).filter(
            and_(
                Document.created_at < cutoff_date,
                or_(
                    ~Document.filename.like('%.pdf'),
                    ~Document.filename.like('%.docx')
                )  # Don't compress binary files
            )
        ).all()
        
        compressed_count = 0
        space_saved = 0
        
        for doc in old_docs:
            # Compress metadata
            if doc.metadata and isinstance(doc.metadata, dict):
                # Keep only essential fields
                compressed_metadata = {
                    "id": doc.id,
                    "filename": doc.filename,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "summary": str(doc.metadata)[:200]  # Truncate
                }
                
                original_size = len(json.dumps(doc.metadata))
                compressed_size = len(json.dumps(compressed_metadata))
                space_saved += (original_size - compressed_size)
                
                doc.metadata = compressed_metadata
                compressed_count += 1
        
        if compressed_count > 0:
            self.session.commit()
        
        logger.info(
            f"[ENTERPRISE-LIBRARIAN] Compressed {compressed_count} documents, "
            f"saved ~{space_saved / 1024:.2f} KB"
        )
        
        return {
            "compressed_count": compressed_count,
            "space_saved_bytes": space_saved,
            "cutoff_date": cutoff_date.isoformat()
        }
    
    def archive_old_documents(self) -> Dict[str, Any]:
        """
        Archive documents beyond archive threshold.
        
        Returns:
            Archive statistics
        """
        logger.info(f"[ENTERPRISE-LIBRARIAN] Archiving documents older than {self.archive_days} days...")
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.archive_days)
        
        old_docs = self.session.query(Document).filter(
            Document.created_at < cutoff_date
        ).all()
        
        archived_count = 0
        
        if old_docs:
            # Group by month
            by_month = {}
            for doc in old_docs:
                month_key = doc.created_at.strftime("%Y-%m") if doc.created_at else "unknown"
                if month_key not in by_month:
                    by_month[month_key] = []
                by_month[month_key].append({
                    "id": doc.id,
                    "filename": doc.filename,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "file_path": doc.file_path
                })
            
            # Save compressed archives
            for month, docs in by_month.items():
                archive_file = self.archive_dir / f"documents_{month}.json.gz"
                
                with gzip.open(archive_file, 'wt', encoding='utf-8') as f:
                    json.dump({
                        "archived_at": datetime.utcnow().isoformat(),
                        "month": month,
                        "count": len(docs),
                        "documents": docs
                    }, f, indent=2)
                
                archived_count += len(docs)
            
            self.session.commit()
        
        logger.info(f"[ENTERPRISE-LIBRARIAN] Archived {archived_count} documents")
        
        return {
            "archived_count": archived_count,
            "archive_files_created": len(by_month) if old_docs else 0
        }
    
    def get_librarian_health(self) -> Dict[str, Any]:
        """
        Get comprehensive librarian system health.
        
        Returns:
            Health metrics
        """
        logger.info("[ENTERPRISE-LIBRARIAN] Calculating health...")
        
        doc_count = self.session.query(Document).count()
        chunk_count = self.session.query(DocumentChunk).count()
        tag_count = self.session.query(LibrarianTag).count()
        
        # Recent activity
        recent_docs = self.session.query(Document).filter(
            Document.created_at >= datetime.utcnow() - timedelta(days=30)
        ).count()
        
        # Calculate health score
        recency_ratio = recent_docs / doc_count if doc_count > 0 else 0.0
        organization_ratio = tag_count / doc_count if doc_count > 0 else 0.0
        
        health_score = (
            recency_ratio * 0.4 +      # Recent activity
            organization_ratio * 0.3 +  # Organization level
            min(1.0, doc_count / 1000.0) * 0.3  # Having enough data
        )
        
        health = {
            "total_documents": doc_count,
            "total_chunks": chunk_count,
            "total_tags": tag_count,
            "recent_30d": recent_docs,
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
            f"[ENTERPRISE-LIBRARIAN] Health: score={health_score:.2f} "
            f"({health['health_status']})"
        )
        
        return health
    
    def get_librarian_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive librarian analytics.
        
        Returns:
            Complete analytics dashboard
        """
        logger.info("[ENTERPRISE-LIBRARIAN] Generating analytics...")
        
        priorities = self.prioritize_documents()
        clusters = self.cluster_documents()
        health = self.get_librarian_health()
        
        # Usage patterns
        top_tags = self.session.query(
            LibrarianTag.name,
            LibrarianTag.usage_count
        ).order_by(
            LibrarianTag.usage_count.desc()
        ).limit(10).all()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "priorities": priorities,
            "clusters": clusters,
            "health": health,
            "top_tags": [
                {"name": name, "usage_count": count}
                for name, count in top_tags
            ]
        }


def get_enterprise_librarian(
    session: Session,
    knowledge_base_path: Path,
    retention_days: int = 90
) -> EnterpriseLibrarian:
    """Factory function to get enterprise librarian."""
    return EnterpriseLibrarian(
        session=session,
        knowledge_base_path=knowledge_base_path,
        retention_days=retention_days
    )
