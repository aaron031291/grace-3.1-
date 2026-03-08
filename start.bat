@echo off
setlocal EnableDelayedExpansion
REM =============================================================================
REM GRACE - One script: backend, frontend, Qdrant, or everything
REM Usage:  start.bat   OR   start.bat [ full | staged | backend | frontend | all | services ]
REM   (no args)  - FULL: Qdrant + Backend + Frontend (one command for everything)
REM   full       - Same: Qdrant, then backend + frontend (2s between)
REM   staged     - Preflight-friendly: 1st runtime (backend) 30s ahead, 2nd (frontend) starts then merges 15s behind
REM   backend    - FastAPI only http://localhost:8000
REM   frontend   - Vite only http://localhost:5173
REM   all        - Backend + Frontend (no Qdrant step)
REM   services   - Qdrant only (Docker or Cloud check)
REM PowerShell:  .\start.bat   or   .\start.bat full
REM =============================================================================

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "MODE=%~1"
if "%MODE%"=="" set "MODE=full"

echo.
echo ===============================================================================
echo    GRACE
echo ===============================================================================
echo.

if /i "%MODE%"=="backend"   goto backend
if /i "%MODE%"=="frontend"  goto frontend
if /i "%MODE%"=="all"       goto all
if /i "%MODE%"=="services"  goto services
if /i "%MODE%"=="full"      goto full
if /i "%MODE%"=="staged"    goto staged
echo Unknown: %MODE%. Use: start.bat   or   start.bat [ full ^| staged ^| backend ^| frontend ^| all ^| services ]
exit /b 1

:full
REM One command: Qdrant + Backend + Frontend (GPU venv, memory, everything)
echo Starting GRACE (Qdrant + Backend + Frontend)...
call :ensure_qdrant
echo.
echo Starting backend and frontend...
if exist "%BACKEND%\venv_gpu\Scripts\activate.bat" (
    start "GRACE Backend"  cmd /k "cd /d %BACKEND% && call venv_gpu\Scripts\activate.bat && python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000"
) else (
    start "GRACE Backend"  cmd /k "cd /d %BACKEND% && call venv\Scripts\activate.bat && python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000"
)
timeout /t 2 /nobreak >nul
start "GRACE Frontend" cmd /k "cd /d %FRONTEND% && npm run dev"
echo.
echo   Backend:  http://localhost:8000   Frontend:  http://localhost:5173
echo   Qdrant:   http://localhost:6333   (if local)
echo.
echo   Two CMD windows should be open: "GRACE Backend" and "GRACE Frontend".
echo   Keep them open. Closing them will stop the servers.
goto end

:staged
REM 1st runtime 30s ahead, 2nd run starts then merges 15s behind (preflight-friendly)
echo Starting GRACE (staged: 1st runtime 30s ahead, 2nd merges 15s behind)...
call :ensure_qdrant
echo.
echo [1st runtime] Backend starting (30s head start)...
if exist "%BACKEND%\venv_gpu\Scripts\activate.bat" (
    start "GRACE Backend"  cmd /k "cd /d %BACKEND% && call venv_gpu\Scripts\activate.bat && python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000"
) else (
    start "GRACE Backend"  cmd /k "cd /d %BACKEND% && call venv\Scripts\activate.bat && python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000"
)
echo   Waiting 30s so backend gets head start...
timeout /t 30 /nobreak >nul
echo [2nd run] Frontend starting (merges 15s behind)...
start "GRACE Frontend" cmd /k "cd /d %FRONTEND% && npm run dev"
echo   Waiting 15s for merge...
timeout /t 15 /nobreak >nul
echo.
echo   Merge complete. Backend: http://localhost:8000   Frontend: http://localhost:5173
echo   Qdrant: http://localhost:6333 (if local)
echo.
echo   Two CMD windows should be open: "GRACE Backend" and "GRACE Frontend".
echo   Keep them open. Closing them will stop the servers.
goto end

:ensure_qdrant
REM Start Qdrant if needed (Cloud = skip; Docker = start)
if exist "%BACKEND%\.env" (
    findstr /b /c:"QDRANT_URL=https" "%BACKEND%\.env" >nul 2>&1
    if not errorlevel 1 (
        echo [OK] Qdrant Cloud configured.
        exit /b 0
    )
)
docker info >nul 2>&1
if errorlevel 1 (
    echo [WARN] Docker not running. Backend will use Qdrant Cloud if set in backend\.env
    exit /b 0
)
docker ps --filter "name=qdrant" --format "{{.Names}}" 2>nul | findstr /r "." >nul
if not errorlevel 1 (
    echo [OK] Qdrant already running.
    exit /b 0
)
echo Starting Qdrant (vector DB)...
docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant:latest 2>nul || docker start qdrant 2>nul
echo Waiting for Qdrant (5s)...
timeout /t 5 /nobreak >nul
exit /b 0

:services
REM Qdrant only
call :ensure_qdrant
goto end

:all
echo Starting backend and frontend...
if exist "%BACKEND%\venv_gpu\Scripts\activate.bat" (
    start "GRACE Backend"  cmd /k "cd /d %BACKEND% && call venv_gpu\Scripts\activate.bat && python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000"
) else (
    start "GRACE Backend"  cmd /k "cd /d %BACKEND% && call venv\Scripts\activate.bat && python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000"
)
timeout /t 2 /nobreak >nul
start "GRACE Frontend" cmd /k "cd /d %FRONTEND% && npm run dev"
echo.
echo   Backend:  http://localhost:8000   Frontend:  http://localhost:5173
goto end

:backend
cd /d "%BACKEND%"
if exist "venv_gpu\Scripts\activate.bat" (
    call venv_gpu\Scripts\activate.bat
    echo Backend GPU venv - http://localhost:8000  Docs - http://localhost:8000/docs
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo Backend - http://localhost:8000  Docs - http://localhost:8000/docs
) else (
    echo Backend venv not found. Run setup_backend.bat first.
    pause
    exit /b 1
)
echo.
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
goto end

:frontend
cd /d "%FRONTEND%"
echo Frontend: http://localhost:5173
echo.
npm run dev
goto end

:end
echo.
endlocal
