"""
Emoji Sanitization System
=========================

Automatically removes emojis from text to prevent encoding issues and improve debugging.

This is enforced throughout the system:
1. LLM outputs are sanitized automatically
2. Pre-commit hooks prevent emojis in code
3. All user-facing output is cleaned

Rationale:
- Emojis cause encoding errors on Windows (cp1252)
- Emojis complicate log parsing and debugging
- Emojis are purely cosmetic and add no functional value
- Removing them improves system reliability and maintainability
"""

import re
import logging
from typing import Any, Dict, List, Optional, Union
from functools import wraps

logger = logging.getLogger(__name__)

# Common emoji patterns (covers most Unicode emoji ranges)
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
    "\U0001F680-\U0001F6FF"  # Transport & Map
    "\U0001F1E0-\U0001F1FF"  # Flags (iOS)
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251"  # Enclosed characters
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002600-\U000026FF"  # Miscellaneous Symbols
    "\U00002700-\U000027BF"  # Dingbats
    "\U0001F018-\U0001F270"  # Various asian characters
    "\U0001F300-\U0001F5FF"  # Misc symbols
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F680-\U0001F6FF"  # Transport
    "\U0001F1E0-\U0001F1FF"  # Flags (iOS)
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols Extended-A
    "\u2600-\u26FF"  # Misc symbols
    "\u2700-\u27BF"  # Dingbats
    "✅❌⚠️✓✗📊🚀⚡💡🎯🔍📝🌟✨🔥💯"  # Common status emojis
    "]+",
    flags=re.UNICODE
)

# Emoji replacements for common status indicators
EMOJI_REPLACEMENTS = {
    '✅': '[OK]',
    '✓': '[OK]',
    '❌': '[ERROR]',
    '✗': '[FAIL]',
    '⚠️': '[WARN]',
    '⚠': '[WARN]',
    '📊': '[STATUS]',
    '🚀': '[START]',
    '⚡': '[FAST]',
    '💡': '[INFO]',
    '🎯': '[TARGET]',
    '🔍': '[SEARCH]',
    '📝': '[NOTE]',
    '🌟': '[IMPORTANT]',
    '✨': '[ENHANCED]',
    '🔥': '[HOT]',
    '💯': '[PERFECT]',
    '🔧': '[FIX]',
    '📁': '[FILE]',
    '📄': '[DOC]',
    '🔐': '[SECURE]',
    '🌐': '[WEB]',
    '💾': '[SAVE]',
    '📤': '[UPLOAD]',
    '📥': '[DOWNLOAD]',
    '🔔': '[NOTIFY]',
    '🎉': '[SUCCESS]',
    '💔': '[FAIL]',
    '⚙️': '[CONFIG]',
}


def remove_emojis(text: str, replace: bool = True) -> str:
    """
    Remove all emojis from text.
    
    Args:
        text: Input text that may contain emojis
        replace: If True, replace common emojis with text equivalents
        
    Returns:
        Text with emojis removed or replaced
    """
    if not isinstance(text, str):
        return text
    
    if replace:
        # First, try to replace known emojis with meaningful text
        for emoji, replacement in EMOJI_REPLACEMENTS.items():
            text = text.replace(emoji, replacement)
    
    # Remove any remaining emojis
    text = EMOJI_PATTERN.sub('', text)
    
    # Clean up multiple spaces that might result from removal
    text = re.sub(r' +', ' ', text).strip()
    
    return text


def sanitize_dict(data: Dict[str, Any], replace: bool = True) -> Dict[str, Any]:
    """
    Recursively sanitize all string values in a dictionary.
    
    Args:
        data: Dictionary that may contain emojis in string values
        replace: If True, replace common emojis with text equivalents
        
    Returns:
        Dictionary with all string values sanitized
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = remove_emojis(value, replace=replace)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, replace=replace)
        elif isinstance(value, list):
            sanitized[key] = sanitize_list(value, replace=replace)
        else:
            sanitized[key] = value
    
    return sanitized


def sanitize_list(data: List[Any], replace: bool = True) -> List[Any]:
    """
    Recursively sanitize all string values in a list.
    
    Args:
        data: List that may contain emojis in string values
        replace: If True, replace common emojis with text equivalents
        
    Returns:
        List with all string values sanitized
    """
    if not isinstance(data, list):
        return data
    
    sanitized = []
    for item in data:
        if isinstance(item, str):
            sanitized.append(remove_emojis(item, replace=replace))
        elif isinstance(item, dict):
            sanitized.append(sanitize_dict(item, replace=replace))
        elif isinstance(item, list):
            sanitized.append(sanitize_list(item, replace=replace))
        else:
            sanitized.append(item)
    
    return sanitized


def sanitize_llm_output(output: Union[str, Dict, List], replace: bool = True) -> Union[str, Dict, List]:
    """
    Sanitize LLM output to remove emojis.
    
    Handles various output formats:
    - String responses
    - JSON dictionaries
    - Lists
    - Nested structures
    
    Args:
        output: LLM output that may contain emojis
        replace: If True, replace common emojis with text equivalents
        
    Returns:
        Sanitized output without emojis
    """
    if isinstance(output, str):
        return remove_emojis(output, replace=replace)
    elif isinstance(output, dict):
        return sanitize_dict(output, replace=replace)
    elif isinstance(output, list):
        return sanitize_list(output, replace=replace)
    else:
        return output


def check_code_for_emojis(code: str, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Check code for emoji usage and return violations.
    
    Args:
        code: Source code to check
        file_path: Optional file path for reporting
        
    Returns:
        List of violations with line numbers and emojis found
    """
    violations = []
    lines = code.split('\n')
    
    for line_num, line in enumerate(lines, start=1):
        # Find emojis in this line
        emojis_found = EMOJI_PATTERN.findall(line)
        
        if emojis_found:
            # Skip comments and docstrings (allow emojis in comments if needed)
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                # Allow emojis in comments, but log them
                continue
            
            violations.append({
                'file': file_path or 'unknown',
                'line': line_num,
                'emojis': emojis_found,
                'code': line.strip()
            })
    
    return violations


def sanitize_decorator(replace: bool = True):
    """
    Decorator to automatically sanitize function return values.
    
    Usage:
        @sanitize_decorator()
        def my_llm_function():
            return "✅ Success!"  # Will return "[OK] Success!"
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            return sanitize_llm_output(result, replace=replace)
        return wrapper
    return decorator


def validate_no_emojis(text: str, context: str = "") -> bool:
    """
    Validate that text contains no emojis.
    
    Args:
        text: Text to validate
        context: Optional context for logging
        
    Returns:
        True if no emojis found, False otherwise
    """
    has_emojis = bool(EMOJI_PATTERN.search(text))
    
    if has_emojis:
        emojis_found = EMOJI_PATTERN.findall(text)
        logger.warning(
            f"Emojis detected in {context or 'text'}: {emojis_found}. "
            f"These will cause encoding issues. Use text equivalents instead."
        )
    
    return not has_emojis


# Export main function
__all__ = [
    'remove_emojis',
    'sanitize_dict',
    'sanitize_list',
    'sanitize_llm_output',
    'check_code_for_emojis',
    'sanitize_decorator',
    'validate_no_emojis',
    'EMOJI_PATTERN',
    'EMOJI_REPLACEMENTS',
]
