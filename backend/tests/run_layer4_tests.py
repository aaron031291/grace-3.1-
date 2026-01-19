"""
Test runner for Layer 4 Action Router tests.
Bypasses conftest Unicode issues by running tests directly.
"""

import sys
import os
import warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set encoding to handle Unicode
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Suppress deprecation warnings from imported modules
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*datetime.utcnow.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="diagnostic_machine")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="cognitive")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="conftest")

import pytest

if __name__ == "__main__":
    # Run tests with minimal config and warning filters
    exit_code = pytest.main([
        __file__.replace('run_layer4_tests.py', 'test_layer4_action_router.py'),
        '-v',
        '--tb=short',
        '-p', 'no:cacheprovider',  # Disable problematic plugins
        '--override-ini=python_files=test_layer4_action_router.py',
        '--override-ini=python_classes=Test*',
        '--override-ini=python_functions=test_*',
        '-W', 'ignore::DeprecationWarning',  # Suppress all deprecation warnings
        '-W', 'ignore::pytest.PytestCollectionWarning',  # Suppress collection warnings
    ])
    sys.exit(exit_code)
