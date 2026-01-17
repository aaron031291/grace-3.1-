@echo off
REM Start GRACE with Watchdog Self-Healing System
REM This will monitor GRACE and automatically fix issues and restart if needed

echo ================================================================================
echo GRACE Watchdog Self-Healing System
echo ================================================================================
echo.
echo This watchdog will:
echo   - Monitor the main GRACE process
echo   - Start the frontend (Vite dev server)
echo   - Detect crashes and failures
echo   - Diagnose root causes
echo   - Apply automatic fixes
echo   - Restart the system when needed
echo.
echo The watchdog runs independently and can fix issues even if
echo the main runtime crashes completely.
echo.
echo Frontend will be available at: http://localhost:5173
echo Backend will be available at: http://localhost:8000
echo.
echo Press CTRL+C to stop the watchdog
echo ================================================================================
echo.

python start_watchdog.py

pause
