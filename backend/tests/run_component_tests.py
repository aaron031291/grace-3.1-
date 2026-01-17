"""
Quick runner script for comprehensive component testing.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.comprehensive_component_tester import main

if __name__ == "__main__":
    main()
