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

# Add project root to path so we can import launcher
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from launcher.launcher import main

if __name__ == "__main__":
    main()
