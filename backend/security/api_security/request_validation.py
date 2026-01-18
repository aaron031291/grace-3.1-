"""
Request Validation and Security for GRACE.

Provides:
- Request signing with HMAC-SHA256
- Replay attack prevention (nonce + timestamp)
- Request size limiting
- Content-Type validation
- Injection prevention (SQL, XSS, path traversal)
"""

import re
import time
import hmac
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set, Tuple, Pattern
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of request validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_data: Optional[Dict[str, Any]] = None
    
    def add_error(self, error: str):
        """Add an error and mark as invalid."""
        self.valid = False
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        """Add a warning."""
        self.warnings.append(warning)


class RequestSigning:
    """
    HMAC-SHA256 request signing for API integrity.
    
    Ensures requests haven't been tampered with in transit.
    """
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        header_name: str = "X-Signature",
        timestamp_header: str = "X-Timestamp",
        max_age_seconds: int = 300
    ):
        self._secret_key = secret_key or secrets.token_hex(32)
        self._header_name = header_name
        self._timestamp_header = timestamp_header
        self._max_age_seconds = max_age_seconds
        
    def _create_signature_base(
        self,
        method: str,
        path: str,
        timestamp: str,
        body: bytes,
        headers: Optional[Dict[str, str]] = None
    ) -> str:
        """Create the string to sign."""
        parts = [
            method.upper(),
            path,
            timestamp,
            hashlib.sha256(body).hexdigest() if body else ""
        ]
        
        if headers:
            sorted_headers = sorted(headers.items())
            parts.append(";".join(f"{k}={v}" for k, v in sorted_headers))
        
        return "\n".join(parts)
    
    def sign(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        headers: Optional[Dict[str, str]] = None,
        timestamp: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Sign a request.
        
        Args:
            method: HTTP method
            path: Request path
            body: Request body
            headers: Headers to include in signature
            timestamp: Optional timestamp (uses current if not provided)
            
        Returns:
            Tuple of (signature, timestamp)
        """
        ts = timestamp or str(int(time.time()))
        base = self._create_signature_base(method, path, ts, body, headers)
        
        signature = hmac.new(
            self._secret_key.encode(),
            base.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature, ts
    
    def verify(
        self,
        signature: str,
        timestamp: str,
        method: str,
        path: str,
        body: bytes = b"",
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify a request signature.
        
        Args:
            signature: Provided signature
            timestamp: Request timestamp
            method: HTTP method
            path: Request path
            body: Request body
            headers: Headers included in signature
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            ts = int(timestamp)
            now = int(time.time())
            
            if abs(now - ts) > self._max_age_seconds:
                return False, "Request timestamp expired"
        except ValueError:
            return False, "Invalid timestamp format"
        
        expected_sig, _ = self.sign(method, path, body, headers, timestamp)
        
        if not hmac.compare_digest(signature, expected_sig):
            return False, "Invalid signature"
        
        return True, None


class ReplayPrevention:
    """
    Replay attack prevention using nonce + timestamp.
    
    Tracks seen nonces to prevent request replay attacks.
    """
    
    def __init__(
        self,
        max_age_seconds: int = 300,
        max_nonces: int = 10000,
        nonce_header: str = "X-Nonce",
        timestamp_header: str = "X-Timestamp"
    ):
        self._max_age_seconds = max_age_seconds
        self._max_nonces = max_nonces
        self._nonce_header = nonce_header
        self._timestamp_header = timestamp_header
        self._seen_nonces: OrderedDict[str, float] = OrderedDict()
        
    def _cleanup_expired(self):
        """Remove expired nonces."""
        now = time.time()
        cutoff = now - self._max_age_seconds
        
        expired = [
            nonce for nonce, ts in self._seen_nonces.items()
            if ts < cutoff
        ]
        
        for nonce in expired:
            del self._seen_nonces[nonce]
        
        while len(self._seen_nonces) > self._max_nonces:
            self._seen_nonces.popitem(last=False)
    
    def generate_nonce(self) -> str:
        """Generate a new nonce."""
        return secrets.token_urlsafe(24)
    
    def check(self, nonce: str, timestamp: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a request is a replay.
        
        Args:
            nonce: Request nonce
            timestamp: Request timestamp
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            ts = int(timestamp)
            now = int(time.time())
            
            if abs(now - ts) > self._max_age_seconds:
                return False, "Request timestamp expired"
        except ValueError:
            return False, "Invalid timestamp format"
        
        self._cleanup_expired()
        
        if nonce in self._seen_nonces:
            logger.warning(f"Replay attack detected: nonce={nonce}")
            return False, "Nonce already used (replay attack detected)"
        
        self._seen_nonces[nonce] = time.time()
        
        return True, None


class SizeLimiter:
    """
    Request body size limiter.
    """
    
    def __init__(
        self,
        max_body_size: int = 10 * 1024 * 1024,
        max_json_depth: int = 20,
        max_array_length: int = 10000,
        max_string_length: int = 1024 * 1024
    ):
        self._max_body_size = max_body_size
        self._max_json_depth = max_json_depth
        self._max_array_length = max_array_length
        self._max_string_length = max_string_length
        
    def check_size(self, content_length: int) -> Tuple[bool, Optional[str]]:
        """Check if content length is acceptable."""
        if content_length > self._max_body_size:
            return False, f"Request body too large: {content_length} > {self._max_body_size}"
        return True, None
    
    def _check_json_depth(self, obj: Any, depth: int = 0) -> Tuple[bool, Optional[str]]:
        """Recursively check JSON nesting depth."""
        if depth > self._max_json_depth:
            return False, f"JSON nesting too deep: {depth} > {self._max_json_depth}"
        
        if isinstance(obj, dict):
            for value in obj.values():
                valid, error = self._check_json_depth(value, depth + 1)
                if not valid:
                    return valid, error
        elif isinstance(obj, list):
            if len(obj) > self._max_array_length:
                return False, f"Array too long: {len(obj)} > {self._max_array_length}"
            for item in obj:
                valid, error = self._check_json_depth(item, depth + 1)
                if not valid:
                    return valid, error
        elif isinstance(obj, str):
            if len(obj) > self._max_string_length:
                return False, f"String too long: {len(obj)} > {self._max_string_length}"
        
        return True, None
    
    def check_json(self, data: Any) -> Tuple[bool, Optional[str]]:
        """Check JSON data for size limits."""
        return self._check_json_depth(data)


class ContentTypeValidator:
    """
    Content-Type header validation.
    """
    
    def __init__(
        self,
        allowed_types: Optional[Set[str]] = None,
        require_charset: bool = False
    ):
        self._allowed_types = allowed_types or {
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
            "text/xml",
            "application/xml"
        }
        self._require_charset = require_charset
        
    def validate(self, content_type: Optional[str], method: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Content-Type header.
        
        Args:
            content_type: Content-Type header value
            method: HTTP method
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if method.upper() in ("GET", "HEAD", "DELETE", "OPTIONS"):
            return True, None
        
        if not content_type:
            return False, "Content-Type header required"
        
        media_type = content_type.split(";")[0].strip().lower()
        
        if media_type not in self._allowed_types:
            return False, f"Content-Type not allowed: {media_type}"
        
        if self._require_charset and "charset" not in content_type.lower():
            return False, "charset required in Content-Type"
        
        return True, None


class InjectionPrevention:
    """
    Injection attack prevention for SQL, XSS, and path traversal.
    """
    
    SQL_PATTERNS: List[Pattern] = [
        re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXEC|EXECUTE)\b)", re.IGNORECASE),
        re.compile(r"(--)|(;)|(\/\*)|(\*\/)", re.IGNORECASE),
        re.compile(r"(\bUNION\b.*\bSELECT\b)", re.IGNORECASE),
        re.compile(r"(\bOR\b\s+\d+\s*=\s*\d+)", re.IGNORECASE),
        re.compile(r"(\bAND\b\s+\d+\s*=\s*\d+)", re.IGNORECASE),
        re.compile(r"(\'|\"|;|--)", re.IGNORECASE),
    ]
    
    XSS_PATTERNS: List[Pattern] = [
        re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),
        re.compile(r"<[^>]*\s(on\w+)=", re.IGNORECASE),
        re.compile(r"<iframe[^>]*>", re.IGNORECASE),
        re.compile(r"<embed[^>]*>", re.IGNORECASE),
        re.compile(r"<object[^>]*>", re.IGNORECASE),
        re.compile(r"expression\s*\(", re.IGNORECASE),
        re.compile(r"url\s*\(\s*[\"']?\s*data:", re.IGNORECASE),
    ]
    
    PATH_TRAVERSAL_PATTERNS: List[Pattern] = [
        re.compile(r"\.\./"),
        re.compile(r"\.\.\\"),
        re.compile(r"%2e%2e[%/\\]", re.IGNORECASE),
        re.compile(r"\.\.%c0%af", re.IGNORECASE),
        re.compile(r"\.\.%c1%9c", re.IGNORECASE),
        re.compile(r"/etc/passwd", re.IGNORECASE),
        re.compile(r"/etc/shadow", re.IGNORECASE),
        re.compile(r"c:\\windows", re.IGNORECASE),
        re.compile(r"\\\\", re.IGNORECASE),
    ]
    
    def __init__(
        self,
        check_sql: bool = True,
        check_xss: bool = True,
        check_path_traversal: bool = True,
        custom_patterns: Optional[List[Pattern]] = None
    ):
        self._check_sql = check_sql
        self._check_xss = check_xss
        self._check_path_traversal = check_path_traversal
        self._custom_patterns = custom_patterns or []
        
    def check_sql_injection(self, value: str) -> Tuple[bool, Optional[str]]:
        """Check for SQL injection patterns."""
        if not self._check_sql:
            return True, None
        
        for pattern in self.SQL_PATTERNS:
            if pattern.search(value):
                logger.warning(f"SQL injection pattern detected: {pattern.pattern}")
                return False, "Potential SQL injection detected"
        
        return True, None
    
    def check_xss(self, value: str) -> Tuple[bool, Optional[str]]:
        """Check for XSS patterns."""
        if not self._check_xss:
            return True, None
        
        for pattern in self.XSS_PATTERNS:
            if pattern.search(value):
                logger.warning(f"XSS pattern detected: {pattern.pattern}")
                return False, "Potential XSS attack detected"
        
        return True, None
    
    def check_path_traversal(self, value: str) -> Tuple[bool, Optional[str]]:
        """Check for path traversal patterns."""
        if not self._check_path_traversal:
            return True, None
        
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if pattern.search(value):
                logger.warning(f"Path traversal pattern detected: {pattern.pattern}")
                return False, "Potential path traversal attack detected"
        
        return True, None
    
    def check_custom(self, value: str) -> Tuple[bool, Optional[str]]:
        """Check custom patterns."""
        for pattern in self._custom_patterns:
            if pattern.search(value):
                logger.warning(f"Custom pattern detected: {pattern.pattern}")
                return False, "Potentially dangerous pattern detected"
        
        return True, None
    
    def check(self, value: str) -> Tuple[bool, List[str]]:
        """
        Run all injection checks on a value.
        
        Returns:
            Tuple of (is_safe, list_of_errors)
        """
        errors = []
        
        checks = [
            self.check_sql_injection,
            self.check_xss,
            self.check_path_traversal,
            self.check_custom
        ]
        
        for check in checks:
            is_safe, error = check(value)
            if not is_safe and error:
                errors.append(error)
        
        return len(errors) == 0, errors
    
    def sanitize(self, value: str) -> str:
        """
        Sanitize a string by escaping dangerous characters.
        
        Note: Prefer validation over sanitization.
        """
        import html
        
        sanitized = html.escape(value)
        
        sanitized = sanitized.replace("'", "&#x27;")
        sanitized = sanitized.replace('"', "&quot;")
        
        return sanitized
    
    def check_dict(self, data: Dict[str, Any], path: str = "") -> Tuple[bool, List[str]]:
        """Recursively check all string values in a dictionary."""
        all_errors = []
        
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            is_safe, errors = self.check(str(key))
            if not is_safe:
                all_errors.extend([f"{current_path} (key): {e}" for e in errors])
            
            if isinstance(value, str):
                is_safe, errors = self.check(value)
                if not is_safe:
                    all_errors.extend([f"{current_path}: {e}" for e in errors])
            elif isinstance(value, dict):
                is_safe, errors = self.check_dict(value, current_path)
                if not is_safe:
                    all_errors.extend(errors)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        is_safe, errors = self.check(item)
                        if not is_safe:
                            all_errors.extend([f"{current_path}[{i}]: {e}" for e in errors])
                    elif isinstance(item, dict):
                        is_safe, errors = self.check_dict(item, f"{current_path}[{i}]")
                        if not is_safe:
                            all_errors.extend(errors)
        
        return len(all_errors) == 0, all_errors


class RequestValidator:
    """
    Complete request validation combining all security checks.
    """
    
    def __init__(
        self,
        request_signing: Optional[RequestSigning] = None,
        replay_prevention: Optional[ReplayPrevention] = None,
        size_limiter: Optional[SizeLimiter] = None,
        content_type_validator: Optional[ContentTypeValidator] = None,
        injection_prevention: Optional[InjectionPrevention] = None,
        require_signing: bool = False,
        require_nonce: bool = False
    ):
        self._signing = request_signing or RequestSigning()
        self._replay = replay_prevention or ReplayPrevention()
        self._size_limiter = size_limiter or SizeLimiter()
        self._content_type = content_type_validator or ContentTypeValidator()
        self._injection = injection_prevention or InjectionPrevention()
        self._require_signing = require_signing
        self._require_nonce = require_nonce
        self._audit_storage = None
        
    def _audit_event(self, action: str, details: Dict[str, Any], severity: str = "warning"):
        """Record security audit event."""
        logger.log(
            logging.WARNING if severity == "warning" else logging.INFO,
            f"[REQUEST-VALIDATION] {action}: {details}"
        )
    
    def validate(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Optional[bytes] = None,
        json_data: Optional[Dict[str, Any]] = None,
        client_ip: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate an incoming request.
        
        Args:
            method: HTTP method
            path: Request path
            headers: Request headers
            body: Raw request body
            json_data: Parsed JSON body
            client_ip: Client IP address
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(valid=True)
        
        content_type = headers.get("Content-Type") or headers.get("content-type")
        is_valid, error = self._content_type.validate(content_type, method)
        if not is_valid and error:
            result.add_error(error)
        
        content_length = headers.get("Content-Length") or headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                is_valid, error = self._size_limiter.check_size(length)
                if not is_valid and error:
                    result.add_error(error)
            except ValueError:
                result.add_error("Invalid Content-Length header")
        
        if json_data:
            is_valid, error = self._size_limiter.check_json(json_data)
            if not is_valid and error:
                result.add_error(error)
        
        signature = headers.get("X-Signature") or headers.get("x-signature")
        timestamp = headers.get("X-Timestamp") or headers.get("x-timestamp")
        
        if self._require_signing:
            if not signature or not timestamp:
                result.add_error("Request signing required")
            elif body is not None:
                is_valid, error = self._signing.verify(
                    signature, timestamp, method, path, body
                )
                if not is_valid and error:
                    result.add_error(error)
        
        nonce = headers.get("X-Nonce") or headers.get("x-nonce")
        
        if self._require_nonce:
            if not nonce or not timestamp:
                result.add_error("Nonce and timestamp required")
            else:
                is_valid, error = self._replay.check(nonce, timestamp)
                if not is_valid and error:
                    result.add_error(error)
        
        if json_data:
            is_safe, errors = self._injection.check_dict(json_data)
            if not is_safe:
                for error in errors:
                    result.add_error(error)
        
        for header_name in ["X-Forwarded-For", "X-Original-URL", "X-Rewrite-URL"]:
            value = headers.get(header_name) or headers.get(header_name.lower())
            if value:
                is_safe, errors = self._injection.check(value)
                if not is_safe:
                    result.add_warning(f"Suspicious header {header_name}")
        
        if not result.valid:
            self._audit_event(
                "validation_failed",
                {
                    "path": path,
                    "method": method,
                    "client_ip": client_ip,
                    "errors": result.errors
                },
                severity="warning"
            )
        
        return result
    
    @property
    def signing(self) -> RequestSigning:
        """Get the request signing service."""
        return self._signing
    
    @property
    def replay_prevention(self) -> ReplayPrevention:
        """Get the replay prevention service."""
        return self._replay


_request_validator: Optional[RequestValidator] = None


def get_request_validator() -> RequestValidator:
    """Get the request validator singleton."""
    global _request_validator
    if _request_validator is None:
        _request_validator = RequestValidator()
    return _request_validator
