#!/usr/bin/env python3
import pytest; pytest.importorskip("api.context_api", reason="api.context_api removed — consolidated into Brain API")
"""
Test script to verify multi-tier query intelligence imports.
"""

import sys
sys.path.insert(0, '/home/zair/Documents/grace/test/grace-3.1-/backend')

print("Testing imports...")

try:
    print("1. Importing BaseModel from database.base...")
    from database.base import BaseModel, Base
    print("   ✅ Success")
    
    print("2. Importing query intelligence models...")
    from models.query_intelligence_models import (
        QueryHandlingLog,
        KnowledgeGap,
        ContextSubmission
    )
    print("   ✅ Success")
    
    print("3. Importing MultiTierQueryHandler...")
    from retrieval.query_intelligence import (
        MultiTierQueryHandler,
        QueryTier,
        ConfidenceMetrics,
        KnowledgeGap as KGap,
        QueryResult
    )
    print("   ✅ Success")
    
    print("4. Importing context API...")
    from api.context_api import router
    print("   ✅ Success")
    
    print("\n✅ All imports successful!")
    print("\nModel classes:")
    print(f"  - QueryHandlingLog: {QueryHandlingLog}")
    print(f"  - KnowledgeGap: {KnowledgeGap}")
    print(f"  - ContextSubmission: {ContextSubmission}")
    print(f"\nBase classes:")
    print(f"  - Base: {Base}")
    print(f"  - BaseModel: {BaseModel}")
    
except ImportError as e:
    print(f"\n❌ Import Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Import test completed successfully!")
