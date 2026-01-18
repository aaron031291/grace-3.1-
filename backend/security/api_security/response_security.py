"""
Response Security for GRACE.

Provides:
- Response signing for integrity verification
- Sensitive data masking for logs
- PII redaction from responses
- Error sanitization to prevent info leakage
- Security headers injection
"""

import re
import hmac
import hashlib
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Set, Pattern, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ResponseSigner:
    """
    HMAC-SHA256 response signing for integrity verification.
    
    Allows clients to verify response integrity.
    """
    
    def __init__(
        self,
        secret_key: str,
        header_name: str = "X-Response-Signature",
        include_timestamp: bool = True
    ):
        self._secret_key = secret_key
        self._header_name = header_name
        self._include_timestamp = include_timestamp
        
    def sign(
        self,
        body: bytes,
        status_code: int,
        content_type: str,
        request_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Sign a response.
        
        Args:
            body: Response body
            status_code: HTTP status code
            content_type: Response Content-Type
            request_id: Optional request correlation ID
            
        Returns:
            Headers to add to response
        """
        timestamp = str(int(datetime.utcnow().timestamp()))
        
        sign_parts = [
            str(status_code),
            content_type,
            hashlib.sha256(body).hexdigest(),
            timestamp
        ]
        
        if request_id:
            sign_parts.append(request_id)
        
        message = "\n".join(sign_parts)
        
        signature = hmac.new(
            self._secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            self._header_name: signature,
        }
        
        if self._include_timestamp:
            headers["X-Response-Timestamp"] = timestamp
        
        return headers
    
    def verify(
        self,
        signature: str,
        body: bytes,
        status_code: int,
        content_type: str,
        timestamp: str,
        request_id: Optional[str] = None
    ) -> bool:
        """Verify a response signature."""
        sign_parts = [
            str(status_code),
            content_type,
            hashlib.sha256(body).hexdigest(),
            timestamp
        ]
        
        if request_id:
            sign_parts.append(request_id)
        
        message = "\n".join(sign_parts)
        
        expected = hmac.new(
            self._secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)


class SensitiveDataMasker:
    """
    Masks sensitive data in logs and debug output.
    """
    
    DEFAULT_PATTERNS: Dict[str, Pattern] = {
        "password": re.compile(r'("password"\s*:\s*")[^"]*(")', re.IGNORECASE),
        "secret": re.compile(r'("secret"\s*:\s*")[^"]*(")', re.IGNORECASE),
        "api_key": re.compile(r'("api_key"\s*:\s*")[^"]*(")', re.IGNORECASE),
        "token": re.compile(r'("token"\s*:\s*")[^"]*(")', re.IGNORECASE),
        "authorization": re.compile(r'(Authorization:\s*)(Bearer\s+)?[^\s]+', re.IGNORECASE),
        "credit_card": re.compile(r'\b(\d{4})\s*-?\s*(\d{4})\s*-?\s*(\d{4})\s*-?\s*(\d{4})\b'),
        "ssn": re.compile(r'\b(\d{3})-?(\d{2})-?(\d{4})\b'),
    }
    
    DEFAULT_FIELD_NAMES: Set[str] = {
        "password", "passwd", "secret", "api_key", "apikey",
        "access_token", "refresh_token", "token", "auth_token",
        "private_key", "client_secret", "credentials", "ssn",
        "social_security", "credit_card", "card_number", "cvv"
    }
    
    def __init__(
        self,
        mask_char: str = "*",
        mask_length: int = 8,
        additional_patterns: Optional[Dict[str, Pattern]] = None,
        additional_fields: Optional[Set[str]] = None
    ):
        self._mask_char = mask_char
        self._mask_length = mask_length
        self._patterns = {**self.DEFAULT_PATTERNS, **(additional_patterns or {})}
        self._sensitive_fields = self.DEFAULT_FIELD_NAMES | (additional_fields or set())
        
    def _mask_value(self, value: Any, reveal_chars: int = 0) -> str:
        """Mask a value, optionally revealing last N characters."""
        if not value:
            return self._mask_char * self._mask_length
        
        str_value = str(value)
        if reveal_chars > 0 and len(str_value) > reveal_chars:
            return self._mask_char * self._mask_length + str_value[-reveal_chars:]
        return self._mask_char * self._mask_length
    
    def mask_string(self, text: str) -> str:
        """Mask sensitive patterns in a string."""
        result = text
        
        for name, pattern in self._patterns.items():
            if name == "credit_card":
                result = pattern.sub(r'\1-****-****-\4', result)
            elif name == "ssn":
                result = pattern.sub(r'***-**-\3', result)
            else:
                result = pattern.sub(rf'\1{self._mask_char * self._mask_length}\2' if '(' in pattern.pattern else self._mask_char * self._mask_length, result)
        
        return result
    
    def mask_dict(self, data: Dict[str, Any], in_place: bool = False) -> Dict[str, Any]:
        """
        Mask sensitive fields in a dictionary.
        
        Args:
            data: Dictionary to mask
            in_place: Whether to modify the original
            
        Returns:
            Masked dictionary
        """
        result = data if in_place else data.copy()
        
        for key, value in list(result.items()):
            key_lower = key.lower()
            
            if key_lower in self._sensitive_fields or any(s in key_lower for s in self._sensitive_fields):
                result[key] = self._mask_value(value)
            elif isinstance(value, dict):
                result[key] = self.mask_dict(value, in_place=False)
            elif isinstance(value, list):
                result[key] = [
                    self.mask_dict(item, in_place=False) if isinstance(item, dict) else item
                    for item in value
                ]
            elif isinstance(value, str):
                result[key] = self.mask_string(value)
        
        return result
    
    def mask_for_logging(self, data: Any) -> str:
        """Prepare data for safe logging."""
        if isinstance(data, dict):
            masked = self.mask_dict(data)
            return json.dumps(masked, default=str)
        elif isinstance(data, str):
            return self.mask_string(data)
        else:
            return self.mask_string(str(data))


class PIIRedactor:
    """
    Personally Identifiable Information (PII) redaction.
    """
    
    PII_PATTERNS: Dict[str, Pattern] = {
        "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        "phone": re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
        "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        "credit_card": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
        "ip_address": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        "date_of_birth": re.compile(r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b'),
        "passport": re.compile(r'\b[A-Z]{1,2}\d{6,9}\b'),
        "driver_license": re.compile(r'\b[A-Z]{1,2}\d{5,8}\b'),
    }
    
    PII_FIELD_NAMES: Set[str] = {
        "email", "phone", "phone_number", "mobile", "ssn",
        "social_security", "date_of_birth", "dob", "birthday",
        "address", "street", "city", "state", "zip", "zipcode",
        "passport", "driver_license", "license_number",
        "first_name", "last_name", "full_name", "name",
        "ip", "ip_address", "user_agent"
    }
    
    def __init__(
        self,
        redact_patterns: Optional[Set[str]] = None,
        redact_fields: Optional[Set[str]] = None,
        redaction_marker: str = "[REDACTED]",
        partial_redact: bool = False
    ):
        self._active_patterns = redact_patterns or set(self.PII_PATTERNS.keys())
        self._active_fields = redact_fields or self.PII_FIELD_NAMES
        self._marker = redaction_marker
        self._partial_redact = partial_redact
        
    def _partial_mask(self, value: str, pattern_type: str) -> str:
        """Create a partial mask showing some characters."""
        if pattern_type == "email":
            parts = value.split("@")
            if len(parts) == 2:
                local = parts[0]
                if len(local) > 2:
                    return f"{local[0]}***{local[-1]}@{parts[1]}"
        elif pattern_type == "phone":
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return f"***-***-{digits[-4:]}"
        elif pattern_type == "credit_card":
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return f"****-****-****-{digits[-4:]}"
        elif pattern_type == "ssn":
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return f"***-**-{digits[-4:]}"
        
        return self._marker
    
    def redact_string(self, text: str) -> str:
        """Redact PII patterns from a string."""
        result = text
        
        for pattern_name in self._active_patterns:
            pattern = self.PII_PATTERNS.get(pattern_name)
            if pattern:
                if self._partial_redact:
                    def replacer(match):
                        return self._partial_mask(match.group(0), pattern_name)
                    result = pattern.sub(replacer, result)
                else:
                    result = pattern.sub(self._marker, result)
        
        return result
    
    def redact_dict(self, data: Dict[str, Any], path: str = "") -> Dict[str, Any]:
        """
        Redact PII from a dictionary.
        
        Args:
            data: Dictionary to redact
            path: Current path (for logging)
            
        Returns:
            Redacted dictionary
        """
        result = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            if key_lower in self._active_fields or any(f in key_lower for f in self._active_fields):
                if isinstance(value, str):
                    result[key] = self._marker
                elif isinstance(value, dict):
                    result[key] = {k: self._marker for k in value}
                elif isinstance(value, list):
                    result[key] = [self._marker for _ in value]
                else:
                    result[key] = self._marker
            elif isinstance(value, dict):
                result[key] = self.redact_dict(value, f"{path}.{key}")
            elif isinstance(value, list):
                result[key] = [
                    self.redact_dict(item, f"{path}.{key}[]") if isinstance(item, dict)
                    else self.redact_string(str(item)) if isinstance(item, str)
                    else item
                    for item in value
                ]
            elif isinstance(value, str):
                result[key] = self.redact_string(value)
            else:
                result[key] = value
        
        return result
    
    def redact_response(self, response_data: Any) -> Any:
        """Redact PII from API response data."""
        if isinstance(response_data, dict):
            return self.redact_dict(response_data)
        elif isinstance(response_data, list):
            return [self.redact_response(item) for item in response_data]
        elif isinstance(response_data, str):
            return self.redact_string(response_data)
        return response_data


class ErrorSanitizer:
    """
    Sanitizes error responses to prevent information leakage.
    """
    
    SENSITIVE_ERROR_PATTERNS: List[Pattern] = [
        re.compile(r'at line \d+', re.IGNORECASE),
        re.compile(r'file ".*?"', re.IGNORECASE),
        re.compile(r'in .*?\.py', re.IGNORECASE),
        re.compile(r'traceback.*?:', re.IGNORECASE | re.DOTALL),
        re.compile(r'stack trace:', re.IGNORECASE),
        re.compile(r'/[a-z/]+/[a-z_]+\.py', re.IGNORECASE),
        re.compile(r'line \d+, in \w+', re.IGNORECASE),
        re.compile(r'password\s*=\s*[\'"][^\'"]+[\'"]', re.IGNORECASE),
        re.compile(r'connection string:.*', re.IGNORECASE),
        re.compile(r'database error:.*', re.IGNORECASE),
    ]
    
    GENERIC_ERROR_MESSAGES: Dict[int, str] = {
        400: "Invalid request",
        401: "Authentication required",
        403: "Access denied",
        404: "Resource not found",
        405: "Method not allowed",
        409: "Resource conflict",
        422: "Validation error",
        429: "Too many requests",
        500: "Internal server error",
        502: "Service temporarily unavailable",
        503: "Service temporarily unavailable",
        504: "Request timeout",
    }
    
    def __init__(
        self,
        debug_mode: bool = False,
        allowed_error_fields: Optional[Set[str]] = None,
        log_original_errors: bool = True
    ):
        self._debug_mode = debug_mode
        self._allowed_fields = allowed_error_fields or {"error", "message", "code", "request_id"}
        self._log_original = log_original_errors
        
    def _contains_sensitive_info(self, message: str) -> bool:
        """Check if message contains sensitive patterns."""
        for pattern in self.SENSITIVE_ERROR_PATTERNS:
            if pattern.search(message):
                return True
        return False
    
    def sanitize_error(
        self,
        error: Exception,
        status_code: int,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sanitize an error for client response.
        
        Args:
            error: The original exception
            status_code: HTTP status code
            request_id: Request correlation ID
            
        Returns:
            Sanitized error response
        """
        error_message = str(error)
        
        if self._log_original:
            logger.error(f"Original error (request_id={request_id}): {error_message}", exc_info=True)
        
        if self._debug_mode:
            return {
                "error": type(error).__name__,
                "message": error_message,
                "status_code": status_code,
                "request_id": request_id
            }
        
        if self._contains_sensitive_info(error_message):
            generic_message = self.GENERIC_ERROR_MESSAGES.get(
                status_code, "An error occurred"
            )
        else:
            generic_message = error_message
        
        response = {
            "error": self.GENERIC_ERROR_MESSAGES.get(status_code, "Error"),
            "message": generic_message,
            "status_code": status_code,
        }
        
        if request_id:
            response["request_id"] = request_id
        
        return response
    
    def sanitize_response(
        self,
        response_data: Dict[str, Any],
        status_code: int
    ) -> Dict[str, Any]:
        """Sanitize a complete error response."""
        if status_code < 400:
            return response_data
        
        if not self._debug_mode:
            result = {}
            for key, value in response_data.items():
                if key in self._allowed_fields:
                    if isinstance(value, str) and self._contains_sensitive_info(value):
                        result[key] = self.GENERIC_ERROR_MESSAGES.get(status_code, "Error")
                    else:
                        result[key] = value
            return result
        
        return response_data


class SecurityHeadersInjector:
    """
    Injects security headers into HTTP responses.
    """
    
    DEFAULT_HEADERS: Dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }
    
    CSP_DIRECTIVES: Dict[str, str] = {
        "default-src": "'self'",
        "script-src": "'self'",
        "style-src": "'self' 'unsafe-inline'",
        "img-src": "'self' data: https:",
        "font-src": "'self'",
        "connect-src": "'self'",
        "frame-ancestors": "'none'",
        "form-action": "'self'",
        "base-uri": "'self'",
    }
    
    def __init__(
        self,
        custom_headers: Optional[Dict[str, str]] = None,
        csp_enabled: bool = True,
        csp_report_only: bool = False,
        csp_report_uri: Optional[str] = None,
        cors_origins: Optional[List[str]] = None
    ):
        self._headers = {**self.DEFAULT_HEADERS, **(custom_headers or {})}
        self._csp_enabled = csp_enabled
        self._csp_report_only = csp_report_only
        self._csp_report_uri = csp_report_uri
        self._cors_origins = cors_origins or []
        self._csp_directives = self.CSP_DIRECTIVES.copy()
        
    def _build_csp(self) -> str:
        """Build Content-Security-Policy header value."""
        directives = []
        for directive, value in self._csp_directives.items():
            directives.append(f"{directive} {value}")
        
        if self._csp_report_uri:
            directives.append(f"report-uri {self._csp_report_uri}")
        
        return "; ".join(directives)
    
    def set_csp_directive(self, directive: str, value: str):
        """Set a CSP directive."""
        self._csp_directives[directive] = value
    
    def get_headers(
        self,
        request_origin: Optional[str] = None,
        include_cors: bool = True
    ) -> Dict[str, str]:
        """
        Get all security headers.
        
        Args:
            request_origin: Origin header from request
            include_cors: Whether to include CORS headers
            
        Returns:
            Dictionary of security headers
        """
        headers = self._headers.copy()
        
        if self._csp_enabled:
            csp_header = "Content-Security-Policy-Report-Only" if self._csp_report_only else "Content-Security-Policy"
            headers[csp_header] = self._build_csp()
        
        if include_cors and request_origin:
            if "*" in self._cors_origins:
                headers["Access-Control-Allow-Origin"] = "*"
            elif request_origin in self._cors_origins:
                headers["Access-Control-Allow-Origin"] = request_origin
                headers["Vary"] = "Origin"
            
            headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key, X-Request-ID"
            headers["Access-Control-Max-Age"] = "86400"
        
        return headers
    
    def inject(self, response_headers: Dict[str, str], request_origin: Optional[str] = None):
        """Inject security headers into an existing headers dict."""
        security_headers = self.get_headers(request_origin)
        response_headers.update(security_headers)


_response_signer: Optional[ResponseSigner] = None
_data_masker: Optional[SensitiveDataMasker] = None
_pii_redactor: Optional[PIIRedactor] = None
_error_sanitizer: Optional[ErrorSanitizer] = None
_security_headers: Optional[SecurityHeadersInjector] = None


def get_response_signer(secret_key: Optional[str] = None) -> ResponseSigner:
    """Get the response signer singleton."""
    global _response_signer
    if _response_signer is None:
        import secrets
        _response_signer = ResponseSigner(secret_key or secrets.token_hex(32))
    return _response_signer


def get_data_masker() -> SensitiveDataMasker:
    """Get the data masker singleton."""
    global _data_masker
    if _data_masker is None:
        _data_masker = SensitiveDataMasker()
    return _data_masker


def get_pii_redactor() -> PIIRedactor:
    """Get the PII redactor singleton."""
    global _pii_redactor
    if _pii_redactor is None:
        _pii_redactor = PIIRedactor()
    return _pii_redactor


def get_error_sanitizer(debug_mode: bool = False) -> ErrorSanitizer:
    """Get the error sanitizer singleton."""
    global _error_sanitizer
    if _error_sanitizer is None:
        _error_sanitizer = ErrorSanitizer(debug_mode=debug_mode)
    return _error_sanitizer


def get_security_headers_injector() -> SecurityHeadersInjector:
    """Get the security headers injector singleton."""
    global _security_headers
    if _security_headers is None:
        _security_headers = SecurityHeadersInjector()
    return _security_headers
