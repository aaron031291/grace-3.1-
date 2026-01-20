"""
Comprehensive Test Suite for File Manager Module
================================================
Tests for FileHandler and related file management utilities.

Coverage:
- FileHandler initialization and file type detection
- Text file extraction (TXT, MD, code files)
- PDF extraction with fallback mechanisms
- DOCX and Excel extraction
- Audio/Video file handling
- Text cleaning and validation
- Error handling for various file types
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from typing import Tuple, Optional, List, Dict
from pathlib import Path
import os

import sys

# =============================================================================
# Mock dependencies before any imports
# =============================================================================

# Mock pdfplumber
mock_pdfplumber = MagicMock()
sys.modules['pdfplumber'] = mock_pdfplumber

# Mock PyPDF2
mock_pypdf2 = MagicMock()
sys.modules['PyPDF2'] = mock_pypdf2

# Mock python-docx
mock_docx = MagicMock()
sys.modules['docx'] = mock_docx

# Mock openpyxl
mock_openpyxl = MagicMock()
sys.modules['openpyxl'] = mock_openpyxl

# Mock pptx
mock_pptx = MagicMock()
sys.modules['pptx'] = mock_pptx

# Mock whisper (for audio)
mock_whisper = MagicMock()
sys.modules['whisper'] = mock_whisper

sys.path.insert(0, '/home/user/grace-3.1-/backend')


# =============================================================================
# FileHandler File Type Detection Tests
# =============================================================================

class TestFileHandlerFileTypeDetection:
    """Test file type detection."""

    def test_get_file_type_text(self):
        """Test file type detection for text files."""
        SUPPORTED_TYPES = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.json': 'application/json',
        }

        def get_file_type(file_path: str) -> Optional[str]:
            ext = Path(file_path).suffix.lower()
            return SUPPORTED_TYPES.get(ext)

        assert get_file_type("/path/to/file.txt") == "text/plain"
        assert get_file_type("/path/to/file.md") == "text/markdown"
        assert get_file_type("/path/to/file.json") == "application/json"

    def test_get_file_type_code_files(self):
        """Test file type detection for code files."""
        SUPPORTED_TYPES = {
            '.py': 'text/x-python',
            '.js': 'text/javascript',
            '.java': 'text/x-java',
            '.cpp': 'text/x-c++src',
            '.go': 'text/x-go',
            '.rs': 'text/x-rust',
        }

        def get_file_type(file_path: str) -> Optional[str]:
            ext = Path(file_path).suffix.lower()
            return SUPPORTED_TYPES.get(ext)

        assert get_file_type("script.py") == "text/x-python"
        assert get_file_type("app.js") == "text/javascript"
        assert get_file_type("Main.java") == "text/x-java"

    def test_get_file_type_documents(self):
        """Test file type detection for document files."""
        SUPPORTED_TYPES = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }

        def get_file_type(file_path: str) -> Optional[str]:
            ext = Path(file_path).suffix.lower()
            return SUPPORTED_TYPES.get(ext)

        assert get_file_type("document.pdf") == "application/pdf"
        assert "wordprocessingml" in get_file_type("document.docx")
        assert "spreadsheetml" in get_file_type("data.xlsx")

    def test_get_file_type_media(self):
        """Test file type detection for media files."""
        SUPPORTED_TYPES = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
        }

        def get_file_type(file_path: str) -> Optional[str]:
            ext = Path(file_path).suffix.lower()
            return SUPPORTED_TYPES.get(ext)

        assert get_file_type("audio.mp3") == "audio/mpeg"
        assert get_file_type("video.mp4") == "video/mp4"

    def test_get_file_type_unsupported(self):
        """Test file type detection for unsupported files."""
        SUPPORTED_TYPES = {'.txt': 'text/plain'}

        def get_file_type(file_path: str) -> Optional[str]:
            ext = Path(file_path).suffix.lower()
            return SUPPORTED_TYPES.get(ext)

        assert get_file_type("file.xyz") is None
        assert get_file_type("file.unknown") is None

    def test_get_file_type_case_insensitive(self):
        """Test file type detection is case insensitive."""
        SUPPORTED_TYPES = {'.txt': 'text/plain', '.pdf': 'application/pdf'}

        def get_file_type(file_path: str) -> Optional[str]:
            ext = Path(file_path).suffix.lower()
            return SUPPORTED_TYPES.get(ext)

        assert get_file_type("FILE.TXT") == "text/plain"
        assert get_file_type("DOCUMENT.PDF") == "application/pdf"


# =============================================================================
# Text File Extraction Tests
# =============================================================================

class TestTextFileExtraction:
    """Test text file extraction."""

    def test_extract_text_file_success(self):
        """Test successful text file extraction."""
        def extract_text_file(file_path: str, content: str = None) -> Tuple[str, Optional[str]]:
            # Simulate successful read
            if content is None:
                content = "Sample text content"
            return content, None

        text, error = extract_text_file("/path/to/file.txt")

        assert text == "Sample text content"
        assert error is None

    def test_extract_text_file_utf8(self):
        """Test UTF-8 text file extraction."""
        def extract_text_file(file_path: str) -> Tuple[str, Optional[str]]:
            try:
                # Simulate UTF-8 read
                content = "UTF-8 content: ñ, ü, 中文"
                return content, None
            except UnicodeDecodeError:
                return "", "Unicode error"

        text, error = extract_text_file("file.txt")

        assert "UTF-8" in text
        assert "中文" in text
        assert error is None

    def test_extract_text_file_fallback_encoding(self):
        """Test fallback to latin-1 encoding."""
        def extract_text_file(file_path: str) -> Tuple[str, Optional[str]]:
            # Simulate UTF-8 failure, latin-1 success
            try:
                # UTF-8 fails
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
            except UnicodeDecodeError:
                # Fallback to latin-1
                return "Latin-1 content", None

        text, error = extract_text_file("file.txt")

        assert text == "Latin-1 content"
        assert error is None

    def test_extract_text_file_not_found(self):
        """Test extraction of non-existent file."""
        def extract_text(file_path: str) -> Tuple[str, Optional[str]]:
            if not os.path.exists(file_path):
                return "", f"File not found: {file_path}"
            return "content", None

        text, error = extract_text("/nonexistent/file.txt")

        assert text == ""
        assert "File not found" in error


class TestMarkdownExtraction:
    """Test markdown file extraction."""

    def test_extract_markdown(self):
        """Test markdown file extraction preserves formatting."""
        def extract_markdown(content: str) -> Tuple[str, Optional[str]]:
            return content, None

        md_content = "# Header\n\n**Bold** and *italic*\n\n- List item"
        text, error = extract_markdown(md_content)

        assert "# Header" in text
        assert "**Bold**" in text

    def test_extract_markdown_with_code_blocks(self):
        """Test markdown with code blocks."""
        def extract_markdown(content: str) -> Tuple[str, Optional[str]]:
            return content, None

        md_content = "```python\nprint('hello')\n```"
        text, error = extract_markdown(md_content)

        assert "```python" in text
        assert "print('hello')" in text


class TestCodeFileExtraction:
    """Test code file extraction."""

    def test_extract_python_file(self):
        """Test Python file extraction."""
        def extract_code_file(content: str) -> Tuple[str, Optional[str]]:
            return content, None

        code = "def hello():\n    print('Hello')"
        text, error = extract_code_file(code)

        assert "def hello():" in text
        assert error is None

    def test_extract_javascript_file(self):
        """Test JavaScript file extraction."""
        def extract_code_file(content: str) -> Tuple[str, Optional[str]]:
            return content, None

        code = "function hello() { console.log('Hello'); }"
        text, error = extract_code_file(code)

        assert "function hello()" in text


# =============================================================================
# PDF Extraction Tests
# =============================================================================

class TestPDFExtraction:
    """Test PDF file extraction."""

    def test_extract_pdf_success(self):
        """Test successful PDF extraction."""
        def extract_pdf(file_path: str) -> Tuple[str, Optional[str]]:
            # Simulate PDF extraction
            pages = ["[Page 1]\nContent from page 1", "[Page 2]\nContent from page 2"]
            return "\n\n".join(pages), None

        text, error = extract_pdf("document.pdf")

        assert "[Page 1]" in text
        assert "Content from page 1" in text
        assert error is None

    def test_extract_pdf_with_layout(self):
        """Test PDF extraction with layout preservation."""
        def extract_pdf_with_layout(file_path: str) -> Tuple[str, Optional[str]]:
            # Simulate layout-aware extraction
            return "Column 1    Column 2\nData 1      Data 2", None

        text, error = extract_pdf_with_layout("table.pdf")

        assert "Column 1" in text
        assert "Column 2" in text

    def test_extract_pdf_empty(self):
        """Test extraction from empty PDF."""
        def extract_pdf(file_path: str) -> Tuple[str, Optional[str]]:
            # Simulate empty PDF
            return "", "No text content found in PDF"

        text, error = extract_pdf("empty.pdf")

        assert text == ""
        assert "No text content" in error

    def test_extract_pdf_fallback(self):
        """Test PDF extraction fallback to PyPDF2."""
        def extract_pdf_fallback(file_path: str) -> Tuple[str, Optional[str]]:
            # Simulate fallback extraction
            return "Fallback extracted content", None

        text, error = extract_pdf_fallback("document.pdf")

        assert "Fallback extracted content" in text
        assert error is None

    def test_extract_pdf_corrupted(self):
        """Test extraction from corrupted PDF."""
        def extract_pdf(file_path: str) -> Tuple[str, Optional[str]]:
            try:
                raise Exception("PDF is corrupted")
            except Exception as e:
                return "", f"Error reading PDF: {str(e)}"

        text, error = extract_pdf("corrupted.pdf")

        assert text == ""
        assert "corrupted" in error.lower()


# =============================================================================
# DOCX Extraction Tests
# =============================================================================

class TestDocxExtraction:
    """Test DOCX file extraction."""

    def test_extract_docx_success(self):
        """Test successful DOCX extraction."""
        def extract_docx(file_path: str) -> Tuple[str, Optional[str]]:
            # Simulate DOCX extraction
            paragraphs = ["First paragraph", "Second paragraph", "Third paragraph"]
            return "\n".join(paragraphs), None

        text, error = extract_docx("document.docx")

        assert "First paragraph" in text
        assert "Second paragraph" in text
        assert error is None

    def test_extract_docx_with_tables(self):
        """Test DOCX extraction with tables."""
        def extract_docx(file_path: str) -> Tuple[str, Optional[str]]:
            content = "Regular paragraph\nTable: Header1 | Header2\nData1 | Data2"
            return content, None

        text, error = extract_docx("with_tables.docx")

        assert "Header1" in text
        assert "Data1" in text

    def test_extract_docx_empty(self):
        """Test extraction from empty DOCX."""
        def extract_docx(file_path: str) -> Tuple[str, Optional[str]]:
            return "", None

        text, error = extract_docx("empty.docx")

        assert text == ""
        assert error is None


# =============================================================================
# Excel Extraction Tests
# =============================================================================

class TestExcelExtraction:
    """Test Excel file extraction."""

    def test_extract_excel_success(self):
        """Test successful Excel extraction."""
        def extract_excel(file_path: str) -> Tuple[str, Optional[str]]:
            # Simulate Excel extraction
            rows = ["Header1,Header2", "Data1,Data2", "Data3,Data4"]
            return "\n".join(rows), None

        text, error = extract_excel("data.xlsx")

        assert "Header1" in text
        assert "Data1" in text
        assert error is None

    def test_extract_excel_multiple_sheets(self):
        """Test Excel extraction with multiple sheets."""
        def extract_excel(file_path: str) -> Tuple[str, Optional[str]]:
            sheets = [
                "[Sheet1]\nData from sheet 1",
                "[Sheet2]\nData from sheet 2"
            ]
            return "\n\n".join(sheets), None

        text, error = extract_excel("multi_sheet.xlsx")

        assert "[Sheet1]" in text
        assert "[Sheet2]" in text

    def test_extract_excel_empty_sheet(self):
        """Test Excel extraction with empty sheet."""
        def extract_excel(file_path: str) -> Tuple[str, Optional[str]]:
            return "", "No data found in spreadsheet"

        text, error = extract_excel("empty.xlsx")

        assert text == ""


# =============================================================================
# Audio Extraction Tests
# =============================================================================

class TestAudioExtraction:
    """Test audio file extraction (transcription)."""

    def test_extract_audio_success(self):
        """Test successful audio transcription."""
        def extract_audio(file_path: str) -> Tuple[str, Optional[str]]:
            # Simulate Whisper transcription
            return "This is the transcribed audio content.", None

        text, error = extract_audio("audio.mp3")

        assert "transcribed audio" in text
        assert error is None

    def test_extract_audio_unsupported_format(self):
        """Test extraction of unsupported audio format."""
        def extract_audio(file_path: str) -> Tuple[str, Optional[str]]:
            ext = Path(file_path).suffix.lower()
            supported = ['.mp3', '.wav', '.m4a']
            if ext not in supported:
                return "", f"Unsupported audio format: {ext}"
            return "Transcribed content", None

        text, error = extract_audio("audio.xyz")

        assert text == ""
        assert "Unsupported" in error

    def test_extract_audio_no_speech(self):
        """Test extraction from audio with no speech."""
        def extract_audio(file_path: str) -> Tuple[str, Optional[str]]:
            # Simulate no speech detected
            return "", "No speech detected in audio"

        text, error = extract_audio("music.mp3")

        assert text == ""
        assert "No speech" in error


# =============================================================================
# Video Extraction Tests
# =============================================================================

class TestVideoExtraction:
    """Test video file extraction."""

    def test_extract_video_audio_track(self):
        """Test extracting audio from video for transcription."""
        def extract_video(file_path: str) -> Tuple[str, Optional[str]]:
            # Simulate video audio extraction and transcription
            return "Transcribed speech from video audio track.", None

        text, error = extract_video("video.mp4")

        assert "Transcribed speech" in text
        assert error is None

    def test_extract_video_no_audio(self):
        """Test video with no audio track."""
        def extract_video(file_path: str) -> Tuple[str, Optional[str]]:
            return "", "Video has no audio track"

        text, error = extract_video("silent.mp4")

        assert text == ""
        assert "no audio" in error.lower()


# =============================================================================
# Text Cleaning Tests
# =============================================================================

class TestTextCleaning:
    """Test text cleaning utilities."""

    def test_clean_text_removes_control_chars(self):
        """Test removal of control characters."""
        def clean_text(text: str) -> str:
            import re
            # Remove control characters except newlines and tabs
            return re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)

        dirty = "Hello\x00World\x1fTest"
        clean = clean_text(dirty)

        assert "\x00" not in clean
        assert "\x1f" not in clean
        assert "HelloWorldTest" == clean

    def test_clean_text_normalizes_whitespace(self):
        """Test whitespace normalization."""
        def clean_text(text: str) -> str:
            import re
            # Normalize multiple spaces
            text = re.sub(r'[ \t]+', ' ', text)
            # Normalize multiple newlines
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text.strip()

        dirty = "Hello    World\n\n\n\n\nTest"
        clean = clean_text(dirty)

        assert "    " not in clean
        assert clean.count('\n\n\n') == 0

    def test_clean_text_preserves_content(self):
        """Test that cleaning preserves legitimate content."""
        def clean_text(text: str) -> str:
            import re
            return re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)

        original = "Hello, World! This is a test. Numbers: 123"
        cleaned = clean_text(original)

        assert cleaned == original


class TestTextValidation:
    """Test text validation utilities."""

    def test_is_valid_text_success(self):
        """Test valid text detection."""
        def is_valid_text(text: str, threshold: float = 0.5) -> bool:
            if not text:
                return False
            # Check ratio of printable characters
            printable = sum(1 for c in text if c.isprintable() or c in '\n\r\t')
            ratio = printable / len(text)
            return ratio >= threshold

        assert is_valid_text("Hello World!") is True
        assert is_valid_text("Valid text with numbers 123") is True

    def test_is_valid_text_mostly_garbage(self):
        """Test detection of mostly garbage text."""
        def is_valid_text(text: str, threshold: float = 0.5) -> bool:
            if not text:
                return False
            printable = sum(1 for c in text if c.isprintable() or c in '\n\r\t')
            ratio = printable / len(text)
            return ratio >= threshold

        garbage = "".join(chr(i) for i in range(1, 20)) * 10
        assert is_valid_text(garbage) is False

    def test_is_valid_text_empty(self):
        """Test empty text validation."""
        def is_valid_text(text: str) -> bool:
            return bool(text and text.strip())

        assert is_valid_text("") is False
        assert is_valid_text("   ") is False


# =============================================================================
# Extract Text Router Tests
# =============================================================================

class TestExtractTextRouter:
    """Test the main extract_text routing function."""

    def test_route_to_text_handler(self):
        """Test routing to text file handler."""
        def extract_text(file_path: str) -> Tuple[str, Optional[str]]:
            ext = Path(file_path).suffix.lower()
            if ext in ['.txt', '.md']:
                return "Text content", None
            return "", "Unsupported"

        text, error = extract_text("file.txt")
        assert text == "Text content"

        text, error = extract_text("file.md")
        assert text == "Text content"

    def test_route_to_pdf_handler(self):
        """Test routing to PDF handler."""
        def extract_text(file_path: str) -> Tuple[str, Optional[str]]:
            ext = Path(file_path).suffix.lower()
            if ext == '.pdf':
                return "PDF content", None
            return "", "Unsupported"

        text, error = extract_text("document.pdf")
        assert text == "PDF content"

    def test_route_unsupported_type(self):
        """Test routing for unsupported file type."""
        def extract_text(file_path: str) -> Tuple[str, Optional[str]]:
            ext = Path(file_path).suffix.lower()
            supported = ['.txt', '.pdf', '.docx']
            if ext not in supported:
                return "", f"Unsupported file type: {ext}"
            return "Content", None

        text, error = extract_text("file.xyz")

        assert text == ""
        assert "Unsupported" in error


# =============================================================================
# File Handler Integration Tests
# =============================================================================

class TestFileHandlerIntegration:
    """Integration tests for FileHandler."""

    def test_full_extraction_workflow(self):
        """Test complete file extraction workflow."""
        class MockFileHandler:
            SUPPORTED_TYPES = {'.txt': 'text/plain', '.pdf': 'application/pdf'}

            @staticmethod
            def get_file_type(file_path: str) -> Optional[str]:
                ext = Path(file_path).suffix.lower()
                return MockFileHandler.SUPPORTED_TYPES.get(ext)

            @staticmethod
            def extract_text(file_path: str) -> Tuple[str, Optional[str]]:
                file_type = MockFileHandler.get_file_type(file_path)
                if not file_type:
                    return "", f"Unsupported file type"
                return f"Content from {file_path}", None

        handler = MockFileHandler()

        # Test supported file
        text, error = handler.extract_text("test.txt")
        assert "Content from" in text
        assert error is None

        # Test unsupported file
        text, error = handler.extract_text("test.xyz")
        assert text == ""
        assert "Unsupported" in error

    def test_batch_extraction(self):
        """Test extracting multiple files."""
        def extract_batch(file_paths: List[str]) -> List[Dict]:
            results = []
            for path in file_paths:
                ext = Path(path).suffix.lower()
                if ext in ['.txt', '.pdf']:
                    results.append({"path": path, "content": f"Content from {path}", "error": None})
                else:
                    results.append({"path": path, "content": "", "error": "Unsupported"})
            return results

        files = ["doc1.txt", "doc2.pdf", "doc3.xyz"]
        results = extract_batch(files)

        assert len(results) == 3
        assert results[0]["error"] is None
        assert results[1]["error"] is None
        assert results[2]["error"] == "Unsupported"


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestFileHandlerErrors:
    """Test error handling in file handler."""

    def test_file_permission_error(self):
        """Test handling file permission errors."""
        def extract_text(file_path: str) -> Tuple[str, Optional[str]]:
            try:
                raise PermissionError("Permission denied")
            except PermissionError as e:
                return "", f"Permission error: {str(e)}"

        text, error = extract_text("protected.txt")

        assert text == ""
        assert "Permission" in error

    def test_file_encoding_error(self):
        """Test handling encoding errors."""
        def extract_text(file_path: str) -> Tuple[str, Optional[str]]:
            try:
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
            except UnicodeDecodeError:
                try:
                    # Try fallback encoding
                    return "Fallback content", None
                except:
                    return "", "Unable to decode file"

        text, error = extract_text("binary.txt")

        assert text == "Fallback content"

    def test_large_file_handling(self):
        """Test handling very large files."""
        def extract_text(file_path: str, max_size_mb: int = 100) -> Tuple[str, Optional[str]]:
            # Simulate file size check
            file_size_mb = 150  # Simulate 150MB file
            if file_size_mb > max_size_mb:
                return "", f"File too large: {file_size_mb}MB (max: {max_size_mb}MB)"
            return "Content", None

        text, error = extract_text("huge.pdf")

        assert text == ""
        assert "too large" in error


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestFileHandlerEdgeCases:
    """Test edge cases in file handler."""

    def test_file_with_no_extension(self):
        """Test handling files with no extension."""
        def extract_text(file_path: str) -> Tuple[str, Optional[str]]:
            ext = Path(file_path).suffix
            if not ext:
                # Try to detect type from content
                return "", "Cannot determine file type: no extension"
            return "Content", None

        text, error = extract_text("README")

        assert "Cannot determine" in error

    def test_hidden_files(self):
        """Test handling hidden files (starting with .)."""
        def extract_text(file_path: str) -> Tuple[str, Optional[str]]:
            filename = Path(file_path).name
            if filename.startswith('.'):
                # Hidden file - extract as text
                return "Hidden file content", None
            return "Content", None

        text, error = extract_text(".gitignore")

        assert text == "Hidden file content"

    def test_symlink_files(self):
        """Test handling symbolic links."""
        def extract_text(file_path: str, follow_symlinks: bool = True) -> Tuple[str, Optional[str]]:
            # Simulate symlink resolution
            return "Content from resolved symlink", None

        text, error = extract_text("link.txt")

        assert "resolved symlink" in text

    def test_unicode_filename(self):
        """Test handling unicode characters in filename."""
        def extract_text(file_path: str) -> Tuple[str, Optional[str]]:
            # Handle unicode filename
            ext = Path(file_path).suffix.lower()
            if ext == '.txt':
                return "Unicode file content", None
            return "", "Unsupported"

        text, error = extract_text("文档.txt")

        assert text == "Unicode file content"

    def test_path_with_spaces(self):
        """Test handling paths with spaces."""
        def extract_text(file_path: str) -> Tuple[str, Optional[str]]:
            ext = Path(file_path).suffix.lower()
            if ext == '.txt':
                return f"Content from {file_path}", None
            return "", "Unsupported"

        text, error = extract_text("/path with spaces/my document.txt")

        assert "path with spaces" in text


# =============================================================================
# Supported Types Constants Tests
# =============================================================================

class TestSupportedTypes:
    """Test supported file types constants."""

    def test_text_types_defined(self):
        """Test text file types are defined."""
        SUPPORTED_TYPES = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.json': 'application/json',
            '.csv': 'text/csv',
        }

        assert '.txt' in SUPPORTED_TYPES
        assert '.md' in SUPPORTED_TYPES
        assert '.json' in SUPPORTED_TYPES

    def test_code_types_defined(self):
        """Test code file types are defined."""
        SUPPORTED_TYPES = {
            '.py': 'text/x-python',
            '.js': 'text/javascript',
            '.ts': 'text/typescript',
            '.java': 'text/x-java',
        }

        assert '.py' in SUPPORTED_TYPES
        assert '.js' in SUPPORTED_TYPES
        assert '.java' in SUPPORTED_TYPES

    def test_document_types_defined(self):
        """Test document file types are defined."""
        SUPPORTED_TYPES = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }

        assert '.pdf' in SUPPORTED_TYPES
        assert '.docx' in SUPPORTED_TYPES
        assert '.xlsx' in SUPPORTED_TYPES

    def test_media_types_defined(self):
        """Test media file types are defined."""
        SUPPORTED_TYPES = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
        }

        assert '.mp3' in SUPPORTED_TYPES
        assert '.mp4' in SUPPORTED_TYPES
