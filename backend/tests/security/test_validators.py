import pytest
import os
from security.validators import InputValidator, sanitize_input, validate_file_path

def test_validate_string():
    validator = InputValidator()
    
    # Valid string
    valid, val, err = validator.validate_string("Hello world")
    assert valid is True
    assert val == "Hello world"
    
    # XSS
    valid, _, err = validator.validate_string("<script>alert(1)</script>")
    assert valid is False
    assert "dangerous content" in err
    
    # SQLi
    valid, _, err = validator.validate_string("SELECT * FROM users")
    assert valid is False
    assert "invalid characters" in err
    
    # Max length
    valid, _, err = validator.validate_string("A" * 10000, max_length=100)
    assert valid is False

def test_validate_path_traversal():
    validator = InputValidator()
    
    # Allowed relative
    valid, path, err = validator.validate_path("some/folder/file.txt")
    assert valid is True
    
    # Traversal attempt
    valid, _, err = validator.validate_path("../../../etc/passwd")
    assert valid is False
    
    valid, _, err = validator.validate_path("folder/%2e%2e/secret.txt")
    assert valid is False

def test_validate_filename():
    validator = InputValidator()
    
    valid, fname, _ = validator.validate_filename("document.pdf", allowed_extensions=[".pdf"])
    assert valid is True
    
    # Invalid extension
    valid, _, _ = validator.validate_filename("shell.py", allowed_extensions=[".pdf"])
    assert valid is False
    
    # Double extension (with suspicious middle)
    valid, _, _ = validator.validate_filename("image.exe.txt", allowed_extensions=[".txt"])
    assert valid is False

def test_validate_email():
    validator = InputValidator()
    
    assert validator.validate_email("test@example.com")[0] is True
    assert validator.validate_email("invalid-email")[0] is False

def test_validate_json_input():
    validator = InputValidator()
    
    data = {
        "valid": "string",
        "nested": {"key": 123},
        "list": [1, 2, 3]
    }
    valid, sanitized, err = validator.validate_json_input(data)
    assert valid is True
    assert sanitized["valid"] == "string"
    
    # Injection in JSON
    bad_data = {
        "xss": "<script>alert()</script>"
    }
    valid, _, err = validator.validate_json_input(bad_data)
    assert valid is False

if __name__ == "__main__":
    pytest.main(['-v', __file__])
