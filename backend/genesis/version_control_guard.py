"""
Version Control Guard - Enforces Genesis Key → Version Control pattern.

This guard ensures that:
1. Genesis Key is ALWAYS the first anchor
2. Version Control takes over after Genesis Key creation for file operations
3. This pattern is enforced throughout the system

Usage:
    from genesis.version_control_guard import enforce_version_control_pattern

    # This will warn (or raise in strict mode) if file operations
    # are not going through symbiotic version control
    enforce_version_control_pattern(
        operation_type="file_modify",
        file_path="/path/to/file.py",
        caller="my_function"
    )
"""

import logging
import warnings
from typing import Optional
from functools import wraps

logger = logging.getLogger(__name__)

# Set to True to raise exceptions instead of warnings
STRICT_MODE = False

# Track operations that bypass the proper pattern
_bypass_counter = {"count": 0, "callers": []}


def enforce_version_control_pattern(
    operation_type: str,
    file_path: Optional[str] = None,
    caller: str = "unknown",
    strict: Optional[bool] = None
) -> bool:
    """
    Enforce the Genesis Key → Version Control pattern.

    For file operations, this function checks that the caller is going
    through the proper symbiotic version control system.

    Args:
        operation_type: Type of operation (file_create, file_modify, file_delete, etc.)
        file_path: Path to file (if applicable)
        caller: Name of the calling function/module
        strict: Override global STRICT_MODE

    Returns:
        True if pattern is being followed correctly

    Raises:
        RuntimeError: In strict mode, if pattern is violated
    """
    is_strict = strict if strict is not None else STRICT_MODE

    # File operations MUST go through symbiotic version control
    file_operations = {"file_create", "file_modify", "file_delete", "file_operation"}

    if operation_type in file_operations:
        # Check if caller is from proper source
        proper_callers = {
            "symbiotic_version_control",
            "track_file_change",
            "pipeline_integration",
            "file_watcher",
            "git_genesis_bridge",
            "version_control_connector"
        }

        caller_is_proper = any(proper in caller.lower() for proper in proper_callers)

        if not caller_is_proper:
            _bypass_counter["count"] += 1
            _bypass_counter["callers"].append(caller)

            message = (
                f"[VERSION-CONTROL-GUARD] File operation '{operation_type}' from '{caller}' "
                f"should go through SymbioticVersionControl.track_file_change() "
                f"to maintain Genesis Key → Version Control chain. "
                f"File: {file_path or 'unknown'}"
            )

            if is_strict:
                logger.error(message)
                raise RuntimeError(message)
            else:
                logger.warning(message)
                warnings.warn(message, UserWarning, stacklevel=2)

            return False

    return True


def require_symbiotic_version_control(func):
    """
    Decorator that enforces symbiotic version control for file operations.

    Use this on functions that modify files to ensure they go through
    the proper Genesis Key → Version Control chain.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Try to extract file_path from arguments
        file_path = kwargs.get("file_path")
        if file_path is None and args:
            file_path = args[0] if isinstance(args[0], str) else None

        enforce_version_control_pattern(
            operation_type="file_operation",
            file_path=file_path,
            caller=f"{func.__module__}.{func.__name__}"
        )
        return func(*args, **kwargs)
    return wrapper


def get_bypass_stats() -> dict:
    """Get statistics about operations that bypassed proper pattern."""
    return {
        "total_bypasses": _bypass_counter["count"],
        "callers": list(set(_bypass_counter["callers"])),
        "unique_callers": len(set(_bypass_counter["callers"]))
    }


def reset_bypass_stats():
    """Reset bypass statistics."""
    _bypass_counter["count"] = 0
    _bypass_counter["callers"] = []


def set_strict_mode(enabled: bool):
    """Enable or disable strict mode globally."""
    global STRICT_MODE
    STRICT_MODE = enabled
    logger.info(f"[VERSION-CONTROL-GUARD] Strict mode {'enabled' if enabled else 'disabled'}")
