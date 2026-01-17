"""
Safe Print Utility
==================
Print function that safely handles Unicode characters on Windows console.

Uses OS adapter for portable Unicode handling.
"""

import sys
from .os_adapter import OS, OSType


def safe_print(*args, **kwargs):
    """
    Print that safely handles Unicode on Windows console.
    
    Replaces Unicode characters that can't be encoded in cp1252 with ASCII equivalents.
    Uses OS adapter to detect console capabilities.
    """
    console_encoding = OSType.detect_console_encoding()
    
    if OS.is_windows and console_encoding.lower() in ["cp1252", "cp437", "latin1"]:
        # Replace Unicode characters with ASCII equivalents
        def sanitize(text):
            if isinstance(text, str):
                replacements = {
                    '✓': '[OK]',
                    '✗': '[FAIL]',
                    '⚠': '[WARN]',
                    '✅': '[OK]',
                    '❌': '[ERROR]',
                    '🔧': '[FIX]',
                    '→': '->',
                    '—': '-',
                    '–': '-',
                }
                for unicode_char, ascii_replacement in replacements.items():
                    text = text.replace(unicode_char, ascii_replacement)
            return text
        
        # Sanitize all arguments
        sanitized_args = [sanitize(arg) for arg in args]
        print(*sanitized_args, **kwargs)
    else:
        # On non-Windows or UTF-8 capable terminals, print normally
        print(*args, **kwargs)


def safe_format(text: str) -> str:
    """
    Safely format text by replacing Unicode characters with ASCII equivalents.
    Uses OS adapter to detect console capabilities.
    """
    console_encoding = OSType.detect_console_encoding()
    
    if OS.is_windows and console_encoding.lower() in ["cp1252", "cp437", "latin1"]:
        replacements = {
            '✓': '[OK]',
            '✗': '[FAIL]',
            '⚠': '[WARN]',
            '✅': '[OK]',
            '❌': '[ERROR]',
            '🔧': '[FIX]',
            '→': '->',
            '—': '-',
            '–': '-',
        }
        for unicode_char, ascii_replacement in replacements.items():
            text = text.replace(unicode_char, ascii_replacement)
    return text
