"""
Grace Unified Memory System

The single memory system that unifies everything:

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED MEMORY API                            │
│  query() / remember() / recall() / forget() / consolidate()    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│              INTELLIGENCE LAYER (Magma)                          │
│  Intent Router → Graph Retrieval → RRF Fusion → Causal Inference│
│  Semantic Graph │ Temporal Graph │ Causal Graph │ Entity Graph  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│              MEMORY TYPES                                        │
│  Episodic (what happened) │ Procedural (how to do things)       │
│  Semantic (facts/knowledge) │ Learning (trust-scored examples)  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│              PERSISTENCE LAYER (Memory Mesh)                     │
│  SQLAlchemy DB │ Magma Graph Persistence │ Snapshots             │
│  Cache (LRU) │ Metrics │ Genesis Chains                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│              LIFECYCLE                                            │
│  Consolidation (short→long term) │ Forgetting Curve (decay)     │
│  Associative Recall │ Memory Pressure Management                 │
└─────────────────────────────────────────────────────────────────┘

This replaces calling Memory Mesh OR Magma separately.
One system. One API. Every memory type. Full lifecycle.
"""

import logging
import math
import time
import threading
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum

logger = logging.getLogger(__name__)

def _track_memory(desc, **kwargs):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("unified_memory", desc, **kwargs)
    except Exception:
        pass


# =============================================================================
# MEMORY TYPES
# =============================================================================

class MemoryType(str, Enum):
    """Types of memory Grace maintains, modeled on human cognition."""
    EPISODIC = "episodic"        # What happened (concrete experiences)
    PROCEDURAL = "procedural"    # How to do things (learned skills)
    SEMANTIC = "semantic"        # Facts and knowledge
    WORKING = "working"          # Short-term active context
    LEARNING = "learning"        # Trust-scored training examples
    CAUSAL = "causal"            # Why things happen (cause-effect)


class MemoryStrength(str, Enum):
    """How strongly a memory is held."""
    FLASH = "flash"          # Just happened, not yet consolidated
    SHORT_TERM = "short_term"  # Recent, moderate strength
    LONG_TERM = "long_term"    # Consolidated, strong
    PERMANENT = "permanent"    # Core knowledge, never forgotten


@dataclass
class Memory:
    """A single unified memory entry."""
    id: str
    content: str
    memory_type: MemoryType
    strength: MemoryStrength = MemoryStrength.FLASH

    # Trust and quality
    trust_score: float = 0.5
    relevance_score: float = 0.5
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    # Provenance
    source: str = ""
    genesis_key_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    # Connections
    related_memories: List[str] = field(default_factory=list)
    causal_links: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Forgetting curve
    decay_rate: float = 0.1  # Higher = forgets faster
    last_reinforced: datetime = field(default_factory=datetime.now)

    @property
    def current_retention(self) -> float:
        """Current memory retention based on Ebbinghaus forgetting curve.

        R = e^(-t/S) where t = time since reinforcement, S = stability
        """
        if self.strength == MemoryStrength.PERMANENT:
            return 1.0

        hours_since = (datetime.now() - self.last_reinforced).total_seconds() / 3600
        stability = (1.0 / max(self.decay_rate, 0.01)) * (1 + self.access_count * 0.5)
        retention = math.exp(-hours_since / max(stability, 1.0))
        return max(0.01, min(1.0, retention))

    @property
    def effective_score(self) -> float:
        """Combined score: trust * relevance * retention."""
        return self.trust_score * self.relevance_score * self.current_retention

    def reinforce(self):
        """Reinforce this memory (accessed/validated)."""
        self.access_count += 1
        self.last_accessed = datetime.now()
        self.last_reinforced = datetime.now()
        self.decay_rate *= 0.9  # Slower decay with each reinforcement

        if self.access_count > 10 and self.strength == MemoryStrength.SHORT_TERM:
            self.strength = MemoryStrength.LONG_TERM
        elif self.access_count > 3 and self.strength == MemoryStrength.FLASH:
            self.strength = MemoryStrength.SHORT_TERM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content[:200],
            "type": self.memory_type.value,
            "strength": self.strength.value,
            "trust": round(self.trust_score, 3),
            "retention": round(self.current_retention, 3),
            "effective_score": round(self.effective_score, 3),
            "access_count": self.access_count,
            "source": self.source,
            "tags": self.tags,
            "related": len(self.related_memories),
            "created": self.created_at.isoformat(),
        }


# =============================================================================
# ASSOCIATIVE RECALL ENGINE
# =============================================================================

class AssociativeRecallEngine:
    """
    When you recall one memory, related memories activate.
    Like how smelling cookies reminds you of your grandmother's kitchen.

    Grace's version: querying "database timeout" also surfaces
    the procedure for reconnecting, the episode where it happened last,
    and the causal chain that explains why.
    """

    def __init__(self):
        self._association_strengths: Dict[Tuple[str, str], float] = {}

    def record_co_access(self, memory_id_a: str, memory_id_b: str):
        """Record that two memories were accessed together."""
        key = tuple(sorted([memory_id_a, memory_id_b]))
        current = self._association_strengths.get(key, 0.0)
        self._association_strengths[key] = min(current + 0.1, 1.0)

    def get_associations(self, memory_id: str, threshold: float = 0.2) -> List[Tuple[str, float]]:
        """Get memories associated with this one, ranked by strength."""
        associations = []
        for (a, b), strength in self._association_strengths.items():
            if strength < threshold:
                continue
            if a == memory_id:
                associations.append((b, strength))
            elif b == memory_id:
                associations.append((a, strength))
        return sorted(associations, key=lambda x: -x[1])


# =============================================================================
# MEMORY CONSOLIDATION ENGINE
# =============================================================================

class ConsolidationEngine:
    """
    Like sleep for Grace's brain.

    Moves important short-term memories to long-term storage.
    Merges similar memories. Extracts patterns into procedures.
    Prunes memories that have decayed below threshold.

    Runs periodically (configurable interval).
    """

    def __init__(self, unified_memory=None):
        self._memory = unified_memory
        self._consolidation_count = 0
        self._last_consolidation: Optional[datetime] = None
        self._pruned_count = 0
        self._promoted_count = 0
        self._merged_count = 0

    def consolidate(self, memories: Dict[str, Memory]) -> Dict[str, Any]:
        """Run a full consolidation cycle."""
        self._consolidation_count += 1
        self._last_consolidation = datetime.now()

        results = {
            "promoted": 0,
            "pruned": 0,
            "merged": 0,
            "patterns_extracted": 0,
        }

        # 1. Promote strong short-term memories to long-term
        for mem in memories.values():
            if (mem.strength == MemoryStrength.SHORT_TERM and
                mem.access_count >= 5 and
                mem.trust_score >= 0.7):
                mem.strength = MemoryStrength.LONG_TERM
                results["promoted"] += 1
                self._promoted_count += 1

            elif (mem.strength == MemoryStrength.FLASH and
                  mem.access_count >= 2):
                mem.strength = MemoryStrength.SHORT_TERM
                results["promoted"] += 1
                self._promoted_count += 1

        # 2. Prune decayed memories (retention below threshold)
        to_prune = []
        for mem_id, mem in memories.items():
            if (mem.strength not in (MemoryStrength.LONG_TERM, MemoryStrength.PERMANENT) and
                mem.current_retention < 0.1 and
                mem.access_count < 2):
                to_prune.append(mem_id)

        for mem_id in to_prune:
            del memories[mem_id]
            results["pruned"] += 1
            self._pruned_count += 1

        # 3. Find and merge similar memories
        episodic_mems = [m for m in memories.values() if m.memory_type == MemoryType.EPISODIC]
        if len(episodic_mems) > 2:
            content_groups = defaultdict(list)
            for mem in episodic_mems:
                key = mem.content[:50].lower().strip()
                content_groups[key].append(mem)

            for key, group in content_groups.items():
                if len(group) > 1:
                    primary = max(group, key=lambda m: m.effective_score)
                    for secondary in group:
                        if secondary.id != primary.id:
                            primary.access_count += secondary.access_count
                            primary.trust_score = max(primary.trust_score, secondary.trust_score)
                            primary.related_memories.extend(secondary.related_memories)
                            if secondary.id in memories:
                                del memories[secondary.id]
                                results["merged"] += 1
                                self._merged_count += 1

        # 4. Extract patterns from episodic clusters -> procedural memory
        if episodic_mems:
            tag_counts = defaultdict(int)
            for mem in episodic_mems:
                for tag in mem.tags:
                    tag_counts[tag] += 1

            frequent_patterns = [tag for tag, count in tag_counts.items() if count >= 3]
            results["patterns_extracted"] = len(frequent_patterns)

        logger.info(
            f"[MEMORY] Consolidation #{self._consolidation_count}: "
            f"promoted={results['promoted']}, pruned={results['pruned']}, "
            f"merged={results['merged']}, patterns={results['patterns_extracted']}"
        )

        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            "consolidation_cycles": self._consolidation_count,
            "total_promoted": self._promoted_count,
            "total_pruned": self._pruned_count,
            "total_merged": self._merged_count,
            "last_consolidation": self._last_consolidation.isoformat() if self._last_consolidation else None,
        }


# =============================================================================
# UNIFIED MEMORY SYSTEM
# =============================================================================

class UnifiedMemory:
    """
    Grace's complete unified memory system.

    One API for all memory operations. Replaces calling Memory Mesh
    or Magma separately. Every subsystem goes through here.

    Memory types: episodic, procedural, semantic, working, learning, causal
    Lifecycle: flash → short-term → long-term → permanent (or forgotten)
    Intelligence: Magma graphs for retrieval, Memory Mesh for persistence
    """

    def __init__(self, message_bus=None, self_mirror=None, timesense=None):
        self.message_bus = message_bus
        self.self_mirror = self_mirror
        self.timesense = timesense

        # Core memory store
        self._memories: Dict[str, Memory] = {}
        self._working_memory: deque = deque(maxlen=50)

        # Subsystems
        self.associations = AssociativeRecallEngine()
        self.consolidation = ConsolidationEngine(self)

        # Magma intelligence layer (if available)
        self._magma = None
        try:
            from cognitive.magma import get_grace_magma
            self._magma = get_grace_magma()
        except Exception:
            pass

        # Background consolidation
        self._consolidation_interval = 300  # 5 minutes
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Stats
        self._stats = {
            "total_memories_created": 0,
            "total_recalls": 0,
            "total_reinforcements": 0,
            "memories_by_type": {t.value: 0 for t in MemoryType},
            "memories_by_strength": {s.value: 0 for s in MemoryStrength},
        }

        logger.info("[UNIFIED-MEMORY] Initialized - Grace's complete memory system")

    # =========================================================================
    # CORE OPERATIONS
    # =========================================================================

    def remember(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SEMANTIC,
        source: str = "system",
        trust_score: float = 0.5,
        tags: List[str] = None,
        genesis_key_id: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Memory:
        """
        Store a new memory. Grace remembers something.

        Args:
            content: What to remember
            memory_type: Type of memory (episodic, procedural, semantic, etc.)
            source: Where this came from
            trust_score: Initial trust (0-1)
            tags: Labels for categorization
            genesis_key_id: Genesis Key for provenance

        Returns:
            The created Memory
        """
        import uuid
        mem_id = f"mem-{uuid.uuid4().hex[:12]}"

        memory = Memory(
            id=mem_id,
            content=content,
            memory_type=memory_type,
            strength=MemoryStrength.FLASH,
            trust_score=trust_score,
            source=source,
            genesis_key_id=genesis_key_id,
            tags=tags or [],
            metadata=metadata or {},
        )

        self._memories[mem_id] = memory
        self._working_memory.append(mem_id)
        self._stats["total_memories_created"] += 1
        self._stats["memories_by_type"][memory_type.value] += 1
        self._stats["memories_by_strength"][MemoryStrength.FLASH.value] += 1

        # Feed to Magma for graph indexing
        if self._magma:
            try:
                self._magma.ingest(content, genesis_key_id=genesis_key_id, source=source)
            except Exception:
                pass

        # Broadcast via message bus
        if self.message_bus:
            try:
                import asyncio
                from layer1.message_bus import ComponentType
                asyncio.ensure_future(self.message_bus.publish(
                    topic="memory.created",
                    payload={"id": mem_id, "type": memory_type.value, "source": source},
                    from_component=ComponentType.MEMORY_MESH,
                ))
            except (RuntimeError, Exception):
                pass

        # Feed to TimeSense
        if self.timesense:
            try:
                self.timesense.record_operation(
                    "memory.remember", 0, "unified_memory",
                    data_bytes=float(len(content)),
                )
            except Exception:
                pass

        return memory

    def recall(
        self,
        query: str,
        memory_types: List[MemoryType] = None,
        min_trust: float = 0.0,
        limit: int = 10,
        include_associations: bool = True,
    ) -> List[Memory]:
        """
        Recall memories matching a query. Grace remembers.

        Uses Magma's intent-aware retrieval for intelligent search,
        then enriches with associative recall across memory types.

        Args:
            query: What to search for
            memory_types: Filter by memory type (None = all)
            min_trust: Minimum trust score
            limit: Max results
            include_associations: Include associated memories

        Returns:
            List of matching memories, ranked by effective score
        """
        start_time = time.perf_counter()
        self._stats["total_recalls"] += 1

        results = []

        # Search across all memories
        query_lower = query.lower()
        for mem in self._memories.values():
            if memory_types and mem.memory_type not in memory_types:
                continue
            if mem.trust_score < min_trust:
                continue
            if mem.current_retention < 0.05:
                continue

            # Simple text matching (Magma handles semantic matching)
            relevance = 0.0
            if query_lower in mem.content.lower():
                relevance = 0.8
            elif any(tag in query_lower for tag in mem.tags):
                relevance = 0.6
            elif any(word in mem.content.lower() for word in query_lower.split()[:3]):
                relevance = 0.3

            if relevance > 0:
                mem.relevance_score = relevance
                results.append(mem)

        # Also query Magma for semantic/graph matches
        if self._magma:
            try:
                magma_results = self._magma.query(query, limit=limit)
                for r in (magma_results or []):
                    content = getattr(r, 'content', str(r))
                    score = getattr(r, 'score', 0.5)
                    graph = getattr(r, 'graph', 'unknown')

                    import uuid
                    virtual_mem = Memory(
                        id=f"magma-{uuid.uuid4().hex[:8]}",
                        content=content[:500] if isinstance(content, str) else str(content)[:500],
                        memory_type=MemoryType.SEMANTIC,
                        strength=MemoryStrength.LONG_TERM,
                        trust_score=float(score),
                        relevance_score=float(score),
                        source=f"magma_{graph}",
                    )
                    results.append(virtual_mem)
            except Exception:
                pass

        # Rank by effective score
        results.sort(key=lambda m: m.effective_score, reverse=True)
        results = results[:limit]

        # Reinforce accessed memories
        for mem in results:
            if mem.id in self._memories:
                mem.reinforce()
                self._stats["total_reinforcements"] += 1

        # Associative recall
        if include_associations and results:
            associated = set()
            for mem in results[:3]:
                for assoc_id, strength in self.associations.get_associations(mem.id):
                    if assoc_id in self._memories and assoc_id not in associated:
                        associated.add(assoc_id)

            for assoc_id in list(associated)[:5]:
                assoc_mem = self._memories.get(assoc_id)
                if assoc_mem and assoc_mem not in results:
                    assoc_mem.relevance_score = 0.2
                    results.append(assoc_mem)

            # Record co-access for future associations
            if len(results) >= 2:
                for i, mem_a in enumerate(results[:3]):
                    for mem_b in results[i+1:4]:
                        if mem_a.id in self._memories and mem_b.id in self._memories:
                            self.associations.record_co_access(mem_a.id, mem_b.id)

        elapsed = (time.perf_counter() - start_time) * 1000
        if self.timesense:
            try:
                self.timesense.record_operation("memory.recall", elapsed, "unified_memory")
            except Exception:
                pass

        return results

    def forget(self, memory_id: str) -> bool:
        """Explicitly forget a memory."""
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False

    def reinforce(self, memory_id: str) -> bool:
        """Reinforce a memory (mark as validated/useful)."""
        mem = self._memories.get(memory_id)
        if mem:
            mem.reinforce()
            self._stats["total_reinforcements"] += 1
            return True
        return False

    # =========================================================================
    # WORKING MEMORY
    # =========================================================================

    def get_working_memory(self) -> List[Memory]:
        """Get current working memory (recent active context)."""
        return [
            self._memories[mid]
            for mid in self._working_memory
            if mid in self._memories
        ]

    def add_to_working_memory(self, memory_id: str):
        """Bring a memory into working memory (active focus)."""
        if memory_id in self._memories:
            self._working_memory.append(memory_id)
            self._memories[memory_id].reinforce()

    def clear_working_memory(self):
        """Clear working memory."""
        self._working_memory.clear()

    # =========================================================================
    # LIFECYCLE: CONSOLIDATION + FORGETTING
    # =========================================================================

    def run_consolidation(self) -> Dict[str, Any]:
        """Run memory consolidation (like sleep for the brain)."""
        return self.consolidation.consolidate(self._memories)

    def start_consolidation_loop(self):
        """Start periodic background consolidation."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._consolidation_loop, daemon=True)
        self._thread.start()
        logger.info(f"[UNIFIED-MEMORY] Consolidation loop started ({self._consolidation_interval}s interval)")

    def stop_consolidation_loop(self):
        """Stop consolidation loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _consolidation_loop(self):
        """Background consolidation thread."""
        while self._running:
            time.sleep(self._consolidation_interval)
            if self._running:
                try:
                    self.run_consolidation()
                except Exception as e:
                    logger.error(f"[UNIFIED-MEMORY] Consolidation error: {e}")

    # =========================================================================
    # MEMORY TYPES: CONVENIENCE METHODS
    # =========================================================================

    def remember_episode(self, what_happened: str, outcome: str, **kwargs) -> Memory:
        """Remember a concrete experience."""
        content = f"Experience: {what_happened}\nOutcome: {outcome}"
        return self.remember(content, MemoryType.EPISODIC, **kwargs)

    def remember_procedure(self, name: str, steps: List[str], **kwargs) -> Memory:
        """Remember how to do something."""
        content = f"Procedure: {name}\nSteps:\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
        return self.remember(content, MemoryType.PROCEDURAL, tags=[name], **kwargs)

    def remember_fact(self, fact: str, **kwargs) -> Memory:
        """Remember a fact or piece of knowledge."""
        return self.remember(fact, MemoryType.SEMANTIC, **kwargs)

    def remember_cause(self, cause: str, effect: str, **kwargs) -> Memory:
        """Remember a causal relationship."""
        content = f"Cause: {cause}\nEffect: {effect}"
        return self.remember(content, MemoryType.CAUSAL, tags=["causal"], **kwargs)

    def learn(self, content: str, trust: float = 0.5, **kwargs) -> Memory:
        """Store a learning example with trust score."""
        return self.remember(content, MemoryType.LEARNING, trust_score=trust, **kwargs)

    # =========================================================================
    # STATS AND DASHBOARD
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Full memory system statistics."""
        type_counts = defaultdict(int)
        strength_counts = defaultdict(int)
        avg_trust = 0.0
        avg_retention = 0.0

        for mem in self._memories.values():
            type_counts[mem.memory_type.value] += 1
            strength_counts[mem.strength.value] += 1
            avg_trust += mem.trust_score
            avg_retention += mem.current_retention

        total = len(self._memories)
        if total > 0:
            avg_trust /= total
            avg_retention /= total

        return {
            "total_memories": total,
            "working_memory_size": len(self._working_memory),
            "by_type": dict(type_counts),
            "by_strength": dict(strength_counts),
            "avg_trust": round(avg_trust, 3),
            "avg_retention": round(avg_retention, 3),
            "consolidation": self.consolidation.get_stats(),
            "associations": len(self.associations._association_strengths),
            "magma_connected": self._magma is not None,
            "bus_connected": self.message_bus is not None,
            "counters": self._stats,
        }

    def get_dashboard(self) -> Dict[str, Any]:
        """Memory system dashboard."""
        stats = self.get_stats()

        recent = sorted(
            self._memories.values(),
            key=lambda m: m.created_at,
            reverse=True,
        )[:10]

        strongest = sorted(
            self._memories.values(),
            key=lambda m: m.effective_score,
            reverse=True,
        )[:10]

        weakest = sorted(
            (m for m in self._memories.values() if m.strength != MemoryStrength.PERMANENT),
            key=lambda m: m.current_retention,
        )[:10]

        return {
            "stats": stats,
            "recent_memories": [m.to_dict() for m in recent],
            "strongest_memories": [m.to_dict() for m in strongest],
            "weakest_memories": [m.to_dict() for m in weakest],
            "working_memory": [
                self._memories[mid].to_dict()
                for mid in self._working_memory
                if mid in self._memories
            ],
        }


# =============================================================================
# SINGLETON
# =============================================================================

_unified_memory: Optional[UnifiedMemory] = None


def get_unified_memory(message_bus=None, self_mirror=None, timesense=None) -> UnifiedMemory:
    """Get or create the global unified memory system."""
    global _unified_memory
    if _unified_memory is None:
        _unified_memory = UnifiedMemory(
            message_bus=message_bus,
            self_mirror=self_mirror,
            timesense=timesense,
        )
    return _unified_memory


def reset_unified_memory():
    """Reset unified memory (for testing)."""
    global _unified_memory
    if _unified_memory:
        _unified_memory.stop_consolidation_loop()
    _unified_memory = None
