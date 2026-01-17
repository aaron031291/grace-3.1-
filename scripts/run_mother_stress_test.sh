#!/bin/bash
# Quick runner script for the Mother of All Stress Tests

echo "=========================================="
echo "MOTHER OF ALL STRESS TESTS"
echo "=========================================="
echo ""
echo "This will run comprehensive stress tests on:"
echo "  - System E2E functionality"
echo "  - Self-healing agent"
echo "  - Pipeline coding agent"
echo "  - Concurrent operations"
echo "  - Performance under load"
echo "  - Recovery capabilities"
echo ""
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

cd "$(dirname "$0")/.."
python scripts/mother_of_all_stress_tests.py
