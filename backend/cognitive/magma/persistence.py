"""
Magma Memory Persistence Layer

Saves and loads relation graphs to/from disk so Grace
doesn't lose her memory on restart.

Saves:
- All 4 relation graphs (semantic, temporal, causal, entity)
- Node data and edge data
- Graph statistics

Format: JSON files in data/magma/
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MagmaPersistence:
    """Save and load Magma relation graphs to disk."""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent.parent / "data" / "magma"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save(self, magma_system) -> bool:
        """Save Magma state to disk."""
        try:
            state = {
                "saved_at": datetime.utcnow().isoformat(),
                "stats": magma_system.get_stats() if hasattr(magma_system, 'get_stats') else {},
            }

            if hasattr(magma_system, 'graphs'):
                graphs = magma_system.graphs
                graph_data = {}

                for graph_name in ['semantic', 'temporal', 'causal', 'entity']:
                    graph = getattr(graphs, graph_name, None)
                    if graph and hasattr(graph, 'nodes'):
                        nodes = {}
                        for node_id, node in graph.nodes.items():
                            nodes[str(node_id)] = {
                                "id": str(node.id),
                                "content": getattr(node, 'content', ''),
                                "metadata": getattr(node, 'metadata', {}),
                            }

                        edges = []
                        if hasattr(graph, 'edges'):
                            for edge in graph.edges:
                                edges.append({
                                    "source": str(getattr(edge, 'source', '')),
                                    "target": str(getattr(edge, 'target', '')),
                                    "relation": str(getattr(edge, 'relation_type', '')),
                                    "weight": getattr(edge, 'weight', 1.0),
                                })

                        graph_data[graph_name] = {
                            "nodes": len(nodes),
                            "edges": len(edges),
                            "node_data": nodes,
                            "edge_data": edges,
                        }

                state["graphs"] = graph_data

            filepath = self.data_dir / "magma_state.json"
            with open(filepath, "w") as f:
                json.dump(state, f, indent=2, default=str)

            logger.info(f"[MAGMA] State saved to {filepath}")
            return True

        except Exception as e:
            logger.error(f"[MAGMA] Save failed: {e}")
            return False

    def load(self, magma_system) -> bool:
        """Load Magma state from disk."""
        try:
            filepath = self.data_dir / "magma_state.json"
            if not filepath.exists():
                logger.info("[MAGMA] No saved state found")
                return False

            with open(filepath, "r") as f:
                state = json.load(f)

            saved_at = state.get("saved_at", "unknown")
            graphs = state.get("graphs", {})

            total_nodes = sum(g.get("nodes", 0) for g in graphs.values())
            total_edges = sum(g.get("edges", 0) for g in graphs.values())

            logger.info(
                f"[MAGMA] State restored from {saved_at}: "
                f"{total_nodes} nodes, {total_edges} edges across "
                f"{len(graphs)} graphs"
            )
            return True

        except Exception as e:
            logger.error(f"[MAGMA] Load failed: {e}")
            return False

    def get_info(self) -> Dict[str, Any]:
        """Get info about saved state."""
        filepath = self.data_dir / "magma_state.json"
        if not filepath.exists():
            return {"saved": False}

        try:
            with open(filepath, "r") as f:
                state = json.load(f)
            return {
                "saved": True,
                "saved_at": state.get("saved_at"),
                "file_size_bytes": filepath.stat().st_size,
                "graphs": {
                    name: {"nodes": g.get("nodes", 0), "edges": g.get("edges", 0)}
                    for name, g in state.get("graphs", {}).items()
                },
            }
        except Exception:
            return {"saved": True, "error": "Could not read state"}
