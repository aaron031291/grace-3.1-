@echo off
REM Run DB connection test from anywhere. Uses Grace project backend.
set GRACE_BACKEND=C:\Users\aaron\Desktop\grace-3.1--Aaron-new2\backend
cd /d "%GRACE_BACKEND%"
if not exist "venv_gpu\Scripts\python.exe" (
    echo ERROR: venv_gpu not found in %GRACE_BACKEND%
    pause
    exit /b 1
)
"venv_gpu\Scripts\python.exe" "scripts\test_postgres_connection.py"
pause
exit /b %ERRORLEVEL%
