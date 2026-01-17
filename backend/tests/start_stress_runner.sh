#!/bin/bash
# Start Continuous Stress Test Runner on Linux/Mac
# This runs aggressive stress tests every 30 minutes

cd "$(dirname "$0")/../.."
python3 backend/tests/continuous_stress_runner.py
