@echo off
REM =============================================================================
REM GRACE Unified Start Script (Windows)
REM =============================================================================
REM Starts both backend (FastAPI) and frontend (Vite) servers
REM Usage: start.bat [backend|frontend|all]
REM Default: all (starts both)
REM =============================================================================

setlocal EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "MODE=%~1"

if "%MODE%"=="" set "MODE=all"

REM Colors for output (Windows 10+)
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "CYAN=[96m"
set "RESET=[0m"

echo %CYAN%==============================================================================%RESET%
echo %CYAN%                         GRACE System Startup                                %RESET%
echo %CYAN%==============================================================================%RESET%
echo.

REM Validate mode
if /i not "%MODE%"=="all" if /i not "%MODE%"=="backend" if /i not "%MODE%"=="frontend" (
    echo %RED%Invalid mode: %MODE%%RESET%
    echo Usage: start.bat [backend^|frontend^|all]
    exit /b 1
)

REM =============================================================================
REM Backend startup function
REM =============================================================================
if /i "%MODE%"=="backend" goto :start_backend
if /i "%MODE%"=="all" goto :start_all
if /i "%MODE%"=="frontend" goto :start_frontend_only

:start_all
echo %YELLOW%Starting GRACE in full-stack mode...%RESET%
echo.

REM Start backend in a new window
echo %GREEN%[1/2] Starting Backend (FastAPI)...%RESET%
start "GRACE Backend" cmd /k "cd /d %BACKEND_DIR% && call venv\Scripts\activate.bat && echo Backend server starting on http://localhost:8000 && python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000"

REM Wait a moment for backend to initialize
timeout /t 3 /nobreak > nul

REM Start frontend in a new window
echo %GREEN%[2/2] Starting Frontend (Vite)...%RESET%
start "GRACE Frontend" cmd /k "cd /d %FRONTEND_DIR% && echo Frontend server starting on http://localhost:5173 && npm run dev"

echo.
echo %CYAN%==============================================================================%RESET%
echo %GREEN%GRACE System Started Successfully!%RESET%
echo %CYAN%==============================================================================%RESET%
echo.
echo   Backend API:  http://localhost:8000
echo   Frontend UI:  http://localhost:5173
echo   API Docs:     http://localhost:8000/docs
echo.
echo %YELLOW%Note: Each service runs in its own window. Close windows to stop services.%RESET%
echo.
goto :eof

:start_backend
echo %GREEN%Starting Backend only (FastAPI)...%RESET%
cd /d %BACKEND_DIR%
call venv\Scripts\activate.bat
echo.
echo %CYAN%Backend server starting on http://localhost:8000%RESET%
echo %CYAN%API Documentation: http://localhost:8000/docs%RESET%
echo.
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
goto :eof

:start_frontend_only
echo %GREEN%Starting Frontend only (Vite)...%RESET%
cd /d %FRONTEND_DIR%
echo.
echo %CYAN%Frontend server starting on http://localhost:5173%RESET%
echo.
npm run dev
goto :eof

endlocal
