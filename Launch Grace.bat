@echo off
chcp 65001 >nul
title Grace 3.1 Launcher
echo.
echo  =============================================
echo   Grace 3.1 -- Starting Launcher
echo  =============================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

REM Navigate to Grace directory
cd /d "%~dp0"

echo [Grace] Launching...
echo [Grace] Browser will open automatically in 2 seconds.
echo [Grace] Close this window to stop the launcher.
echo.

python grace_launcher.py

pause
