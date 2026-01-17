"""
Quick test to verify diagnostic engine and self-healing can start
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

print("Testing imports...")

# Test diagnostic engine
try:
    from diagnostic_machine.diagnostic_engine import start_diagnostic_engine
    print("[OK] Diagnostic engine import OK")
except Exception as e:
    print(f"[ERROR] Diagnostic engine import failed: {e}")
    sys.exit(1)

# Test healing system
try:
    from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
    print("[OK] Self-healing system import OK")
except Exception as e:
    print(f"[ERROR] Self-healing system import failed: {e}")
    sys.exit(1)

# Test database
try:
    from database.config import DatabaseConfig
    from database.connection import DatabaseConnection
    from database.session import initialize_session_factory, get_db
    print("[OK] Database imports OK")
except Exception as e:
    print(f"✗ Database imports failed: {e}")
    sys.exit(1)

print("\nAll imports successful! Systems should be able to start.")
