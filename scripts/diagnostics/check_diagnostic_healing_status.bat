@echo off
REM Check status of Diagnostic Engine and Self-Healing Agent

echo ========================================
echo Diagnostic Engine and Self-Healing Status
echo ========================================
echo.

REM Check if Python processes are running
echo [Checking Python processes...]
tasklist | findstr /I "python.exe" >nul
if %errorlevel% == 0 (
    echo [OK] Python processes are running:
    tasklist | findstr /I "python.exe"
) else (
    echo [WARNING] No Python processes found
)
echo.

REM Check log file
if exist "logs\diagnostic_healing.log" (
    echo [OK] Log file exists: logs\diagnostic_healing.log
    echo.
    echo Last 10 lines of log:
    echo ----------------------------------------
    powershell -Command "Get-Content logs\diagnostic_healing.log -Tail 10"
    echo ----------------------------------------
) else (
    echo [WARNING] Log file not found: logs\diagnostic_healing.log
)
echo.

REM Check console log
if exist "logs\diagnostic_healing_console.log" (
    echo [OK] Console log exists: logs\diagnostic_healing_console.log
    echo Last 5 lines:
    echo ----------------------------------------
    powershell -Command "Get-Content logs\diagnostic_healing_console.log -Tail 5"
    echo ----------------------------------------
) else (
    echo [INFO] Console log not found (may be running in background)
)
echo.

pause
