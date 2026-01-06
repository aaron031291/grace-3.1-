@echo off
REM Master migration script for GRACE database (Windows)
REM This script runs all migrations in the correct order

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%"

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║        GRACE DATABASE MIGRATION SCRIPT                      ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python is not installed or not in PATH.
    echo   Please install Python 3.10 or higher and add it to PATH.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo Using Python: %PYTHON_VERSION%
echo Working directory: %BACKEND_DIR%
echo.

cd /d "%BACKEND_DIR%"

REM Run the Python migration script
echo ════════════════════════════════════════════════════════════
echo Starting migrations...
echo ════════════════════════════════════════════════════════════
echo.

python run_all_migrations.py

set EXIT_CODE=%errorlevel%

if %EXIT_CODE% equ 0 (
    echo.
    echo ════════════════════════════════════════════════════════════
    echo ✓ All migrations completed successfully!
    echo ════════════════════════════════════════════════════════════
    echo.
    echo Your database is ready for use.
) else (
    echo.
    echo ════════════════════════════════════════════════════════════
    echo ✗ Migration script exited with errors.
    echo ════════════════════════════════════════════════════════════
)

REM Keep the window open so user can see the output
pause

exit /b %EXIT_CODE%
