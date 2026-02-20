# Validators

**File:** `security/validators.py`

## Overview

Input Validation and Sanitization for GRACE

Provides secure input handling to prevent:
- XSS attacks
- SQL injection
- Path traversal
- Command injection

## Classes

- `InputValidator`

## Key Methods

- `validate_string()`
- `validate_path()`
- `validate_filename()`
- `validate_email()`
- `validate_url()`
- `validate_json_input()`
- `get_validator()`
- `sanitize_input()`
- `validate_file_path()`

---
*Grace 3.1*
