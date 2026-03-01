"""
API routers module.

NOTE: Do NOT import heavy modules here. This file is loaded by every
api.* import. Previously it imported api.ingest which loaded embedding,
vector_db, ingestion — causing ALL optional API imports to fail if
any of those heavy dependencies were missing.
"""

# Lazy import only — don't block the package
def get_ingest_router():
    from .ingest import router as ingest_router
    return ingest_router

__all__ = ["get_ingest_router"]
