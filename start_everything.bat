@echo off
setlocal EnableDelayedExpansion
REM =============================================================================
REM GRACE - Hardened startup: self-heal first, run in chunks, ghost in parallel
REM Run from project root:  cd "path\to\grace-3.1--Aaron-new2"  then  start_everything.bat
REM Or call with full path:  "C:\...\grace-3.1--Aaron-new2\start_everything.bat"
REM =============================================================================
set "ROOT=%~dp0"
cd /d "%ROOT%"
set "BACKEND=%ROOT%backend"
set "SCRIPT=%BACKEND%\scripts\setup_gpu.py"

echo.
echo ===============================================================================
echo    GRACE - Hardened startup (preflight + chunks + ghost + self-learning)
echo ===============================================================================
echo.

cd /d "%ROOT%"

REM --- Phase 0a: Self-learning from last successful run ---
echo [Phase 0a] Self-learning (from last success)...
python startup_preflight.py --chunk 3
echo.

REM --- Phase 0: Self-first preflight (no venv) ---
echo [Phase 0] Self-heal before runtime...
python startup_preflight.py --chunk 0
if errorlevel 1 (
    echo [!!] Preflight chunk 0 failed.
    pause
    exit /b 1
)
echo.

REM --- Phase 0b: Apply startup knowledge from last run error ---
echo [Phase 0b] Startup knowledge (fix from last error)...
python startup_preflight.py --chunk 2
echo.

REM --- Phase 0c (optional): Deterministic scan + auto-fix ---
if defined GRACE_PREFLIGHT_FULL (
    echo [Phase 0c] Full preflight: deterministic scan...
    python startup_preflight.py --chunk 1
    echo.
)

REM --- Phase 1: GPU setup ---
echo [Phase 1] GPU / embedding device...
if not exist "%SCRIPT%" goto :phase1_skip
call "%BACKEND%\run_setup_gpu.bat"
cd /d "%ROOT%"
goto :phase1_done
:phase1_skip
echo [OK] GPU setup skipped (script not found).
:phase1_done
echo.

REM --- Phase 2: Staged runtime (1st 30s ahead, 2nd merges 15s behind) ---
echo [Phase 2] Staged runtime: 1st (backend) 30s ahead, 2nd (frontend) merges 15s behind...
call "%ROOT%start.bat" staged

REM --- Phase 3: Ghost - parallel watcher (real-time health check) ---
echo [Phase 3] Ghost watcher (parallel): monitoring backend health...
start /b "" python "%ROOT%startup_ghost.py" --timeout 90 --interval 10
echo    Ghost runs in background; if backend does not respond in 90s, next startup will apply fixes from knowledge.
echo.

echo ===============================================================================
echo    GRACE is starting.
echo    Backend:     http://localhost:8000
echo    Frontend:    http://localhost:5173
echo    Ops Console: http://localhost:8765
echo ===============================================================================
echo.
echo   Look for two CMD windows: "GRACE Backend" and "GRACE Frontend".
echo   Keep them open. If you don't see them, check the taskbar or run from project folder:
echo     cd "C:\Users\aaron\Desktop\grace-3.1--Aaron-new2"
echo     start_everything.bat
echo.
endlocal
