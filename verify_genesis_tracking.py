"""
Genesis Key Tracking Verification Script

Tests and verifies what's actually being tracked in real-time.
Checks for the missing 5% gaps.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, UTC, timedelta

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from database.session import initialize_session_factory, get_db
from models.genesis_key_models import GenesisKey, GenesisKeyType, GenesisKeyStatus
from sqlalchemy import func, and_, or_

def verify_tracking():
    """Verify what's actually being tracked."""
    print("=" * 80)
    print("GENESIS KEY TRACKING VERIFICATION")
    print("=" * 80)
    print()
    
    # Initialize database
    try:
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="backend/data/grace.db"
        )
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())
        print("[OK] Database connected")
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return
    
    try:
        # Get recent Genesis Keys (last 24 hours)
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        
        try:
            recent_keys = session.query(GenesisKey).filter(
                GenesisKey.when_timestamp >= cutoff
            ).all()
        except Exception as e:
            # Database may not have new columns yet - try without them
            print(f"[WARN] Database schema may need migration: {e}")
            print("      Attempting basic query...")
            try:
                recent_keys = session.query(GenesisKey).limit(100).all()
                print(f"[OK] Retrieved {len(recent_keys)} keys (limited query)")
            except Exception as e2:
                print(f"[ERROR] Cannot query database: {e2}")
                return
        
        total_recent = len(recent_keys)
        print(f"\n[INFO] Recent Genesis Keys (last 24 hours): {total_recent}")
        print()
        
        # Count by type
        print("[INFO] Breakdown by Type:")
        print("-" * 80)
        
        type_counts = {}
        for key in recent_keys:
            key_type = key.key_type.value if hasattr(key.key_type, 'value') else str(key.key_type)
            type_counts[key_type] = type_counts.get(key_type, 0) + 1
        
        for key_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_recent * 100) if total_recent > 0 else 0
            print(f"  {key_type:30s} {count:5d} ({percentage:5.1f}%)")
        
        print()
        
        # Check for WebSocket tracking
        print("[CHECK] Checking for WebSocket Tracking:")
        print("-" * 80)
        websocket_keys = session.query(GenesisKey).filter(
            GenesisKey.when_timestamp >= cutoff,
            GenesisKey.tags.contains('websocket')
        ).all()
        
        if websocket_keys:
            print(f"  [OK] WebSocket events tracked: {len(websocket_keys)}")
        else:
            print(f"  [GAP] WebSocket events NOT tracked (GAP #1)")
            print(f"     Expected: WebSocket connections, messages, voice events")
        
        # Check for scheduled task tracking
        print("\n[CHECK] Checking for Scheduled Task Tracking:")
        print("-" * 80)
        scheduled_keys = session.query(GenesisKey).filter(
            GenesisKey.when_timestamp >= cutoff,
            or_(
                GenesisKey.tags.contains('scheduled'),
                GenesisKey.tags.contains('curation'),
                GenesisKey.tags.contains('archival'),
                GenesisKey.what_description.like('%scheduled%'),
                GenesisKey.what_description.like('%curation%'),
                GenesisKey.what_description.like('%archival%')
            )
        ).all()
        
        if scheduled_keys:
            print(f"  [OK] Scheduled tasks tracked: {len(scheduled_keys)}")
            for key in scheduled_keys[:3]:
                print(f"     - {key.what_description[:60]}")
        else:
            print(f"  [GAP] Scheduled tasks NOT tracked (GAP #2)")
            print(f"     Expected: Daily curation, archival tasks")
        
        # Check for background thread tracking
        print("\n[CHECK] Checking for Background Thread Tracking:")
        print("-" * 80)
        thread_keys = session.query(GenesisKey).filter(
            GenesisKey.when_timestamp >= cutoff,
            or_(
                GenesisKey.tags.contains('thread'),
                GenesisKey.tags.contains('background'),
                GenesisKey.what_description.like('%thread%'),
                GenesisKey.what_description.like('%background%')
            )
        ).all()
        
        if thread_keys:
            print(f"  [OK] Background threads tracked: {len(thread_keys)}")
            for key in thread_keys[:3]:
                print(f"     - {key.what_description[:60]}")
        else:
            print(f"  [GAP] Background threads NOT tracked (GAP #3)")
            print(f"     Expected: File watcher, health monitor, mirror analysis threads")
        
        # Check for orchestrator cycles
        print("\n[CHECK] Checking for Orchestrator Cycle Tracking:")
        print("-" * 80)
        orchestrator_keys = session.query(GenesisKey).filter(
            GenesisKey.when_timestamp >= cutoff,
            or_(
                GenesisKey.tags.contains('orchestrator'),
                GenesisKey.tags.contains('cycle'),
                GenesisKey.what_description.like('%orchestration%'),
                GenesisKey.what_description.like('%cycle%')
            )
        ).all()
        
        if orchestrator_keys:
            print(f"  [OK] Orchestrator cycles tracked: {len(orchestrator_keys)}")
        else:
            print(f"  [WARN] Orchestrator cycles NOT tracked (GAP #5)")
            print(f"     Note: Learning operations are tracked, but cycles may not be")
        
        # Check intent verification fields
        print("\n[CHECK] Checking Intent Verification Fields:")
        print("-" * 80)
        
        try:
            with_intent = session.query(GenesisKey).filter(
                GenesisKey.when_timestamp >= cutoff,
                GenesisKey.change_origin.isnot(None)
            ).count()
            
            without_intent = session.query(GenesisKey).filter(
                GenesisKey.when_timestamp >= cutoff,
                GenesisKey.change_origin.is_(None)
            ).count()
        except Exception as e:
            print(f"  [WARN] Intent verification fields not in database yet (migration needed)")
            print(f"         Error: {e}")
            with_intent = 0
            without_intent = len(recent_keys)
        
        total = with_intent + without_intent
        intent_percentage = (with_intent / total * 100) if total > 0 else 0
        
        print(f"  Keys with intent verification: {with_intent} ({intent_percentage:.1f}%)")
        print(f"  Keys without intent verification: {without_intent} ({100-intent_percentage:.1f}%)")
        
        if with_intent > 0:
            print(f"  [OK] Intent verification fields in use")
        else:
            print(f"  [WARN] Intent verification fields not yet used (new feature)")
        
        # Check state machine versioning
        print("\n[CHECK] Checking State Machine Versioning:")
        print("-" * 80)
        
        try:
            with_version = session.query(GenesisKey).filter(
                GenesisKey.when_timestamp >= cutoff,
                GenesisKey.genesis_version.isnot(None)
            ).count()
            
            print(f"  Keys with version numbers: {with_version}")
            
            if with_version > 0:
                print(f"  [OK] State machine versioning in use")
                # Get version range
                max_version = session.query(func.max(GenesisKey.genesis_version)).filter(
                    GenesisKey.genesis_version.isnot(None)
                ).scalar()
                print(f"  Current Genesis version: {max_version}")
            else:
                print(f"  [WARN] State machine versioning not yet used (new feature)")
        except Exception as e:
            print(f"  [WARN] State machine versioning fields not in database yet (migration needed)")
            with_version = 0
        
        # Check capability binding
        print("\n[CHECK] Checking Capability Binding:")
        print("-" * 80)
        
        try:
            with_capabilities = session.query(GenesisKey).filter(
                GenesisKey.when_timestamp >= cutoff,
                GenesisKey.required_capabilities.isnot(None)
            ).count()
            
            print(f"  Keys with capability requirements: {with_capabilities}")
            
            if with_capabilities > 0:
                print(f"  [OK] Capability binding in use")
            else:
                print(f"  [WARN] Capability binding not yet used (new feature)")
        except Exception as e:
            print(f"  [WARN] Capability binding fields not in database yet (migration needed)")
            with_capabilities = 0
        
        # Summary
        print("\n" + "=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)
        print()
        
        gaps_found = []
        
        if not websocket_keys:
            gaps_found.append("WebSocket Events (2%)")
        
        if not scheduled_keys:
            gaps_found.append("Scheduled Tasks (1.5%)")
        
        if not thread_keys:
            gaps_found.append("Background Threads (1%)")
        
        if not orchestrator_keys:
            gaps_found.append("Orchestrator Cycles (0.5%)")
        
        if gaps_found:
            print(f"[GAPS] FOUND: {len(gaps_found)}")
            for gap in gaps_found:
                print(f"   - {gap}")
        else:
            print("[OK] NO GAPS FOUND - All areas tracked!")
        
        print()
        print(f"[STATS] Total Keys Tracked (24h): {total_recent}")
        print(f"[STATS] Keys with Intent Verification: {with_intent}")
        print(f"[STATS] Keys with State Machine Versioning: {with_version}")
        print(f"[STATS] Keys with Capability Binding: {with_capabilities}")
        
        # Coverage estimate
        if total_recent > 0:
            coverage = ((total_recent - len(gaps_found) * 10) / total_recent * 100) if gaps_found else 100
            print()
            print(f"[STATS] Estimated Coverage: {coverage:.1f}%")
        
    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    verify_tracking()
