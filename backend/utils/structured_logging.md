# Structured Logging

**File:** `utils/structured_logging.py`

## Overview

Structured Logging Configuration
================================
JSON-formatted logging for production environments.
Supports correlation IDs, context injection, and log levels.

## Classes

- `StructuredLogFormatter`
- `StructuredLogger`
- `LoggingMiddleware`

## Key Methods

- `format()`
- `info_with_context()`
- `error_with_context()`
- `warning_with_context()`
- `debug_with_context()`
- `setup_structured_logging()`
- `get_logger()`
- `set_request_context()`
- `clear_request_context()`
- `generate_request_id()`
- `log_function_call()`
- `decorator()`
- `log_async_function_call()`
- `decorator()`

---
*Grace 3.1*
