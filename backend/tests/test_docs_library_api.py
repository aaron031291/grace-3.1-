"""Tests for Docs Library API helpers."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDocsLibraryHelpers:

    def test_safe_json_parse_valid(self):
        from api.docs_library_api import _safe_json_parse
        assert _safe_json_parse('["a","b"]') == ["a", "b"]
        assert _safe_json_parse('{"k":"v"}') == {"k": "v"}

    def test_safe_json_parse_invalid(self):
        from api.docs_library_api import _safe_json_parse
        assert _safe_json_parse("not json", []) == []
        assert _safe_json_parse(None, {}) == {}
        assert _safe_json_parse("", "default") == "default"

    def test_guess_mime(self):
        from api.docs_library_api import _guess_mime
        assert _guess_mime("report.pdf") == "application/pdf"
        assert _guess_mime("notes.txt") == "text/plain"
        assert _guess_mime("data.csv") == "text/csv"
        assert _guess_mime("doc.docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert _guess_mime("script.py") == "text/x-python"
        assert _guess_mime("unknown.xyz") == "application/octet-stream"

    def test_file_extension(self):
        from api.docs_library_api import _file_extension
        assert _file_extension("test.pdf") == ".pdf"
        assert _file_extension("file.TXT") == ".txt"
        assert _file_extension("noext") == ""
        assert _file_extension("") == ""

    def test_doc_to_dict_minimal(self):
        from api.docs_library_api import _doc_to_dict

        class FakeDoc:
            id = 1
            filename = "test.txt"
            original_filename = "test.txt"
            file_path = ""
            file_size = 100
            mime_type = "text/plain"
            source = "upload"
            status = "completed"
            upload_method = "ui-upload"
            total_chunks = 0
            tags = None
            description = None
            document_metadata = None
            confidence_score = 0.8
            created_at = None
            updated_at = None

        result = _doc_to_dict(FakeDoc())
        assert result["id"] == 1
        assert result["filename"] == "test.txt"
        assert result["file_size"] == 100
        assert result["status"] == "completed"
        assert result["tags"] == []
        assert result["folder"] == ""

    def test_doc_to_dict_with_folder(self):
        from api.docs_library_api import _doc_to_dict
        import json

        class FakeDoc:
            id = 2
            filename = "report.pdf"
            original_filename = "report.pdf"
            file_path = ""
            file_size = 5000
            mime_type = "application/pdf"
            source = "knowledge_base"
            status = "completed"
            upload_method = "librarian_upload"
            total_chunks = 5
            tags = json.dumps(["research", "ai"])
            description = "An AI report"
            document_metadata = json.dumps({"directory": "reports/2024"})
            confidence_score = 0.9
            created_at = None
            updated_at = None

        result = _doc_to_dict(FakeDoc())
        assert result["tags"] == ["research", "ai"]
        assert result["description"] == "An AI report"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
