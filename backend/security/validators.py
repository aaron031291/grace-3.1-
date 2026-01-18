"""
Input Validation and Sanitization for GRACE

Provides secure input handling to prevent:
- XSS attacks
- SQL injection
- Path traversal
- Command injection
"""

import re
import html
from typing import Any, Optional, List, Union
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import unquote

from .config import get_security_config


class InputValidator:
    """
    Validates and sanitizes user input.

    Use this for all user-provided data before processing.
    """

    def __init__(self):
        self.config = get_security_config()

        # Dangerous patterns to detect
        self.xss_patterns = [
            re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"on\w+\s*=", re.IGNORECASE),  # onclick=, onload=, etc.
            re.compile(r"<iframe", re.IGNORECASE),
            re.compile(r"<object", re.IGNORECASE),
            re.compile(r"<embed", re.IGNORECASE),
        ]

        self.sql_patterns = [
            re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC)\b.*\b(FROM|INTO|TABLE|DATABASE)\b", re.IGNORECASE),
            re.compile(r";\s*(SELECT|INSERT|UPDATE|DELETE|DROP)", re.IGNORECASE),
            re.compile(r"'\s*(OR|AND)\s*'?\s*\d*\s*=\s*\d*", re.IGNORECASE),  # ' OR '1'='1
            re.compile(r"'\s*(OR|AND)\s*'[^']*'\s*=\s*'[^']*'", re.IGNORECASE),  # ' OR '1'='1' pattern
            re.compile(r"\d+'\s*(OR|AND)\s*'[^']*'\s*=\s*'", re.IGNORECASE),  # 1' OR '1'='1
            re.compile(r"--\s*$", re.MULTILINE),  # SQL comment
            re.compile(r"/\*.*\*/", re.DOTALL),  # Block comments /* */
        ]

        self.path_traversal_patterns = [
            re.compile(r"\.\./"),
            re.compile(r"\.\.\\"),
            re.compile(r"%2e%2e[/\\]", re.IGNORECASE),
            re.compile(r"%252e%252e[/\\]", re.IGNORECASE),
        ]

        self.command_injection_patterns = [
            re.compile(r"[;&|`$]"),  # Shell metacharacters
            re.compile(r"\$\("),      # Command substitution
            re.compile(r"`[^`]+`"),   # Backtick execution
        ]

    def validate_string(
        self,
        value: str,
        max_length: Optional[int] = None,
        allow_html: bool = False,
        allow_special_chars: bool = True,
        field_name: str = "input"
    ) -> tuple:
        """
        Validate a string input.

        Args:
            value: The string to validate
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML tags
            allow_special_chars: Whether to allow special characters
            field_name: Name of the field for error messages

        Returns:
            (is_valid, sanitized_value, error_message)
        """
        if not isinstance(value, str):
            return (False, None, f"{field_name} must be a string")

        # Check length
        max_len = max_length or self.config.MAX_STRING_LENGTH
        if len(value) > max_len:
            return (False, None, f"{field_name} exceeds maximum length of {max_len}")

        # Check for XSS if HTML not allowed
        if not allow_html:
            for pattern in self.xss_patterns:
                if pattern.search(value):
                    return (False, None, f"{field_name} contains potentially dangerous content")

        # Check for SQL injection patterns
        for pattern in self.sql_patterns:
            if pattern.search(value):
                return (False, None, f"{field_name} contains invalid characters")

        # Sanitize the value
        sanitized = value
        if not allow_html:
            sanitized = html.escape(value)

        return (True, sanitized, None)

    def validate_path(
        self,
        value: str,
        base_path: Optional[str] = None,
        allow_absolute: bool = False,
        field_name: str = "path"
    ) -> tuple:
        """
        Validate a file path to prevent path traversal.

        Args:
            value: The path to validate
            base_path: If provided, ensure path is within this directory
            allow_absolute: Whether to allow absolute paths
            field_name: Name of the field for error messages

        Returns:
            (is_valid, normalized_path, error_message)
        """
        if not isinstance(value, str):
            return (False, None, f"{field_name} must be a string")

        # URL-decode the value to catch encoded traversal attempts
        # Decode multiple times to catch double-encoding
        decoded_value = value
        for _ in range(3):
            prev = decoded_value
            decoded_value = unquote(decoded_value)
            if decoded_value == prev:
                break

        # Check for path traversal patterns on both original and decoded
        for check_value in [value, decoded_value]:
            for pattern in self.path_traversal_patterns:
                if pattern.search(check_value):
                    return (False, None, f"{field_name} contains invalid path sequence")

        # Check for null bytes
        if "\x00" in value or "\x00" in decoded_value:
            return (False, None, f"{field_name} contains invalid characters")

        try:
            # Normalize the path
            path = Path(value)

            # Check for absolute path if not allowed
            if not allow_absolute and path.is_absolute():
                return (False, None, f"{field_name} must be a relative path")

            # If base_path provided, ensure the path stays within it
            if base_path:
                base = Path(base_path).resolve()
                full_path = (base / value).resolve()

                # Check if resolved path is within base
                try:
                    full_path.relative_to(base)
                except ValueError:
                    return (False, None, f"{field_name} must be within the allowed directory")

                return (True, str(full_path), None)

            return (True, str(path), None)

        except Exception as e:
            return (False, None, f"Invalid {field_name}: {str(e)}")

    def validate_filename(
        self,
        value: str,
        allowed_extensions: Optional[List[str]] = None,
        field_name: str = "filename"
    ) -> tuple:
        """
        Validate a filename.

        Args:
            value: The filename to validate
            allowed_extensions: List of allowed file extensions
            field_name: Name of the field for error messages

        Returns:
            (is_valid, sanitized_filename, error_message)
        """
        if not isinstance(value, str):
            return (False, None, f"{field_name} must be a string")

        # Remove path components
        filename = Path(value).name

        # Check for dangerous characters
        dangerous_chars = ['/', '\\', '\x00', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            if char in filename:
                return (False, None, f"{field_name} contains invalid character: {char}")

        # Check extension if specified
        if allowed_extensions is None:
            allowed_extensions = self.config.ALLOWED_FILE_EXTENSIONS

        if allowed_extensions:
            ext = Path(filename).suffix.lower()
            if ext not in allowed_extensions:
                return (False, None, f"File type '{ext}' not allowed. Allowed: {', '.join(allowed_extensions)}")

        # Check for double extensions (e.g., file.txt.exe)
        parts = filename.split('.')
        if len(parts) > 2:
            # Check if any middle extension is suspicious
            suspicious_exts = ['.exe', '.bat', '.cmd', '.sh', '.ps1', '.vbs']
            for part in parts[1:-1]:
                if f'.{part.lower()}' in suspicious_exts:
                    return (False, None, f"{field_name} contains suspicious extension")

        return (True, filename, None)

    def validate_email(self, value: str, field_name: str = "email") -> tuple:
        """
        Validate an email address.

        Returns:
            (is_valid, sanitized_email, error_message)
        """
        if not isinstance(value, str):
            return (False, None, f"{field_name} must be a string")

        # Check for consecutive dots (invalid in domain)
        if ".." in value:
            return (False, None, f"Invalid {field_name} format")

        # Basic email pattern - requires no consecutive dots
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)+$'
        )

        if not email_pattern.match(value):
            return (False, None, f"Invalid {field_name} format")

        # Check length
        if len(value) > 254:
            return (False, None, f"{field_name} is too long")

        return (True, value.lower().strip(), None)

    def validate_url(self, value: str, allowed_schemes: List[str] = None, field_name: str = "url") -> tuple:
        """
        Validate a URL.

        Returns:
            (is_valid, sanitized_url, error_message)
        """
        if not isinstance(value, str):
            return (False, None, f"{field_name} must be a string")

        allowed_schemes = allowed_schemes or ["http", "https"]

        # Parse URL
        from urllib.parse import urlparse
        try:
            parsed = urlparse(value)

            if parsed.scheme not in allowed_schemes:
                return (False, None, f"{field_name} must use {' or '.join(allowed_schemes)}")

            if not parsed.netloc:
                return (False, None, f"Invalid {field_name}")

            return (True, value, None)

        except Exception:
            return (False, None, f"Invalid {field_name}")

    def validate_json_input(self, data: Any, max_depth: int = 10, current_depth: int = 0) -> tuple:
        """
        Recursively validate JSON data structure.

        Returns:
            (is_valid, sanitized_data, error_message)
        """
        if current_depth > max_depth:
            return (False, None, "JSON structure too deeply nested")

        if isinstance(data, str):
            return self.validate_string(data)

        elif isinstance(data, dict):
            if len(data) > self.config.MAX_ARRAY_LENGTH:
                return (False, None, f"Object has too many keys (max: {self.config.MAX_ARRAY_LENGTH})")

            sanitized = {}
            for key, value in data.items():
                # Validate key
                key_valid, sanitized_key, error = self.validate_string(key, max_length=256)
                if not key_valid:
                    return (False, None, f"Invalid key: {error}")

                # Validate value recursively
                value_valid, sanitized_value, error = self.validate_json_input(
                    value, max_depth, current_depth + 1
                )
                if not value_valid:
                    return (False, None, error)

                sanitized[sanitized_key] = sanitized_value

            return (True, sanitized, None)

        elif isinstance(data, list):
            if len(data) > self.config.MAX_ARRAY_LENGTH:
                return (False, None, f"Array too long (max: {self.config.MAX_ARRAY_LENGTH})")

            sanitized = []
            for item in data:
                valid, sanitized_item, error = self.validate_json_input(
                    item, max_depth, current_depth + 1
                )
                if not valid:
                    return (False, None, error)
                sanitized.append(sanitized_item)

            return (True, sanitized, None)

        elif isinstance(data, (int, float, bool, type(None))):
            return (True, data, None)

        else:
            return (False, None, f"Unsupported data type: {type(data)}")


# Convenience functions
_validator: Optional[InputValidator] = None


def get_validator() -> InputValidator:
    """Get the input validator singleton."""
    global _validator
    if _validator is None:
        _validator = InputValidator()
    return _validator


def sanitize_input(value: str, **kwargs) -> str:
    """
    Convenience function to sanitize a string input.

    Args:
        value: The string to sanitize
        **kwargs: Additional arguments passed to validate_string

    Returns:
        Sanitized string

    Raises:
        ValueError: If input is invalid
    """
    validator = get_validator()
    is_valid, sanitized, error = validator.validate_string(value, **kwargs)

    if not is_valid:
        raise ValueError(error)

    return sanitized


def validate_file_path(path: str, base_path: str) -> str:
    """
    Convenience function to validate a file path.

    Args:
        path: The path to validate
        base_path: The base directory path must be within

    Returns:
        Normalized absolute path

    Raises:
        ValueError: If path is invalid or escapes base_path
    """
    validator = get_validator()
    is_valid, normalized, error = validator.validate_path(path, base_path=base_path)

    if not is_valid:
        raise ValueError(error)

    return normalized
