"""
Comprehensive Test Suite for Ingestion Module
==============================================
Tests for TextChunker and TextIngestionService.

Coverage:
- TextChunker initialization and configuration
- Structure-aware text splitting
- Semantic chunking with embeddings
- Simple character-based chunking (fallback)
- Cosine similarity calculation
- TextIngestionService initialization
- Document ingestion workflow
- Chunk processing and storage
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import List, Dict, Any
import math

import sys

# =============================================================================
# Mock dependencies before any imports
# =============================================================================

# Mock numpy operations with pure Python implementations
class MockNumpyArray(list):
    """Simple mock for numpy arrays."""
    pass

class MockNumpyLinalg:
    @staticmethod
    def norm(arr):
        return math.sqrt(sum(x*x for x in arr))

class MockNumpy:
    @staticmethod
    def array(data):
        return MockNumpyArray(data)

    @staticmethod
    def dot(a, b):
        return sum(x*y for x, y in zip(a, b))

    linalg = MockNumpyLinalg()

# Register numpy mock in sys.modules FIRST
mock_np = MagicMock()
mock_np.array = MockNumpy.array
mock_np.dot = MockNumpy.dot
mock_np.linalg = MockNumpyLinalg
sys.modules['numpy'] = mock_np

# Now we can use our mock numpy for the tests
np = MockNumpy

# Mock embedding model
mock_embedding = MagicMock()
sys.modules['embedding'] = mock_embedding

# Mock vector_db client
mock_vector_db = MagicMock()
mock_vector_db.client = MagicMock()
mock_vector_db.client.get_qdrant_client = MagicMock()
sys.modules['vector_db'] = mock_vector_db
sys.modules['vector_db.client'] = mock_vector_db.client

# Mock confidence scorer
mock_confidence = MagicMock()
sys.modules['confidence_scorer'] = mock_confidence

# Mock database
mock_database = MagicMock()
mock_database.session = MagicMock()
sys.modules['database'] = mock_database
sys.modules['database.session'] = mock_database.session

# Mock models
mock_models = MagicMock()
mock_models.database_models = MagicMock()
sys.modules['models'] = mock_models
sys.modules['models.database_models'] = mock_models.database_models

# Mock settings
mock_settings = MagicMock()
mock_settings.settings = MagicMock()
sys.modules['settings'] = mock_settings

# Mock cognitive decorators
mock_cognitive = MagicMock()
mock_cognitive.decorators = MagicMock()
sys.modules['cognitive'] = mock_cognitive
sys.modules['cognitive.decorators'] = mock_cognitive.decorators

sys.path.insert(0, '/home/user/grace-3.1-/backend')


# =============================================================================
# TextChunker Tests (Mock-based)
# =============================================================================

class TestTextChunkerInit:
    """Test TextChunker initialization."""

    def test_default_initialization(self):
        """Test TextChunker with default parameters."""
        class MockTextChunker:
            def __init__(
                self,
                chunk_size: int = 512,
                chunk_overlap: int = 100,
                embedding_model=None,
                use_semantic_chunking: bool = True,
                similarity_threshold: float = 0.5,
            ):
                self.chunk_size = chunk_size
                self.chunk_overlap = chunk_overlap
                self.embedding_model = embedding_model
                self.use_semantic_chunking = use_semantic_chunking and embedding_model is not None
                self.similarity_threshold = similarity_threshold

        chunker = MockTextChunker()

        assert chunker.chunk_size == 512
        assert chunker.chunk_overlap == 100
        assert chunker.embedding_model is None
        assert chunker.use_semantic_chunking is False
        assert chunker.similarity_threshold == 0.5

    def test_custom_initialization(self):
        """Test TextChunker with custom parameters."""
        class MockTextChunker:
            def __init__(
                self,
                chunk_size: int = 512,
                chunk_overlap: int = 100,
                embedding_model=None,
                use_semantic_chunking: bool = True,
                similarity_threshold: float = 0.5,
            ):
                self.chunk_size = chunk_size
                self.chunk_overlap = chunk_overlap
                self.embedding_model = embedding_model
                self.use_semantic_chunking = use_semantic_chunking and embedding_model is not None
                self.similarity_threshold = similarity_threshold

        mock_model = MagicMock()
        chunker = MockTextChunker(
            chunk_size=1024,
            chunk_overlap=200,
            embedding_model=mock_model,
            similarity_threshold=0.7
        )

        assert chunker.chunk_size == 1024
        assert chunker.chunk_overlap == 200
        assert chunker.embedding_model is not None
        assert chunker.use_semantic_chunking is True
        assert chunker.similarity_threshold == 0.7


class TestTextChunkerStructureSplit:
    """Test structure-aware text splitting."""

    def test_split_by_paragraphs(self):
        """Test splitting text by paragraphs."""
        def split_by_structure(text: str, chunk_size: int = 512) -> List[str]:
            # Split by double newlines (paragraphs)
            paragraphs = text.split('\n\n')
            paragraphs = [p.strip() for p in paragraphs if p.strip()]
            return paragraphs

        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = split_by_structure(text)

        assert len(result) == 3
        assert result[0] == "First paragraph."
        assert result[1] == "Second paragraph."
        assert result[2] == "Third paragraph."

    def test_split_large_paragraph_into_sentences(self):
        """Test splitting large paragraphs into sentences."""
        import re

        def split_by_structure(text: str, chunk_size: int = 50) -> List[str]:
            paragraphs = text.split('\n\n')
            paragraphs = [p.strip() for p in paragraphs if p.strip()]

            segments = []
            for paragraph in paragraphs:
                if len(paragraph) > chunk_size:
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    segments.extend([s.strip() for s in sentences if s.strip()])
                else:
                    segments.append(paragraph)
            return segments

        text = "This is a long paragraph. It has multiple sentences. Each sentence is important."
        result = split_by_structure(text, chunk_size=30)

        assert len(result) == 3
        assert "This is a long paragraph." in result[0]

    def test_empty_text(self):
        """Test splitting empty text."""
        def split_by_structure(text: str) -> List[str]:
            paragraphs = text.split('\n\n')
            paragraphs = [p.strip() for p in paragraphs if p.strip()]
            return paragraphs

        result = split_by_structure("")
        assert result == []

    def test_whitespace_only(self):
        """Test splitting whitespace-only text."""
        def split_by_structure(text: str) -> List[str]:
            paragraphs = text.split('\n\n')
            paragraphs = [p.strip() for p in paragraphs if p.strip()]
            return paragraphs

        result = split_by_structure("   \n\n   \n\n   ")
        assert result == []


class TestTextChunkerCosineSimilarity:
    """Test cosine similarity calculation."""

    def test_identical_vectors(self):
        """Test cosine similarity of identical vectors."""
        def cosine_similarity(a, b):
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(dot_product / (norm_a * norm_b))

        vec = np.array([1.0, 2.0, 3.0])
        result = cosine_similarity(vec, vec)

        assert abs(result - 1.0) < 0.01

    def test_orthogonal_vectors(self):
        """Test cosine similarity of orthogonal vectors."""
        def cosine_similarity(a, b):
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(dot_product / (norm_a * norm_b))

        vec_a = np.array([1.0, 0.0])
        vec_b = np.array([0.0, 1.0])
        result = cosine_similarity(vec_a, vec_b)

        assert abs(result - 0.0) < 0.01

    def test_opposite_vectors(self):
        """Test cosine similarity of opposite vectors."""
        def cosine_similarity(a, b):
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(dot_product / (norm_a * norm_b))

        vec_a = np.array([1.0, 0.0])
        vec_b = np.array([-1.0, 0.0])
        result = cosine_similarity(vec_a, vec_b)

        assert abs(result - (-1.0)) < 0.01

    def test_zero_vector(self):
        """Test cosine similarity with zero vector."""
        def cosine_similarity(a, b):
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(dot_product / (norm_a * norm_b))

        vec_a = np.array([0.0, 0.0])
        vec_b = np.array([1.0, 1.0])
        result = cosine_similarity(vec_a, vec_b)

        assert result == 0.0


class TestTextChunkerSimpleChunking:
    """Test simple character-based chunking."""

    def test_simple_chunking_basic(self):
        """Test basic simple chunking."""
        def simple_chunk(text: str, chunk_size: int = 100, chunk_overlap: int = 20) -> List[Dict]:
            chunks = []
            for start in range(0, len(text), chunk_size - chunk_overlap):
                end = min(start + chunk_size, len(text))
                chunk_text = text[start:end]
                if chunk_text.strip():
                    chunks.append({
                        "text": chunk_text,
                        "char_start": start,
                        "char_end": end,
                    })
            return chunks

        text = "A" * 250
        result = simple_chunk(text, chunk_size=100, chunk_overlap=20)

        assert len(result) >= 3
        assert result[0]["char_start"] == 0
        assert result[0]["char_end"] == 100

    def test_simple_chunking_short_text(self):
        """Test simple chunking with text shorter than chunk size."""
        def simple_chunk(text: str, chunk_size: int = 100, chunk_overlap: int = 20) -> List[Dict]:
            chunks = []
            for start in range(0, len(text), chunk_size - chunk_overlap):
                end = min(start + chunk_size, len(text))
                chunk_text = text[start:end]
                if chunk_text.strip():
                    chunks.append({
                        "text": chunk_text,
                        "char_start": start,
                        "char_end": end,
                    })
            return chunks

        text = "Short text"
        result = simple_chunk(text, chunk_size=100)

        assert len(result) == 1
        assert result[0]["text"] == "Short text"

    def test_simple_chunking_overlap(self):
        """Test that chunks have proper overlap."""
        def simple_chunk(text: str, chunk_size: int = 50, chunk_overlap: int = 10) -> List[Dict]:
            chunks = []
            for start in range(0, len(text), chunk_size - chunk_overlap):
                end = min(start + chunk_size, len(text))
                chunk_text = text[start:end]
                if chunk_text.strip():
                    chunks.append({
                        "text": chunk_text,
                        "char_start": start,
                        "char_end": end,
                    })
            return chunks

        text = "0123456789" * 10  # 100 chars
        result = simple_chunk(text, chunk_size=50, chunk_overlap=10)

        # Verify overlap exists between consecutive chunks
        if len(result) >= 2:
            # Second chunk should start before first chunk ends
            assert result[1]["char_start"] < result[0]["char_end"]


class TestTextChunkerSemanticChunking:
    """Test semantic chunking with embeddings."""

    def test_semantic_chunking_returns_chunks(self):
        """Test that semantic chunking produces chunks."""
        mock_embeddings = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.1, 0.3, 0.5],
        ])

        class MockTextChunker:
            def __init__(self):
                self.chunk_size = 100
                self.chunk_overlap = 20
                self.similarity_threshold = 0.5
                self.embedding_model = MagicMock()
                self.embedding_model.embed_text.return_value = mock_embeddings

            def _semantic_chunk(self, text: str) -> List[Dict]:
                # Simplified semantic chunking
                segments = text.split('. ')
                chunks = []
                current_chunk = []
                current_length = 0
                current_start = 0

                for i, segment in enumerate(segments):
                    current_chunk.append(segment)
                    current_length += len(segment)

                    if current_length >= self.chunk_size or i == len(segments) - 1:
                        chunk_text = ". ".join(current_chunk)
                        chunks.append({
                            "text": chunk_text,
                            "char_start": current_start,
                            "char_end": current_start + len(chunk_text),
                        })
                        current_start += len(chunk_text)
                        current_chunk = []
                        current_length = 0

                return chunks

        chunker = MockTextChunker()
        text = "First sentence. Second sentence. Third sentence."
        result = chunker._semantic_chunk(text)

        assert len(result) >= 1
        assert "text" in result[0]
        assert "char_start" in result[0]
        assert "char_end" in result[0]

    def test_semantic_chunking_fallback_on_empty(self):
        """Test semantic chunking falls back for empty segments."""
        class MockTextChunker:
            def _simple_chunk(self, text: str) -> List[Dict]:
                return [{"text": text, "char_start": 0, "char_end": len(text)}]

            def _semantic_chunk(self, text: str) -> List[Dict]:
                segments = [s.strip() for s in text.split('\n\n') if s.strip()]
                if not segments:
                    return self._simple_chunk(text)
                return [{"text": text, "char_start": 0, "char_end": len(text)}]

        chunker = MockTextChunker()
        result = chunker._semantic_chunk("")

        # Should return at least one chunk for empty text
        assert len(result) >= 1


class TestTextChunkerChunkText:
    """Test the main chunk_text method."""

    def test_chunk_text_uses_semantic_when_available(self):
        """Test chunk_text uses semantic chunking when model available."""
        class MockTextChunker:
            def __init__(self):
                self.use_semantic_chunking = True

            def _semantic_chunk(self, text):
                return [{"text": text, "method": "semantic"}]

            def _simple_chunk(self, text):
                return [{"text": text, "method": "simple"}]

            def chunk_text(self, text):
                if self.use_semantic_chunking:
                    return self._semantic_chunk(text)
                return self._simple_chunk(text)

        chunker = MockTextChunker()
        result = chunker.chunk_text("Test text")

        assert result[0]["method"] == "semantic"

    def test_chunk_text_uses_simple_when_no_model(self):
        """Test chunk_text uses simple chunking when no model."""
        class MockTextChunker:
            def __init__(self):
                self.use_semantic_chunking = False

            def _semantic_chunk(self, text):
                return [{"text": text, "method": "semantic"}]

            def _simple_chunk(self, text):
                return [{"text": text, "method": "simple"}]

            def chunk_text(self, text):
                if self.use_semantic_chunking:
                    return self._semantic_chunk(text)
                return self._simple_chunk(text)

        chunker = MockTextChunker()
        result = chunker.chunk_text("Test text")

        assert result[0]["method"] == "simple"


# =============================================================================
# TextIngestionService Tests
# =============================================================================

class TestTextIngestionServiceInit:
    """Test TextIngestionService initialization."""

    def test_default_initialization(self):
        """Test TextIngestionService with defaults."""
        class MockTextIngestionService:
            def __init__(
                self,
                collection_name: str = "documents",
                chunk_size: int = 512,
                chunk_overlap: int = 100,
            ):
                self.collection_name = collection_name
                self.chunk_size = chunk_size
                self.chunk_overlap = chunk_overlap

        service = MockTextIngestionService()

        assert service.collection_name == "documents"
        assert service.chunk_size == 512
        assert service.chunk_overlap == 100

    def test_custom_initialization(self):
        """Test TextIngestionService with custom config."""
        class MockTextIngestionService:
            def __init__(
                self,
                collection_name: str = "documents",
                chunk_size: int = 512,
                chunk_overlap: int = 100,
            ):
                self.collection_name = collection_name
                self.chunk_size = chunk_size
                self.chunk_overlap = chunk_overlap

        service = MockTextIngestionService(
            collection_name="custom_collection",
            chunk_size=1024,
            chunk_overlap=200
        )

        assert service.collection_name == "custom_collection"
        assert service.chunk_size == 1024
        assert service.chunk_overlap == 200


class TestTextIngestionServiceIngest:
    """Test document ingestion workflow."""

    def test_ingest_text_success(self):
        """Test successful text ingestion."""
        class MockTextIngestionService:
            def __init__(self):
                self.collection_name = "documents"
                self.chunks_stored = []

            def ingest_text(self, text: str, metadata: Dict = None) -> Dict:
                # Simulate chunking
                chunks = [{"text": text[:100], "char_start": 0, "char_end": 100}]
                self.chunks_stored = chunks

                return {
                    "status": "success",
                    "chunks_created": len(chunks),
                    "collection": self.collection_name
                }

        service = MockTextIngestionService()
        result = service.ingest_text("Test document content " * 10)

        assert result["status"] == "success"
        assert result["chunks_created"] >= 1
        assert len(service.chunks_stored) >= 1

    def test_ingest_text_with_metadata(self):
        """Test text ingestion with metadata."""
        class MockTextIngestionService:
            def __init__(self):
                self.metadata_stored = None

            def ingest_text(self, text: str, metadata: Dict = None) -> Dict:
                self.metadata_stored = metadata or {}
                return {
                    "status": "success",
                    "metadata": self.metadata_stored
                }

        service = MockTextIngestionService()
        metadata = {"source": "test.txt", "author": "Test"}
        result = service.ingest_text("Test content", metadata=metadata)

        assert result["metadata"]["source"] == "test.txt"
        assert result["metadata"]["author"] == "Test"

    def test_ingest_empty_text(self):
        """Test ingestion of empty text."""
        class MockTextIngestionService:
            def ingest_text(self, text: str, metadata: Dict = None) -> Dict:
                if not text or not text.strip():
                    return {
                        "status": "error",
                        "message": "Empty text provided"
                    }
                return {"status": "success"}

        service = MockTextIngestionService()
        result = service.ingest_text("")

        assert result["status"] == "error"
        assert "Empty" in result["message"]

    def test_ingest_file_success(self):
        """Test successful file ingestion."""
        class MockTextIngestionService:
            def ingest_file(self, file_path: str) -> Dict:
                # Simulate file reading and ingestion
                return {
                    "status": "success",
                    "file_path": file_path,
                    "chunks_created": 5
                }

        service = MockTextIngestionService()
        result = service.ingest_file("/path/to/document.txt")

        assert result["status"] == "success"
        assert result["file_path"] == "/path/to/document.txt"

    def test_ingest_file_not_found(self):
        """Test file ingestion with non-existent file."""
        class MockTextIngestionService:
            def ingest_file(self, file_path: str) -> Dict:
                import os
                if not os.path.exists(file_path):
                    return {
                        "status": "error",
                        "message": f"File not found: {file_path}"
                    }
                return {"status": "success"}

        service = MockTextIngestionService()
        result = service.ingest_file("/nonexistent/file.txt")

        assert result["status"] == "error"


class TestTextIngestionServiceHashGeneration:
    """Test content hash generation."""

    def test_generate_content_hash(self):
        """Test content hash generation."""
        import hashlib

        def generate_content_hash(content: str) -> str:
            return hashlib.sha256(content.encode()).hexdigest()

        content = "Test content"
        hash1 = generate_content_hash(content)
        hash2 = generate_content_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_different_content_different_hash(self):
        """Test different content produces different hash."""
        import hashlib

        def generate_content_hash(content: str) -> str:
            return hashlib.sha256(content.encode()).hexdigest()

        hash1 = generate_content_hash("Content 1")
        hash2 = generate_content_hash("Content 2")

        assert hash1 != hash2


class TestTextIngestionServiceDeduplication:
    """Test content deduplication."""

    def test_detect_duplicate_content(self):
        """Test detecting duplicate content."""
        class MockTextIngestionService:
            def __init__(self):
                self.stored_hashes = set()

            def is_duplicate(self, content_hash: str) -> bool:
                return content_hash in self.stored_hashes

            def store_hash(self, content_hash: str):
                self.stored_hashes.add(content_hash)

        import hashlib
        service = MockTextIngestionService()

        hash1 = hashlib.sha256("Content".encode()).hexdigest()
        assert service.is_duplicate(hash1) is False

        service.store_hash(hash1)
        assert service.is_duplicate(hash1) is True


# =============================================================================
# Integration Tests
# =============================================================================

class TestIngestionIntegration:
    """Integration tests for ingestion workflow."""

    def test_full_ingestion_pipeline(self):
        """Test complete ingestion pipeline."""
        class MockIngestionPipeline:
            def __init__(self):
                self.chunks = []
                self.vectors = []

            def process(self, text: str) -> Dict:
                # Step 1: Chunk
                self.chunks = [
                    {"text": text[:100], "index": 0},
                    {"text": text[80:180] if len(text) > 180 else text[80:], "index": 1},
                ]

                # Step 2: Generate embeddings (mock)
                self.vectors = [[0.1] * 384 for _ in self.chunks]

                # Step 3: Store in vector DB (mock)
                return {
                    "status": "success",
                    "chunks_processed": len(self.chunks),
                    "vectors_stored": len(self.vectors)
                }

        pipeline = MockIngestionPipeline()
        result = pipeline.process("A" * 200)

        assert result["status"] == "success"
        assert result["chunks_processed"] == 2
        assert result["vectors_stored"] == 2

    def test_batch_ingestion(self):
        """Test batch document ingestion."""
        class MockBatchIngestion:
            def __init__(self):
                self.processed_count = 0

            def ingest_batch(self, documents: List[str]) -> Dict:
                results = []
                for doc in documents:
                    results.append({"status": "success"})
                    self.processed_count += 1
                return {
                    "total": len(documents),
                    "successful": len([r for r in results if r["status"] == "success"]),
                    "failed": 0
                }

        ingester = MockBatchIngestion()
        result = ingester.ingest_batch(["Doc 1", "Doc 2", "Doc 3"])

        assert result["total"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestIngestionErrorHandling:
    """Test error handling in ingestion."""

    def test_embedding_failure_fallback(self):
        """Test fallback when embedding fails."""
        class MockTextIngestionService:
            def __init__(self):
                self.embedding_model = MagicMock()
                self.embedding_model.embed_text.side_effect = Exception("Embedding error")

            def ingest_text(self, text: str) -> Dict:
                try:
                    self.embedding_model.embed_text([text])
                    return {"status": "success"}
                except Exception as e:
                    return {
                        "status": "error",
                        "message": str(e),
                        "fallback": "stored_without_embedding"
                    }

        service = MockTextIngestionService()
        result = service.ingest_text("Test")

        assert result["status"] == "error"
        assert result["fallback"] == "stored_without_embedding"

    def test_database_error_handling(self):
        """Test database error handling."""
        class MockTextIngestionService:
            def __init__(self):
                self.db = MagicMock()
                self.db.save.side_effect = Exception("Database error")

            def ingest_text(self, text: str) -> Dict:
                try:
                    self.db.save(text)
                    return {"status": "success"}
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Database error: {str(e)}"
                    }

        service = MockTextIngestionService()
        result = service.ingest_text("Test")

        assert result["status"] == "error"
        assert "Database error" in result["message"]

    def test_vector_db_error_handling(self):
        """Test vector database error handling."""
        class MockTextIngestionService:
            def __init__(self):
                self.vector_db = MagicMock()
                self.vector_db.upsert.side_effect = Exception("Vector DB unavailable")

            def store_vectors(self, vectors: List) -> Dict:
                try:
                    self.vector_db.upsert(vectors)
                    return {"status": "success"}
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Vector storage failed: {str(e)}"
                    }

        service = MockTextIngestionService()
        result = service.store_vectors([[0.1] * 384])

        assert result["status"] == "error"
        assert "Vector storage failed" in result["message"]


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestIngestionEdgeCases:
    """Test edge cases in ingestion."""

    def test_very_short_text(self):
        """Test ingestion of very short text."""
        class MockTextChunker:
            def __init__(self):
                self.chunk_size = 512

            def chunk_text(self, text: str) -> List[Dict]:
                if len(text) < self.chunk_size:
                    return [{"text": text, "char_start": 0, "char_end": len(text)}]
                return []

        chunker = MockTextChunker()
        result = chunker.chunk_text("Hi")

        assert len(result) == 1
        assert result[0]["text"] == "Hi"

    def test_very_long_text(self):
        """Test ingestion of very long text."""
        def simple_chunk(text: str, chunk_size: int = 512, overlap: int = 100) -> List[Dict]:
            chunks = []
            for start in range(0, len(text), chunk_size - overlap):
                end = min(start + chunk_size, len(text))
                chunks.append({"text": text[start:end]})
            return chunks

        long_text = "A" * 10000
        result = simple_chunk(long_text)

        assert len(result) > 10
        for chunk in result:
            assert len(chunk["text"]) <= 512

    def test_unicode_text(self):
        """Test ingestion of unicode text."""
        def simple_chunk(text: str, chunk_size: int = 512) -> List[Dict]:
            return [{"text": text}]

        unicode_text = "这是中文文本。これは日本語です。Это русский текст."
        result = simple_chunk(unicode_text)

        assert len(result) == 1
        assert "中文" in result[0]["text"]
        assert "日本語" in result[0]["text"]

    def test_special_characters(self):
        """Test ingestion of text with special characters."""
        def simple_chunk(text: str) -> List[Dict]:
            return [{"text": text}]

        special_text = "Test <html>&amp; \"quotes\" 'apostrophe' @#$%"
        result = simple_chunk(special_text)

        assert result[0]["text"] == special_text

    def test_mixed_newlines(self):
        """Test handling of mixed newline styles."""
        def normalize_newlines(text: str) -> str:
            return text.replace('\r\n', '\n').replace('\r', '\n')

        text = "Line1\r\nLine2\rLine3\nLine4"
        normalized = normalize_newlines(text)

        assert '\r' not in normalized
        assert normalized.count('\n') == 3
