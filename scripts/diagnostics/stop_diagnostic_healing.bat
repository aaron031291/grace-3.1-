@echo off
REM Stop Diagnostic Engine and Self-Healing Agent

echo Stopping Diagnostic Engine and Self-Healing Agent...
echo.

REM Find Python processes running the diagnostic/healing script
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr /I "PID"') do (
    echo Checking process %%a...
    REM Note: This is a simple approach. For production, you'd want to check
    REM if the process is actually running our script, not just any Python process.
)

echo.
echo To stop all Python processes (WARNING: This will stop ALL Python scripts):
echo   taskkill /F /IM python.exe
echo.
echo For a safer approach, manually identify the process ID from:
echo   tasklist ^| findstr python
echo Then kill it with:
echo   taskkill /F /PID [process_id]
echo.

pause
