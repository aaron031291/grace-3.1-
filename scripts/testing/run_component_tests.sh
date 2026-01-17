#!/bin/bash
# Run comprehensive component tests with self-healing

echo "========================================"
echo "GRACE Comprehensive Component Tester"
echo "========================================"
echo ""
echo "This will test all 400+ components and send bugs to self-healing system."
echo ""

cd "$(dirname "$0")"
cd backend

python -m tests.comprehensive_component_tester --trust-level 3

if [ $? -ne 0 ]; then
    echo ""
    echo "Tests completed with failures. Check the report for details."
    exit 1
else
    echo ""
    echo "All tests passed!"
    exit 0
fi
