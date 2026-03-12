@echo off
REM =============================================================================
REM GRACE Backend Setup (Windows)
REM =============================================================================
REM Creates venv, installs deps, copies .env, runs migrations
REM Usage: setup_backend.bat
REM =============================================================================

setlocal EnableDelayedExpansion
set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"

echo.
echo ===============================================================================
echo    GRACE Backend Setup
echo ===============================================================================
echo.

cd /d "%BACKEND_DIR%"
if not exist "requirements.txt" (
    echo Error: backend\requirements.txt not found.
    exit /b 1
)

REM 1. Virtual environment
echo [1/4] Virtual environment...
if not exist "venv" (
    python -m venv venv
    echo   Created venv
) else (
    echo   venv already exists
)
call venv\Scripts\activate.bat

REM 2. Dependencies
echo.
echo [2/4] Installing dependencies (pip install -r requirements.txt)...
pip install -r requirements.txt
if errorlevel 1 (
    echo pip install failed.
    exit /b 1
)

REM 3. Environment file
echo.
echo [3/4] Environment config...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo   Created .env from .env.example
    ) else (
        echo   Warning: .env.example not found. Create .env manually.
    )
) else (
    echo   .env already exists
)

REM 4. Migrations
echo.
echo [4/4] Database migrations...
python run_all_migrations.py
if errorlevel 1 (
    echo Migrations failed.
    exit /b 1
)

echo.
echo ===============================================================================
echo    Backend setup complete.
echo    To start:  .\start.bat backend   (in PowerShell)
echo    Or:       start.bat backend     (in CMD)
echo ===============================================================================
echo.
endlocal
exit /b 0
