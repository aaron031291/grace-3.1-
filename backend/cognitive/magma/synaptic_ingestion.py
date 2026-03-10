"""
Magma Memory - Synaptic Ingestion

Write/update path for the Magma memory system:
1. Event Segmentation - Break content into meaningful segments
2. Dense/Sparse Embedding - Generate embeddings for segments
3. Semantic Linking - Connect to existing semantic concepts
4. Temporal Linking - Establish time relationships
5. Entity Linking - Link entities across contexts
6. Causal Inference - Detect cause-effect relationships

This is the ingestion pipeline that feeds the relation graphs.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from enum import Enum
from datetime import datetime, timezone
import uuid
import re
import logging

from cognitive.magma.relation_graphs import (
    MagmaRelationGraphs,
    GraphNode,
    GraphEdge,
    RelationType
)

logger = logging.getLogger(__name__)


class SegmentType(Enum):
    """Types of segments extracted from content."""
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    CONCEPT = "concept"
    ENTITY = "entity"
    EVENT = "event"
    FACT = "fact"
    PROCEDURE = "procedure"


@dataclass
class Segment:
    """A segment extracted from content."""
    id: str
    content: str
    segment_type: SegmentType
    start_pos: int
    end_pos: int
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    entities: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class IngestionResult:
    """Result of ingesting content."""
    segments: List[Segment]
    nodes_created: List[str]  # Node IDs
    edges_created: List[str]  # Edge IDs
    entities_linked: int
    concepts_linked: int
    temporal_links: int
    causal_links: int
    genesis_key_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventSegmenter:
    """
    Segments content into meaningful units for graph ingestion.

    Strategies:
    - Sentence segmentation
    - Paragraph segmentation
    - Entity extraction
    - Concept extraction
    """

    def __init__(self):
        # Simple sentence boundaries
        self.sentence_pattern = re.compile(r'(?<=[.!?])\s+')

        # Paragraph boundaries
        self.paragraph_pattern = re.compile(r'\n\n+')

        # Common entities (simplified - would use NER in production)
        self.entity_pattern = re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b')

        logger.info("[MAGMA-SEGMENTER] EventSegmenter initialized")

    def segment(
        self,
        content: str,
        segment_type: SegmentType = SegmentType.SENTENCE
    ) -> List[Segment]:
        """
        Segment content into units.

        Args:
            content: Raw content to segment
            segment_type: Type of segmentation to perform

        Returns:
            List of Segment objects
        """
        if segment_type == SegmentType.SENTENCE:
            return self._segment_sentences(content)
        elif segment_type == SegmentType.PARAGRAPH:
            return self._segment_paragraphs(content)
        elif segment_type == SegmentType.ENTITY:
            return self._extract_entities(content)
        elif segment_type == SegmentType.CONCEPT:
            return self._extract_concepts(content)
        else:
            return self._segment_sentences(content)

    def _segment_sentences(self, content: str) -> List[Segment]:
        """Segment into sentences."""
        sentences = self.sentence_pattern.split(content)
        segments = []

        pos = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            start = content.find(sentence, pos)
            end = start + len(sentence)

            # Extract entities from sentence
            entities = self.entity_pattern.findall(sentence)

            segments.append(Segment(
                id=f"seg-{uuid.uuid4().hex[:8]}",
                content=sentence,
                segment_type=SegmentType.SENTENCE,
                start_pos=start,
                end_pos=end,
                entities=entities
            ))

            pos = end

        return segments

    def _segment_paragraphs(self, content: str) -> List[Segment]:
        """Segment into paragraphs."""
        paragraphs = self.paragraph_pattern.split(content)
        segments = []

        pos = 0
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            start = content.find(para, pos)
            end = start + len(para)

            entities = self.entity_pattern.findall(para)

            segments.append(Segment(
                id=f"seg-{uuid.uuid4().hex[:8]}",
                content=para,
                segment_type=SegmentType.PARAGRAPH,
                start_pos=start,
                end_pos=end,
                entities=entities
            ))

            pos = end

        return segments

    def _extract_entities(self, content: str) -> List[Segment]:
        """Extract entities as segments."""
        entities = self.entity_pattern.findall(content)
        segments = []

        for entity in set(entities):  # Unique entities
            # Find first occurrence
            start = content.find(entity)
            end = start + len(entity)

            segments.append(Segment(
                id=f"ent-{uuid.uuid4().hex[:8]}",
                content=entity,
                segment_type=SegmentType.ENTITY,
                start_pos=start,
                end_pos=end,
                entities=[entity]
            ))

        return segments

    def _extract_concepts(self, content: str) -> List[Segment]:
        """Extract concepts (noun phrases) as segments."""
        # Simplified concept extraction - would use NLP in production
        # Look for patterns like "the X of Y" or technical terms
        concept_patterns = [
            r'\b(?:the\s+)?(\w+(?:\s+\w+)*)\s+(?:of|for|in)\s+(\w+(?:\s+\w+)*)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*)',
        ]

        concepts = set()
        for pattern in concept_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    concepts.update(m for m in match if len(m) > 2)
                elif len(match) > 2:
                    concepts.add(match)

        segments = []
        for concept in concepts:
            start = content.lower().find(concept.lower())
            if start >= 0:
                segments.append(Segment(
                    id=f"con-{uuid.uuid4().hex[:8]}",
                    content=concept,
                    segment_type=SegmentType.CONCEPT,
                    start_pos=start,
                    end_pos=start + len(concept),
                    concepts=[concept]
                ))

        return segments


class SemanticLinker:
    """Links segments to semantic concepts in the graph."""

    def __init__(self, graphs: MagmaRelationGraphs, similarity_threshold: float = 0.7):
        self.graphs = graphs
        self.similarity_threshold = similarity_threshold

    def link_segment(
        self,
        segment: Segment,
        embedding: Optional[List[float]] = None
    ) -> List[str]:
        """
        Link a segment to existing semantic concepts.

        Returns list of created edge IDs.
        """
        if not embedding:
            return []

        # Add segment as new concept node
        node_id = self.graphs.semantic.add_concept(
            content=segment.content,
            embedding=embedding,
            metadata={"segment_id": segment.id, "segment_type": segment.segment_type.value}
        )

        # Return node ID (edges are auto-created by SemanticGraph)
        return [node_id]


class TemporalLinker:
    """Links segments to temporal events in the graph."""

    def __init__(self, graphs: MagmaRelationGraphs):
        self.graphs = graphs

    def link_segment(
        self,
        segment: Segment,
        timestamp: Optional[datetime] = None
    ) -> List[str]:
        """
        Link a segment to temporal graph.

        Returns list of created node/edge IDs.
        """
        ts = timestamp or segment.timestamp

        # Add as temporal event
        node_id = self.graphs.temporal.add_event(
            content=segment.content,
            timestamp=ts,
            metadata={"segment_id": segment.id}
        )

        return [node_id]


class EntityLinker:
    """Links entities across contexts in the entity graph."""

    def __init__(self, graphs: MagmaRelationGraphs):
        self.graphs = graphs
        self.entity_cache: Dict[str, str] = {}  # entity_name -> node_id

    def link_entities(self, segment: Segment) -> List[str]:
        """
        Link entities from segment to entity graph.

        Creates entity nodes and co-occurrence edges.
        """
        created_ids = []

        # Create/find entity nodes
        entity_node_ids = []
        for entity in segment.entities:
            entity_lower = entity.lower()

            if entity_lower in self.entity_cache:
                entity_node_ids.append(self.entity_cache[entity_lower])
            else:
                # Create new entity node
                node_id = self.graphs.entity.add_entity(
                    name=entity,
                    entity_type="extracted",
                    attributes={"source_segment": segment.id}
                )
                self.entity_cache[entity_lower] = node_id
                entity_node_ids.append(node_id)
                created_ids.append(node_id)

        # Record co-occurrences between entities in same segment
        for i, ent1_id in enumerate(entity_node_ids):
            for ent2_id in entity_node_ids[i+1:]:
                self.graphs.entity.record_co_occurrence(
                    ent1_id, ent2_id,
                    context=segment.content[:100]  # First 100 chars as context
                )

        return created_ids


class CausalLinker:
    """Detects and links causal relationships."""

    def __init__(self, graphs: MagmaRelationGraphs):
        self.graphs = graphs

        # Causal indicator patterns
        self.causal_patterns = [
            (r'(\w+(?:\s+\w+)*)\s+causes?\s+(\w+(?:\s+\w+)*)', RelationType.CAUSAL_CAUSES),
            (r'(\w+(?:\s+\w+)*)\s+leads?\s+to\s+(\w+(?:\s+\w+)*)', RelationType.CAUSAL_CAUSES),
            (r'(\w+(?:\s+\w+)*)\s+results?\s+in\s+(\w+(?:\s+\w+)*)', RelationType.CAUSAL_CAUSES),
            (r'because\s+of\s+(\w+(?:\s+\w+)*)[,.]?\s+(\w+(?:\s+\w+)*)', RelationType.CAUSAL_CAUSED_BY),
            (r'(\w+(?:\s+\w+)*)\s+enables?\s+(\w+(?:\s+\w+)*)', RelationType.CAUSAL_ENABLES),
            (r'(\w+(?:\s+\w+)*)\s+prevents?\s+(\w+(?:\s+\w+)*)', RelationType.CAUSAL_PREVENTS),
        ]

    def detect_causal_relations(
        self,
        segment: Segment
    ) -> List[Tuple[str, str, RelationType]]:
        """
        Detect causal relationships in segment.

        Returns list of (cause, effect, relation_type) tuples.
        """
        relations = []

        for pattern, relation_type in self.causal_patterns:
            matches = re.findall(pattern, segment.content.lower())
            for match in matches:
                if len(match) >= 2:
                    relations.append((match[0], match[1], relation_type))

        return relations

    def link_causal_relations(
        self,
        segment: Segment
    ) -> List[str]:
        """
        Create causal links from segment.

        Returns list of created edge IDs.
        """
        relations = self.detect_causal_relations(segment)
        created_ids = []

        for cause, effect, relation_type in relations:
            # Create or find cause node
            cause_node = GraphNode(
                id=f"causal-{uuid.uuid4().hex[:8]}",
                node_type="cause",
                content=cause,
                metadata={"source_segment": segment.id}
            )
            self.graphs.causal.add_node(cause_node)

            # Create or find effect node
            effect_node = GraphNode(
                id=f"causal-{uuid.uuid4().hex[:8]}",
                node_type="effect",
                content=effect,
                metadata={"source_segment": segment.id}
            )
            self.graphs.causal.add_node(effect_node)

            # Create causal link
            edge_id = self.graphs.causal.add_causal_link(
                cause_node.id,
                effect_node.id,
                relation_type,
                confidence=0.6,
                evidence=[segment.content[:200]]
            )
            created_ids.append(edge_id)

        return created_ids


class SynapticIngestionPipeline:
    """
    Complete ingestion pipeline for Magma memory.

    Orchestrates:
    1. Event segmentation
    2. Embedding generation (placeholder - needs actual embedder)
    3. Semantic linking
    4. Temporal linking
    5. Entity linking
    6. Causal inference
    """

    def __init__(
        self,
        graphs: MagmaRelationGraphs,
        embedding_fn: Optional[Callable[[str], List[float]]] = None
    ):
        """
        Initialize ingestion pipeline.

        Args:
            graphs: MagmaRelationGraphs instance
            embedding_fn: Optional function to generate embeddings
        """
        self.graphs = graphs
        self.embedding_fn = embedding_fn or self._default_embedding

        self.segmenter = EventSegmenter()
        self.semantic_linker = SemanticLinker(graphs)
        self.temporal_linker = TemporalLinker(graphs)
        self.entity_linker = EntityLinker(graphs)
        self.causal_linker = CausalLinker(graphs)

        logger.info("[MAGMA-INGESTION] SynapticIngestionPipeline initialized")

    def _default_embedding(self, text: str) -> List[float]:
        """Default embedding function (placeholder)."""
        # Simple hash-based pseudo-embedding for testing
        # In production, use actual embedding model
        import hashlib
        hash_bytes = hashlib.sha256(text.encode()).digest()
        return [b / 255.0 for b in hash_bytes] * 12  # 384 dimensions

    def ingest(
        self,
        content: str,
        genesis_key_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IngestionResult:
        """
        Ingest content into Magma memory.

        Args:
            content: Content to ingest
            genesis_key_id: Optional Genesis Key for tracking
            timestamp: Optional timestamp for temporal linking
            metadata: Optional additional metadata

        Returns:
            IngestionResult with details of what was created
        """
        timestamp = timestamp or datetime.now(timezone.utc)
        metadata = metadata or {}

        # 1. Segment content
        sentence_segments = self.segmenter.segment(content, SegmentType.SENTENCE)
        entity_segments = self.segmenter.segment(content, SegmentType.ENTITY)

        all_segments = sentence_segments + entity_segments

        # Track results
        nodes_created = []
        edges_created = []
        entities_linked = 0
        concepts_linked = 0
        temporal_links = 0
        causal_links = 0

        # 2. Process each segment
        for segment in sentence_segments:
            # Generate embedding
            embedding = self.embedding_fn(segment.content)
            segment.embedding = embedding

            # Semantic linking
            semantic_ids = self.semantic_linker.link_segment(segment, embedding)
            nodes_created.extend(semantic_ids)
            concepts_linked += len(semantic_ids)

            # Temporal linking
            temporal_ids = self.temporal_linker.link_segment(segment, timestamp)
            nodes_created.extend(temporal_ids)
            temporal_links += len(temporal_ids)

            # Entity linking
            entity_ids = self.entity_linker.link_entities(segment)
            nodes_created.extend(entity_ids)
            entities_linked += len(segment.entities)

            # Causal inference
            causal_ids = self.causal_linker.link_causal_relations(segment)
            edges_created.extend(causal_ids)
            causal_links += len(causal_ids)

        logger.info(
            f"[MAGMA-INGESTION] Ingested {len(all_segments)} segments: "
            f"{concepts_linked} concepts, {entities_linked} entities, "
            f"{temporal_links} temporal, {causal_links} causal"
        )

        return IngestionResult(
            segments=all_segments,
            nodes_created=nodes_created,
            edges_created=edges_created,
            entities_linked=entities_linked,
            concepts_linked=concepts_linked,
            temporal_links=temporal_links,
            causal_links=causal_links,
            genesis_key_id=genesis_key_id,
            metadata={
                "timestamp": timestamp.isoformat(),
                "source_length": len(content),
                **metadata
            }
        )

    def ingest_batch(
        self,
        contents: List[str],
        genesis_key_id: Optional[str] = None
    ) -> List[IngestionResult]:
        """
        Ingest multiple pieces of content.

        Args:
            contents: List of content strings
            genesis_key_id: Optional shared Genesis Key

        Returns:
            List of IngestionResult objects
        """
        results = []
        for content in contents:
            result = self.ingest(content, genesis_key_id=genesis_key_id)
            results.append(result)
        return results
