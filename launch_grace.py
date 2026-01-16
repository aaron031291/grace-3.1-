#!/usr/bin/env python3
"""
Grace Launcher Entry Point
==========================
Simple entry point for launching Grace with the strict launcher.

Usage:
    python launch_grace.py
"""

import sys
from pathlib import Path

# Add launcher to path
launcher_dir = Path(__file__).parent / "launcher"
sys.path.insert(0, str(launcher_dir.parent))

from launcher.launcher import main

if __name__ == "__main__":
    main()
