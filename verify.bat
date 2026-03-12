@echo off
REM =============================================================================
REM GRACE Verification Script (Windows)
REM =============================================================================
REM Checks backend health, Qdrant, and optionally frontend
REM Usage: verify.bat
REM =============================================================================

setlocal EnableDelayedExpansion
set "PASS=0"
set "FAIL=0"

set "GREEN=[92m"
set "RED=[91m"
set "CYAN=[96m"
set "YELLOW=[93m"
set "RESET=[0m"

echo.
echo %CYAN%===============================================================================%RESET%
echo %CYAN%   GRACE System Verification                                                      %RESET%
echo %CYAN%===============================================================================%RESET%
echo.

REM Backend health (port 8000)
echo [1/3] Backend API (http://localhost:8000/health)...
curl -s -o nul -w "%%{http_code}" http://localhost:8000/health 2>nul | findstr "200" >nul
if %errorlevel% equ 0 (
    echo   %GREEN%OK%RESET% Backend is running
    set /a PASS+=1
) else (
    echo   %RED%FAIL%RESET% Backend not responding. Start with: start.bat backend
    set /a FAIL+=1
)
echo.

REM Qdrant (port 6333)
echo [2/3] Qdrant (http://localhost:6333/health)...
curl -s -o nul -w "%%{http_code}" http://localhost:6333/health 2>nul | findstr "200" >nul
if %errorlevel% equ 0 (
    echo   %GREEN%OK%RESET% Qdrant is running
    set /a PASS+=1
) else (
    echo   %RED%FAIL%RESET% Qdrant not responding. Run: start.bat services (or use Qdrant Cloud in backend\.env)
    set /a FAIL+=1
)
echo.

REM Frontend (port 5173) - optional
echo [3/3] Frontend (http://localhost:5173)...
curl -s -o nul -w "%%{http_code}" http://localhost:5173 2>nul | findstr "200" >nul
if %errorlevel% equ 0 (
    echo   %GREEN%OK%RESET% Frontend is running
    set /a PASS+=1
) else (
    echo   %YELLOW%SKIP%RESET% Frontend not running. Start with: start.bat frontend
)
echo.

echo %CYAN%===============================================================================%RESET%
if %FAIL% gtr 0 (
    echo   %RED%Result: %FAIL% required check(s) failed.%RESET%
    echo   Backend and Qdrant are required for RAG. Start services and run verify again.
) else (
    echo   %GREEN%Result: Core services OK. Backend: http://localhost:8000  Docs: http://localhost:8000/docs%RESET%
)
echo %CYAN%===============================================================================%RESET%
echo.
endlocal
exit /b 0
