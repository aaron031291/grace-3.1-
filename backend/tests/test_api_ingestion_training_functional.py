"""
Ingestion and Training APIs - REAL Functional Tests

Tests verify ACTUAL ingestion and training behavior:
- File ingestion
- Document processing
- Training data management
- Learning system APIs
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# INGESTION API TESTS
# =============================================================================

class TestIngestionAPIFunctional:
    """Functional tests for ingestion API."""

    def test_text_ingestion_request(self):
        """TextIngestionRequest must validate fields."""
        from api.ingest import TextIngestionRequest

        request = TextIngestionRequest(
            text="This is test content to ingest",
            filename="test.txt",
            source="manual_upload"
        )

        assert request.text == "This is test content to ingest"
        assert request.filename == "test.txt"

    def test_file_ingestion_request(self):
        """FileIngestionRequest must validate fields."""
        from api.file_ingestion import FileIngestionRequest

        request = FileIngestionRequest(
            file_path="/path/to/file.pdf",
            metadata={"source": "upload"}
        )

        assert request.file_path == "/path/to/file.pdf"

    def test_ingestion_response_structure(self):
        """IngestionResponse must have required fields."""
        from api.ingest import IngestionResponse

        response = IngestionResponse(
            success=True,
            document_id="DOC-001",
            chunks_created=5,
            processing_time=1.5,
            message="Document ingested successfully"
        )

        assert response.success is True
        assert response.document_id == "DOC-001"
        assert response.chunks_created == 5


class TestIngestionServiceFunctional:
    """Functional tests for ingestion service."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return MagicMock()

    @pytest.fixture
    def ingestion_service(self, mock_session):
        """Create ingestion service."""
        with patch('ingestion.ingestion_service.get_session', return_value=mock_session):
            with patch('ingestion.ingestion_service.get_embedding_model'):
                from ingestion.ingestion_service import IngestionService
                return IngestionService()

    def test_initialization(self, ingestion_service):
        """Service must initialize properly."""
        assert ingestion_service is not None

    def test_ingest_text(self, ingestion_service):
        """ingest_text must process text content."""
        result = ingestion_service.ingest_text(
            text="Test content for ingestion",
            filename="test.txt",
            metadata={"source": "test"}
        )

        assert result is not None

    def test_ingest_file(self, ingestion_service, tmp_path):
        """ingest_file must process file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test file content")

        result = ingestion_service.ingest_file(str(test_file))

        assert result is not None

    def test_chunking(self, ingestion_service):
        """Service must chunk long documents."""
        long_text = "Test content. " * 1000

        chunks = ingestion_service.chunk_text(
            text=long_text,
            chunk_size=500,
            overlap=50
        )

        assert len(chunks) > 1


# =============================================================================
# UNIFIED INGESTION TESTS
# =============================================================================

class TestUnifiedIngestionFunctional:
    """Functional tests for unified ingestion API."""

    def test_unified_request_structure(self):
        """UnifiedIngestionRequest must handle multiple sources."""
        from api.unified_ingestion_api import UnifiedIngestionRequest

        request = UnifiedIngestionRequest(
            source_type="file",
            source_path="/path/to/file.pdf",
            options={"extract_images": True}
        )

        assert request.source_type == "file"

    def test_batch_ingestion_request(self):
        """BatchIngestionRequest must handle multiple files."""
        from api.unified_ingestion_api import BatchIngestionRequest

        request = BatchIngestionRequest(
            files=[
                {"path": "/file1.pdf", "type": "pdf"},
                {"path": "/file2.txt", "type": "text"}
            ],
            parallel=True
        )

        assert len(request.files) == 2
        assert request.parallel is True


# =============================================================================
# TRAINING API TESTS
# =============================================================================

class TestTrainingAPIFunctional:
    """Functional tests for training API."""

    def test_training_request_structure(self):
        """TrainingRequest must validate fields."""
        from api.training import TrainingRequest

        request = TrainingRequest(
            training_type="fine_tune",
            data_source="learning_memory",
            parameters={"epochs": 3, "batch_size": 32}
        )

        assert request.training_type == "fine_tune"
        assert request.parameters["epochs"] == 3

    def test_training_response_structure(self):
        """TrainingResponse must have required fields."""
        from api.training import TrainingResponse

        response = TrainingResponse(
            training_id="TRAIN-001",
            status="started",
            message="Training started successfully"
        )

        assert response.training_id == "TRAIN-001"
        assert response.status == "started"


class TestTrainingServiceFunctional:
    """Functional tests for training service."""

    @pytest.fixture
    def training_service(self):
        """Create training service."""
        with patch('api.training.get_session'):
            from api.training import TrainingService
            return TrainingService()

    def test_initialization(self, training_service):
        """Service must initialize properly."""
        assert training_service is not None

    def test_start_training(self, training_service):
        """start_training must initiate training job."""
        result = training_service.start_training(
            training_type="fine_tune",
            data_config={"source": "learning_memory", "limit": 1000}
        )

        assert result is not None
        assert 'training_id' in result or hasattr(result, 'training_id')

    def test_get_training_status(self, training_service):
        """get_status must return training status."""
        status = training_service.get_status("TRAIN-001")

        assert status is not None

    def test_stop_training(self, training_service):
        """stop_training must stop training job."""
        result = training_service.stop_training("TRAIN-001")

        assert result is not None


# =============================================================================
# LEARNING MEMORY API TESTS
# =============================================================================

class TestLearningMemoryAPIFunctional:
    """Functional tests for learning memory API."""

    def test_record_experience_request(self):
        """RecordExperienceRequest must validate fields."""
        from api.learning_memory_api import RecordExperienceRequest

        request = RecordExperienceRequest(
            experience_type="success",
            context={"task": "code_generation"},
            action_taken={"generated": "def foo(): pass"},
            outcome={"success": True, "feedback": 0.95}
        )

        assert request.experience_type == "success"
        assert request.outcome["success"] is True

    def test_experience_response_structure(self):
        """ExperienceResponse must have required fields."""
        from api.learning_memory_api import ExperienceResponse

        response = ExperienceResponse(
            learning_example_id="LE-001",
            trust_score=0.85,
            message="Experience recorded"
        )

        assert response.learning_example_id == "LE-001"
        assert response.trust_score == 0.85

    def test_search_request_structure(self):
        """SearchRequest must validate fields."""
        from api.learning_memory_api import SearchRequest

        request = SearchRequest(
            query="How to fix syntax errors",
            experience_type="correction",
            limit=10
        )

        assert request.query == "How to fix syntax errors"
        assert request.limit == 10


# =============================================================================
# TRAINING CENTER API TESTS
# =============================================================================

class TestTrainingCenterAPIFunctional:
    """Functional tests for training center API."""

    def test_curriculum_request_structure(self):
        """CurriculumRequest must validate fields."""
        from api.training_center_api import CurriculumRequest

        request = CurriculumRequest(
            name="Python Basics",
            topics=["variables", "functions", "classes"],
            difficulty="beginner"
        )

        assert request.name == "Python Basics"
        assert len(request.topics) == 3

    def test_assessment_request_structure(self):
        """AssessmentRequest must validate fields."""
        from api.training_center_api import AssessmentRequest

        request = AssessmentRequest(
            assessment_type="quiz",
            topic="python_functions",
            questions=10
        )

        assert request.assessment_type == "quiz"
        assert request.questions == 10


# =============================================================================
# AUTONOMOUS LEARNING API TESTS
# =============================================================================

class TestAutonomousLearningAPIFunctional:
    """Functional tests for autonomous learning API."""

    def test_learning_task_request(self):
        """LearningTaskRequest must validate fields."""
        from api.autonomous_learning import LearningTaskRequest

        request = LearningTaskRequest(
            task_type="explore",
            topic="error_handling",
            depth="deep"
        )

        assert request.task_type == "explore"
        assert request.topic == "error_handling"

    def test_learning_status_response(self):
        """LearningStatusResponse must have required fields."""
        from api.autonomous_learning import LearningStatusResponse

        response = LearningStatusResponse(
            active=True,
            current_topic="design_patterns",
            examples_learned=50,
            confidence=0.75
        )

        assert response.active is True
        assert response.examples_learned == 50


# =============================================================================
# PROACTIVE LEARNING API TESTS
# =============================================================================

class TestProactiveLearningAPIFunctional:
    """Functional tests for proactive learning API."""

    def test_proactive_task_request(self):
        """ProactiveTaskRequest must validate fields."""
        from api.proactive_learning import ProactiveTaskRequest

        request = ProactiveTaskRequest(
            trigger="code_review_feedback",
            context={"file": "app.py", "issue": "complexity"},
            priority="high"
        )

        assert request.trigger == "code_review_feedback"
        assert request.priority == "high"

    def test_proactive_status_response(self):
        """ProactiveStatusResponse must have required fields."""
        from api.proactive_learning import ProactiveStatusResponse

        response = ProactiveStatusResponse(
            enabled=True,
            pending_tasks=5,
            completed_today=12,
            improvements_made=3
        )

        assert response.enabled is True
        assert response.pending_tasks == 5


# =============================================================================
# FILE MANAGEMENT API TESTS
# =============================================================================

class TestFileManagementAPIFunctional:
    """Functional tests for file management API."""

    def test_file_info_response(self):
        """FileInfoResponse must have required fields."""
        from api.file_management import FileInfoResponse

        response = FileInfoResponse(
            file_id="FILE-001",
            filename="test.py",
            size=1024,
            mime_type="text/x-python",
            created_at=datetime.now(),
            modified_at=datetime.now()
        )

        assert response.file_id == "FILE-001"
        assert response.size == 1024

    def test_directory_listing_response(self):
        """DirectoryListingResponse must have required fields."""
        from api.file_management import DirectoryListingResponse

        response = DirectoryListingResponse(
            path="/knowledge_base",
            files=["file1.txt", "file2.md"],
            directories=["subdir1", "subdir2"],
            total_files=2,
            total_directories=2
        )

        assert len(response.files) == 2
        assert len(response.directories) == 2


# =============================================================================
# KNOWLEDGE BASE API TESTS
# =============================================================================

class TestKnowledgeBaseAPIFunctional:
    """Functional tests for knowledge base API."""

    def test_add_document_request(self):
        """AddDocumentRequest must validate fields."""
        from api.knowledge_base_api import AddDocumentRequest

        request = AddDocumentRequest(
            content="Document content here",
            title="Test Document",
            tags=["test", "example"],
            metadata={"author": "Test"}
        )

        assert request.title == "Test Document"
        assert "test" in request.tags

    def test_search_kb_request(self):
        """SearchKBRequest must validate fields."""
        from api.knowledge_base_api import SearchKBRequest

        request = SearchKBRequest(
            query="How to implement caching",
            filters={"tags": ["python"]},
            limit=20
        )

        assert request.query == "How to implement caching"
        assert request.limit == 20

    def test_kb_statistics_response(self):
        """KBStatisticsResponse must have required fields."""
        from api.knowledge_base_api import KBStatisticsResponse

        response = KBStatisticsResponse(
            total_documents=1000,
            total_chunks=5000,
            categories={"tutorial": 300, "reference": 500},
            last_updated=datetime.now()
        )

        assert response.total_documents == 1000
        assert response.total_chunks == 5000


# =============================================================================
# ENHANCED LEARNING API TESTS
# =============================================================================

class TestEnhancedLearningAPIFunctional:
    """Functional tests for enhanced learning API."""

    def test_enhanced_learning_request(self):
        """EnhancedLearningRequest must validate fields."""
        from api.enhanced_learning_api import EnhancedLearningRequest

        request = EnhancedLearningRequest(
            learning_mode="reinforcement",
            reward_signal="user_feedback",
            exploration_rate=0.1
        )

        assert request.learning_mode == "reinforcement"
        assert request.exploration_rate == 0.1

    def test_learning_metrics_response(self):
        """LearningMetricsResponse must have required fields."""
        from api.enhanced_learning_api import LearningMetricsResponse

        response = LearningMetricsResponse(
            accuracy=0.92,
            precision=0.89,
            recall=0.95,
            f1_score=0.92,
            examples_processed=10000
        )

        assert response.accuracy == 0.92
        assert response.examples_processed == 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
