#!/usr/bin/env python3
"""
Quick Start Script for Sandbox Practice

Simple launcher for sandbox practice sessions.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from scripts.sandbox_practice_healing_and_coding import run_practice_scenarios

if __name__ == "__main__":
    print("\n🚀 Starting Sandbox Practice Session...\n")
    run_practice_scenarios()
