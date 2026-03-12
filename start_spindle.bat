@echo off
setlocal EnableDelayedExpansion
REM =============================================================================
REM SPINDLE DAEMON - Autonomous Parallel Runtime
REM This script launches Spindle in a decoupled environment.
REM Spindle bounds-checks itself and connects to Grace via ZeroMQ.
REM =============================================================================

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"

echo.
echo ===============================================================================
echo    SPINDLE AUTONOMOUS DAEMON
echo ===============================================================================
echo.

cd /d "%BACKEND%"
if exist "venv_gpu\Scripts\activate.bat" (
    call venv_gpu\Scripts\activate.bat
    echo Spindle GPU venv activated.
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo Spindle CPU venv activated.
) else (
    echo [ERROR] Backend venv not found. Run setup_backend.bat first.
    pause
    exit /b 1
)
echo.
echo Launching Spindle Peer Process...
python spindle_daemon.py
pause
