#!/bin/bash
# =============================================================================
# GRACE deterministic build verification (Unix/Mac/WSL)
# =============================================================================
# On Windows PowerShell: use verify_built.bat or verify_built.ps1 instead.
# Runs scripts/verify_built.py to verify every built artifact in a fixed order.
# Writes verification_manifest.json with timestamp and results.
# Exit code 0 only if all required checks pass.
# Usage: ./verify_built.sh
# =============================================================================

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
exec python3 scripts/verify_built.py "$@"
