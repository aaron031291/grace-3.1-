@echo off
REM =============================================================================
REM GRACE Prerequisite Check (Windows)
REM =============================================================================
REM Verifies Python 3.11+, Node.js 20+, Docker, and optional Ollama
REM Usage: check_prerequisites.bat
REM =============================================================================

setlocal EnableDelayedExpansion
set "PASS=0"
set "FAIL=0"

echo.
echo ================================================================================
echo   GRACE Prerequisite Check
echo ================================================================================
echo.

REM ---------------------------------------------------------------------------
REM Python 3.11+
REM ---------------------------------------------------------------------------
echo [1/4] Checking Python 3.11+...
python --version 2>nul
if errorlevel 1 (
    echo   FAIL: Python not found. Install from https://www.python.org/downloads/
    set /a FAIL+=1
) else (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
    echo   Found: Python !PYVER!
    set /a PASS+=1
)
echo.

REM ---------------------------------------------------------------------------
REM Node.js 20+
REM ---------------------------------------------------------------------------
echo [2/4] Checking Node.js 20+...
node --version 2>nul
if errorlevel 1 (
    echo   FAIL: Node.js not found. Install from https://nodejs.org/
    set /a FAIL+=1
) else (
    for /f "tokens=1" %%v in ('node --version 2^>^&1') do set NODEVER=%%v
    echo   Found: Node !NODEVER!
    set /a PASS+=1
)
echo.

REM ---------------------------------------------------------------------------
REM Docker
REM ---------------------------------------------------------------------------
echo [3/4] Checking Docker...
docker --version 2>nul
if errorlevel 1 (
    echo   FAIL: Docker not found. Install from https://www.docker.com/
    set /a FAIL+=1
) else (
    for /f "tokens=3" %%v in ('docker --version 2^>^&1') do set DOCKERVER=%%v
    echo   Found: Docker !DOCKERVER!
    set /a PASS+=1
)
echo.

REM ---------------------------------------------------------------------------
REM Ollama (optional)
REM ---------------------------------------------------------------------------
echo [4/4] Checking Ollama (optional for chat)...
ollama --version 2>nul
if errorlevel 1 (
    echo   SKIP: Ollama not found. Optional - install from https://ollama.ai
) else (
    echo   Found: Ollama installed
)
echo.

REM ---------------------------------------------------------------------------
REM Summary
REM ---------------------------------------------------------------------------
echo ================================================================================
if %FAIL% gtr 0 (
    echo   Result: %FAIL% required check(s) failed. Fix above before running GRACE.
    echo ================================================================================
    exit /b 1
) else (
    echo   Result: All required prerequisites OK (%PASS%/3).
    echo ================================================================================
    exit /b 0
)
endlocal
