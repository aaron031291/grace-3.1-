"""Exit 0 if Python 3.11 or 3.12 (CUDA wheels), else 1. No args."""
import sys
v = sys.version_info
sys.exit(0 if (v.major == 3 and v.minor in (11, 12)) else 1)
