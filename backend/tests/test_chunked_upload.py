"""
import pytest; pytest.importorskip("api.chunked_upload_api", reason="api.chunked_upload_api removed — consolidated into Brain API")
Tests for the chunked upload API.
Validates the full chunked upload lifecycle: initiate → chunk → complete.
"""

import os
import sys
import hashlib
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SKIP_EMBEDDING_LOAD", "true")
os.environ.setdefault("SKIP_QDRANT_CHECK", "true")
os.environ.setdefault("SKIP_OLLAMA_CHECK", "true")
os.environ.setdefault("DISABLE_GENESIS_TRACKING", "true")


class TestChunkedUploadModule:
    """Test the chunked upload module imports and constants."""

    def test_import_module(self):
        from api.chunked_upload_api import router
        assert router is not None
        assert router.prefix == "/api/upload"

    def test_constants(self):
        from api.chunked_upload_api import (
            MAX_FILE_SIZE, DEFAULT_CHUNK_SIZE,
            MIN_CHUNK_SIZE, MAX_CHUNK_SIZE, ORPHAN_TTL_HOURS
        )
        assert MAX_FILE_SIZE == 5 * 1024 * 1024 * 1024  # 5 GB
        assert DEFAULT_CHUNK_SIZE == 5 * 1024 * 1024     # 5 MB
        assert MIN_CHUNK_SIZE == 1 * 1024 * 1024         # 1 MB
        assert MAX_CHUNK_SIZE == 50 * 1024 * 1024        # 50 MB
        assert ORPHAN_TTL_HOURS == 24

    def test_format_size(self):
        from api.chunked_upload_api import _fmt_size
        assert _fmt_size(0) == "0 B"
        assert _fmt_size(512) == "512 B"
        assert _fmt_size(1024) == "1.0 KB"
        assert _fmt_size(1024 * 1024) == "1.0 MB"
        assert _fmt_size(1024 * 1024 * 1024) == "1.00 GB"
        assert _fmt_size(5 * 1024 * 1024 * 1024) == "5.00 GB"


class TestSessionManagement:
    """Test upload session creation, persistence, and cleanup."""

    def test_create_and_get_session(self):
        from api.chunked_upload_api import (
            _create_session, _get_session, _remove_session, _get_temp_dir
        )
        import shutil

        uid = "up_test_session_001"
        try:
            _create_session(uid, {
                "upload_id": uid,
                "filename": "test.pdf",
                "file_size": 1000,
                "chunk_size": 500,
                "total_chunks": 2,
                "received_chunks": set(),
                "status": "in_progress",
            })

            session = _get_session(uid)
            assert session is not None
            assert session["filename"] == "test.pdf"
            assert session["total_chunks"] == 2
            assert session["status"] == "in_progress"
        finally:
            _remove_session(uid)
            chunk_dir = _get_temp_dir() / uid
            if chunk_dir.exists():
                shutil.rmtree(chunk_dir)

    def test_session_persistence_to_disk(self):
        from api.chunked_upload_api import (
            _create_session, _get_session, _remove_session,
            _upload_sessions, _get_temp_dir, _session_lock
        )
        import shutil

        uid = "up_test_persist_002"
        try:
            _create_session(uid, {
                "upload_id": uid,
                "filename": "persist.txt",
                "file_size": 500,
                "chunk_size": 500,
                "total_chunks": 1,
                "received_chunks": set(),
                "status": "in_progress",
            })

            # Remove from memory to force disk load
            with _session_lock:
                _upload_sessions.pop(uid, None)

            session = _get_session(uid)
            assert session is not None
            assert session["filename"] == "persist.txt"
        finally:
            _remove_session(uid)
            chunk_dir = _get_temp_dir() / uid
            if chunk_dir.exists():
                shutil.rmtree(chunk_dir)

    def test_update_session(self):
        from api.chunked_upload_api import (
            _create_session, _get_session, _update_session, _remove_session, _get_temp_dir
        )
        import shutil

        uid = "up_test_update_003"
        try:
            _create_session(uid, {
                "upload_id": uid,
                "filename": "update.bin",
                "file_size": 1000,
                "chunk_size": 500,
                "total_chunks": 2,
                "received_chunks": set(),
                "status": "in_progress",
            })

            _update_session(uid, {"status": "assembling", "received_chunks": {0, 1}})

            session = _get_session(uid)
            assert session["status"] == "assembling"
            assert 0 in session["received_chunks"]
            assert 1 in session["received_chunks"]
        finally:
            _remove_session(uid)
            chunk_dir = _get_temp_dir() / uid
            if chunk_dir.exists():
                shutil.rmtree(chunk_dir)


class TestChunkSizeCalculation:
    """Test that chunk sizes and counts are computed correctly."""

    def test_exact_division(self):
        file_size = 10 * 1024 * 1024  # 10 MB
        chunk_size = 5 * 1024 * 1024  # 5 MB
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        assert total_chunks == 2

    def test_remainder_chunk(self):
        file_size = 12 * 1024 * 1024  # 12 MB
        chunk_size = 5 * 1024 * 1024  # 5 MB
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        assert total_chunks == 3  # 5 + 5 + 2

    def test_single_chunk(self):
        file_size = 3 * 1024 * 1024   # 3 MB
        chunk_size = 5 * 1024 * 1024  # 5 MB
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        assert total_chunks == 1

    def test_5gb_file(self):
        file_size = 5 * 1024 * 1024 * 1024  # 5 GB
        chunk_size = 5 * 1024 * 1024        # 5 MB
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        assert total_chunks == 1024

    def test_chunk_size_clamping(self):
        from api.chunked_upload_api import MIN_CHUNK_SIZE, MAX_CHUNK_SIZE
        # Too small
        user_size = 100
        clamped = max(MIN_CHUNK_SIZE, min(user_size, MAX_CHUNK_SIZE))
        assert clamped == MIN_CHUNK_SIZE

        # Too large
        user_size = 100 * 1024 * 1024
        clamped = max(MIN_CHUNK_SIZE, min(user_size, MAX_CHUNK_SIZE))
        assert clamped == MAX_CHUNK_SIZE

        # Just right
        user_size = 10 * 1024 * 1024
        clamped = max(MIN_CHUNK_SIZE, min(user_size, MAX_CHUNK_SIZE))
        assert clamped == user_size


class TestEndToEndChunkedUpload:
    """Simulate a full chunked upload without going through HTTP."""

    def test_full_lifecycle(self, tmp_path):
        from api.chunked_upload_api import (
            _create_session, _get_session, _update_session,
            _remove_session, _get_temp_dir, _cleanup_chunks
        )

        # Create test data: 15 bytes, chunk size 5
        test_data = b"Hello, chunked upload works great!"
        file_size = len(test_data)
        chunk_size = 10
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        uid = "up_test_e2e_004"

        try:
            _create_session(uid, {
                "upload_id": uid,
                "filename": "test_e2e.txt",
                "file_size": file_size,
                "chunk_size": chunk_size,
                "total_chunks": total_chunks,
                "file_hash": hashlib.sha256(test_data).hexdigest(),
                "folder": "",
                "received_chunks": set(),
                "chunk_hashes": {},
                "status": "in_progress",
            })

            # Simulate chunk uploads
            chunk_dir = _get_temp_dir() / uid
            chunk_dir.mkdir(parents=True, exist_ok=True)

            for i in range(total_chunks):
                start = i * chunk_size
                end = min(start + chunk_size, file_size)
                chunk_data = test_data[start:end]
                chunk_hash = hashlib.sha256(chunk_data).hexdigest()

                chunk_path = chunk_dir / f"chunk_{i:06d}"
                chunk_path.write_bytes(chunk_data)

                session = _get_session(uid)
                received = session.get("received_chunks", set())
                if isinstance(received, list):
                    received = set(received)
                received.add(i)
                hashes = session.get("chunk_hashes", {})
                hashes[str(i)] = chunk_hash
                _update_session(uid, {"received_chunks": received, "chunk_hashes": hashes})

            # Verify all chunks received
            session = _get_session(uid)
            received = session.get("received_chunks", set())
            if isinstance(received, list):
                received = set(received)
            assert len(received) == total_chunks

            # Simulate assembly
            assembled = b""
            file_hash = hashlib.sha256()
            for i in range(total_chunks):
                chunk_path = chunk_dir / f"chunk_{i:06d}"
                data = chunk_path.read_bytes()
                file_hash.update(data)
                assembled += data

            assert assembled == test_data
            assert file_hash.hexdigest() == session["file_hash"]

        finally:
            _cleanup_chunks(uid)
            _remove_session(uid)
            import shutil
            chunk_dir = _get_temp_dir() / uid
            if chunk_dir.exists():
                shutil.rmtree(chunk_dir)


class TestOrphanCleanup:
    """Test that stale upload sessions are cleaned up."""

    def test_cleanup_completed_sessions(self):
        from api.chunked_upload_api import (
            _get_temp_dir, cleanup_orphaned_uploads
        )
        import shutil

        uid = "up_test_cleanup_005"
        chunk_dir = _get_temp_dir() / uid
        chunk_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "upload_id": uid,
            "status": "completed",
            "created_at": "2020-01-01T00:00:00",
        }
        (chunk_dir / "meta.json").write_text(json.dumps(meta))

        cleaned = cleanup_orphaned_uploads()
        assert cleaned >= 1
        assert not chunk_dir.exists()


class TestSecurityMiddleware:
    """Verify security middleware allows chunk requests through."""

    def test_chunk_upload_path_gets_higher_limit(self):
        from security.middleware import RequestValidationMiddleware
        # The middleware checks path and applies different limits
        # Verify the config change
        from security.config import get_security_config
        config = get_security_config()
        assert config.MAX_FILE_UPLOAD_SIZE_MB == 5120  # 5 GB


class TestIntegrationWithDocsLibrary:
    """Verify chunked upload integrates with docs library registration."""

    def test_register_document_callable(self):
        from api.docs_library_api import register_document
        assert callable(register_document)

    def test_guess_mime_for_large_files(self):
        from api.docs_library_api import _guess_mime
        assert _guess_mime("dataset.csv") == "text/csv"
        assert _guess_mime("archive.pdf") == "application/pdf"
        assert _guess_mime("model.bin") == "application/octet-stream"
        assert _guess_mime("readme.md") == "text/markdown"
