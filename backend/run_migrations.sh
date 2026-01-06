#!/bin/bash
# Master migration script for GRACE database
# This script runs all migrations in the correct order

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║        GRACE DATABASE MIGRATION SCRIPT                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 is not installed. Please install Python 3.10 or higher."
    exit 1
fi

echo "Using Python: $(python3 --version)"
echo "Working directory: $BACKEND_DIR"
echo ""

cd "$BACKEND_DIR"

# Run the Python migration script
echo "════════════════════════════════════════════════════════════"
echo "Starting migrations..."
echo "════════════════════════════════════════════════════════════"
echo ""

python3 run_all_migrations.py

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "✓ All migrations completed successfully!"
    echo "════════════════════════════════════════════════════════════"
else
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "✗ Migration script exited with errors."
    echo "════════════════════════════════════════════════════════════"
fi

exit $EXIT_CODE
