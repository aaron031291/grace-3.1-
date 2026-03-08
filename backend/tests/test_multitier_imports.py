#!/usr/bin/env python3
"""
Test script to verify multi-tier query intelligence imports.
"""
import sys
from pathlib import Path

# Ensure backend is on path (portable)
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def test_multitier_imports():
    """Verify multi-tier query intelligence and related imports."""
    from database.base import BaseModel, Base
    from models.query_intelligence_models import (
        QueryHandlingLog,
        KnowledgeGap,
        ContextSubmission,
    )
    from retrieval.query_intelligence import (
        MultiTierQueryHandler,
        QueryTier,
        ConfidenceMetrics,
        QueryResult,
    )
    from api.context_api import router

    assert QueryHandlingLog is not None
    assert KnowledgeGap is not None
    assert ContextSubmission is not None
    assert MultiTierQueryHandler is not None
    assert router is not None
