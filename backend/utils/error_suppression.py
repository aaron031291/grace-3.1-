"""
Utility to check if error logging should be suppressed based on settings.
"""
try:
    from settings import settings
except ImportError:
    settings = None


def should_suppress_genesis_error() -> bool:
    """Check if Genesis errors should be suppressed."""
    return settings and settings.SUPPRESS_GENESIS_ERRORS


def should_suppress_qdrant_error() -> bool:
    """Check if Qdrant errors should be suppressed."""
    return settings and settings.SUPPRESS_QDRANT_ERRORS


def should_suppress_ingestion_error() -> bool:
    """Check if ingestion errors should be suppressed."""
    return settings and settings.SUPPRESS_INGESTION_ERRORS


def should_suppress_embedding_error() -> bool:
    """Check if embedding errors should be suppressed."""
    return settings and settings.SUPPRESS_EMBEDDING_ERRORS
