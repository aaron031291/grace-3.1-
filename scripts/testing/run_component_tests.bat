@echo off
REM Run comprehensive component tests with self-healing

echo ========================================
echo GRACE Comprehensive Component Tester
echo ========================================
echo.
echo This will test all 400+ components and send bugs to self-healing system.
echo.

cd /d "%~dp0"
cd backend

python -m tests.comprehensive_component_tester --trust-level 3

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Tests completed with failures. Check the report for details.
    pause
    exit /b 1
) else (
    echo.
    echo All tests passed!
    pause
    exit /b 0
)
