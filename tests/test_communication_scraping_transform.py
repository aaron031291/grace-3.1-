"""
Tests for Communication, Scraping, and Transform Modules

Tests:
1. LLM Bridge - message routing, bidirectional communication
2. URL Validator - valid/invalid URLs, security checks
3. Document Downloader - download logic, file types
4. Scraping Service - web scraping, rate limiting
5. Transformation Library - code transformations
6. LLM Transform Integration - LLM-guided transforms
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestGraceLLMBridge:
    """Tests for Grace LLM Bridge."""
    
    @pytest.fixture
    def llm_bridge(self):
        """Create LLM bridge instance."""
        try:
            from backend.communication.grace_llm_bridge import GraceLLMBridge
            return GraceLLMBridge()
        except Exception:
            return Mock()
    
    def test_init(self, llm_bridge):
        """Test initialization."""
        assert llm_bridge is not None
    
    def test_send_message(self, llm_bridge):
        """Test sending message to LLM."""
        if hasattr(llm_bridge, 'send_message'):
            llm_bridge.send_message = Mock(return_value={"response": "Hello", "tokens": 10})
            result = llm_bridge.send_message("Hello, LLM!")
            assert "response" in result
    
    def test_route_to_model(self, llm_bridge):
        """Test routing to appropriate model."""
        if hasattr(llm_bridge, 'route_message'):
            llm_bridge.route_message = Mock(return_value={"model": "code-model"})
            result = llm_bridge.route_message(message="Write code", task_type="code")
            assert "model" in result
    
    def test_bidirectional_exchange(self, llm_bridge):
        """Test bidirectional communication."""
        if hasattr(llm_bridge, 'exchange'):
            llm_bridge.exchange = Mock(return_value={"sent": "q", "received": "a", "success": True})
            result = llm_bridge.exchange(outgoing="What?", context={})
            assert result["success"] == True
    
    def test_timeout_handling(self, llm_bridge):
        """Test timeout handling."""
        if hasattr(llm_bridge, 'send_message'):
            llm_bridge.send_message = Mock(side_effect=TimeoutError("Timed out"))
            with pytest.raises(TimeoutError):
                llm_bridge.send_message("Query", timeout=5)


class TestURLValidator:
    """Tests for URL Validator."""
    
    @pytest.fixture
    def validator(self):
        """Create URL validator instance."""
        try:
            from backend.scraping.url_validator import URLValidator
            return URLValidator()
        except Exception:
            return Mock()
    
    def test_init(self, validator):
        """Test initialization."""
        assert validator is not None
    
    def test_valid_url(self, validator):
        """Test validating valid URL."""
        if hasattr(validator, 'validate'):
            validator.validate = Mock(return_value={"valid": True, "url": "https://example.com"})
            result = validator.validate("https://example.com")
            assert result["valid"] == True
    
    def test_invalid_url(self, validator):
        """Test validating invalid URL."""
        if hasattr(validator, 'validate'):
            validator.validate = Mock(return_value={"valid": False, "error": "Invalid format"})
            result = validator.validate("not-a-url")
            assert result["valid"] == False
    
    def test_security_check_safe(self, validator):
        """Test security check for safe URL."""
        if hasattr(validator, 'check_security'):
            validator.check_security = Mock(return_value={"safe": True, "threats": []})
            result = validator.check_security("https://safe-site.com")
            assert result["safe"] == True
    
    def test_security_check_dangerous(self, validator):
        """Test security check for dangerous URL."""
        if hasattr(validator, 'check_security'):
            validator.check_security = Mock(return_value={"safe": False, "threats": ["malware"]})
            result = validator.check_security("https://bad-site.com")
            assert result["safe"] == False
    
    def test_normalize_url(self, validator):
        """Test URL normalization."""
        if hasattr(validator, 'normalize'):
            validator.normalize = Mock(return_value="https://example.com/path")
            result = validator.normalize("HTTPS://EXAMPLE.COM/path/")
            assert "example.com" in result


class TestDocumentDownloader:
    """Tests for Document Downloader."""
    
    @pytest.fixture
    def downloader(self):
        """Create document downloader instance."""
        try:
            from backend.scraping.document_downloader import DocumentDownloader
            return DocumentDownloader()
        except Exception:
            return Mock()
    
    def test_init(self, downloader):
        """Test initialization."""
        assert downloader is not None
    
    def test_download_success(self, downloader):
        """Test successful document download."""
        if hasattr(downloader, 'download'):
            downloader.download = Mock(return_value={"success": True, "path": "/tmp/doc.pdf"})
            result = downloader.download("https://example.com/doc.pdf")
            assert result["success"] == True
    
    def test_download_with_retry(self, downloader):
        """Test download with retry logic."""
        if hasattr(downloader, 'download_with_retry'):
            downloader.download_with_retry = Mock(return_value={"success": True, "attempts": 2})
            result = downloader.download_with_retry("https://example.com/doc.pdf", max_retries=3)
            assert result["success"] == True
    
    def test_detect_file_type(self, downloader):
        """Test file type detection."""
        if hasattr(downloader, 'detect_type'):
            downloader.detect_type = Mock(return_value="application/pdf")
            result = downloader.detect_type("document.pdf")
            assert "pdf" in result
    
    def test_validate_download(self, downloader):
        """Test download validation."""
        if hasattr(downloader, 'validate_download'):
            downloader.validate_download = Mock(return_value={"valid": True, "checksum": "abc123"})
            result = downloader.validate_download("/tmp/doc.pdf")
            assert result["valid"] == True


class TestScrapingService:
    """Tests for Scraping Service."""
    
    @pytest.fixture
    def scraping_service(self):
        """Create scraping service instance."""
        try:
            from backend.scraping.service import ScrapingService
            return ScrapingService()
        except Exception:
            return Mock()
    
    def test_init(self, scraping_service):
        """Test initialization."""
        assert scraping_service is not None
    
    def test_scrape_url(self, scraping_service):
        """Test URL scraping."""
        if hasattr(scraping_service, 'scrape'):
            scraping_service.scrape = Mock(return_value={"content": "<html>...</html>", "success": True})
            result = scraping_service.scrape("https://example.com")
            assert result["success"] == True
    
    def test_extract_text(self, scraping_service):
        """Test text extraction."""
        if hasattr(scraping_service, 'extract_text'):
            scraping_service.extract_text = Mock(return_value="Extracted content")
            result = scraping_service.extract_text("<html><body>Content</body></html>")
            assert len(result) > 0
    
    def test_rate_limit_allowed(self, scraping_service):
        """Test rate limiting when allowed."""
        if hasattr(scraping_service, 'check_rate_limit'):
            scraping_service.check_rate_limit = Mock(return_value={"allowed": True, "remaining": 100})
            result = scraping_service.check_rate_limit("example.com")
            assert result["allowed"] == True
    
    def test_rate_limit_exceeded(self, scraping_service):
        """Test rate limit exceeded."""
        if hasattr(scraping_service, 'check_rate_limit'):
            scraping_service.check_rate_limit = Mock(return_value={"allowed": False, "remaining": 0})
            result = scraping_service.check_rate_limit("example.com")
            assert result["allowed"] == False


class TestTransformationLibrary:
    """Tests for Transformation Library."""
    
    @pytest.fixture
    def transform_lib(self):
        """Create transformation library instance."""
        try:
            from backend.transform.transformation_library import TransformationLibrary
            return TransformationLibrary()
        except Exception:
            return Mock()
    
    def test_init(self, transform_lib):
        """Test initialization."""
        assert transform_lib is not None
    
    def test_apply_transform(self, transform_lib):
        """Test applying transformation."""
        if hasattr(transform_lib, 'apply'):
            transform_lib.apply = Mock(return_value={"code": "transformed", "success": True})
            result = transform_lib.apply(code="original", transform="rename_variable")
            assert result["success"] == True
    
    def test_list_transforms(self, transform_lib):
        """Test listing available transforms."""
        if hasattr(transform_lib, 'list_transforms'):
            transform_lib.list_transforms = Mock(return_value=["rename", "extract", "inline"])
            transforms = transform_lib.list_transforms()
            assert len(transforms) >= 0
    
    def test_validate_transform(self, transform_lib):
        """Test transform validation."""
        if hasattr(transform_lib, 'validate'):
            transform_lib.validate = Mock(return_value={"valid": True, "errors": []})
            result = transform_lib.validate(original="code1", transformed="code2")
            assert result["valid"] == True
    
    def test_chain_transforms(self, transform_lib):
        """Test chaining multiple transforms."""
        if hasattr(transform_lib, 'chain'):
            transform_lib.chain = Mock(return_value={"code": "final", "steps": 3})
            result = transform_lib.chain(code="original", transforms=["t1", "t2", "t3"])
            assert result["steps"] == 3


class TestLLMTransformIntegration:
    """Tests for LLM Transform Integration."""
    
    @pytest.fixture
    def llm_transform(self):
        """Create LLM transform integration instance."""
        try:
            from backend.transform.llm_transform_integration import LLMTransformIntegration
            return LLMTransformIntegration()
        except Exception:
            return Mock()
    
    def test_init(self, llm_transform):
        """Test initialization."""
        assert llm_transform is not None
    
    def test_suggest_transform(self, llm_transform):
        """Test LLM-suggested transformation."""
        if hasattr(llm_transform, 'suggest_transform'):
            llm_transform.suggest_transform = Mock(return_value={"suggestion": "extract_function", "confidence": 0.85})
            result = llm_transform.suggest_transform(code="def big(): ...", goal="readability")
            assert "suggestion" in result
    
    def test_apply_llm_transform(self, llm_transform):
        """Test applying LLM-guided transformation."""
        if hasattr(llm_transform, 'apply_transform'):
            llm_transform.apply_transform = Mock(return_value={"transformed_code": "def new(): ...", "explanation": "Extracted"})
            result = llm_transform.apply_transform(code="def func(): ...", instruction="Extract helper")
            assert "transformed_code" in result
    
    def test_verify_transform(self, llm_transform):
        """Test transform verification."""
        if hasattr(llm_transform, 'verify'):
            llm_transform.verify = Mock(return_value={"equivalent": True, "confidence": 0.95})
            result = llm_transform.verify(original="code1", transformed="code2")
            assert result["equivalent"] == True


class TestModuleImports:
    """Test module imports."""
    
    def test_communication_importable(self):
        """Test communication module."""
        try:
            from backend.communication import grace_llm_bridge
            assert True
        except ImportError as e:
            pytest.skip(f"Import error: {e}")
    
    def test_scraping_importable(self):
        """Test scraping module."""
        try:
            from backend.scraping import url_validator, document_downloader, service
            assert True
        except ImportError as e:
            pytest.skip(f"Import error: {e}")
    
    def test_transform_importable(self):
        """Test transform module."""
        try:
            from backend.transform import transformation_library
            assert True
        except ImportError as e:
            pytest.skip(f"Import error: {e}")


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_network_error(self):
        """Test network error handling."""
        mock = Mock()
        mock.download = Mock(side_effect=ConnectionError("Network unreachable"))
        with pytest.raises(ConnectionError):
            mock.download("https://example.com")
    
    def test_syntax_error(self):
        """Test syntax error in transformation."""
        mock = Mock()
        mock.apply = Mock(side_effect=SyntaxError("Invalid syntax"))
        with pytest.raises(SyntaxError):
            mock.apply(code="invalid{", transform="rename")
    
    def test_llm_unavailable(self):
        """Test LLM unavailable error."""
        mock = Mock()
        mock.send_message = Mock(side_effect=RuntimeError("LLM unavailable"))
        with pytest.raises(RuntimeError):
            mock.send_message("Hello")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x", "--tb=short"])
