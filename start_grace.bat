@echo off
REM ==========================================
REM  Grace Autonomous AI System - Windows
REM ==========================================

echo.
echo ==========================================
echo   Grace Autonomous AI System
echo ==========================================
echo.

cd /d "%~dp0"

REM Check Python
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+
    pause
    exit /b 1
)

REM Check Node
node --version 2>nul
if errorlevel 1 (
    echo [WARN] Node.js not found - frontend won't build
)

REM Setup mode
if "%1"=="--setup" goto setup
goto start

:setup
echo.
echo [SETUP] First-time setup...
echo.

REM Install Python dependencies
echo Installing Python dependencies...
cd backend
pip install -r requirements.txt
cd ..

REM Install frontend
echo Building frontend...
cd frontend
call npm install
call npm run build
cd ..

REM Pull Ollama models (if installed)
where ollama >nul 2>&1
if not errorlevel 1 (
    echo Pulling AI models...
    ollama pull qwen2.5-coder:7b
    ollama pull deepseek-r1:7b
    ollama pull qwen2.5:7b
    ollama pull nomic-embed-text
    echo Models pulled!
) else (
    echo [WARN] Ollama not installed. Install from https://ollama.com
)

echo.
echo Setup complete! Run: start_grace.bat
echo.
pause
exit /b 0

:start
echo.
echo Starting Grace...
echo.

REM Load env
cd backend

REM Start backend
echo Starting backend on http://localhost:8000 ...
echo.
echo Quick commands:
echo   Smoke test:  curl http://localhost:8000/api/audit/test/smoke
echo   Logic test:  curl http://localhost:8000/api/audit/test/logic
echo   Health:      curl http://localhost:8000/health
echo.

python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
