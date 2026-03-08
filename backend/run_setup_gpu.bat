@echo off
REM Run GPU setup - use venv python directly (no activate.bat to avoid batch parser issues)
cd /d "%~dp0"
if exist "venv_gpu\Scripts\python.exe" (
    venv_gpu\Scripts\python.exe scripts\setup_gpu.py 2>nul
) else if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe scripts\setup_gpu.py 2>nul
) else (
    python scripts\setup_gpu.py 2>nul
)
