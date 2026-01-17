@echo off
REM Start Diagnostic Engine and Self-Healing Agent in Background
REM This script runs the diagnostic and healing systems as a background service

echo Starting Diagnostic Engine and Self-Healing Agent in background...
echo.

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Start Python script in background (detached window)
start "DiagnosticHealing" /MIN python run_diagnostic_and_healing.py

REM Wait a moment to see if it starts
timeout /t 2 /nobreak >nul

REM Check if process started
tasklist | findstr /I "python" >nul
if %errorlevel% == 0 (
    echo [OK] Diagnostic Engine and Self-Healing Agent started in background
    echo.
    echo Logs are being written to:
    echo   - logs\diagnostic_healing.log (main log)
    echo   - logs\diagnostic_healing_console.log (console output)
    echo.
    echo To check status, view the log files or run:
    echo   tasklist ^| findstr python
    echo.
    echo To stop, find the Python process and terminate it, or restart your system.
) else (
    echo [ERROR] Failed to start. Check logs\diagnostic_healing_console.log for errors.
)

pause
