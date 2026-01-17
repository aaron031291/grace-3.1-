import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models.database_models import Document
from models.librarian_models import DocumentTag, LibrarianTag, DocumentRelationship
from librarian.tag_manager import TagManager
from librarian.relationship_manager import RelationshipManager
class ContentVisualizer:
    logger = logging.getLogger(__name__)
    """
    Content visualization utilities.

    Generates data structures for visualizing:
    - Tag relationships and usage
    - Document relationship graphs
    - Organization hierarchies
    - Statistics and trends
    """

    def __init__(
        self,
        db_session: Session,
        tag_manager: Optional[TagManager] = None,
        relationship_manager: Optional[RelationshipManager] = None
    ):
        """
        Initialize visualizer.

        Args:
            db_session: Database session
            tag_manager: Optional tag manager
            relationship_manager: Optional relationship manager
        """
        self.db = db_session
        self.tag_manager = tag_manager or TagManager(db_session)
        self.relationship_manager = relationship_manager

        logger.info("[CONTENT-VISUALIZER] Initialized")

    def get_tag_cloud_data(
        self,
        min_usage: int = 1,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Generate tag cloud data structure.

        Returns tags with usage counts, suitable for tag cloud visualization.

        Args:
            min_usage: Minimum usage count to include
            limit: Maximum number of tags

        Returns:
            Dict with tag cloud data
        """
        try:
            # Get tag usage counts
            usage_counts = self.db.query(
                LibrarianTag.name,
                func.count(DocumentTag.document_id).label('usage_count')
            ).join(
                DocumentTag, LibrarianTag.id == DocumentTag.tag_id
            ).group_by(
                LibrarianTag.id, LibrarianTag.name
            ).having(
                func.count(DocumentTag.document_id) >= min_usage
            ).order_by(
                desc('usage_count')
            ).limit(limit).all()

            # Calculate size ranges
            if usage_counts:
                max_usage = max(count for _, count in usage_counts)
                min_usage_val = min(count for _, count in usage_counts)
                size_range = max_usage - min_usage_val if max_usage > min_usage_val else 1
            else:
                max_usage = 1
                min_usage_val = 1
                size_range = 1

            tags = []
            for name, count in usage_counts:
                # Normalize size (1.0 to 3.0)
                if size_range > 0:
                    normalized = ((count - min_usage_val) / size_range) * 2.0 + 1.0
                else:
                    normalized = 2.0

                tags.append({
                    "name": name,
                    "usage_count": count,
                    "size": round(normalized, 2),
                    "color": self._get_tag_color(name)
                })

            return {
                "tags": tags,
                "total_tags": len(tags),
                "max_usage": max_usage,
                "min_usage": min_usage_val
            }

        except Exception as e:
            logger.error(f"Error generating tag cloud data: {e}")
            return {
                "tags": [],
                "total_tags": 0,
                "error": str(e)
            }

    def get_relationship_graph(
        self,
        document_id: Optional[int] = None,
        max_depth: int = 2,
        limit_per_level: int = 10
    ) -> Dict[str, Any]:
        """
        Generate relationship graph structure.

        Creates a graph structure showing document relationships.

        Args:
            document_id: Optional root document ID (if None, shows all relationships)
            max_depth: Maximum depth to traverse
            limit_per_level: Maximum relationships per level

        Returns:
            Dict with graph structure (nodes and edges)
        """
        try:
            nodes = []
            edges = []
            node_ids = set()

            if document_id:
                # Start from specific document
                root_doc = self.db.query(Document).filter(Document.id == document_id).first()
                if root_doc:
                    self._build_graph_from_doc(
                        root_doc, nodes, edges, node_ids,
                        max_depth, limit_per_level, 0
                    )
            else:
                # Get all relationships
                relationships = self.db.query(DocumentRelationship).limit(limit_per_level * max_depth).all()
                
                for rel in relationships:
                    source_id = rel.source_document_id
                    target_id = rel.target_document_id

                    # Add source node
                    if source_id not in node_ids:
                        source_doc = self.db.query(Document).filter(Document.id == source_id).first()
                        if source_doc:
                            nodes.append({
                                "id": source_id,
                                "label": source_doc.filename or f"Doc {source_id}",
                                "type": "document"
                            })
                            node_ids.add(source_id)

                    # Add target node
                    if target_id not in node_ids:
                        target_doc = self.db.query(Document).filter(Document.id == target_id).first()
                        if target_doc:
                            nodes.append({
                                "id": target_id,
                                "label": target_doc.filename or f"Doc {target_id}",
                                "type": "document"
                            })
                            node_ids.add(target_id)

                    # Add edge
                    edges.append({
                        "source": source_id,
                        "target": target_id,
                        "type": rel.relationship_type,
                        "confidence": rel.confidence,
                        "label": rel.relationship_type
                    })

            return {
                "nodes": nodes,
                "edges": edges,
                "total_nodes": len(nodes),
                "total_edges": len(edges)
            }

        except Exception as e:
            logger.error(f"Error generating relationship graph: {e}")
            return {
                "nodes": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "error": str(e)
            }

    def get_organization_hierarchy(
        self,
        base_path: str = "documents"
    ) -> Dict[str, Any]:
        """
        Generate organization hierarchy structure.

        Creates a tree structure showing folder organization.

        Args:
            base_path: Base path to start from

        Returns:
            Dict with hierarchy tree structure
        """
        try:
            # Get all documents with file paths
            documents = self.db.query(Document).filter(
                Document.file_path.isnot(None),
                Document.status == "completed"
            ).all()

            # Build folder structure
            hierarchy = {"name": base_path, "type": "folder", "children": [], "file_count": 0}
            path_map = {base_path: hierarchy}

            for doc in documents:
                if not doc.file_path:
                    continue

                # Split path into components
                path_parts = doc.file_path.replace("\\", "/").split("/")
                
                current_path = base_path
                current_node = hierarchy

                for part in path_parts[:-1]:  # All parts except filename
                    if not part:
                        continue

                    current_path = f"{current_path}/{part}" if current_path else part

                    if current_path not in path_map:
                        new_node = {
                            "name": part,
                            "type": "folder",
                            "path": current_path,
                            "children": [],
                            "file_count": 0
                        }
                        current_node["children"].append(new_node)
                        path_map[current_path] = new_node
                        current_node = new_node
                    else:
                        current_node = path_map[current_path]

                # Add file to current folder
                current_node["file_count"] += 1
                current_node["children"].append({
                    "name": path_parts[-1],
                    "type": "file",
                    "document_id": doc.id,
                    "filename": doc.filename
                })

            # Calculate total file counts for folders
            def count_files(node):
                if node["type"] == "file":
                    return 1
                total = 0
                for child in node.get("children", []):
                    total += count_files(child)
                node["total_files"] = total
                return total

            count_files(hierarchy)

            return {
                "hierarchy": hierarchy,
                "total_folders": len(path_map),
                "total_files": hierarchy.get("total_files", 0)
            }

        except Exception as e:
            logger.error(f"Error generating organization hierarchy: {e}")
            return {
                "hierarchy": {},
                "error": str(e)
            }

    def get_statistics_timeline(
        self,
        days: int = 30,
        interval: str = "day"
    ) -> Dict[str, Any]:
        """
        Generate statistics timeline data.

        Shows document creation/processing trends over time.

        Args:
            days: Number of days to look back
            interval: Time interval ("day", "week", "month")

        Returns:
            Dict with timeline statistics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            documents = self.db.query(Document).filter(
                Document.created_at >= cutoff_date
            ).all()

            # Group by interval
            timeline = defaultdict(lambda: {
                "date": None,
                "documents_created": 0,
                "documents_processed": 0,
                "tags_assigned": 0,
                "avg_confidence": 0.0
            })

            for doc in documents:
                if not doc.created_at:
                    continue

                if interval == "day":
                    key = doc.created_at.strftime("%Y-%m-%d")
                elif interval == "week":
                    week_start = doc.created_at - timedelta(days=doc.created_at.weekday())
                    key = week_start.strftime("%Y-W%W")
                else:  # month
                    key = doc.created_at.strftime("%Y-%m")

                timeline[key]["date"] = key
                timeline[key]["documents_created"] += 1

                if doc.status == "completed":
                    timeline[key]["documents_processed"] += 1

                # Get tags for this document
                doc_tags = self.tag_manager.get_document_tags(doc.id)
                timeline[key]["tags_assigned"] += len(doc_tags)

                # Track confidence scores
                if doc.confidence_score:
                    if timeline[key]["avg_confidence"] == 0:
                        timeline[key]["avg_confidence"] = doc.confidence_score
                    else:
                        # Simple average (could use proper weighted average)
                        count = timeline[key]["documents_processed"]
                        timeline[key]["avg_confidence"] = (
                            (timeline[key]["avg_confidence"] * (count - 1) + doc.confidence_score) / count
                        )

            # Convert to list and sort
            timeline_list = sorted(timeline.values(), key=lambda x: x["date"])

            return {
                "timeline": timeline_list,
                "interval": interval,
                "days": days,
                "total_points": len(timeline_list)
            }

        except Exception as e:
            logger.error(f"Error generating statistics timeline: {e}")
            return {
                "timeline": [],
                "error": str(e)
            }

    def get_content_analytics(
        self
    ) -> Dict[str, Any]:
        """
        Generate comprehensive content analytics.

        Returns overall statistics and insights about the content library.

        Returns:
            Dict with analytics data
        """
        try:
            # Basic counts
            total_docs = self.db.query(Document).count()
            completed_docs = self.db.query(Document).filter(Document.status == "completed").count()
            pending_docs = self.db.query(Document).filter(Document.status == "pending").count()

            # Tag statistics
            total_tags = self.db.query(LibrarianTag).count()
            total_tag_assignments = self.db.query(DocumentTag).count()

            # Relationship statistics
            total_relationships = self.db.query(DocumentRelationship).count()
            
            relationship_types = self.db.query(
                DocumentRelationship.relationship_type,
                func.count(DocumentRelationship.id).label('count')
            ).group_by(DocumentRelationship.relationship_type).all()

            rel_type_counts = {rel_type: count for rel_type, count in relationship_types}

            # Source distribution
            sources = self.db.query(
                Document.source,
                func.count(Document.id).label('count')
            ).group_by(Document.source).all()

            source_distribution = {source: count for source, count in sources}

            # Confidence distribution
            avg_confidence = self.db.query(func.avg(Document.confidence_score)).filter(
                Document.confidence_score.isnot(None)
            ).scalar() or 0.0

            # File type distribution
            file_types = defaultdict(int)
            docs_with_files = self.db.query(Document).filter(
                Document.filename.isnot(None)
            ).all()

            for doc in docs_with_files:
                if doc.filename and '.' in doc.filename:
                    ext = doc.filename.split('.')[-1].lower()
                    file_types[ext] += 1

            return {
                "documents": {
                    "total": total_docs,
                    "completed": completed_docs,
                    "pending": pending_docs,
                    "completion_rate": completed_docs / total_docs if total_docs > 0 else 0
                },
                "tags": {
                    "total_tags": total_tags,
                    "total_assignments": total_tag_assignments,
                    "avg_tags_per_doc": total_tag_assignments / completed_docs if completed_docs > 0 else 0
                },
                "relationships": {
                    "total": total_relationships,
                    "by_type": rel_type_counts,
                    "avg_per_doc": total_relationships / completed_docs if completed_docs > 0 else 0
                },
                "sources": {
                    "distribution": source_distribution,
                    "unique_sources": len(source_distribution)
                },
                "confidence": {
                    "average": round(avg_confidence, 3),
                    "total_scored": completed_docs
                },
                "file_types": {
                    "distribution": dict(file_types),
                    "unique_types": len(file_types)
                }
            }

        except Exception as e:
            logger.error(f"Error generating content analytics: {e}")
            return {
                "error": str(e)
            }

    def _build_graph_from_doc(
        self,
        doc: Document,
        nodes: List[Dict],
        edges: List[Dict],
        node_ids: set,
        max_depth: int,
        limit: int,
        current_depth: int
    ):
        """Recursively build graph from a document."""
        if current_depth >= max_depth:
            return

        doc_id = doc.id
        if doc_id not in node_ids:
            nodes.append({
                "id": doc_id,
                "label": doc.filename or f"Doc {doc_id}",
                "type": "document",
                "depth": current_depth
            })
            node_ids.add(doc_id)

        # Get relationships
        relationships = self.db.query(DocumentRelationship).filter(
            DocumentRelationship.source_document_id == doc_id
        ).limit(limit).all()

        for rel in relationships:
            target_id = rel.target_document_id
            target_doc = self.db.query(Document).filter(Document.id == target_id).first()

            if target_doc:
                # Recursively add connected documents
                if target_id not in node_ids:
                    self._build_graph_from_doc(
                        target_doc, nodes, edges, node_ids,
                        max_depth, limit, current_depth + 1
                    )

                # Add edge
                edges.append({
                    "source": doc_id,
                    "target": target_id,
                    "type": rel.relationship_type,
                    "confidence": rel.confidence,
                    "label": rel.relationship_type
                })

    def _get_tag_color(self, tag_name: str) -> str:
        """Generate a color for a tag based on its name."""
        # Simple hash-based color generation
        hash_val = hash(tag_name) % 360
        return f"hsl({hash_val}, 70%, 50%)"
