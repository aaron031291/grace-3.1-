"""
MAGMA Graph Persistence Layer
==============================
Backs the in-memory MAGMA graphs with database storage.

Two operations:
  1. save() — persist current graph state to DB (called on every mutation)
  2. load() — rehydrate graphs from DB on startup

Uses the established run_in_executor pattern for non-blocking async.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from database.session import session_scope
from models.memory_graph_models import GraphNodeRecord, GraphEdgeRecord

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="graph-persist")


class GraphPersistence:
    """Saves and loads MAGMA graph nodes/edges to/from the database."""

    def __init__(self, workspace_id: Optional[str] = None):
        self.workspace_id = workspace_id

    def save_node(self, graph_type: str, node) -> None:
        """Persist a single graph node to the database."""
        try:
            with session_scope() as session:
                existing = session.query(GraphNodeRecord).filter_by(
                    node_id=node.id
                ).first()

                embedding_json = json.dumps(node.embedding) if node.embedding else None
                meta = {}
                if hasattr(node, 'metadata') and node.metadata:
                    meta = {k: (v.isoformat() if isinstance(v, datetime) else v)
                            for k, v in node.metadata.items()}

                if existing:
                    existing.content = node.content
                    existing.embedding_json = embedding_json
                    existing.metadata_json = meta
                    existing.trust_score = node.trust_score
                    existing.genesis_key_id = node.genesis_key_id
                else:
                    record = GraphNodeRecord(
                        node_id=node.id,
                        graph_type=graph_type,
                        node_type=node.node_type,
                        content=node.content,
                        embedding_json=embedding_json,
                        metadata_json=meta,
                        genesis_key_id=node.genesis_key_id,
                        trust_score=node.trust_score,
                        workspace_id=self.workspace_id,
                    )
                    session.add(record)
        except Exception as e:
            logger.warning(f"[GraphPersist] Failed to save node {node.id}: {e}")

    def save_edge(self, graph_type: str, edge) -> None:
        """Persist a single graph edge to the database."""
        try:
            with session_scope() as session:
                existing = session.query(GraphEdgeRecord).filter_by(
                    edge_id=edge.id
                ).first()

                if existing:
                    existing.weight = edge.weight
                    existing.confidence = edge.confidence
                    existing.metadata_json = edge.metadata or {}
                else:
                    record = GraphEdgeRecord(
                        edge_id=edge.id,
                        graph_type=graph_type,
                        source_node_id=edge.source_id,
                        target_node_id=edge.target_id,
                        relation_type=edge.relation_type.value if hasattr(edge.relation_type, 'value') else str(edge.relation_type),
                        weight=edge.weight,
                        confidence=edge.confidence,
                        metadata_json=edge.metadata or {},
                        genesis_key_id=edge.genesis_key_id,
                        workspace_id=self.workspace_id,
                    )
                    session.add(record)
        except Exception as e:
            logger.warning(f"[GraphPersist] Failed to save edge {edge.id}: {e}")

    def load_graph(self, graph_type: str) -> Dict[str, Any]:
        """Load all nodes and edges for a graph type from the database."""
        try:
            with session_scope() as session:
                node_query = session.query(GraphNodeRecord).filter_by(graph_type=graph_type)
                edge_query = session.query(GraphEdgeRecord).filter_by(graph_type=graph_type)

                if self.workspace_id:
                    node_query = node_query.filter_by(workspace_id=self.workspace_id)
                    edge_query = edge_query.filter_by(workspace_id=self.workspace_id)

                nodes = []
                for record in node_query.all():
                    embedding = None
                    if record.embedding_json:
                        try:
                            embedding = json.loads(record.embedding_json)
                        except (json.JSONDecodeError, TypeError):
                            pass

                    nodes.append({
                        "id": record.node_id,
                        "node_type": record.node_type,
                        "content": record.content,
                        "embedding": embedding,
                        "metadata": record.metadata_json or {},
                        "genesis_key_id": record.genesis_key_id,
                        "trust_score": record.trust_score,
                        "created_at": record.created_at,
                    })

                edges = []
                for record in edge_query.all():
                    edges.append({
                        "id": record.edge_id,
                        "source_id": record.source_node_id,
                        "target_id": record.target_node_id,
                        "relation_type": record.relation_type,
                        "weight": record.weight,
                        "confidence": record.confidence,
                        "metadata": record.metadata_json or {},
                        "genesis_key_id": record.genesis_key_id,
                    })

                return {"nodes": nodes, "edges": edges}
        except Exception as e:
            logger.warning(f"[GraphPersist] Failed to load graph {graph_type}: {e}")
            return {"nodes": [], "edges": []}

    def get_stats(self) -> Dict[str, Any]:
        """Get persistence statistics."""
        try:
            with session_scope() as session:
                from sqlalchemy import func
                node_counts = dict(
                    session.query(GraphNodeRecord.graph_type, func.count(GraphNodeRecord.id))
                    .group_by(GraphNodeRecord.graph_type).all()
                )
                edge_counts = dict(
                    session.query(GraphEdgeRecord.graph_type, func.count(GraphEdgeRecord.id))
                    .group_by(GraphEdgeRecord.graph_type).all()
                )
                return {
                    "nodes_by_graph": node_counts,
                    "edges_by_graph": edge_counts,
                    "total_nodes": sum(node_counts.values()),
                    "total_edges": sum(edge_counts.values()),
                }
        except Exception as e:
            logger.warning(f"[GraphPersist] Failed to get stats: {e}")
            return {"total_nodes": 0, "total_edges": 0}


def get_graph_persistence(workspace_id: Optional[str] = None) -> GraphPersistence:
    return GraphPersistence(workspace_id)
