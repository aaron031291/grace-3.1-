import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict
from sqlalchemy.orm import Session
from cognitive.learning_memory import LearningExample, LearningPattern
from cognitive.episodic_memory import Episode
from cognitive.procedural_memory import Procedure
from cognitive.memory_mesh_snapshot import MemoryMeshSnapshot
from cognitive.advanced_memory_cognition import get_advanced_memory_cognition, AdvancedMemoryCognition
logger = logging.getLogger(__name__)

class MagmaLayer(str, Enum):
    """Magma memory layers."""
    SURFACE = "surface"  # Active, fluid (recent, frequently accessed)
    MANTLE = "mantle"  # Semi-crystallized (patterns, validated)
    CORE = "core"  # Solidified (principles, fundamental)


@dataclass
class MagmaMemory:
    """Memory with Magma layer classification."""
    memory_id: str
    memory_type: str  # "learning", "episodic", "procedural"
    layer: MagmaLayer
    content: Dict[str, Any]
    temperature: float  # 0-1, how "hot" (active) the memory is
    crystallized: float  # 0-1, how "solid" (validated) the memory is
    flow_rate: float  # How fast memory moves between layers
    last_accessed: datetime
    access_count: int


class MagmaMemorySystem:
    """
    Magma Memory System - Hierarchical multi-layered memory architecture.
    
    Features:
    1. Surface Layer - Active, fluid memories (recent, hot)
    2. Mantle Layer - Semi-crystallized patterns (validated, warm)
    3. Core Layer - Solidified principles (fundamental, cool)
    4. Layer Flow - Memories naturally flow from surface → mantle → core
    5. Memory Mesh Integration - Persists via Memory Mesh snapshots
    """
    
    def __init__(
        self,
        session: Session,
        knowledge_base_path,
        memory_mesh_snapshot: Optional[MemoryMeshSnapshot] = None
    ):
        """Initialize Magma Memory System."""
        self.session = session
        self.kb_path = knowledge_base_path
        self.memory_mesh_snapshot = memory_mesh_snapshot
        
        # Import advanced cognition
        self.advanced_cognition = get_advanced_memory_cognition(session, knowledge_base_path)
        
        # Layer thresholds
        self.layer_thresholds = {
            MagmaLayer.SURFACE: {
                "max_age_days": 7,
                "min_access_count": 0,
                "min_temperature": 0.7,
                "max_crystallized": 0.3
            },
            MagmaLayer.MANTLE: {
                "max_age_days": 90,
                "min_access_count": 3,
                "min_temperature": 0.3,
                "max_crystallized": 0.7
            },
            MagmaLayer.CORE: {
                "max_age_days": None,  # No age limit
                "min_access_count": 10,
                "min_temperature": 0.0,
                "max_crystallized": 0.8
            }
        }
        
        # Layer statistics
        self.layer_stats = {
            layer: {
                "count": 0,
                "total_temperature": 0.0,
                "total_crystallized": 0.0
            }
            for layer in MagmaLayer
        }
        
        logger.info("[MAGMA-MEMORY] Initialized with 3 layers: Surface, Mantle, Core")
    
    # ==================== LAYER CLASSIFICATION ====================
    
    def classify_memory_layer(
        self,
        memory: Dict[str, Any],
        access_count: int = 0,
        last_accessed: Optional[datetime] = None
    ) -> Tuple[MagmaLayer, float, float]:
        """
        Classify memory into Magma layer.
        
        Returns:
            (layer, temperature, crystallized)
        """
        # Calculate temperature (how "hot" = active)
        age_days = 0
        if last_accessed:
            age_days = (datetime.utcnow() - last_accessed).days
        else:
            created_at = memory.get("created_at") or memory.get("timestamp")
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                age_days = (datetime.utcnow() - created_at).days
        
        # Temperature decays with age and increases with access
        recency_factor = max(0, 1.0 - (age_days / 7.0))  # Decay over 7 days
        access_factor = min(1.0, access_count / 10.0)  # Cap at 10 accesses
        temperature = (recency_factor * 0.7) + (access_factor * 0.3)
        
        # Calculate crystallized (how "solid" = validated)
        trust_score = memory.get("trust_score", 0.5)
        success_rate = memory.get("success_rate", 0.5)
        times_validated = memory.get("times_validated", 0)
        
        trust_factor = trust_score
        success_factor = success_rate if success_rate else trust_score
        validation_factor = min(1.0, times_validated / 5.0)  # Cap at 5 validations
        
        crystallized = (trust_factor * 0.4) + (success_factor * 0.4) + (validation_factor * 0.2)
        
        # Classify layer
        if temperature >= 0.7 and crystallized < 0.3:
            layer = MagmaLayer.SURFACE  # Hot and fluid
        elif crystallized >= 0.8 or (access_count >= 10 and trust_score >= 0.8):
            layer = MagmaLayer.CORE  # Solidified
        else:
            layer = MagmaLayer.MANTLE  # Semi-crystallized
        
        return layer, temperature, crystallized
    
    def get_memories_by_layer(
        self,
        layer: MagmaLayer,
        limit: int = 100
    ) -> List[MagmaMemory]:
        """Get memories in a specific layer."""
        memories = []
        
        # Get learning memories
        learning_examples = self.session.query(LearningExample).limit(limit * 3).all()
        for ex in learning_examples:
            memory_dict = {
                "id": ex.id,
                "type": "learning",
                "trust_score": ex.trust_score,
                "times_referenced": ex.times_referenced,
                "times_validated": ex.times_validated,
                "created_at": ex.created_at,
                "last_used": ex.last_used
            }
            
            layer_class, temperature, crystallized = self.classify_memory_layer(
                memory_dict,
                access_count=ex.times_referenced,
                last_accessed=ex.last_used
            )
            
            if layer_class == layer:
                memories.append(MagmaMemory(
                    memory_id=f"learning_{ex.id}",
                    memory_type="learning",
                    layer=layer_class,
                    content={"example": ex},
                    temperature=temperature,
                    crystallized=crystallized,
                    flow_rate=self._calculate_flow_rate(temperature, crystallized),
                    last_accessed=ex.last_used or ex.created_at,
                    access_count=ex.times_referenced
                ))
        
        # Get episodic memories
        episodes = self.session.query(Episode).limit(limit * 2).all()
        for ep in episodes:
            memory_dict = {
                "id": ep.id,
                "type": "episodic",
                "trust_score": ep.trust_score,
                "created_at": ep.created_at,
                "timestamp": ep.timestamp
            }
            
            layer_class, temperature, crystallized = self.classify_memory_layer(
                memory_dict,
                last_accessed=ep.timestamp
            )
            
            if layer_class == layer:
                memories.append(MagmaMemory(
                    memory_id=f"episodic_{ep.id}",
                    memory_type="episodic",
                    layer=layer_class,
                    content={"episode": ep},
                    temperature=temperature,
                    crystallized=crystallized,
                    flow_rate=self._calculate_flow_rate(temperature, crystallized),
                    last_accessed=ep.timestamp,
                    access_count=0
                ))
        
        # Get procedural memories
        procedures = self.session.query(Procedure).limit(limit).all()
        for proc in procedures:
            memory_dict = {
                "id": proc.id,
                "type": "procedural",
                "success_rate": proc.success_rate,
                "created_at": proc.created_at
            }
            
            layer_class, temperature, crystallized = self.classify_memory_layer(
                memory_dict
            )
            
            if layer_class == layer:
                memories.append(MagmaMemory(
                    memory_id=f"procedural_{proc.id}",
                    memory_type="procedural",
                    layer=layer_class,
                    content={"procedure": proc},
                    temperature=temperature,
                    crystallized=crystallized,
                    flow_rate=self._calculate_flow_rate(temperature, crystallized),
                    last_accessed=proc.created_at,
                    access_count=proc.times_used or 0
                ))
        
        # Sort by flow rate (most likely to move)
        memories.sort(key=lambda m: m.flow_rate, reverse=True)
        
        return memories[:limit]
    
    def _calculate_flow_rate(self, temperature: float, crystallized: float) -> float:
        """Calculate flow rate between layers."""
        # Flow is highest when temperature is dropping and crystallized is increasing
        # This means memory is moving from surface → mantle → core
        flow_rate = (1.0 - temperature) * crystallized
        return flow_rate
    
    # ==================== MEMORY FLOW ====================
    
    def process_memory_flow(self) -> Dict[str, Any]:
        """
        Process natural memory flow between layers.
        
        Memories naturally flow: Surface → Mantle → Core
        """
        results = {
            "surface_to_mantle": 0,
            "mantle_to_core": 0,
            "core_memories": 0,
            "errors": []
        }
        
        try:
            # Get surface memories that should move to mantle
            surface_memories = self.get_memories_by_layer(MagmaLayer.SURFACE, limit=1000)
            
            for magma_mem in surface_memories:
                # Check if should move to mantle
                if magma_mem.temperature < 0.5 and magma_mem.crystallized > 0.4:
                    # Move to mantle (in practice, this would update metadata)
                    results["surface_to_mantle"] += 1
                    logger.debug(f"[MAGMA-FLOW] Moving {magma_mem.memory_id} Surface → Mantle")
            
            # Get mantle memories that should move to core
            mantle_memories = self.get_memories_by_layer(MagmaLayer.MANTLE, limit=1000)
            
            for magma_mem in mantle_memories:
                # Check if should move to core
                if magma_mem.crystallized >= 0.8 and magma_mem.access_count >= 10:
                    # Move to core (in practice, this would update metadata)
                    results["mantle_to_core"] += 1
                    logger.debug(f"[MAGMA-FLOW] Moving {magma_mem.memory_id} Mantle → Core")
            
            # Count core memories
            core_memories = self.get_memories_by_layer(MagmaLayer.CORE, limit=1000)
            results["core_memories"] = len(core_memories)
            
            logger.info(
                f"[MAGMA-FLOW] Processed flow: "
                f"{results['surface_to_mantle']} Surface→Mantle, "
                f"{results['mantle_to_core']} Mantle→Core, "
                f"{results['core_memories']} Core memories"
            )
            
        except Exception as e:
            logger.error(f"[MAGMA-FLOW] Flow processing error: {e}")
            results["errors"].append(str(e))
        
        return results
    
    # ==================== MEMORY MESH INTEGRATION ====================
    
    def integrate_with_memory_mesh(self) -> Dict[str, Any]:
        """
        Integrate Magma layers with Memory Mesh snapshot.
        
        This ensures:
        - Magma layer classification is persisted
        - Memory Mesh captures layer distribution
        - Snapshots include layer metadata
        """
        if not self.memory_mesh_snapshot:
            # Create memory mesh snapshot if not provided
            from cognitive.memory_mesh_snapshot import MemoryMeshSnapshot
            self.memory_mesh_snapshot = MemoryMeshSnapshot(
                session=self.session,
                knowledge_base_path=self.kb_path
            )
        
        # Get layer distribution
        layer_distribution = {}
        for layer in MagmaLayer:
            memories = self.get_memories_by_layer(layer, limit=1000)
            layer_distribution[layer.value] = {
                "count": len(memories),
                "avg_temperature": sum(m.temperature for m in memories) / len(memories) if memories else 0.0,
                "avg_crystallized": sum(m.crystallized for m in memories) / len(memories) if memories else 0.0
            }
        
        # Create snapshot with Magma metadata
        snapshot = self.memory_mesh_snapshot.create_snapshot()
        
        # Add Magma layer information to snapshot
        snapshot["magma_layers"] = layer_distribution
        snapshot["magma_metadata"] = {
            "system": "magma_memory",
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "layer_flow": self.process_memory_flow()
        }
        
        logger.info(
            f"[MAGMA-MESH] Integrated with Memory Mesh: "
            f"Surface={layer_distribution.get('surface', {}).get('count', 0)}, "
            f"Mantle={layer_distribution.get('mantle', {}).get('count', 0)}, "
            f"Core={layer_distribution.get('core', {}).get('count', 0)}"
        )
        
        return snapshot
    
    # ==================== RETRIEVAL WITH LAYERS ====================
    
    def retrieve_memories_with_layers(
        self,
        query: str,
        prefer_layer: Optional[MagmaLayer] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Retrieve memories with layer-aware prioritization.
        
        Strategy:
        - Surface: Recent, active memories (best for current context)
        - Mantle: Validated patterns (best for reliability)
        - Core: Fundamental principles (best for grounding)
        """
        results = {
            "surface": [],
            "mantle": [],
            "core": [],
            "recommendations": []
        }
        
        # Get memories from each layer
        if prefer_layer == MagmaLayer.SURFACE or prefer_layer is None:
            surface_mems = self.get_memories_by_layer(MagmaLayer.SURFACE, limit=limit)
            results["surface"] = [
                {
                    "id": m.memory_id,
                    "type": m.memory_type,
                    "temperature": m.temperature,
                    "crystallized": m.crystallized,
                    "content": m.content
                }
                for m in surface_mems
            ]
        
        if prefer_layer == MagmaLayer.MANTLE or prefer_layer is None:
            mantle_mems = self.get_memories_by_layer(MagmaLayer.MANTLE, limit=limit)
            results["mantle"] = [
                {
                    "id": m.memory_id,
                    "type": m.memory_type,
                    "temperature": m.temperature,
                    "crystallized": m.crystallized,
                    "content": m.content
                }
                for m in mantle_mems
            ]
        
        if prefer_layer == MagmaLayer.CORE or prefer_layer is None:
            core_mems = self.get_memories_by_layer(MagmaLayer.CORE, limit=limit)
            results["core"] = [
                {
                    "id": m.memory_id,
                    "type": m.memory_type,
                    "temperature": m.temperature,
                    "crystallized": m.crystallized,
                    "content": m.content
                }
                for m in core_mems
            ]
        
        # Recommendations
        if prefer_layer is None:
            total_surface = len(results["surface"])
            total_mantle = len(results["mantle"])
            total_core = len(results["core"])
            
            if total_surface > total_mantle + total_core:
                results["recommendations"].append("High surface memory - focus on recent/active patterns")
            elif total_core > total_surface + total_mantle:
                results["recommendations"].append("High core memory - focus on fundamental principles")
            else:
                results["recommendations"].append("Balanced memory layers - use for comprehensive context")
        
        return results
    
    def get_layer_statistics(self) -> Dict[str, Any]:
        """Get statistics for each layer."""
        stats = {}
        
        for layer in MagmaLayer:
            memories = self.get_memories_by_layer(layer, limit=1000)
            
            if memories:
                stats[layer.value] = {
                    "count": len(memories),
                    "avg_temperature": sum(m.temperature for m in memories) / len(memories),
                    "avg_crystallized": sum(m.crystallized for m in memories) / len(memories),
                    "avg_flow_rate": sum(m.flow_rate for m in memories) / len(memories),
                    "memory_types": {
                        "learning": len([m for m in memories if m.memory_type == "learning"]),
                        "episodic": len([m for m in memories if m.memory_type == "episodic"]),
                        "procedural": len([m for m in memories if m.memory_type == "procedural"])
                    }
                }
            else:
                stats[layer.value] = {
                    "count": 0,
                    "avg_temperature": 0.0,
                    "avg_crystallized": 0.0,
                    "avg_flow_rate": 0.0,
                    "memory_types": {}
                }
        
        return stats


def get_magma_memory_system(
    session: Session,
    knowledge_base_path,
    memory_mesh_snapshot: Optional[MemoryMeshSnapshot] = None
) -> MagmaMemorySystem:
    """Factory function to get Magma Memory System."""
    return MagmaMemorySystem(session, knowledge_base_path, memory_mesh_snapshot)
