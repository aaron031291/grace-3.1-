@echo off
REM =============================================================================
REM GRACE Frontend Setup (Windows)
REM =============================================================================
REM Installs npm dependencies
REM Usage: setup_frontend.bat
REM =============================================================================

setlocal
set "ROOT_DIR=%~dp0"
set "FRONTEND_DIR=%ROOT_DIR%frontend"

set "GREEN=[92m"
set "RED=[91m"
set "CYAN=[96m"
set "RESET=[0m"

echo.
echo %CYAN%===============================================================================%RESET%
echo %CYAN%   GRACE Frontend Setup                                                          %RESET%
echo %CYAN%===============================================================================%RESET%
echo.

cd /d "%FRONTEND_DIR%"
if not exist "package.json" (
    echo %RED%Error: frontend\package.json not found.%RESET%
    exit /b 1
)

echo %GREEN%Installing dependencies (npm install)...%RESET%
npm install
if errorlevel 1 (
    echo %RED%npm install failed.%RESET%
    exit /b 1
)

echo.
echo %CYAN%===============================================================================%RESET%
echo %GREEN%   Frontend setup complete. Run: start.bat frontend  (or start.bat for both)%RESET%
echo %CYAN%===============================================================================%RESET%
echo.
endlocal
exit /b 0
