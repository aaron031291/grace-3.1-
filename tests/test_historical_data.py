"""
Tests for PerformanceTracker historical data functionality.

Tests:
1. record_processing()
2. get_processing_history() with filters
3. get_processing_stats()
4. Max size limit (1000 entries)
5. JSON file storage
"""

import pytest
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPerformanceTracker:
    """Tests for the PerformanceTracker class."""

    @pytest.fixture
    def temp_history_dir(self, tmp_path):
        """Create a temporary directory for history files."""
        history_dir = tmp_path / "processing_history"
        history_dir.mkdir(parents=True, exist_ok=True)
        return history_dir

    @pytest.fixture
    def tracker(self, temp_history_dir):
        """Create a PerformanceTracker with temporary storage."""
        from backend.file_manager.adaptive_file_processor import PerformanceTracker

        with patch.object(PerformanceTracker, 'HISTORY_DIR', temp_history_dir):
            tracker = PerformanceTracker(session=None)
            tracker.HISTORY_DIR = temp_history_dir
            return tracker


class TestRecordProcessing:
    """Tests for record_processing() method."""

    @pytest.fixture
    def temp_history_dir(self, tmp_path):
        history_dir = tmp_path / "processing_history"
        history_dir.mkdir(parents=True, exist_ok=True)
        return history_dir

    @pytest.fixture
    def tracker(self, temp_history_dir):
        from backend.file_manager.adaptive_file_processor import PerformanceTracker
        tracker = PerformanceTracker(session=None)
        tracker.HISTORY_DIR = temp_history_dir
        return tracker

    def test_record_processing_basic(self, tracker, temp_history_dir):
        """Test basic processing recording."""
        file_path = "/test/file.py"
        result = {
            "processing_type": "analysis",
            "duration_ms": 150.5,
            "success": True,
            "result_summary": "Analyzed 100 lines",
            "error": None
        }

        tracker.record_processing(file_path, result)

        history = tracker.get_processing_history(file_path)
        assert len(history) == 1
        assert history[0]["processing_type"] == "analysis"
        assert history[0]["success"] is True

    def test_record_processing_with_error(self, tracker):
        """Test recording processing with error."""
        file_path = "/test/error_file.py"
        result = {
            "processing_type": "embedding",
            "duration_ms": 50.0,
            "success": False,
            "result_summary": "",
            "error": "Connection timeout"
        }

        tracker.record_processing(file_path, result)

        history = tracker.get_processing_history(file_path)
        assert len(history) == 1
        assert history[0]["success"] is False
        assert history[0]["error"] == "Connection timeout"

    def test_record_processing_multiple_entries(self, tracker):
        """Test recording multiple processing entries."""
        file_path = "/test/multi.py"

        for i in range(5):
            result = {
                "processing_type": f"type_{i}",
                "duration_ms": float(i * 10),
                "success": True,
                "result_summary": f"Result {i}"
            }
            tracker.record_processing(file_path, result)

        history = tracker.get_processing_history(file_path)
        assert len(history) == 5

    def test_record_processing_timestamp_added(self, tracker):
        """Test that timestamp is automatically added."""
        file_path = "/test/timestamp.py"
        result = {
            "processing_type": "test",
            "duration_ms": 100,
            "success": True,
            "result_summary": "Test"
        }

        before = datetime.now()
        tracker.record_processing(file_path, result)
        after = datetime.now()

        history = tracker.get_processing_history(file_path)
        assert len(history) == 1
        timestamp = datetime.fromisoformat(history[0]["timestamp"])
        assert before <= timestamp <= after


class TestGetProcessingHistory:
    """Tests for get_processing_history() method."""

    @pytest.fixture
    def temp_history_dir(self, tmp_path):
        history_dir = tmp_path / "processing_history"
        history_dir.mkdir(parents=True, exist_ok=True)
        return history_dir

    @pytest.fixture
    def tracker(self, temp_history_dir):
        from backend.file_manager.adaptive_file_processor import PerformanceTracker
        tracker = PerformanceTracker(session=None)
        tracker.HISTORY_DIR = temp_history_dir
        return tracker

    @pytest.fixture
    def populated_tracker(self, tracker):
        """Create tracker with pre-populated data."""
        file_path = "/test/history.py"

        for i in range(10):
            result = {
                "processing_type": "analysis" if i % 2 == 0 else "embedding",
                "duration_ms": float(i * 100),
                "success": i % 3 != 0,
                "result_summary": f"Result {i}"
            }
            tracker.record_processing(file_path, result)

        return tracker, file_path

    def test_get_history_empty(self, tracker):
        """Test getting history for file with no records."""
        history = tracker.get_processing_history("/nonexistent/file.py")
        assert history == []

    def test_get_history_all(self, populated_tracker):
        """Test getting all history entries."""
        tracker, file_path = populated_tracker
        history = tracker.get_processing_history(file_path)
        assert len(history) == 10

    def test_get_history_with_limit(self, populated_tracker):
        """Test getting history with limit."""
        tracker, file_path = populated_tracker
        history = tracker.get_processing_history(file_path, limit=5)
        assert len(history) == 5

    def test_get_history_filter_by_type(self, populated_tracker):
        """Test filtering history by processing type."""
        tracker, file_path = populated_tracker
        history = tracker.get_processing_history(
            file_path,
            processing_type="analysis"
        )
        assert len(history) == 5
        assert all(h["processing_type"] == "analysis" for h in history)

    def test_get_history_filter_by_start_date(self, tracker):
        """Test filtering history by start date."""
        file_path = "/test/date_filter.py"

        old_record = {
            "file_path": file_path,
            "timestamp": (datetime.now() - timedelta(days=10)).isoformat(),
            "processing_type": "old",
            "duration_ms": 100,
            "success": True,
            "result_summary": "Old record",
            "error": None
        }

        new_record = {
            "processing_type": "new",
            "duration_ms": 100,
            "success": True,
            "result_summary": "New record"
        }

        history_file = tracker._get_history_file(file_path)
        with open(history_file, 'w') as f:
            json.dump([old_record], f)

        tracker.record_processing(file_path, new_record)

        start_date = datetime.now() - timedelta(days=5)
        history = tracker.get_processing_history(
            file_path,
            start_date=start_date
        )

        assert len(history) == 1
        assert history[0]["processing_type"] == "new"

    def test_get_history_filter_by_end_date(self, tracker):
        """Test filtering history by end date."""
        file_path = "/test/end_date.py"

        tracker.record_processing(file_path, {
            "processing_type": "current",
            "duration_ms": 100,
            "success": True,
            "result_summary": "Current"
        })

        end_date = datetime.now() - timedelta(days=1)
        history = tracker.get_processing_history(
            file_path,
            end_date=end_date
        )

        assert len(history) == 0

    def test_get_history_combined_filters(self, populated_tracker):
        """Test combining multiple filters."""
        tracker, file_path = populated_tracker
        history = tracker.get_processing_history(
            file_path,
            limit=3,
            processing_type="analysis"
        )

        assert len(history) <= 3
        assert all(h["processing_type"] == "analysis" for h in history)


class TestGetProcessingStats:
    """Tests for get_processing_stats() method."""

    @pytest.fixture
    def temp_history_dir(self, tmp_path):
        history_dir = tmp_path / "processing_history"
        history_dir.mkdir(parents=True, exist_ok=True)
        return history_dir

    @pytest.fixture
    def tracker(self, temp_history_dir):
        from backend.file_manager.adaptive_file_processor import PerformanceTracker
        tracker = PerformanceTracker(session=None)
        tracker.HISTORY_DIR = temp_history_dir
        return tracker

    def test_get_stats_empty(self, tracker):
        """Test getting stats for file with no records."""
        stats = tracker.get_processing_stats("/nonexistent/file.py")

        assert stats["total_processed"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_time_ms"] == 0.0
        assert stats["processing_types"] == []
        assert stats["first_processed"] is None
        assert stats["last_processed"] is None

    def test_get_stats_single_record(self, tracker):
        """Test stats with single record."""
        file_path = "/test/single.py"
        tracker.record_processing(file_path, {
            "processing_type": "analysis",
            "duration_ms": 100,
            "success": True,
            "result_summary": "Done"
        })

        stats = tracker.get_processing_stats(file_path)

        assert stats["total_processed"] == 1
        assert stats["success_rate"] == 1.0
        assert stats["avg_time_ms"] == 100
        assert "analysis" in stats["processing_types"]
        assert stats["first_processed"] is not None
        assert stats["last_processed"] is not None

    def test_get_stats_success_rate(self, tracker):
        """Test success rate calculation."""
        file_path = "/test/success_rate.py"

        for success in [True, True, True, False]:
            tracker.record_processing(file_path, {
                "processing_type": "test",
                "duration_ms": 100,
                "success": success,
                "result_summary": ""
            })

        stats = tracker.get_processing_stats(file_path)

        assert stats["total_processed"] == 4
        assert stats["success_rate"] == 0.75

    def test_get_stats_avg_time(self, tracker):
        """Test average time calculation."""
        file_path = "/test/avg_time.py"

        for duration in [100, 200, 300]:
            tracker.record_processing(file_path, {
                "processing_type": "test",
                "duration_ms": duration,
                "success": True,
                "result_summary": ""
            })

        stats = tracker.get_processing_stats(file_path)

        assert stats["avg_time_ms"] == 200

    def test_get_stats_processing_types(self, tracker):
        """Test collecting processing types."""
        file_path = "/test/types.py"

        for ptype in ["analysis", "embedding", "chunking", "analysis"]:
            tracker.record_processing(file_path, {
                "processing_type": ptype,
                "duration_ms": 100,
                "success": True,
                "result_summary": ""
            })

        stats = tracker.get_processing_stats(file_path)

        assert len(stats["processing_types"]) == 3
        assert set(stats["processing_types"]) == {"analysis", "embedding", "chunking"}

    def test_get_stats_timestamps(self, tracker):
        """Test first and last processed timestamps."""
        file_path = "/test/timestamps.py"

        for _ in range(3):
            tracker.record_processing(file_path, {
                "processing_type": "test",
                "duration_ms": 100,
                "success": True,
                "result_summary": ""
            })

        stats = tracker.get_processing_stats(file_path)

        first = datetime.fromisoformat(stats["first_processed"])
        last = datetime.fromisoformat(stats["last_processed"])
        assert first <= last


class TestMaxSizeLimit:
    """Tests for max history size limit (1000 entries)."""

    @pytest.fixture
    def temp_history_dir(self, tmp_path):
        history_dir = tmp_path / "processing_history"
        history_dir.mkdir(parents=True, exist_ok=True)
        return history_dir

    @pytest.fixture
    def tracker(self, temp_history_dir):
        from backend.file_manager.adaptive_file_processor import PerformanceTracker
        tracker = PerformanceTracker(session=None)
        tracker.HISTORY_DIR = temp_history_dir
        return tracker

    def test_max_history_per_file_constant(self, tracker):
        """Test that MAX_HISTORY_PER_FILE is 1000."""
        assert tracker.MAX_HISTORY_PER_FILE == 1000

    def test_history_truncated_at_limit(self, tracker):
        """Test that history is truncated when limit exceeded."""
        file_path = "/test/limit.py"
        max_limit = tracker.MAX_HISTORY_PER_FILE

        for i in range(max_limit + 50):
            tracker.record_processing(file_path, {
                "processing_type": f"type_{i}",
                "duration_ms": float(i),
                "success": True,
                "result_summary": f"Result {i}"
            })

        history = tracker.get_processing_history(file_path, limit=max_limit + 100)

        assert len(history) <= max_limit

    def test_oldest_entries_removed(self, tracker):
        """Test that oldest entries are removed when limit exceeded."""
        file_path = "/test/oldest.py"
        max_limit = tracker.MAX_HISTORY_PER_FILE

        for i in range(max_limit + 10):
            tracker.record_processing(file_path, {
                "processing_type": f"type_{i}",
                "duration_ms": float(i),
                "success": True,
                "result_summary": f"Result {i}"
            })

        history = tracker.get_processing_history(file_path, limit=max_limit + 100)

        assert "type_0" not in [h["processing_type"] for h in history]
        assert "type_9" not in [h["processing_type"] for h in history]
        assert f"type_{max_limit + 9}" in [h["processing_type"] for h in history]


class TestJSONFileStorage:
    """Tests for JSON file storage functionality."""

    @pytest.fixture
    def temp_history_dir(self, tmp_path):
        history_dir = tmp_path / "processing_history"
        history_dir.mkdir(parents=True, exist_ok=True)
        return history_dir

    @pytest.fixture
    def tracker(self, temp_history_dir):
        from backend.file_manager.adaptive_file_processor import PerformanceTracker
        tracker = PerformanceTracker(session=None)
        tracker.HISTORY_DIR = temp_history_dir
        return tracker

    def test_history_file_created(self, tracker, temp_history_dir):
        """Test that history file is created on first record."""
        file_path = "/test/new_file.py"
        tracker.record_processing(file_path, {
            "processing_type": "test",
            "duration_ms": 100,
            "success": True,
            "result_summary": "Test"
        })

        history_files = list(temp_history_dir.glob("*.json"))
        assert len(history_files) == 1

    def test_history_file_valid_json(self, tracker, temp_history_dir):
        """Test that history file contains valid JSON."""
        file_path = "/test/valid_json.py"
        tracker.record_processing(file_path, {
            "processing_type": "test",
            "duration_ms": 100,
            "success": True,
            "result_summary": "Test"
        })

        history_file = tracker._get_history_file(file_path)
        with open(history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) == 1

    def test_history_file_persisted(self, tracker, temp_history_dir):
        """Test that history survives reload."""
        file_path = "/test/persist.py"
        tracker.record_processing(file_path, {
            "processing_type": "test",
            "duration_ms": 100,
            "success": True,
            "result_summary": "Test"
        })

        from backend.file_manager.adaptive_file_processor import PerformanceTracker
        new_tracker = PerformanceTracker(session=None)
        new_tracker.HISTORY_DIR = temp_history_dir

        history = new_tracker.get_processing_history(file_path)
        assert len(history) == 1

    def test_long_file_path_handling(self, tracker, temp_history_dir):
        """Test handling of very long file paths."""
        long_path = "/" + "a" * 300 + "/file.py"
        tracker.record_processing(long_path, {
            "processing_type": "test",
            "duration_ms": 100,
            "success": True,
            "result_summary": "Test"
        })

        history = tracker.get_processing_history(long_path)
        assert len(history) == 1

    def test_special_characters_in_path(self, tracker, temp_history_dir):
        """Test handling of special characters in file paths."""
        special_path = "/test/file with spaces & symbols!.py"
        tracker.record_processing(special_path, {
            "processing_type": "test",
            "duration_ms": 100,
            "success": True,
            "result_summary": "Test"
        })

        history = tracker.get_processing_history(special_path)
        assert len(history) == 1

    def test_corrupted_json_handling(self, tracker, temp_history_dir):
        """Test graceful handling of corrupted JSON files."""
        file_path = "/test/corrupted.py"
        history_file = tracker._get_history_file(file_path)

        with open(history_file, 'w') as f:
            f.write("{ invalid json }")

        history = tracker.get_processing_history(file_path)
        assert history == []

        tracker.record_processing(file_path, {
            "processing_type": "test",
            "duration_ms": 100,
            "success": True,
            "result_summary": "Test"
        })

        history = tracker.get_processing_history(file_path)
        assert len(history) == 1

    def test_multiple_files_separate_storage(self, tracker, temp_history_dir):
        """Test that different files have separate storage."""
        file1 = "/test/file1.py"
        file2 = "/test/file2.py"

        tracker.record_processing(file1, {
            "processing_type": "type1",
            "duration_ms": 100,
            "success": True,
            "result_summary": "File 1"
        })

        tracker.record_processing(file2, {
            "processing_type": "type2",
            "duration_ms": 200,
            "success": False,
            "result_summary": "File 2"
        })

        history1 = tracker.get_processing_history(file1)
        history2 = tracker.get_processing_history(file2)

        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0]["processing_type"] == "type1"
        assert history2[0]["processing_type"] == "type2"


class TestThreadSafety:
    """Tests for thread safety of the tracker."""

    @pytest.fixture
    def temp_history_dir(self, tmp_path):
        history_dir = tmp_path / "processing_history"
        history_dir.mkdir(parents=True, exist_ok=True)
        return history_dir

    @pytest.fixture
    def tracker(self, temp_history_dir):
        from backend.file_manager.adaptive_file_processor import PerformanceTracker
        tracker = PerformanceTracker(session=None)
        tracker.HISTORY_DIR = temp_history_dir
        return tracker

    def test_concurrent_writes(self, tracker):
        """Test concurrent writes to the same file."""
        import threading

        file_path = "/test/concurrent.py"
        num_threads = 10
        records_per_thread = 10

        def write_records(thread_id):
            for i in range(records_per_thread):
                tracker.record_processing(file_path, {
                    "processing_type": f"thread_{thread_id}_{i}",
                    "duration_ms": float(i),
                    "success": True,
                    "result_summary": f"Thread {thread_id} Record {i}"
                })

        threads = [
            threading.Thread(target=write_records, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        history = tracker.get_processing_history(file_path, limit=1000)

        assert len(history) == num_threads * records_per_thread
