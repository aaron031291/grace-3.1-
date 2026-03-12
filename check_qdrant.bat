@echo off
REM Quick Qdrant connectivity check. Run from project root.
cd /d "%~dp0"
if exist "backend\scripts\check_qdrant.py" (
    set PYTHONPATH=%~dp0backend
    python backend\scripts\check_qdrant.py
) else (
    echo Run from GRACE project root. backend\scripts\check_qdrant.py not found.
    exit /b 1
)
