@echo off
REM Start Continuous Stress Test Runner on Windows
REM This runs aggressive stress tests every 30 minutes

cd /d "%~dp0\..\.."
python backend\tests\continuous_stress_runner.py

pause
