"""
Utility functions for the Librarian System.

Provides common helper functions used across librarian components.
"""

import re
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib
import json


def normalize_tag_name(tag_name: str) -> str:
    """
    Normalize tag name to lowercase with consistent formatting.

    Args:
        tag_name: Raw tag name

    Returns:
        str: Normalized tag name (lowercase, trimmed)

    Example:
        >>> normalize_tag_name("  AI Research  ")
        'ai research'
        >>> normalize_tag_name("Python-Code")
        'python-code'
    """
    return tag_name.strip().lower()


def validate_tag_name(tag_name: str) -> bool:
    """
    Validate that a tag name meets requirements.

    Requirements:
    - Length between 1 and 100 characters
    - Contains only alphanumeric, spaces, hyphens, underscores
    - No leading/trailing spaces after normalization

    Args:
        tag_name: Tag name to validate

    Returns:
        bool: True if valid, False otherwise

    Example:
        >>> validate_tag_name("ai-research")
        True
        >>> validate_tag_name("")
        False
        >>> validate_tag_name("tag with spaces")
        True
        >>> validate_tag_name("tag@invalid!")
        False
    """
    normalized = normalize_tag_name(tag_name)

    # Check length
    if not (1 <= len(normalized) <= 100):
        return False

    # Check allowed characters: alphanumeric, spaces, hyphens, underscores
    pattern = r'^[a-z0-9\s\-_]+$'
    return bool(re.match(pattern, normalized))


def validate_hex_color(color: str) -> bool:
    """
    Validate that a string is a valid hex color code.

    Args:
        color: Color string to validate (e.g., "#3B82F6")

    Returns:
        bool: True if valid hex color, False otherwise

    Example:
        >>> validate_hex_color("#3B82F6")
        True
        >>> validate_hex_color("#FFF")
        True
        >>> validate_hex_color("blue")
        False
        >>> validate_hex_color("#GGGGGG")
        False
    """
    # Match #RGB or #RRGGBB format
    pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
    return bool(re.match(pattern, color))


def generate_default_color(tag_name: str) -> str:
    """
    Generate a consistent color for a tag based on its name.

    Uses hash of tag name to generate a consistent color.
    This ensures the same tag always gets the same color.

    Args:
        tag_name: Tag name

    Returns:
        str: Hex color code

    Example:
        >>> color = generate_default_color("ai")
        >>> len(color)
        7
        >>> color.startswith("#")
        True
    """
    # Hash the tag name
    hash_obj = hashlib.md5(tag_name.encode())
    hash_hex = hash_obj.hexdigest()

    # Take first 6 characters for color
    color = f"#{hash_hex[:6]}"

    return color


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing or replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename safe for filesystem

    Example:
        >>> sanitize_filename("my file.txt")
        'my_file.txt'
        >>> sanitize_filename("file<>?.txt")
        'file.txt'
    """
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')

    # Remove invalid characters for most filesystems
    invalid_chars = r'[<>:"/\\|?*]'
    filename = re.sub(invalid_chars, '', filename)

    return filename


def format_confidence_score(score: float) -> str:
    """
    Format confidence score as percentage string.

    Args:
        score: Confidence score (0.0-1.0)

    Returns:
        str: Formatted percentage (e.g., "85%")

    Example:
        >>> format_confidence_score(0.856)
        '86%'
        >>> format_confidence_score(0.5)
        '50%'
    """
    percentage = round(score * 100)
    return f"{percentage}%"


def parse_confidence_label(label: str) -> float:
    """
    Parse confidence label to numeric score.

    Args:
        label: Confidence label ("low", "medium", "high")

    Returns:
        float: Numeric confidence score

    Example:
        >>> parse_confidence_label("high")
        0.9
        >>> parse_confidence_label("medium")
        0.7
        >>> parse_confidence_label("low")
        0.4
    """
    label_map = {
        "low": 0.4,
        "medium": 0.7,
        "high": 0.9
    }
    return label_map.get(label.lower(), 0.5)


def extract_file_extension(filename: str) -> Optional[str]:
    """
    Extract file extension from filename.

    Args:
        filename: File name or path

    Returns:
        Optional[str]: Extension without dot (e.g., "pdf") or None

    Example:
        >>> extract_file_extension("document.pdf")
        'pdf'
        >>> extract_file_extension("archive.tar.gz")
        'gz'
        >>> extract_file_extension("README")
        None
    """
    if '.' not in filename:
        return None

    return filename.rsplit('.', 1)[-1].lower()


def match_pattern(text: str, pattern: str, case_sensitive: bool = False) -> bool:
    """
    Check if text matches regex pattern.

    Args:
        text: Text to match against
        pattern: Regex pattern
        case_sensitive: Whether to use case-sensitive matching

    Returns:
        bool: True if pattern matches, False otherwise

    Example:
        >>> match_pattern("document.pdf", r"\\.pdf$", case_sensitive=False)
        True
        >>> match_pattern("README.md", r"^README", case_sensitive=True)
        True
        >>> match_pattern("readme.md", r"^README", case_sensitive=True)
        False
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        return bool(re.search(pattern, text, flags))
    except re.error:
        # Invalid regex pattern
        return False


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to append if truncated

    Returns:
        str: Truncated text

    Example:
        >>> truncate_text("This is a very long text", max_length=15)
        'This is a ve...'
        >>> truncate_text("Short", max_length=20)
        'Short'
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def safe_json_dumps(obj: Any, default: Any = None) -> str:
    """
    Safely serialize object to JSON string.

    Handles non-serializable types like datetime.

    Args:
        obj: Object to serialize
        default: Default value for non-serializable types

    Returns:
        str: JSON string

    Example:
        >>> result = safe_json_dumps({"date": datetime(2024, 1, 1)})
        >>> "2024-01-01" in result
        True
    """
    def json_default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        if hasattr(o, '__dict__'):
            return o.__dict__
        return default if default is not None else str(o)

    return json.dumps(obj, default=json_default)


def safe_json_loads(json_string: str, default: Any = None) -> Any:
    """
    Safely deserialize JSON string.

    Args:
        json_string: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Any: Parsed object or default

    Example:
        >>> safe_json_loads('{"key": "value"}')
        {'key': 'value'}
        >>> safe_json_loads('invalid json', default={})
        {}
    """
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}


def deduplicate_list(items: List[Any]) -> List[Any]:
    """
    Remove duplicates from list while preserving order.

    Args:
        items: List with potential duplicates

    Returns:
        List: List with duplicates removed

    Example:
        >>> deduplicate_list([1, 2, 2, 3, 1, 4])
        [1, 2, 3, 4]
        >>> deduplicate_list(["a", "b", "a", "c"])
        ['a', 'b', 'c']
    """
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def calculate_similarity_score(text1: str, text2: str) -> float:
    """
    Calculate simple similarity score between two texts.

    Uses Jaccard similarity on word sets.

    Args:
        text1: First text
        text2: Second text

    Returns:
        float: Similarity score (0.0-1.0)

    Example:
        >>> calculate_similarity_score("hello world", "hello there")
        0.3333333333333333
        >>> calculate_similarity_score("same", "same")
        1.0
    """
    # Normalize and split into words
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return 0.0

    # Jaccard similarity
    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return intersection / union if union > 0 else 0.0


def batch_items(items: List[Any], batch_size: int = 100) -> List[List[Any]]:
    """
    Split list into batches of specified size.

    Args:
        items: List to batch
        batch_size: Size of each batch

    Returns:
        List[List]: List of batches

    Example:
        >>> batch_items([1, 2, 3, 4, 5], batch_size=2)
        [[1, 2], [3, 4], [5]]
    """
    batches = []
    for i in range(0, len(items), batch_size):
        batches.append(items[i:i + batch_size])
    return batches
